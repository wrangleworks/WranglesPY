import json
import logging

import pytest
import requests
import wrangles.extract as extract
from wrangles import ai_config
from wrangles import ai_cache


@pytest.fixture(autouse=True)
def _clear_result_cache():
    ai_cache.clear()
    yield
    ai_cache.clear()


class _Response:
    def __init__(self, body, ok=True, status_code=200, headers=None):
        self._body = body
        self.ok = ok
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._body


def test_extract_ai_uses_responses_structured_outputs(monkeypatch, caplog):
    calls = []
    body = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"length":"25mm"}',
                    }
                ],
            }
        ]
    }

    def post(**kwargs):
        calls.append(kwargs)
        return _Response(body)

    monkeypatch.setattr(extract._openai_responses._requests, "post", post)

    with caplog.at_level(logging.WARNING, logger="wrangles.openai_responses"):
        result = extract.ai(
            "wrench 25mm",
            "key",
            output={
                "length": {
                    "type": "string",
                    "description": "Any length in the input",
                    "examples": ["25mm"],
                }
            },
            model="gpt-5-mini",
            seed=1,
            threads=1,
        )

    payload = calls[0]["json"]
    schema = payload["text"]["format"]["schema"]
    assert result == {"length": "25mm"}
    assert calls[0]["url"] == "https://api.openai.com/v1/responses"
    assert payload["model"] == "gpt-5-mini"
    assert "reasoning" not in payload
    assert payload["text"]["verbosity"] == "low"
    assert payload["text"]["format"]["strict"] is True
    assert payload["store"] is False
    assert "tools" not in payload
    assert "include" not in payload
    assert calls[0]["timeout"] <= 12
    assert "seed" not in payload
    assert "Ignored legacy OpenAI parameter 'seed'" in caplog.text
    assert "examples" not in schema["properties"]["length"]
    assert 'examples are ["25mm"]' in payload["instructions"]
    assert schema["required"] == ["length"]
    assert schema["additionalProperties"] is False


def test_extract_ai_web_search_returns_metadata_sources_and_caches_them(monkeypatch):
    calls = []
    body = {
        "output": [
            {
                "type": "web_search_call",
                "action": {
                    "type": "search",
                    "sources": [
                        {"type": "url", "url": "https://example.com/a"},
                        {
                            "type": "url",
                            "url": "https://example.com/b",
                            "title": "Source B",
                        },
                    ],
                },
            },
            {
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": '{"output":"Acme"}',
                    "annotations": [
                        {
                            "type": "url_citation",
                            "url": "https://example.com/a",
                            "title": "Source A",
                        },
                        {
                            "type": "url_citation",
                            "url": "https://example.com/c",
                            "title": "Source C",
                        },
                    ],
                }],
            },
        ]
    }
    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or _Response(body),
    )
    arguments = {
        "input": "Who makes this product?",
        "api_key": "tenant-key",
        "output": "Manufacturer name",
        "web_search": True,
        "threads": 1,
    }

    first = extract.ai(**arguments)
    second = extract.ai(**arguments)

    assert first == {
        "output": "Acme",
        "web_search_sources": [
            {"title": "Source A", "url": "https://example.com/a"},
            {"title": "Source B", "url": "https://example.com/b"},
            {"title": "Source C", "url": "https://example.com/c"},
        ],
    }
    assert second == first
    assert len(calls) == 1
    payload = calls[0]["json"]
    assert payload["tools"] == [{"type": "web_search"}]
    assert payload["include"] == ["web_search_call.action.sources"]
    assert payload["tool_choice"] == "auto"
    assert "authorized evidence in addition to DATA" in payload["instructions"]


