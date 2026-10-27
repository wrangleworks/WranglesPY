"""Synthetic OpenRouter contracts. All requests and retry sleeps are mocked."""

import copy
import traceback

import pytest
import requests

from wrangles.clients import openrouter, typesafe


QUESTIONS = {
    "fit": {"type": "score", "instructions": "How well does it fit?",
            "criteria": ["Unsupported", "Supported"]},
    "best": {"type": "choice", "instructions": "Which fits?",
             "criteria": {"pump": "A pump", "motor": "A motor"}},
    "explicit": {"type": "noul", "instructions": "Is the type explicit?"},
}
PAYLOAD = {
    "model": "microsoft/microsoft-decision-1", "provider": "Microsoft",
    "usage": {"input_tokens": 120, "output_tokens": 0, "cost": 0.00000504},
    "answers": {
        "fit": {"type": "score", "score": 0.9, "confidence": 0.7,
                "probabilities": {"0": 0.1, "1": 0.9},
                "legend": {"0": "Unsupported", "1": "Supported"}},
        "best": {"type": "choice", "choice": "pump", "confidence": 0.6,
                 "probabilities": {"pump": 0.9, "motor": 0.1}},
        "explicit": {"type": "noul", "noul": 0.95},
    },
}


class Response:
    def __init__(self, *, status=200, payload=None):
        self.status_code = status
        self.headers = {"Retry-After": "0"}
        self.payload = copy.deepcopy(PAYLOAD if payload is None else payload)
        self.closed = False

    def json(self):
        return self.payload

    def close(self):
        self.closed = True


@pytest.fixture
def transport(monkeypatch):
    calls, responses, sleeps = [], [], []

    def post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(typesafe._requests, "post", post)
    monkeypatch.setattr(typesafe._time, "sleep", sleeps.append)
    return calls, responses, sleeps


def call(**overrides):
    return openrouter.call_systemone(**{
        "state": "synthetic product", "questions": copy.deepcopy(QUESTIONS),
        "model": "microsoft/microsoft-decision-1", "api_key": "synthetic-secret",
        "url": "https://openrouter.ai/api/alpha/decisions", "timeout": 7, "retries": 1,
        **overrides,
    })


def test_mixed_response_and_gateway_request_are_preserved(transport):
    calls, responses, sleeps = transport
    response = Response()
    responses.append(response)
    result = call()
    assert result is response.payload
    assert result == PAYLOAD
    assert calls == [{
        "url": "https://openrouter.ai/api/alpha/decisions", "timeout": 7,
        "allow_redirects": False,
        "headers": {"Authorization": "Bearer synthetic-secret", "Content-Type": "application/json"},
        "json": {"state": "synthetic product", "model": PAYLOAD["model"], "questions": QUESTIONS},
    }]
    assert response.closed and not sleeps


@pytest.mark.parametrize("question,field", [
    ("fit", "confidence"), ("fit", "probabilities"), ("fit", "legend"),
    ("best", "confidence"), ("best", "probabilities"), ("explicit", "noul"),
])
def test_missing_required_answer_data_fails_without_retry(transport, question, field):
    calls, responses, sleeps = transport
    payload = copy.deepcopy(PAYLOAD)
    del payload["answers"][question][field]
    response = Response(payload=payload)
    responses.append(response)
    with pytest.raises(openrouter.OpenRouterResponseError, match="Invalid OpenRouter response"):
        call()
    assert len(calls) == 1 and not sleeps and response.closed


@pytest.mark.parametrize("status", [301, 307, 400, 401, 402, 403, 413, 422])
def test_permanent_errors_are_provider_specific_and_sanitized(transport, status):
    calls, responses, sleeps = transport
    response = Response(status=status, payload={"error": "private response"})
    responses.append(response)
    with pytest.raises(openrouter.OpenRouterError) as caught:
        call()
    assert caught.value.status_code == status
    assert caught.value.attempts == 1
    assert str(caught.value) == f"OpenRouter request failed with HTTP {status}."
    rendered = "".join(traceback.format_exception(caught.type, caught.value, caught.tb))
    assert "private response" not in rendered and "synthetic-secret" not in rendered
    assert not sleeps and len(calls) == 1 and response.closed


@pytest.mark.parametrize("status", [429, 500, 503])
def test_retryable_status_recovers_and_closes_responses(transport, status):
    calls, responses, sleeps = transport
    first, second = Response(status=status), Response()
    responses.extend([first, second])
    assert call() == PAYLOAD
    assert len(calls) == 2 and sleeps == [0]
    assert first.closed and second.closed


def test_transport_failure_does_not_expose_low_level_cause(transport):
    calls, responses, sleeps = transport
    responses.extend([requests.Timeout("synthetic-secret"), requests.Timeout("private state")])
    with pytest.raises(openrouter.OpenRouterError) as caught:
        call()
    assert caught.value.attempts == 2
    assert str(caught.value) == "OpenRouter request failed during transport."
    rendered = "".join(traceback.format_exception(caught.type, caught.value, caught.tb))
    assert "private state" not in rendered and "synthetic-secret" not in rendered
    assert len(calls) == 2 and sleeps == [1]
