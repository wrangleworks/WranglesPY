import json

import pytest


class JsonResponse:
    """Minimal requests-like response for contract tests."""

    def __init__(self, body, ok=True, status_code=200, headers=None, text=None):
        self._body = body
        self.ok = ok
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text if text is not None else json.dumps(body)

    def json(self):
        return self._body


class MalformedJsonResponse(JsonResponse):
    def __init__(self, ok=True, status_code=200, headers=None, text="not json"):
        super().__init__(None, ok=ok, status_code=status_code, headers=headers, text=text)

    def json(self):
        raise json.JSONDecodeError("Malformed response body", self.text, 0)


@pytest.fixture
def json_response_factory():
    return JsonResponse


@pytest.fixture
def malformed_json_response_factory():
    return MalformedJsonResponse


@pytest.fixture
def openai_output_text_body():
    def make(payload):
        return {
            "output": [{
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": json.dumps(payload),
                }],
            }]
        }

    return make


@pytest.fixture
def openai_success_response(json_response_factory, openai_output_text_body):
    def make(payload):
        return json_response_factory(openai_output_text_body(payload))

    return make


@pytest.fixture
def openai_rate_limit_response(json_response_factory):
    def make(retry_after="1"):
        return json_response_factory(
            {"error": {"message": "Rate limit reached", "type": "requests"}},
            ok=False,
            status_code=429,
            headers={"retry-after": retry_after},
        )

    return make


@pytest.fixture
def fake_model_id():
    return "12345678-1234-1234-1234-123456789abc"


@pytest.fixture
def model_creation_response(json_response_factory, fake_model_id):
    return json_response_factory({"model_id": fake_model_id})


@pytest.fixture
def created_model_ids():
    model_ids = []
    yield model_ids

    if not model_ids:
        return

    import wrangles

    cleanup_errors = []
    for model_id in model_ids:
        try:
            wrangles.train.delete(model_id)
        except Exception as exc:
            cleanup_errors.append(f"{model_id}: {exc}")

    if cleanup_errors:
        raise RuntimeError(
            "Failed to clean up live test model(s): " + "; ".join(cleanup_errors)
        )