def test_extract_ai_web_search_preserves_expert_tool_settings(monkeypatch):
    calls = []
    body = {
        "output": [{
            "type": "message",
            "content": [{
                "type": "output_text",
                "text": '{"manufacturer":"Acme"}',
                "annotations": [],
            }],
        }]
    }
    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or _Response(body),
    )

    result = extract.ai(
        "Acme part",
        "key",
        output={"manufacturer": {"type": "string"}},
        web_search=True,
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        include=["reasoning.encrypted_content"],
        tool_choice="required",
        threads=1,
    )

    assert result == {"manufacturer": "Acme", "web_search_sources": []}
    payload = calls[0]["json"]
    assert payload["tools"] == [
        {"type": "code_interpreter", "container": {"type": "auto"}},
        {"type": "web_search"},
    ]
    assert payload["include"] == [
        "reasoning.encrypted_content",
        "web_search_call.action.sources",
    ]
    assert payload["tool_choice"] == "required"


def test_extract_ai_web_search_failure_still_returns_empty_sources(monkeypatch):
    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: _Response({
            "output": [
                {
                    "type": "web_search_call",
                    "action": {
                        "type": "search",
                        "sources": [{"url": "https://example.com/failure-source"}],
                    },
                },
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "not json"}],
                },
            ]
        }),
    )

    result = extract.ai(
        "Acme part",
        "key",
        output="Manufacturer name",
        web_search=True,
        retries=0,
        threads=1,
    )

    assert result["web_search_sources"] == [{
        "title": "",
        "url": "https://example.com/failure-source",
    }]
    assert result["output"].startswith("Invalid structured response")


def test_extract_ai_web_search_validates_protocol_and_reserved_output():
    with pytest.raises(ValueError, match="only with protocol='responses'"):
        extract.ai(
            "Acme part",
            "key",
            output={"manufacturer": {"type": "string"}},
            web_search=True,
            protocol="chat_completions",
        )

    with pytest.raises(ValueError, match="web_search must be true or false"):
        extract.ai(
            "Acme part",
            "key",
            output={"manufacturer": {"type": "string"}},
            web_search="yes",
        )

    with pytest.raises(ValueError, match="is reserved"):
        extract.ai(
            "Acme part",
            "key",
            output={"web search sources": {"type": "string"}},
            web_search=True,
        )


def test_record_examples_are_stable_instructions_and_part_of_the_result_cache_key(monkeypatch):
    calls = []
    body = {
        "output": [{
            "type": "message",
            "content": [{
                "type": "output_text",
                "text": '{"color":"yellow"}',
            }],
        }]
    }
    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or _Response(body),
    )
    common = {
        "input": "yellow handle",
        "api_key": "key",
        "output": {"color": {"type": "string"}},
        "threads": 1,
    }

    extract.ai(
        record_examples=[{
            "input": "yellow grip",
            "output": {"color": "yellow"},
        }],
        **common,
    )
    extract.ai(
        record_examples=[{
            "input": "red grip",
            "output": {"color": "red"},
        }],
        **common,
    )

    assert len(calls) == 2
    assert "<record_example" in calls[0]["json"]["instructions"]
    assert calls[0]["json"]["prompt_cache_key"] != calls[1]["json"]["prompt_cache_key"]


def test_examples_remains_a_compatibility_alias_for_record_examples(monkeypatch):
    calls = []
    body = {
        "output": [{
            "type": "message",
            "content": [{
                "type": "output_text",
                "text": '{"color":"yellow"}',
            }],
        }]
    }
    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or _Response(body),
    )
    common = {
        "input": "yellow handle",
        "api_key": "key",
        "output": {"color": {"type": "string"}},
        "threads": 1,
    }

    result = extract.ai(
        examples=[{
            "name": "legacy Python alias",
            "input": "yellow grip",
            "output": {"color": "yellow"},
        }],
        **common,
    )

    assert result == {"color": "yellow"}
    assert "legacy Python alias" in calls[0]["json"]["instructions"]
    with pytest.raises(ValueError, match="not both"):
        extract.ai(
            examples=[{"input": "yellow", "output": {"color": "yellow"}}],
            record_examples=[{"input": "red", "output": {"color": "red"}}],
            **common,
        )


