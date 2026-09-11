"""
Shared helpers for OpenAI Responses API calls.
"""
import copy as _copy
import hashlib as _hashlib
import json as _json
import logging as _logging
import math as _math
import os as _os
import random as _random
import re as _re
import threading as _threading
import time as _time
import uuid as _uuid
from typing import Any as _Any
from typing import Dict as _Dict
from typing import List as _List
from typing import Literal as _Literal
from typing import Union as _Union

import requests as _requests
from pydantic import Field as _Field
from pydantic import ValidationError as _ValidationError
from pydantic import create_model as _create_model

from . import ai_attachments as _ai_attachments


_LOG = _logging.getLogger(__name__)
_LOCK = _threading.Lock()
_SUCCESS_STATS = {}
_UNSET = object()
WEB_SEARCH_SOURCES_KEY = "web_search_sources"
_JSON_TYPE_MAP = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
    "null": type(None),
}


_OPENAI_SCHEMA_KEYS = {
    "$defs",
    "additionalProperties",
    "anyOf",
    "description",
    "enum",
    "exclusiveMaximum",
    "exclusiveMinimum",
    "items",
    "maximum",
    "maxItems",
    "maxLength",
    "minimum",
    "minItems",
    "minLength",
    "multipleOf",
    "properties",
    "required",
    "title",
    "type",
}

_LEGACY_RESPONSES_PARAM_MAP = {
    "max_tokens": "max_output_tokens",
    "max_completion_tokens": "max_output_tokens",
}

_IGNORED_RESPONSES_PARAMS = {
    "seed": "Responses does not support deterministic seeding; remove 'seed' from the definition.",
}

_INCOMPATIBLE_RESPONSES_PARAMS = {
    "n": "Responses returns one generation per request; submit separate requests instead.",
    "response_format": "Use the extract.ai output schema; Responses structured output is sent through text.format.",
}

_RATE_LIMIT_HEADERS = (
    "x-ratelimit-limit-requests",
    "x-ratelimit-limit-tokens",
    "x-ratelimit-remaining-requests",
    "x-ratelimit-remaining-tokens",
    "x-ratelimit-reset-requests",
    "x-ratelimit-reset-tokens",
    "retry-after",
    "x-request-id",
)

_USAGE_TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cached_input_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
    "cache_write_input_tokens",
    "cache_write_tokens",
)
_USAGE_DETAIL_FIELDS = {
    "input_tokens_details": (
        "cached_tokens",
        "cache_write_tokens",
        "cache_creation_tokens",
        "audio_tokens",
        "image_tokens",
        "text_tokens",
    ),
    "output_tokens_details": (
        "reasoning_tokens",
        "audio_tokens",
        "text_tokens",
        "accepted_prediction_tokens",
        "rejected_prediction_tokens",
    ),
}


def _diagnostic_identifier(value, api_key=None):
    if not isinstance(value, str) or not _re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", value):
        return None
    if (
        (api_key and api_key in value)
        or _re.search(r"(?:sk-|Bearer|base64)", value, _re.IGNORECASE)
        or _re.search(r"[A-Za-z0-9+/]{64,}", value)
    ):
        return None
    return value


def _token_count(value):
    return value if type(value) is int and 0 <= value <= 2**63 - 1 else None


def _diagnostic_hash(value, api_key):
    if isinstance(value, str) and value != api_key and _re.fullmatch(r"[0-9a-f]{64}", value):
        return value
    return None


def _attachment_context(data, api_key):
    if not isinstance(data, _ai_attachments.PreparedRecord):
        return []
    sources = []
    for attachment in data.attachments[:_ai_attachments.MAX_ATTACHMENTS]:
        identity = attachment.identity()
        source_id = _diagnostic_identifier(identity.get("id"), api_key)
        media_type = identity.get("media_type")
        sources.append({
            "id": (
                source_id
                if source_id and _re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", source_id)
                else None
            ),
            "media_type": media_type if isinstance(media_type, str) and media_type in {
                "application/pdf", "image/png", "image/jpeg", "image/webp"
            } else None,
            "sha256": _diagnostic_hash(identity.get("sha256"), api_key),
        })
    return sources


def _usage_number(value):
    if type(value) in (int, float) and 0 <= value <= 2**63 - 1 and _math.isfinite(value):
        return value
    return None


