"""Offline coverage for extract.ai request metadata and recipe forwarding."""

from copy import deepcopy
import json

import jsonschema
import pandas as pd
import pytest
import requests
import yaml

import wrangles.extract as extract
from wrangles import ai_cache, config, recipe


@pytest.fixture(autouse=True)
def _isolate_request_state(monkeypatch):
    ai_cache.clear()
    monkeypatch.setattr(config, "api_user", None)
    monkeypatch.delenv("WRANGLES_USER", raising=False)
    yield
    ai_cache.clear()


@pytest.fixture(params=["responses", "chat_completions"])
def transport(monkeypatch, request):
    protocol = request.param
    calls = []

    def post(**kwargs):
        calls.append(deepcopy(kwargs))
        result = json.dumps({"length": "25mm"})
        if protocol == "responses":
            body = {
                "output": [{
                    "type": "message",
                    "content": [{"type": "output_text", "text": result}],
                }]
            }
        else:
            body = {
                "choices": [{
                    "message": {
                        "tool_calls": [{"function": {"arguments": result}}]
                    }
                }]
            }
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(body).encode("utf-8")
        return response

    monkeypatch.setattr(extract._openai_responses._requests, "post", post)
    return protocol, calls


def _extract(protocol, **kwargs):
    return extract.ai(
        "wrench 25mm",
        "synthetic-api-key",
        output={"length": {"type": "string"}},
        threads=1,
        protocol=protocol,
        **kwargs,
    )


@pytest.mark.parametrize("arguments", [{}, {"metadata": None}, {"metadata": {}}])
def test_metadata_omitted_null_and_empty_have_distinct_request_behavior(
    transport, arguments
):
    protocol, calls = transport

    assert _extract(protocol, **arguments) == {"length": "25mm"}

    payload = calls[0]["json"]
    if arguments.get("metadata") is None:
        assert "metadata" not in payload
    else:
        assert payload["metadata"] == {}


def test_metadata_is_forwarded_without_modifying_caller_values(transport):
    protocol, calls = transport
    metadata = {
        "recipe_name": "Synthetic product classification",
        "wrangles_user": "synthetic-user@example.test",
        "batch": "trial-01",
    }
    original = deepcopy(metadata)

    assert _extract(protocol, metadata=metadata) == {"length": "25mm"}

    assert calls[0]["json"]["metadata"] == original
    assert metadata == original


@pytest.mark.parametrize(
    "metadata",
    [
        "recipe_name=example",
        [("recipe_name", "example")],
        {1: "non-string key"},
        {"batch": 1},
        {"enabled": True},
        {"recipe_name": None},
        {"k" * 65: "too long"},
        {"recipe_name": "v" * 513},
        {f"field_{index}": "value" for index in range(17)},
    ],
    ids=[
        "string", "list", "non-string-key", "number", "boolean", "null-value",
        "long-key", "long-value", "too-many-fields",
    ],
)
def test_invalid_metadata_fails_before_making_any_request(transport, metadata):
    protocol, calls = transport

    with pytest.raises(ValueError, match="metadata"):
        _extract(protocol, metadata=metadata)

    assert calls == []


def test_metadata_accepts_provider_limits(transport):
    protocol, calls = transport
    metadata = {f"field_{index}": "value" for index in range(15)}
    metadata["k" * 64] = "v" * 512

    assert _extract(protocol, metadata=metadata) == {"length": "25mm"}

    assert calls[0]["json"]["metadata"] == metadata


def test_metadata_separates_result_cache_without_changing_model_prompt(transport):
    protocol, calls = transport
    first = {"recipe_name": "Synthetic recipe A", "wrangles_user": "user-a"}
    second = {"recipe_name": "Synthetic recipe B", "wrangles_user": "user-b"}

    for metadata in (first, first, second, second, first):
        assert _extract(protocol, metadata=metadata) == {"length": "25mm"}

    assert len(calls) == 2
    first_payload = calls[0]["json"]
    second_payload = calls[1]["json"]
    assert first_payload["metadata"] == first
    assert second_payload["metadata"] == second
    assert {key: value for key, value in first_payload.items() if key != "metadata"} == {
        key: value for key, value in second_payload.items() if key != "metadata"
    }
    if protocol == "responses":
        assert first_payload["prompt_cache_key"] == second_payload["prompt_cache_key"]


def test_recipe_metadata_resolves_explicit_recipe_and_user_variables(transport):
    protocol, calls = transport
    definition = {
        "wrangles": [{
            "extract.ai": {
                "input": "Description",
                "api_key": "synthetic-api-key",
                "output": {"length": {"type": "string"}},
                "protocol": protocol,
                "metadata": {
                    "recipe_name": "${recipe_name}",
                    "wrangles_user": "${WRANGLES_USER}",
                    "batch": "trial-01",
                },
            }
        }]
    }

    result = recipe.run(
        definition,
        dataframe=pd.DataFrame({"Description": ["wrench 25mm"]}),
        variables={
            "recipe_name": "Synthetic classification recipe",
            "WRANGLES_USER": "synthetic-user@example.test",
            "applied_permission_group": None,
        },
    )

    assert result["length"].tolist() == ["25mm"]
    assert len(calls) == 1
    assert calls[0]["json"]["metadata"] == {
        "recipe_name": "Synthetic classification recipe",
        "wrangles_user": "synthetic-user@example.test",
        "batch": "trial-01",
    }


def test_recipe_metadata_schema_accepts_empty_and_provider_maximums():
    schema = yaml.safe_load(recipe._recipe_wrangles.extract.ai.__doc__)
    metadata_schema = schema["properties"]["metadata"]
    validator = jsonschema.Draft202012Validator(metadata_schema)
    metadata = {f"field_{index}": "value" for index in range(15)}
    metadata["k" * 64] = "v" * 512

    validator.validate({})
    validator.validate(metadata)


@pytest.mark.parametrize(
    "metadata",
    [
        {f"field_{index}": "value" for index in range(17)},
        {"k" * 65: "value"},
        {"recipe_name": "v" * 513},
        {"batch": 123},
    ],
    ids=["too-many-fields", "long-key", "long-value", "non-string-value"],
)
def test_recipe_metadata_schema_rejects_values_outside_provider_contract(metadata):
    schema = yaml.safe_load(recipe._recipe_wrangles.extract.ai.__doc__)
    validator = jsonschema.Draft202012Validator(schema["properties"]["metadata"])

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(metadata)