def test_field_examples_are_stable_system_content_for_legacy_protocol(monkeypatch):
    calls = []
    body = {
        "choices": [{
            "message": {
                "tool_calls": [{
                    "function": {"arguments": '{"color":"yellow"}'}
                }]
            }
        }]
    }
    monkeypatch.setattr(
        extract._openai._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or _Response(body),
    )

    result = extract.ai(
        "yellow handle",
        "key",
        output={
            "color": {
                "type": "string",
                "examples": [{"input": "yellow grip", "output": "yellow"}],
            }
        },
        protocol="chat_completions",
        threads=1,
    )

    assert result == {"color": "yellow"}
    stable_content = "\n".join(
        message["content"]
        for message in calls[0]["json"]["messages"]
        if message["role"] == "system"
    )
    assert "<field_example" in stable_content
    assert "yellow grip" in stable_content


def test_extract_ai_omits_default_reasoning_for_non_reasoning_models(monkeypatch):
    calls = []
    body = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"fruits":["bananas","lemons"]}',
                    }
                ],
            }
        ]
    }

    def post(**kwargs):
        calls.append(kwargs)
        return _Response(body)

    monkeypatch.setattr(extract._openai_responses._requests, "post", post)

    result = extract.ai(
        "I had 3 strawberries, 5 bananas and 2 lemons",
        "key",
        output={
            "fruits": {
                "type": "array",
                "description": "Return the names of any fruits that are yellow",
            }
        },
        model="gpt-4o-mini",
        threads=1,
    )

    payload = calls[0]["json"]
    assert result == {"fruits": ["bananas", "lemons"]}
    assert "reasoning" not in payload
    assert "verbosity" not in payload["text"]


@pytest.mark.parametrize(
    ("model", "supported"),
    [
        ("o3-mini", False),
        ("gpt-5", False),
        ("gpt-5-mini", False),
        ("gpt-5.1", True),
        ("gpt-5.4-mini", True),
        ("gpt-5.4-pro", False),
    ],
)
def test_reasoning_none_model_compatibility(model, supported):
    assert extract._openai_responses.supports_reasoning_effort(model, "none") is supported


def test_extract_ai_scalar_output_returns_scalar_with_responses(monkeypatch):
    body = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"output":12}',
                    }
                ],
            }
        ]
    }

    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: _Response(body),
    )

    result = extract.ai(
        "12 penguins",
        "key",
        output={
            "type": "number",
            "description": "The number of penguins",
        },
        threads=1,
    )

    assert result == 12


def test_extract_ai_keeps_chat_completions_override(monkeypatch):
    calls = []

    def chatgpt(data, api_key, settings, url, timeout, retries, deadline_at):
        calls.append((data, api_key, settings, url, timeout, retries, deadline_at))
        return {"length": "25mm"}

    monkeypatch.setattr(extract._openai, "chatGPT", chatgpt)

    result = extract.ai(
        "wrench 25mm",
        "key",
        output={"length": "Any length in the input"},
        url="https://api.openai.com/v1/chat/completions",
        threads=1,
    )

    settings = calls[0][2]
    assert result == {"length": "25mm"}
    assert calls[0][3] == "https://api.openai.com/v1/chat/completions"
    assert calls[0][4] == 12
    assert settings["tools"][0]["function"]["parameters"]["required"] == ["length"]


def test_extract_ai_validates_responses_output_with_pydantic(monkeypatch):
    body = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"count":"not a number"}',
                    }
                ],
            }
        ]
    }

    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: _Response(body),
    )

    result = extract.ai(
        "12 penguins",
        "key",
        output={
            "count": {
                "type": "integer",
                "description": "The number of penguins",
            }
        },
        threads=1,
    )

    assert "Invalid structured response" in result["count"]


