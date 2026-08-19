"""
Bounded in-memory cache and duplicate suppression for AI-backed wrangles.

Only hashed request identities and successful result values are retained. Raw
inputs, prompts, and API credentials are never stored in cache keys or logs.
"""
import copy as _copy
import hashlib as _hashlib
import json as _json
import logging as _logging
import os as _os
import threading as _threading
import time as _time
from collections import OrderedDict as _OrderedDict
from concurrent import futures as _futures
from dataclasses import dataclass as _dataclass
from typing import Callable as _Callable


_LOG = _logging.getLogger(__name__)
_LOCK = _threading.Lock()
_CACHE = _OrderedDict()
_INFLIGHT = {}
_STATS = {
    "hits": 0,
    "misses": 0,
    "coalesced": 0,
    "stores": 0,
    "expired": 0,
    "evictions": 0,
    "skipped_large": 0,
    "skipped_error": 0,
}


@_dataclass(frozen=True)
class CachePolicy:
    enabled: bool
    ttl_seconds: float
    max_entries: int
    max_value_bytes: int
    single_flight: bool
    log_every: int


class _Flight:
    def __init__(self):
        self.event = _threading.Event()
        self.result = None
        self.exception = None


def _env_bool(name: str, default: bool) -> bool:
    value = _os.getenv(name)
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false.")


