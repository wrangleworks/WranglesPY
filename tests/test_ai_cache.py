import concurrent.futures
import threading

import pytest

from wrangles import ai_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    ai_cache.clear()
    yield
    ai_cache.clear()


def _policy(**overrides):
    values = {
        "enabled": True,
        "ttl_seconds": 60,
        "max_entries": 10,
        "max_value_bytes": 10000,
        "single_flight": True,
        "log_every": 0,
    }
    values.update(overrides)
    return ai_cache.CachePolicy(**values)


def test_cache_key_is_stable_and_tenant_scoped():
    common = {
        "namespace": "extract.ai",
        "provider": "openai",
        "protocol": "responses",
        "static_request": {"model": "gpt-5.4-mini"},
        "data": '{"value":"12 VDC"}',
    }

    first = ai_cache.make_key(tenant_secret="key-a", **common)
    same = ai_cache.make_key(tenant_secret="key-a", **common)
    another_tenant = ai_cache.make_key(tenant_secret="key-b", **common)

    assert first == same
    assert first != another_tenant
    assert "key-a" not in first


def test_batch_deduplicates_rows_preserves_order_and_reuses_warm_cache():
    calls = []
    rows = ["alpha", "beta", "alpha"]

    def compute(row):
        calls.append(row)
        return {"value": row}

    kwargs = {
        "key_for": lambda row: f"key:{row}",
        "compute": compute,
        "cacheable": lambda result: True,
        "max_workers": 3,
        "policy": _policy(),
    }
    first = ai_cache.execute_batch(rows, **kwargs)
    second = ai_cache.execute_batch(rows, **kwargs)

    assert first == [
        {"value": "alpha"},
        {"value": "beta"},
        {"value": "alpha"},
    ]
    assert second == first
    assert sorted(calls) == ["alpha", "beta"]
    assert ai_cache.stats()["entries"] == 2
    assert ai_cache.stats()["hits"] == 2


def test_cached_results_are_defensive_copies():
    policy = _policy()
    first = ai_cache.get_or_compute(
        "key",
        lambda: {"items": ["original"]},
        policy=policy,
        cacheable=lambda result: True,
    )
    first["items"].append("mutated")
    second = ai_cache.get_or_compute(
        "key",
        lambda: pytest.fail("cache miss"),
        policy=policy,
        cacheable=lambda result: True,
    )

    assert second == {"items": ["original"]}


def test_errors_and_oversized_values_are_not_cached():
    calls = []
    error_policy = _policy()

    for _ in range(2):
        ai_cache.get_or_compute(
            "error",
            lambda: calls.append("error") or {"value": "Timed Out"},
            policy=error_policy,
            cacheable=lambda result: False,
        )

    large_policy = _policy(max_value_bytes=10)
    for _ in range(2):
        ai_cache.get_or_compute(
            "large",
            lambda: calls.append("large") or {"value": "too large"},
            policy=large_policy,
            cacheable=lambda result: True,
        )

    assert calls == ["error", "error", "large", "large"]
    assert ai_cache.stats()["skipped_error"] == 2
    assert ai_cache.stats()["skipped_large"] == 2


def test_ttl_and_lru_limits(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(ai_cache._time, "monotonic", lambda: now[0])
    policy = _policy(ttl_seconds=5, max_entries=2)

    for key in ("one", "two", "three"):
        ai_cache.get_or_compute(
            key,
            lambda key=key: {"value": key},
            policy=policy,
            cacheable=lambda result: True,
        )
    assert ai_cache.stats()["entries"] == 2
    assert ai_cache.stats()["evictions"] == 1

    now[0] = 106.0
    result = ai_cache.get_or_compute(
        "two",
        lambda: {"value": "refreshed"},
        policy=policy,
        cacheable=lambda result: True,
    )
    assert result == {"value": "refreshed"}
    assert ai_cache.stats()["expired"] == 2


def test_single_flight_coalesces_concurrent_callers():
    started = threading.Event()
    release = threading.Event()
    calls = []
    policy = _policy()

    def compute():
        calls.append("call")
        started.set()
        release.wait(2)
        return {"value": "done"}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(
            ai_cache.get_or_compute,
            "shared",
            compute,
            policy=policy,
            cacheable=lambda result: True,
        )
        assert started.wait(1)
        second = executor.submit(
            ai_cache.get_or_compute,
            "shared",
            compute,
            policy=policy,
            cacheable=lambda result: True,
        )
        for _ in range(100):
            if ai_cache.stats()["coalesced"] == 1:
                break
            threading.Event().wait(0.01)
        assert ai_cache.stats()["coalesced"] == 1
        release.set()

    assert first.result() == {"value": "done"}
    assert second.result() == {"value": "done"}
    assert calls == ["call"]
    assert ai_cache.stats()["coalesced"] == 1


def test_cache_can_be_disabled_per_call_or_environment(monkeypatch):
    config = {
        "enabled": True,
        "ttl_seconds": 60,
        "max_entries": 10,
        "max_value_bytes": 1000,
    }

    assert ai_cache.resolve_policy(config, enabled=False).enabled is False

    monkeypatch.setenv("WRANGLES_EXTRACT_AI_CACHE_ENABLED", "false")
    assert ai_cache.resolve_policy(config).enabled is False

    monkeypatch.setenv("WRANGLES_EXTRACT_AI_CACHE_ENABLED", "sometimes")
    with pytest.raises(ValueError, match="must be true or false"):
        ai_cache.resolve_policy(config)