def test_extract_ai_reports_rate_limit_diagnostics(monkeypatch):
    body = {
        "error": {
            "message": "Rate limit reached for requests per min.",
            "type": "requests",
            "code": "rate_limit_exceeded",
        }
    }
    headers = {
        "x-request-id": "req_123",
        "x-ratelimit-limit-requests": "500",
        "x-ratelimit-remaining-requests": "0",
        "x-ratelimit-reset-requests": "1s",
        "retry-after": "2",
    }

    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: _Response(body, ok=False, status_code=429, headers=headers),
    )

    result = extract.ai(
        "wrench 25mm",
        "key",
        output={"length": {"type": "string", "description": "Any length"}},
        threads=1,
        retries=0,
    )

    assert "status=429" in result["length"]
    assert "limit=requests_per_minute" in result["length"]
    assert "request_id=req_123" in result["length"]
    assert "retry_after=2s" in result["length"]


def test_extract_ai_respects_retry_after_on_rate_limit(monkeypatch):
    calls = []
    sleeps = []
    rate_limit_body = {
        "error": {
            "message": "Rate limit reached for requests per min.",
            "type": "requests",
        }
    }
    success_body = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"length":"25mm"}',
                    }
                ],
            }
        ]
    }
    responses = [
        _Response(
            rate_limit_body,
            ok=False,
            status_code=429,
            headers={
                "x-ratelimit-remaining-requests": "0",
                "retry-after": "3",
            },
        ),
        _Response(success_body),
    ]

    def post(**kwargs):
        calls.append(kwargs)
        return responses.pop(0)

    monkeypatch.setattr(extract._openai_responses._requests, "post", post)
    monkeypatch.setattr(
        extract._openai_responses._time,
        "sleep",
        lambda delay: sleeps.append(delay),
    )

    result = extract.ai(
        "wrench 25mm",
        "key",
        output={"length": {"type": "string", "description": "Any length"}},
        threads=1,
        retries=1,
    )

    assert result == {"length": "25mm"}
    assert len(calls) == 2
    assert sleeps == [3.0]


def test_extract_ai_logs_success_rate_limit_header_summary(monkeypatch, caplog):
    extract._openai_responses._SUCCESS_STATS.clear()
    body = {
        "usage": {
            "input_tokens": 100,
            "output_tokens": 10,
            "total_tokens": 110,
            "input_tokens_details": {"cached_tokens": 75},
        },
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"length":"25mm"}',
                    }
                ],
            }
        ]
    }
    responses = [
        _Response(
            body,
            headers={
                "x-request-id": "req_1",
                "x-ratelimit-remaining-requests": "10",
                "x-ratelimit-remaining-tokens": "100",
                "x-ratelimit-reset-requests": "1s",
                "x-ratelimit-reset-tokens": "1s",
            },
        ),
        _Response(
            body,
            headers={
                "x-request-id": "req_2",
                "x-ratelimit-remaining-requests": "8",
                "x-ratelimit-remaining-tokens": "90",
                "x-ratelimit-reset-requests": "2s",
                "x-ratelimit-reset-tokens": "2s",
            },
        ),
    ]

    monkeypatch.setenv("WRANGLES_OPENAI_LOG_RATE_LIMITS", "true")
    monkeypatch.setenv("WRANGLES_OPENAI_LOG_EVERY", "2")
    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: responses.pop(0),
    )

    with caplog.at_level(logging.INFO, logger="wrangles.openai_responses"):
        result = extract.ai(
            ["wrench 25mm", "bolt 25mm"],
            "key",
            output={"length": {"type": "string", "description": "Any length"}},
            threads=1,
        )

    summary = json.loads(
        next(record.message for record in caplog.records if "openai_rate_limit_summary" in record.message)
    )

    assert result == [{"length": "25mm"}, {"length": "25mm"}]
    assert summary["responses"] == 2
    assert summary["min_remaining_requests"] == 8
    assert summary["min_remaining_tokens"] == 90
    assert summary["latest_request_id"] == "req_2"
    assert summary["input_tokens"] == 200
    assert summary["output_tokens"] == 20
    assert summary["cached_tokens"] == 150
    assert summary["cache_hit_responses"] == 2