def _env_number(name: str, default, converter):
    value = _os.getenv(name)
    if value is None:
        return default
    try:
        return converter(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a valid {converter.__name__}.") from exc


def resolve_policy(
    config: dict,
    *,
    enabled: bool = None,
    ttl_seconds: float = None,
) -> CachePolicy:
    """Resolve config, per-call overrides, and operational environment switches."""
    config = config or {}
    configured_enabled = config.get("enabled", True)
    configured_single_flight = config.get("single_flight", True)
    if not isinstance(configured_enabled, bool):
        raise ValueError("extract_ai.cache.enabled must be true or false.")
    if not isinstance(configured_single_flight, bool):
        raise ValueError("extract_ai.cache.single_flight must be true or false.")
    resolved_enabled = (
        enabled
        if enabled is not None
        else configured_enabled
    )
    resolved_enabled = _env_bool(
        "WRANGLES_EXTRACT_AI_CACHE_ENABLED",
        resolved_enabled,
    )
    resolved_ttl = (
        ttl_seconds
        if ttl_seconds is not None
        else config.get("ttl_seconds", 3600)
    )
    resolved_ttl = _env_number(
        "WRANGLES_EXTRACT_AI_CACHE_TTL_SECONDS",
        resolved_ttl,
        float,
    )
    max_entries = _env_number(
        "WRANGLES_EXTRACT_AI_CACHE_MAX_ENTRIES",
        config.get("max_entries", 512),
        int,
    )
    max_value_bytes = _env_number(
        "WRANGLES_EXTRACT_AI_CACHE_MAX_VALUE_BYTES",
        config.get("max_value_bytes", 65536),
        int,
    )
    single_flight = _env_bool(
        "WRANGLES_EXTRACT_AI_CACHE_SINGLE_FLIGHT",
        configured_single_flight,
    )
    log_every = _env_number(
        "WRANGLES_EXTRACT_AI_CACHE_LOG_EVERY",
        config.get("log_every", 100),
        int,
    )

    if not isinstance(resolved_enabled, bool):
        raise ValueError("cache must be true or false.")
    if (
        not isinstance(resolved_ttl, (int, float))
        or isinstance(resolved_ttl, bool)
        or resolved_ttl <= 0
    ):
        raise ValueError("cache_ttl must be a positive number of seconds.")
    if not isinstance(max_entries, int) or isinstance(max_entries, bool) or max_entries < 0:
        raise ValueError("WRANGLES_EXTRACT_AI_CACHE_MAX_ENTRIES must be non-negative.")
    if (
        not isinstance(max_value_bytes, int)
        or isinstance(max_value_bytes, bool)
        or max_value_bytes < 0
    ):
        raise ValueError("WRANGLES_EXTRACT_AI_CACHE_MAX_VALUE_BYTES must be non-negative.")
    if not isinstance(log_every, int) or isinstance(log_every, bool) or log_every < 0:
        raise ValueError("WRANGLES_EXTRACT_AI_CACHE_LOG_EVERY must be non-negative.")

    return CachePolicy(
        enabled=resolved_enabled and max_entries > 0 and max_value_bytes > 0,
        ttl_seconds=float(resolved_ttl),
        max_entries=max_entries,
        max_value_bytes=max_value_bytes,
        single_flight=single_flight,
        log_every=log_every,
    )


def _canonical_bytes(value) -> bytes:
    return _json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def make_key(
    *,
    namespace: str,
    provider: str,
    protocol: str,
    tenant_secret: str,
    static_request: dict,
    data,
) -> str:
    """Create a privacy-preserving identity for one effective AI request."""
    tenant_hash = _hashlib.sha256(
        str(tenant_secret).encode("utf-8")
    ).hexdigest()
    material = {
        "version": 1,
        "namespace": namespace,
        "provider": provider,
        "protocol": protocol,
        "tenant": tenant_hash,
        "request": static_request,
        "data": data,
    }
    return _hashlib.sha256(_canonical_bytes(material)).hexdigest()


def _prune_expired(now: float) -> None:
    expired_keys = [
        key
        for key, (expires_at, _, _) in _CACHE.items()
        if expires_at <= now
    ]
    for key in expired_keys:
        _CACHE.pop(key, None)
        _STATS["expired"] += 1


def _store(key: str, value, policy: CachePolicy) -> bool:
    try:
        value_size = len(_canonical_bytes(value))
    except (TypeError, ValueError):
        return False
    if value_size > policy.max_value_bytes:
        with _LOCK:
            _STATS["skipped_large"] += 1
        return False

    with _LOCK:
        _CACHE[key] = (
            _time.monotonic() + policy.ttl_seconds,
            _copy.deepcopy(value),
            value_size,
        )
        _CACHE.move_to_end(key)
        _STATS["stores"] += 1
        while len(_CACHE) > policy.max_entries:
            _CACHE.popitem(last=False)
            _STATS["evictions"] += 1
    return True


def _maybe_log(policy: CachePolicy) -> None:
    if policy.log_every <= 0:
        return
    with _LOCK:
        operations = _STATS["hits"] + _STATS["misses"]
        if operations == 0 or operations % policy.log_every:
            return
        payload = {
            "event": "extract_ai_result_cache",
            **_STATS,
            "entries": len(_CACHE),
            "inflight": len(_INFLIGHT),
        }
    _LOG.info(_json.dumps(payload, sort_keys=True))


def get_or_compute(
    key: str,
    compute: _Callable,
    *,
    policy: CachePolicy,
    cacheable: _Callable,
    deadline_at: float = None,
):
    """Return a cached value or compute it once across concurrent callers."""
    if not policy.enabled:
        return compute()

    owner = True
    flight = None
    cached = None
    found = False
    with _LOCK:
        _prune_expired(_time.monotonic())
        entry = _CACHE.get(key)
        if entry is not None:
            _CACHE.move_to_end(key)
            _STATS["hits"] += 1
            cached = _copy.deepcopy(entry[1])
            found = True
        else:
            _STATS["misses"] += 1
            if policy.single_flight:
                flight = _INFLIGHT.get(key)
                if flight is None:
                    flight = _Flight()
                    _INFLIGHT[key] = flight
                else:
                    owner = False
                    _STATS["coalesced"] += 1

    if found:
        _maybe_log(policy)
        return cached

    if not owner:
        wait_timeout = None
        if deadline_at is not None:
            wait_timeout = max(deadline_at - _time.monotonic(), 0)
        if not flight.event.wait(wait_timeout):
            return compute()
        if flight.exception is not None:
            raise flight.exception
        _maybe_log(policy)
        return _copy.deepcopy(flight.result)

    try:
        result = compute()
        if cacheable(result):
            _store(key, result, policy)
        else:
            with _LOCK:
                _STATS["skipped_error"] += 1
        if flight is not None:
            flight.result = _copy.deepcopy(result)
        return result
    except Exception as exc:
        if flight is not None:
            flight.exception = exc
        raise
    finally:
        if flight is not None:
            flight.event.set()
            with _LOCK:
                _INFLIGHT.pop(key, None)
        _maybe_log(policy)


def execute_batch(
    input_rows: list,
    *,
    key_for: _Callable,
    compute: _Callable,
    cacheable: _Callable,
    max_workers: int,
    policy: CachePolicy,
    deadline_at: float = None,
) -> list:
    """Execute rows in order while deduplicating identical effective requests."""
    if not input_rows:
        return []

    if not policy.enabled:
        with _futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            return list(executor.map(compute, input_rows))

    grouped = _OrderedDict()
    for index, row in enumerate(input_rows):
        key = key_for(row)
        group = grouped.setdefault(key, {"row": row, "indices": []})
        group["indices"].append(index)

    results = [None] * len(input_rows)
    worker_count = min(max_workers, len(grouped))
    with _futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_groups = {}
        for key, group in grouped.items():
            row = group["row"]
            future = executor.submit(
                get_or_compute,
                key,
                lambda row=row: compute(row),
                policy=policy,
                cacheable=cacheable,
                deadline_at=deadline_at,
            )
            future_groups[future] = group

        for future, group in future_groups.items():
            result = future.result()
            for index in group["indices"]:
                results[index] = _copy.deepcopy(result)

    return results


def clear() -> None:
    """Clear all cached values, in-flight bookkeeping, and counters."""
    with _LOCK:
        _CACHE.clear()
        _INFLIGHT.clear()
        for key in _STATS:
            _STATS[key] = 0


def stats() -> dict:
    """Return cache counters without exposing cache keys or values."""
    with _LOCK:
        return {
            **_STATS,
            "entries": len(_CACHE),
            "inflight": len(_INFLIGHT),
            "value_bytes": sum(entry[2] for entry in _CACHE.values()),
        }
