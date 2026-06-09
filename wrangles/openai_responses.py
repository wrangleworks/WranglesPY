"""
Shared helpers for OpenAI Responses API calls.
"""
import copy as _copy
import hashlib as _hashlib
import json as _json
import logging as _logging
import os as _os
import random as _random
import re as _re
import threading as _threading
import time as _time
from typing import Any as _Any
from typing import Dict as _Dict
from typing import List as _List
from typing import Literal as _Literal
from typing import Union as _Union

import requests as _requests
from pydantic import Field as _Field
from pydantic import ValidationError as _ValidationError
from pydantic import create_model as _create_model


_LOG = _logging.getLogger(__name__)
_LOCK = _threading.Lock()
_SUCCESS_STATS = {}
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

_UNSUPPORTED_RESPONSES_PARAMS = {
    "seed",
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
    return headers.get(name) or headers.get(name.upper()) or headers.get(name.lower())


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


def _response_context(response, endpoint: str, model: str = None, attempt: int = None, elapsed_seconds: float = None) -> dict:
    body = _response_json(response)
    error = body.get("error", {}) if isinstance(body, dict) else {}
    headers = _rate_limit_headers(response)
    status_code = getattr(response, "status_code", None)
    message = error.get("message", "") if isinstance(error, dict) else ""

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
        "endpoint": endpoint,
        "model": model,
        "attempt": attempt,
        "elapsed_seconds": round(elapsed_seconds, 3) if elapsed_seconds is not None else None,
        "message": message,
        "type": error.get("type") if isinstance(error, dict) else None,
        "code": error.get("code") if isinstance(error, dict) else None,
        "param": error.get("param") if isinstance(error, dict) else None,
        "request_id": headers.get("x-request-id"),
        "limit_family": limit_family,
        "retry_after": _parse_delay(headers.get("retry-after")),
        "rate_limit_headers": {
            key: value
            for key, value in headers.items()
            if key != "retry-after"
        },
    }


def _should_retry(context: dict) -> bool:
    status_code = context.get("status_code")
    return status_code == 429 or status_code in (408, 409, 500, 502, 503, 504)


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


def _sleep_for_retry(context: dict, backoff_time: float) -> float:
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
    if not _truthy(_os.getenv("WRANGLES_OPENAI_LOG_RATE_LIMITS", "")):
        return
    headers = context.get("rate_limit_headers", {})
    if not headers:
        return

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
                "max_elapsed_seconds": 0,
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
            stats["max_elapsed_seconds"] = max(stats["max_elapsed_seconds"], context["elapsed_seconds"])
        stats["latest_reset_requests"] = headers.get("x-ratelimit-reset-requests")
        stats["latest_reset_tokens"] = headers.get("x-ratelimit-reset-tokens")
        stats["latest_request_id"] = context.get("request_id")

        if stats["responses"] % _success_log_every() != 0:
            return

        log_stats = {
            stat_key: value
            for stat_key, value in stats.items()
            if value not in (None, "", {})
        }
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


def supports_low_verbosity(model: str) -> bool:
    """
    Return whether a model supports low text verbosity.
    """
    model = (model or "").lower()
    return model.startswith("gpt-5")


def sanitize_schema(schema: dict) -> dict:
    """
    Convert a user schema to the subset required by OpenAI Structured Outputs.
    """
    schema = _json.loads(_json.dumps(schema))
    schema = {
        key: value
        for key, value in schema.items()
        if key in _OPENAI_SCHEMA_KEYS
    }

    if schema.get("type") == "object":
        properties = schema.get("properties", {})
        schema["required"] = list(properties.keys())
        schema["additionalProperties"] = False
        schema["properties"] = {
            key: sanitize_schema(value)
            for key, value in properties.items()
        }

    if schema.get("type") == "array" and isinstance(schema.get("items"), dict):
        schema["items"] = sanitize_schema(schema["items"])

    if isinstance(schema.get("anyOf"), list):
        schema["anyOf"] = [
            sanitize_schema(option)
            for option in schema["anyOf"]
            if isinstance(option, dict)
        ]

    return schema


def schema_type_to_python(schema: dict, name: str) -> _Any:
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
            return build_response_model(f"{name}Model", properties)
        return _Dict[str, _Any]

    return _JSON_TYPE_MAP.get(schema_type, _Any)