def test_ai_defaults_are_packaged_and_public():
    policy = ai_config.extract_ai()

    assert ai_config.config_path().is_file()
    assert policy["provider"] == "openai"
    assert policy["protocol"] == "responses"
    assert policy["max_concurrency"] == 32
    assert policy["request_timeout_seconds"] == 12
    assert policy["total_deadline_seconds"] == 15
    assert policy["retries"] == 1
    assert policy["reasoning"] == {"effort": "none"}
    assert policy["store"] is False
    assert policy["cache"] == {
        "enabled": True,
        "ttl_seconds": 3600,
        "max_entries": 512,
        "max_value_bytes": 65536,
        "single_flight": True,
        "log_every": 100,
    }


def test_ai_config_can_be_overridden(monkeypatch, tmp_path):
    override = tmp_path / "ai.yml"
    override.write_text(
        "\n".join([
            "version: 1",
            "extract_ai:",
            "  provider: openai",
            "  protocol: responses",
            "  model: custom-model",
        ]),
        encoding="utf-8",
    )

    monkeypatch.setenv("WRANGLES_AI_CONFIG", str(override))
    ai_config.clear_cache()
    try:
        assert ai_config.extract_ai()["model"] == "custom-model"
    finally:
        ai_config.clear_cache()


def test_extract_ai_maps_or_rejects_legacy_responses_parameters(caplog):
    with caplog.at_level(logging.WARNING, logger="wrangles.openai_responses"):
        params = extract._openai_responses.sanitize_request_params(
            {"max_tokens": 100, "seed": 7}
        )

    assert params == {"max_output_tokens": 100}
    assert "Mapped legacy OpenAI parameter 'max_tokens'" in caplog.text
    assert "Ignored legacy OpenAI parameter 'seed'" in caplog.text

    with pytest.raises(ValueError, match="response_format"):
        extract._openai_responses.sanitize_request_params(
            {"response_format": {"type": "json_object"}}
        )

    with pytest.raises(ValueError, match="Both legacy 'max_tokens'"):
        extract._openai_responses.sanitize_request_params(
            {"max_tokens": 100, "max_output_tokens": 200}
        )


def test_extract_ai_rejects_unsupported_provider_and_protocol_conflicts():
    output = {"length": {"type": "string"}}

    with pytest.raises(ValueError, match="Unsupported extract.ai provider"):
        extract.ai("25mm", "key", output=output, provider="another-provider")

    with pytest.raises(ValueError, match="Chat Completions url"):
        extract.ai(
            "25mm",
            "key",
            output=output,
            protocol="responses",
            url="https://api.openai.com/v1/chat/completions",
        )


@pytest.mark.parametrize(
    ("setting", "value", "message"),
    [
        ("threads", 0, "threads"),
        ("retries", -1, "retries"),
        ("timeout", 0, "timeout"),
        ("deadline", 0, "deadline"),
    ],
)
def test_extract_ai_validates_runtime_limits(setting, value, message):
    with pytest.raises(ValueError, match=message):
        extract.ai(
            "25mm",
            "key",
            output={"length": {"type": "string"}},
            **{setting: value},
        )


def _requests_response(body, status_code=200, headers=None):
    response = requests.Response()
    response.status_code = status_code
    response.headers.update(headers or {})
    response._content = json.dumps(body).encode("utf-8")
    response.encoding = "utf-8"
    return response


def test_extract_ai_retries_real_falsey_requests_response(monkeypatch):
    sleeps = []
    responses = [
        _requests_response(
            {"error": {"message": "Rate limit reached", "type": "requests"}},
            status_code=429,
            headers={"retry-after": "1"},
        ),
        _requests_response({
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": '{"length":"25mm"}'}],
            }]
        }),
    ]

    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: responses.pop(0),
    )
    monkeypatch.setattr(
        extract._openai_responses._time,
        "sleep",
        lambda delay: sleeps.append(delay),
    )

    result = extract.ai(
        "wrench 25mm",
        "key",
        output={"length": {"type": "string"}},
        threads=1,
        retries=1,
    )

    assert result == {"length": "25mm"}
    assert sleeps == [1.0]
    assert responses == []


