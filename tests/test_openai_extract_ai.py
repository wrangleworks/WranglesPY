import wrangles.extract as extract


class _Response:
    ok = True

    def __init__(self, body):
        self._body = body

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