def build_response_model(name: str, properties: dict):
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
            _Field(..., **field_kwargs),
        )

    return _create_model(
        name,
        __config__={"extra": "forbid"},
        **fields,
    )


def validate_structured_output(parsed: dict, schema: dict) -> dict:
    if schema.get("type") != "object":
        return parsed

    response_model = build_response_model(
        "ExtractAIResponse",
        schema.get("properties", {}),
    )
    return response_model.model_validate(parsed).model_dump()


def format_input_data(data: _Any) -> str:
    if isinstance(data, (dict, list)):
        return _json.dumps(data, ensure_ascii=False, default=str, indent=2)
    return str(data)


def error_result(required_fields: list, message: str) -> dict:
    return {
        field: message
        for field in required_fields
    }


def extract_response_text(response_json: dict) -> str:
    if response_json.get("error"):
        error = response_json["error"]
        if isinstance(error, dict):
            raise ValueError(error.get("message", "The API returned an error."))
        raise ValueError(str(error))

    if response_json.get("status") == "incomplete":
        details = response_json.get("incomplete_details") or {}
        reason = details.get("reason") if isinstance(details, dict) else None
        if reason:
            raise ValueError(f"The model response was incomplete: {reason}.")
        raise ValueError("The model response was incomplete.")

    if response_json.get("output_text"):
        return response_json["output_text"]

    for item in response_json.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "")
            if content.get("type") == "refusal":
                raise ValueError(content.get("refusal", "The model refused the request."))

    raise ValueError("Could not find 'output_text' in the API response.")


def prompt_cache_key(namespace: str, model: str, schema: dict) -> str:
    stable_schema = _json.dumps(schema, sort_keys=True, separators=(",", ":"))
    digest = _hashlib.sha256(stable_schema.encode("utf-8")).hexdigest()[:16]
    return f"{namespace}:{model}:{digest}"


def sanitize_request_params(params: dict) -> dict:
    return {
        key: value
        for key, value in params.items()
        if key not in _UNSUPPORTED_RESPONSES_PARAMS
    }


def call_structured(
    data: _Any,
    api_key: str,
    payload: dict,
    url: str,
    timeout: int,
    retries: int,
    required_fields: list,
) -> dict:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    request_payload = _copy.deepcopy(payload)
    request_payload["input"] = [
        {
            "role": "user",
            "content": f"DATA:\n{format_input_data(data)}",
        }
    ]

    response = None
    backoff_time = 1
    for attempt in range(retries + 1):
        try:
            started = _time.time()
            response = _requests.post(
                url=url,
                headers=headers,
                json=request_payload,
                timeout=timeout,
            )
            elapsed_seconds = _time.time() - started
        except _requests.exceptions.ReadTimeout:
            if attempt >= retries:
                return error_result(required_fields, "Timed Out")
        except Exception as e:
            if attempt >= retries:
                return error_result(required_fields, str(e))

        if response and response.ok:
            try:
                output_text = extract_response_text(response.json())
                parsed = _json.loads(output_text)
                if not isinstance(parsed, dict):
                    raise ValueError("Structured response was not a JSON object.")
                schema = request_payload.get("text", {}).get("format", {}).get("schema", {})
                _handle_success(
                    response,
                    endpoint="responses",
                    model=request_payload.get("model"),
                    elapsed_seconds=elapsed_seconds,
                )
                return validate_structured_output(parsed, schema)
            except (_json.JSONDecodeError, _ValidationError, ValueError) as e:
                if attempt >= retries:
                    return error_result(required_fields, f"Invalid structured response: {e}")
        else:
            context = _response_context(
                response,
                endpoint="responses",
                model=request_payload.get("model"),
                attempt=attempt + 1,
            )
            error_message = context.get("message", "")

            if error_message:
                if "Invalid schema" in error_message:
                    raise ValueError("The schema submitted for output is not valid.")
                if "Incorrect API key" in error_message:
                    raise ValueError("API Key provided is missing or invalid.")
            if attempt >= retries or not _should_retry(context):
                _log_api_error(context, final=True)
                return error_result(required_fields, _error_message(context))
            _log_api_error(context, final=False)

        if response and not response.ok:
            _sleep_for_retry(context, backoff_time)
        else:
            _time.sleep(backoff_time)
        backoff_time *= 2

    return error_result(required_fields, "Failed")