def test_extract_ai_does_not_retry_past_total_deadline(monkeypatch):
    calls = []
    rate_limit = _requests_response(
        {"error": {"message": "Rate limit reached", "type": "requests"}},
        status_code=429,
        headers={"retry-after": "3"},
    )

    def post(**kwargs):
        calls.append(kwargs)
        return rate_limit

    monkeypatch.setattr(extract._openai_responses._requests, "post", post)

    result = extract.ai(
        "wrench 25mm",
        "key",
        output={"length": {"type": "string"}},
        threads=1,
        retries=2,
        deadline=1,
    )

    assert result == {"length": "Deadline Exceeded"}
    assert len(calls) == 1
    assert calls[0]["timeout"] <= 1


def test_legacy_chat_transport_retries_real_falsey_response(monkeypatch):
    calls = []
    sleeps = []
    responses = [
        _requests_response(
            {"error": {"message": "Rate limit reached", "type": "requests"}},
            status_code=429,
            headers={"retry-after": "1"},
        ),
        _requests_response({
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "function": {"arguments": '{"length":"25mm"}'}
                    }]
                }
            }]
        }),
    ]

    monkeypatch.setattr(
        extract._openai._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or responses.pop(0),
    )
    monkeypatch.setattr(
        extract._openai_responses._time,
        "sleep",
        lambda delay: sleeps.append(delay),
    )

    result = extract.ai(
        "wrench 25mm",
        "key",
        output={"length": {"type": "string"}},
        protocol="chat_completions",
        threads=1,
        retries=1,
    )

    assert result == {"length": "25mm"}
    assert len(calls) == 2
    assert sleeps == [1.0]


def test_saved_model_and_call_instructions_use_shared_compiler(monkeypatch):
    calls = []
    saved = {
        "Settings": {
            "GPTModel": "gpt-5-mini",
            "AdditionalMessages": "Normalize units.",
        },
        "Columns": [
            "Find",
            "Description",
            "Type",
            "Default",
            "Examples",
            "Enum",
            "Notes",
            "Properties",
        ],
        "Data": [[
            "Voltage",
            "Voltage and unit",
            "object",
            "",
            "",
            "",
            "",
            "value,uom",
        ]],
    }
    body = {
        "output": [{
            "type": "message",
            "content": [{
                "type": "output_text",
                "text": '{"Voltage":{"value":12,"uom":"VDC"}}',
            }],
        }]
    }

    monkeypatch.setattr(extract._data, "model_content", lambda model_id: saved)
    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or _Response(body),
    )

    result = extract.ai(
        "12 VDC",
        "key",
        model_id="saved-model",
        messages="Prefer explicit source values.",
        threads=1,
    )

    payload = calls[0]["json"]
    voltage = payload["text"]["format"]["schema"]["properties"]["Voltage"]
    assert result == {"Voltage": {"value": 12, "uom": "VDC"}}
    assert payload["model"] == "gpt-5-mini"
    assert payload["text"]["format"]["strict"] is True
    assert voltage["required"] == ["value", "uom"]
    assert "Normalize units." in payload["instructions"]
    assert "Prefer explicit source values." in payload["instructions"]


def test_dynamic_recipe_output_relaxes_only_nested_dictionary(monkeypatch):
    calls = []
    body = {
        "output": [{
            "type": "message",
            "content": [{
                "type": "output_text",
                "text": '{"attributes":{"Voltage":"12 VDC"},"source":"description"}',
            }],
        }]
    }

    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or _Response(body),
    )

    result = extract.ai(
        "Voltage: 12 VDC",
        "key",
        output={
            "attributes": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            },
            "source": {"type": "string"},
        },
        threads=1,
    )

    text_format = calls[0]["json"]["text"]["format"]
    assert result == {
        "attributes": {"Voltage": "12 VDC"},
        "source": "description",
    }
    assert text_format["strict"] is False
    assert text_format["schema"]["additionalProperties"] is False
    assert text_format["schema"]["properties"]["attributes"]["additionalProperties"] == {
        "type": "string"
    }