def _usage_context(body, api_key=None):
    usage = body.get("usage") if isinstance(body, dict) else None
    usage = usage if isinstance(usage, dict) else {}
    remaining = [64]

    def bounded_values(value, depth=0):
        if isinstance(value, dict):
            if depth >= 4:
                return None
            result = {}
            for key, item in value.items():
                if remaining[0] <= 0:
                    break
                if (
                    not isinstance(key, str)
                    or not _re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", key)
                    or (api_key and api_key in key)
                ):
                    continue
                remaining[0] -= 1
                result[key] = bounded_values(item, depth + 1)
            return result
        if isinstance(value, list):
            if depth >= 4:
                return None
            result = []
            for item in value[:16]:
                if remaining[0] <= 0:
                    break
                remaining[0] -= 1
                result.append(bounded_values(item, depth + 1))
            return result
        return _usage_number(value)

    result = bounded_values(usage)
    for name in _USAGE_TOKEN_FIELDS:
        result[name] = _usage_number(usage.get(name))
    for name, fields in _USAGE_DETAIL_FIELDS.items():
        details = usage.get(name)
        details = details if isinstance(details, dict) else {}
        safe_details = result.get(name)
        safe_details = safe_details if isinstance(safe_details, dict) else {}
        for field in fields:
            safe_details[field] = _usage_number(details.get(field))
        result[name] = safe_details
    return result


def _sanitize_error_text(message, api_key=None):
    if not isinstance(message, str) or not message:
        return ""
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    text = message[:4096]
    # Keep the explanation, not any echoed JSON request that follows it.
    structured = _re.search(r"""[\{\[]\s*["'\{\[]""", text)
    if structured:
        text = text[:structured.start()] + "[structured details omitted]"
    text = _re.sub(
        r"""(?i)data:[^\s,"'<>]{0,200},\s*[A-Za-z0-9+/_=-]*(?:\r?\n[A-Za-z0-9+/_=-]+)*""",
        "[binary data omitted]",
        text,
    )
    text = _re.sub(
        r"""(?i)\b(?:base64|file_data|image_data|binary_data)["']?[\s:=,]+["']?"""
        r"""[A-Za-z0-9+/_=-]+(?:\r?\n[A-Za-z0-9+/_=-]+)*""",
        "[binary data omitted]",
        text,
    )
    text = _re.sub(
        r"\b[A-Za-z0-9+/_-]{64,}={0,2}",
        "[binary data omitted]",
        text,
    )
    text = _re.sub(
        r"(?i)\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/\[\]=-]+",
        "[REDACTED]",
        text,
    )
    text = _re.sub(
        r"""(?i)(\b(?:[\w-]*api[_ -]?key|authorization|proxy-authorization|[\w-]*password|"""
        r"""[\w-]*secret(?:[_ -](?:access[_ -])?key)?|access[_-]?token|refresh[_-]?token|token)"""
        r"""\b(?:\s+provided)?["']?\s*[:=]\s*)"""
        r"""(?:"[^"]*"|'[^']*'|[^\s,;]+)""",
        r"\1[REDACTED]",
        text,
    )
    text = _re.sub(r"\bsk-[A-Za-z0-9_-]+", "[REDACTED]", text)
    text = _re.sub(
        r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",
        "[REDACTED]",
        text,
    )
    text = _re.sub(r"""https?://[^\s<>"']+""", "[URL omitted]", text)
    text = " ".join("".join(char if char.isprintable() else " " for char in text).split())
    return text[:509] + "..." if len(text) > 512 else text


def _provider_error_message(message, api_key=None):
    return _sanitize_error_text(message, api_key)


def _transport_error_message(error, api_key=None):
    message = _sanitize_error_text(str(error), api_key) or "Transport request failed."
    return f"OpenAI API error | transport: {message}"


def _incomplete_reason(body):
    details = body.get("incomplete_details") if isinstance(body, dict) else None
    reason = details.get("reason") if isinstance(details, dict) else None
    return reason if isinstance(reason, str) and reason in {"max_output_tokens", "content_filter"} else None


