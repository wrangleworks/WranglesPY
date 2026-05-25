"""
Shared helpers for OpenAI Responses API calls.
"""
import copy as _copy
import hashlib as _hashlib
import json as _json
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
            response = _requests.post(
                url=url,
                headers=headers,
                json=request_payload,
                timeout=timeout,
            )
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
                return validate_structured_output(parsed, schema)
            except (_json.JSONDecodeError, _ValidationError, ValueError) as e:
                if attempt >= retries:
                    return error_result(required_fields, f"Invalid structured response: {e}")
        else:
            try:
                error_message = response.json().get("error", {}).get("message", "")
            except Exception:
                error_message = ""

            if error_message:
                if "Invalid schema" in error_message:
                    raise ValueError("The schema submitted for output is not valid.")
                if "Incorrect API key" in error_message:
                    raise ValueError("API Key provided is missing or invalid.")
                if attempt >= retries:
                    return error_result(required_fields, error_message)

        _time.sleep(backoff_time)
        backoff_time *= 2

    return error_result(required_fields, "Failed")