def test_extract_ai_deduplicates_batch_and_reuses_warm_result_cache(monkeypatch):
    calls = []
    body = {
        "output": [{
            "type": "message",
            "content": [{
                "type": "output_text",
                "text": '{"length":"25mm"}',
            }],
        }]
    }
    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or _Response(body),
    )

    arguments = {
        "input": ["wrench 25mm", "wrench 25mm", "wrench 25mm"],
        "api_key": "tenant-key",
        "output": {"length": {"type": "string"}},
        "threads": 3,
    }
    first = extract.ai(**arguments)
    second = extract.ai(**arguments)

    assert first == [{"length": "25mm"}] * 3
    assert second == first
    assert len(calls) == 1
    assert ai_cache.stats()["stores"] == 1
    assert ai_cache.stats()["hits"] == 1


def test_extract_ai_cache_is_tenant_scoped_and_bypassable(monkeypatch):
    calls = []
    body = {
        "output": [{
            "type": "message",
            "content": [{
                "type": "output_text",
                "text": '{"length":"25mm"}',
            }],
        }]
    }
    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or _Response(body),
    )
    common = {
        "input": "wrench 25mm",
        "output": {"length": {"type": "string"}},
        "threads": 1,
    }

    extract.ai(api_key="tenant-a", **common)
    extract.ai(api_key="tenant-b", **common)
    extract.ai(api_key="tenant-a", cache=False, **common)

    assert len(calls) == 3


def test_extract_ai_does_not_cache_failures(monkeypatch):
    calls = []
    rate_limit = _requests_response(
        {"error": {"message": "Rate limit reached", "type": "requests"}},
        status_code=429,
    )
    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or rate_limit,
    )
    arguments = {
        "input": "wrench 25mm",
        "api_key": "tenant-key",
        "output": {"length": {"type": "string"}},
        "threads": 1,
        "retries": 0,
    }

    first = extract.ai(**arguments)
    second = extract.ai(**arguments)

    assert "OpenAI API error" in first["length"]
    assert second == first
    assert len(calls) == 2
    assert ai_cache.stats()["stores"] == 0
    assert ai_cache.stats()["skipped_error"] == 2


def test_prompt_cache_key_covers_complete_static_prefix(monkeypatch):
    payloads = []
    body = {
        "output": [{
            "type": "message",
            "content": [{
                "type": "output_text",
                "text": '{"length":"25mm"}',
            }],
        }]
    }
    monkeypatch.setattr(
        extract._openai_responses._requests,
        "post",
        lambda **kwargs: payloads.append(kwargs["json"]) or _Response(body),
    )
    common = {
        "input": "wrench 25mm",
        "api_key": "tenant-key",
        "output": {"length": {"type": "string"}},
        "threads": 1,
        "cache": False,
    }

    extract.ai(messages="Use source units.", **common)
    extract.ai(messages="Use source units.", **common)
    extract.ai(messages="Convert to inches.", **common)

    keys = [payload["prompt_cache_key"] for payload in payloads]
    assert keys[0] == keys[1]
    assert keys[0] != keys[2]


def test_legacy_chat_completions_uses_same_result_cache(monkeypatch):
    calls = []
    body = {
        "choices": [{
            "message": {
                "tool_calls": [{
                    "function": {"arguments": '{"length":"25mm"}'}
                }]
            }
        }]
    }
    monkeypatch.setattr(
        extract._openai._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or _Response(body),
    )

    result = extract.ai(
        ["wrench 25mm", "wrench 25mm"],
        "tenant-key",
        output={"length": {"type": "string"}},
        protocol="chat_completions",
        threads=2,
    )

    assert result == [{"length": "25mm"}, {"length": "25mm"}]
    assert len(calls) == 1
