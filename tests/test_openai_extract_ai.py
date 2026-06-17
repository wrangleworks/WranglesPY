import json
import logging

import wrangles.extract as extract


class _Response:
    def __init__(self, body, ok=True, status_code=200, headers=None):
        self._body = body
        self.ok = ok
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._body


def test_extract_ai_uses_responses_structured_outputs(monkeypatch):
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
    assert payload["reasoning"] == {"effort": "low"}
    assert payload["text"]["verbosity"] == "low"
    assert payload["text"]["format"]["strict"] is True
    assert "seed" not in payload
    assert "examples" not in schema["properties"]["length"]
    assert 'examples are ["25mm"]' in payload["instructions"]
    assert schema["required"] == ["length"]
    assert schema["additionalProperties"] is False


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

    def chatgpt(data, api_key, settings, url, timeout, retries):
        calls.append((data, api_key, settings, url, timeout, retries))
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