def _log_request_attempt(
    call_id, attempt, model, response, body, elapsed_seconds, outcome, api_key,
    request_key=None, attachments=(),
):
    body = body if isinstance(body, dict) else {}
    status = body.get("status")
    event = {
        "event": "openai_request_attempt",
        "call_id": call_id,
        "request_key": _diagnostic_hash(request_key, api_key),
        "attachments": list(attachments),
        "attempt": attempt,
        "requested_model": _diagnostic_identifier(model, api_key),
        "response_model": _diagnostic_identifier(body.get("model"), api_key),
        "response_id": _diagnostic_identifier(body.get("id"), api_key),
        "request_id": _diagnostic_identifier(
            _header(getattr(response, "headers", {}), "x-request-id"), api_key
        ),
        "response_status": status if isinstance(status, str) and status in {
            "completed", "incomplete", "failed", "cancelled", "queued", "in_progress"
        } else None,
        "status_code": _token_count(getattr(response, "status_code", None)),
        "incomplete_reason": _incomplete_reason(body),
        "elapsed_seconds": round(max(elapsed_seconds, 0), 3),
        "outcome": outcome,
        "usage": _usage_context(body, api_key),
    }
    _LOG.info("%s", _json.dumps(event, sort_keys=True))


def _truthy(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _response_json(response):
    try:
        return response.json()
    except Exception:
        return {}


def _header(headers, name):
    if not headers:
        return None
    return next(
        (value for key, value in headers.items() if str(key).lower() == name.lower()),
        None,
    )


def _int_header(headers, name):
    try:
        return int(headers.get(name))
    except (TypeError, ValueError):
        return None


def _parse_delay(value) -> float:
    if value in (None, ""):
        return None
    text = str(value).strip().lower()
    try:
        return max(float(text), 0)
    except ValueError:
        pass

    total = 0.0
    matched = False
    for amount, unit in _re.findall(r"(\d+(?:\.\d+)?)(ms|s|m|h)", text):
        matched = True
        amount = float(amount)
        if unit == "ms":
            total += amount / 1000
        elif unit == "s":
            total += amount
        elif unit == "m":
            total += amount * 60
        elif unit == "h":
            total += amount * 3600
    return total if matched else None


def _rate_limit_headers(response) -> dict:
    headers = getattr(response, "headers", {}) or {}
    return {
        name: _header(headers, name)
        for name in _RATE_LIMIT_HEADERS
        if _header(headers, name) is not None
    }


def _response_context(
    response,
    endpoint: str,
    model: str = None,
    attempt: int = None,
    elapsed_seconds: float = None,
    body=_UNSET,
    api_key: str = None,
) -> dict:
    if body is _UNSET:
        body = _response_json(response)
    error = body.get("error", {}) if isinstance(body, dict) else {}
    usage = _usage_context(body, api_key)
    input_details = usage["input_tokens_details"]
    headers = {
        name: _diagnostic_identifier(value, api_key)
        for name, value in _rate_limit_headers(response).items()
    }
    status_code = _token_count(getattr(response, "status_code", None))
    message = error.get("message", "") if isinstance(error, dict) else ""
    message = message if isinstance(message, str) else ""

    remaining_requests = headers.get("x-ratelimit-remaining-requests")
    remaining_tokens = headers.get("x-ratelimit-remaining-tokens")
    limit_family = None
    if status_code == 429 or "rate limit" in message.lower() or remaining_requests == "0" or remaining_tokens == "0":
        if remaining_requests == "0":
            limit_family = "requests_per_minute"
        elif remaining_tokens == "0":
            limit_family = "tokens_per_minute"
        elif "tokens per min" in message.lower():
            limit_family = "tokens_per_minute"
        elif "requests per min" in message.lower() or "requests per minute" in message.lower():
            limit_family = "requests_per_minute"
        else:
            limit_family = "rate_limit"

    return {
        "status_code": status_code,
        "endpoint": _diagnostic_identifier(endpoint, api_key),
        "model": _diagnostic_identifier(model, api_key),
        "attempt": attempt,
        "elapsed_seconds": round(elapsed_seconds, 3) if elapsed_seconds is not None else None,
        "message": _provider_error_message(message, api_key),
        "type": _diagnostic_identifier(error.get("type"), api_key) if isinstance(error, dict) else None,
        "code": _diagnostic_identifier(error.get("code"), api_key) if isinstance(error, dict) else None,
        "param": _diagnostic_identifier(error.get("param"), api_key) if isinstance(error, dict) else None,
        "request_id": headers.get("x-request-id"),
        "limit_family": limit_family,
        "retry_after": _parse_delay(headers.get("retry-after")),
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "total_tokens": usage["total_tokens"],
        "cached_tokens": input_details["cached_tokens"],
        "rate_limit_headers": {
            key: value
            for key, value in headers.items()
            if key != "retry-after"
        },
    }


def _should_retry(context: dict) -> bool:
    status_code = context.get("status_code")
    return status_code == 429 or status_code in (408, 409, 500, 502, 503, 504)


def _raise_for_fatal_error(context: dict) -> None:
    if str(context.get("code", "")).lower() == "model_not_found":
        raise ValueError(
            f"OpenAI model {context.get('model')!r} does not exist or is not accessible."
        )


def _error_message(context: dict) -> str:
    parts = ["OpenAI API error"]
    if context.get("status_code"):
        parts.append(f"status={context['status_code']}")
    if context.get("limit_family"):
        parts.append(f"limit={context['limit_family']}")
    if context.get("model"):
        parts.append(f"model={context['model']}")
    if context.get("request_id"):
        parts.append(f"request_id={context['request_id']}")
    if context.get("retry_after") is not None:
        parts.append(f"retry_after={context['retry_after']:.3g}s")
    if context.get("message"):
        parts.append(f"message={context['message']}")
    return " | ".join(parts)


def _log_api_error(context: dict, final: bool = False) -> None:
    log_context = {
        key: value
        for key, value in context.items()
        if value not in (None, "", {})
    }
    _LOG.log(
        _logging.ERROR if final else _logging.WARNING,
        "%s: %s",
        "Final OpenAI API error" if final else "Retrying OpenAI API error",
        _json.dumps(log_context, sort_keys=True),
    )


def _sleep_for_retry(
    context: dict,
    backoff_time: float,
) -> float:
    if context.get("retry_after") is not None:
        delay = min(context["retry_after"], 60)
    else:
        delay = min(backoff_time + _random.uniform(0, min(backoff_time, 1)), 60)

    _time.sleep(delay)
    return delay


def _success_log_every() -> int:
    try:
        return max(int(_os.getenv("WRANGLES_OPENAI_LOG_EVERY", "100")), 1)
    except ValueError:
        return 100


def _record_success(context: dict) -> None:
    if not (
        _truthy(_os.getenv("WRANGLES_OPENAI_LOG_RATE_LIMITS", ""))
        or _truthy(_os.getenv("WRANGLES_OPENAI_LOG_METRICS", ""))
    ):
        return
    headers = context.get("rate_limit_headers", {})
    key = (context.get("endpoint") or "unknown", context.get("model") or "unknown")
    remaining_requests = _int_header(headers, "x-ratelimit-remaining-requests")
    remaining_tokens = _int_header(headers, "x-ratelimit-remaining-tokens")

    with _LOCK:
        stats = _SUCCESS_STATS.setdefault(
            key,
            {
                "event": "openai_rate_limit_summary",
                "endpoint": context.get("endpoint"),
                "model": context.get("model"),
                "responses": 0,
                "min_remaining_requests": None,
                "min_remaining_tokens": None,
                "max_elapsed_seconds": None,
                "input_tokens": None,
                "output_tokens": None,
                "cached_tokens": None,
                "input_tokens_missing_responses": 0,
                "output_tokens_missing_responses": 0,
                "cached_tokens_missing_responses": 0,
                "usage_totals_partial": False,
                "cache_hit_responses": None,
                "latest_reset_requests": None,
                "latest_reset_tokens": None,
                "latest_request_id": None,
            },
        )
        stats["responses"] += 1
        if remaining_requests is not None:
            stats["min_remaining_requests"] = (
                remaining_requests
                if stats["min_remaining_requests"] is None
                else min(stats["min_remaining_requests"], remaining_requests)
            )
        if remaining_tokens is not None:
            stats["min_remaining_tokens"] = (
                remaining_tokens
                if stats["min_remaining_tokens"] is None
                else min(stats["min_remaining_tokens"], remaining_tokens)
            )
        if context.get("elapsed_seconds") is not None:
            stats["max_elapsed_seconds"] = (
                context["elapsed_seconds"]
                if stats["max_elapsed_seconds"] is None
                else max(stats["max_elapsed_seconds"], context["elapsed_seconds"])
            )
        for name in ("input_tokens", "output_tokens", "cached_tokens"):
            value = context.get(name)
            if value is None:
                stats[f"{name}_missing_responses"] += 1
                stats["usage_totals_partial"] = True
            else:
                stats[name] = value if stats[name] is None else stats[name] + value
        if context.get("cached_tokens") is not None:
            if stats["cache_hit_responses"] is None:
                stats["cache_hit_responses"] = 0
            if context["cached_tokens"] > 0:
                stats["cache_hit_responses"] += 1
        stats["latest_reset_requests"] = headers.get("x-ratelimit-reset-requests")
        stats["latest_reset_tokens"] = headers.get("x-ratelimit-reset-tokens")
        stats["latest_request_id"] = context.get("request_id")

        if stats["responses"] % _success_log_every() != 0:
            return

        log_stats = dict(stats)
    _LOG.info("%s", _json.dumps(log_stats, sort_keys=True))


def _handle_success(response, endpoint: str, model: str = None, elapsed_seconds: float = None) -> dict:
    context = _response_context(
        response,
        endpoint=endpoint,
        model=model,
        elapsed_seconds=elapsed_seconds,
    )
    _record_success(context)
    return context


def supports_reasoning(model: str) -> bool:
    """
    Return whether a model supports the Responses API reasoning parameter.
    """
    model = (model or "").lower()
    return model.startswith(("gpt-5", "o1", "o3", "o4"))


def supports_reasoning_effort(model: str, effort: str) -> bool:
    """
    Return whether a model supports a specific reasoning effort.

    OpenAI models before GPT-5.1 do not support ``none``. Pro models also
    require reasoning, so they cannot honor the package's no-reasoning
    default. Other effort/model compatibility is left to the provider because
    it varies more narrowly by model.
    """
    if not supports_reasoning(model):
        return False

    effort = str(effort or "").strip().lower()
    if effort != "none":
        return True

    model = (model or "").strip().lower()
    if "-pro" in model:
        return False

    version = _re.match(r"^gpt-5\.(\d+)(?:-|$)", model)
    return bool(version and int(version.group(1)) >= 1)


def supports_low_verbosity(model: str) -> bool:
    """
    Return whether a model supports low text verbosity.
    """
    model = (model or "").lower()
    return model.startswith("gpt-5")


def sanitize_schema(schema: dict, strict: bool = True) -> dict:
    """
    Convert a user schema to the subset required by OpenAI Structured Outputs.
    """
    schema = _json.loads(_json.dumps(schema))
    schema = {
        key: value
        for key, value in schema.items()
        if key in _OPENAI_SCHEMA_KEYS
    }

    schema_types = (
        schema.get("type")
        if isinstance(schema.get("type"), list)
        else [schema.get("type")]
    )

    if "object" in schema_types:
        properties = schema.get("properties", {})
        schema["required"] = list(properties.keys())
        schema["properties"] = {
            key: sanitize_schema(value, strict=strict)
            for key, value in properties.items()
        }
        additional = schema.get("additionalProperties", False)
        if strict:
            schema["additionalProperties"] = False
        elif isinstance(additional, dict):
            schema["additionalProperties"] = sanitize_schema(
                additional,
                strict=False,
            )
        else:
            schema["additionalProperties"] = bool(additional)

    if "array" in schema_types and isinstance(schema.get("items"), dict):
        schema["items"] = sanitize_schema(schema["items"], strict=strict)

    if isinstance(schema.get("anyOf"), list):
        schema["anyOf"] = [
            sanitize_schema(option, strict=strict)
            for option in schema["anyOf"]
            if isinstance(option, dict)
        ]

    return schema


def schema_type_to_python(schema: dict, name: str) -> _Any:
    if isinstance(schema.get("anyOf"), list):
        python_types = tuple(
            schema_type_to_python(option, f"{name}Option{index}")
            for index, option in enumerate(schema["anyOf"])
            if isinstance(option, dict)
        )
        if python_types:
            return _Union.__getitem__(python_types)

    if schema.get("enum"):
        return _Literal.__getitem__(tuple(schema["enum"]))

    schema_type = schema.get("type", "string")
    if isinstance(schema_type, list):
        python_types = tuple(
            schema_type_to_python({**schema, "type": item}, name)
            for item in schema_type
        )
        return _Union.__getitem__(python_types)

    if schema_type == "array":
        return _List[schema_type_to_python(schema.get("items", {}), f"{name}Item")]

    if schema_type == "object":
        properties = schema.get("properties")
        if isinstance(properties, dict) and properties:
            return build_response_model(f"{name}Model", schema)
        additional = schema.get("additionalProperties")
        value_type = (
            schema_type_to_python(additional, f"{name}Value")
            if isinstance(additional, dict)
            else _Any
        )
        return _Dict[str, value_type]

    return _JSON_TYPE_MAP.get(schema_type, _Any)


def build_response_model(name: str, schema: dict):
    properties = schema.get("properties", {})
    required = set(schema.get("required", properties))
    fields = {}
    constraint_map = {
        "minimum": "ge",
        "maximum": "le",
        "exclusiveMinimum": "gt",
        "exclusiveMaximum": "lt",
        "multipleOf": "multiple_of",
        "minLength": "min_length",
        "maxLength": "max_length",
        "minItems": "min_length",
        "maxItems": "max_length",
    }

    for field_name, schema in properties.items():
        field_type = schema_type_to_python(
            schema,
            str(field_name).title().replace(" ", ""),
        )
        field_kwargs = {
            "description": schema.get("description"),
        }
        for schema_key, field_key in constraint_map.items():
            if schema_key in schema:
                field_kwargs[field_key] = schema[schema_key]

        fields[field_name] = (
            field_type,
            _Field(... if field_name in required else None, **field_kwargs),
        )

    return _create_model(
        name,
        __config__={
            "extra": (
                "allow"
                if schema.get("additionalProperties") not in (None, False)
                else "forbid"
            )
        },
        **fields,
    )


def validate_structured_output(parsed: dict, schema: dict) -> dict:
    if schema.get("type") != "object":
        return parsed

    response_model = build_response_model(
        "ExtractAIResponse",
        schema,
    )
    return response_model.model_validate(parsed).model_dump()


def format_input_data(data: _Any) -> str:
    if isinstance(data, (dict, list)):
        return _json.dumps(data, ensure_ascii=False, default=str, indent=2)
    return str(data)


def _uses_web_search(payload: dict) -> bool:
    tools = payload.get("tools", [])
    if not isinstance(tools, list):
        return False
    return any(
        isinstance(tool, dict)
        and tool.get("type") in {"web_search", "web_search_preview"}
        for tool in tools
    )


def extract_web_search_sources(response_json: dict) -> list:
    """Return cited and consulted web URLs in stable response order."""
    annotation_titles = {}
    annotations = []
    output = response_json.get("output", [])
    if not isinstance(output, list):
        output = []

    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content_items = item.get("content", [])
        if not isinstance(content_items, list):
            continue
        for content in content_items:
            if not isinstance(content, dict):
                continue
            content_annotations = content.get("annotations", [])
            if not isinstance(content_annotations, list):
                continue
            for annotation in content_annotations:
                if (
                    not isinstance(annotation, dict)
                    or annotation.get("type") != "url_citation"
                ):
                    continue
                url = annotation.get("url")
                if not isinstance(url, str) or not url.strip():
                    continue
                url = url.strip()
                title = annotation.get("title")
                title = title.strip() if isinstance(title, str) else ""
                annotations.append((url, title))
                if title and url not in annotation_titles:
                    annotation_titles[url] = title

    sources = []
    positions = {}

    def add_source(url, title=""):
        if not isinstance(url, str) or not url.strip():
            return
        url = url.strip()
        title = title.strip() if isinstance(title, str) else ""
        title = title or annotation_titles.get(url, "")
        if url in positions:
            existing = sources[positions[url]]
            if not existing["title"] and title:
                existing["title"] = title
            return
        positions[url] = len(sources)
        sources.append({"title": title, "url": url})

    for item in output:
        if not isinstance(item, dict) or item.get("type") != "web_search_call":
            continue
        action = item.get("action")
        if not isinstance(action, dict):
            continue
        action_sources = action.get("sources", [])
        if isinstance(action_sources, list):
            for source in action_sources:
                if isinstance(source, dict):
                    add_source(source.get("url"), source.get("title", ""))
        add_source(action.get("url"), action.get("title", ""))

    for url, title in annotations:
        add_source(url, title)

    return sources


def error_result(
    required_fields: list,
    message: str,
    include_web_search_sources: bool = False,
) -> dict:
    result = {
        field: message
        for field in required_fields
    }
    if include_web_search_sources:
        result[WEB_SEARCH_SOURCES_KEY] = []
    return result


def extract_response_text(response_json: dict) -> str:
    if not isinstance(response_json, dict):
        raise ValueError("The API response was not a JSON object.")

    if response_json.get("error"):
        error = response_json["error"]
        if isinstance(error, dict):
            raise ValueError(_provider_error_message(error.get("message")) or "The API returned an error.")
        raise ValueError("The API returned an error.")

    if response_json.get("status") == "incomplete":
        reason = _incomplete_reason(response_json)
        if reason:
            raise ValueError(f"The model response was incomplete: {reason}.")
        raise ValueError("The model response was incomplete.")

    if response_json.get("output_text"):
        return response_json["output_text"]

    output = response_json.get("output")
    for item in output if isinstance(output, list) else []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        contents = item.get("content")
        for content in contents if isinstance(contents, list) else []:
            if not isinstance(content, dict):
                continue
            if content.get("type") == "output_text":
                return content.get("text", "")
            if content.get("type") == "refusal":
                raise ValueError("The model refused the request.")

    raise ValueError("Could not find 'output_text' in the API response.")


def prompt_cache_key(namespace: str, model: str, static_prefix: dict) -> str:
    """
    Identify the complete reusable request prefix, excluding row-level input.
    """
    stable_prefix = _json.dumps(
        static_prefix,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    digest = _hashlib.sha256(stable_prefix.encode("utf-8")).hexdigest()[:16]
    return f"{namespace}:{model}:{digest}"


def sanitize_request_params(params: dict) -> dict:
    """
    Translate known Chat Completions parameters and reject ambiguous ones.

    This compatibility layer is intentionally explicit and temporary. It emits
    warnings for every legacy parameter it consumes so definitions can be
    upgraded and the mappings removed later.
    """
    sanitized = _copy.deepcopy(params)

    for old_name, new_name in _LEGACY_RESPONSES_PARAM_MAP.items():
        if old_name not in sanitized:
            continue
        if new_name in sanitized:
            raise ValueError(
                f"Both legacy '{old_name}' and Responses '{new_name}' were provided."
            )
        sanitized[new_name] = sanitized.pop(old_name)
        _LOG.warning(
            "Mapped legacy OpenAI parameter '%s' to '%s'; update this extract.ai definition.",
            old_name,
            new_name,
        )

    for name, guidance in _IGNORED_RESPONSES_PARAMS.items():
        if name in sanitized:
            sanitized.pop(name)
            _LOG.warning(
                "Ignored legacy OpenAI parameter '%s': %s",
                name,
                guidance,
            )

    for name, guidance in _INCOMPATIBLE_RESPONSES_PARAMS.items():
        if name in sanitized:
            raise ValueError(
                f"OpenAI parameter '{name}' is not compatible with extract.ai Responses calls. "
                f"{guidance}"
            )

    return sanitized


def call_structured(
    data: _Any,
    api_key: str,
    payload: dict,
    url: str,
    timeout: int,
    retries: int,
    required_fields: list,
    request_key: str = None,
) -> dict:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    request_payload = _copy.deepcopy(payload)
    request_payload["input"] = [
        {
            "role": "user",
            "content": (
                data.content()
                if isinstance(data, _ai_attachments.PreparedRecord)
                else f"DATA:\n{format_input_data(data)}"
            ),
        }
    ]
    include_web_search_sources = _uses_web_search(request_payload)

    def failure(message: str, response_json: dict = None) -> dict:
        result = error_result(
            required_fields,
            message,
            include_web_search_sources=include_web_search_sources,
        )
        if include_web_search_sources and isinstance(response_json, dict):
            result[WEB_SEARCH_SOURCES_KEY] = extract_web_search_sources(response_json)
        return result

    call_id = _uuid.uuid4().hex
    attachment_context = _attachment_context(data, api_key)
    backoff_time = 1
    for attempt in range(retries + 1):
        response = None
        response_json = None
        context = {}
        elapsed_seconds = None
        outcome = "transport_error"
        started = _time.monotonic()
        try:
            try:
                response = _requests.post(
                    url=url,
                    headers=headers,
                    json=request_payload,
                    timeout=timeout,
                )
            except _requests.exceptions.Timeout:
                outcome = "timeout"
                if attempt >= retries:
                    return failure("Timed Out")
            except Exception as error:
                if attempt >= retries:
                    return failure(_transport_error_message(error, api_key))

            elapsed_seconds = _time.monotonic() - started
            if response is not None:
                outcome = "http_error" if not response.ok else "invalid_response"
                try:
                    response_json = response.json()
                except Exception:
                    pass
                context = _response_context(
                    response,
                    endpoint="responses",
                    model=request_payload.get("model"),
                    attempt=attempt + 1,
                    elapsed_seconds=elapsed_seconds,
                    body=response_json,
                    api_key=api_key,
                )
                # Usage belongs to the HTTP attempt, even if its output cannot be used.
                _record_success(context)

                if response.ok:
                    try:
                        if response_json is None:
                            outcome = "json_error"
                            raise ValueError("The API response was not valid JSON.")
                        if isinstance(response_json, dict):
                            if response_json.get("error"):
                                outcome = "api_error"
                            elif response_json.get("status") == "incomplete":
                                outcome = "incomplete"
                        output_text = extract_response_text(response_json)
                        outcome = "json_error"
                        parsed = _json.loads(output_text)
                        outcome = "schema_error"
                        if not isinstance(parsed, dict):
                            raise ValueError("Structured response was not a JSON object.")
                        schema = request_payload.get("text", {}).get("format", {}).get("schema", {})
                        validated = validate_structured_output(parsed, schema)
                        if include_web_search_sources:
                            validated[WEB_SEARCH_SOURCES_KEY] = extract_web_search_sources(
                                response_json
                            )
                        outcome = "success"
                        return validated
                    except (_json.JSONDecodeError, _ValidationError, ValueError, TypeError):
                        if attempt >= retries:
                            messages = {
                                "json_error": "The API response did not contain valid JSON.",
                                "schema_error": "Output did not match the requested schema.",
                                "incomplete": "The model response was incomplete.",
                                "api_error": "The API returned an error.",
                                "invalid_response": "The API did not return structured output.",
                            }
                            reason = _incomplete_reason(response_json)
                            if outcome == "incomplete" and reason:
                                messages[outcome] = f"The model response was incomplete: {reason}."
                            return failure(
                                f"Invalid structured response: {messages[outcome]}",
                                response_json=response_json,
                            )
                else:
                    _raise_for_fatal_error(context)
                    error_message = context.get("message", "")
                    if "Invalid schema" in error_message:
                        raise ValueError(
                            "The schema submitted for output is not valid. "
                            f"Provider guidance: {error_message}"
                        )
                    if "Incorrect API key" in error_message:
                        raise ValueError("API Key provided is missing or invalid.")
                    if (
                        isinstance(data, _ai_attachments.PreparedRecord)
                        and context.get("status_code") in {400, 404, 415, 422}
                    ):
                        raise ValueError(
                            f"OpenAI rejected the attachment request (HTTP {context['status_code']}). "
                            "Select a model that supports image/PDF inputs and structured Responses "
                            "output, and check the attachment format, size, and model context limits."
                            + (f" Provider guidance: {error_message}" if error_message else "")
                        )
                    if attempt >= retries or not _should_retry(context):
                        _log_api_error(context, final=True)
                        return failure(_error_message(context))
                    _log_api_error(context, final=False)
        finally:
            if elapsed_seconds is None:
                elapsed_seconds = _time.monotonic() - started
            _log_request_attempt(
                call_id,
                attempt + 1,
                request_payload.get("model"),
                response,
                response_json,
                elapsed_seconds,
                outcome,
                api_key,
                request_key,
                attachment_context,
            )

        if response is not None and not response.ok:
            _sleep_for_retry(context, backoff_time)
        else:
            _sleep_for_retry({}, backoff_time)
        backoff_time *= 2

    return failure("Failed")
