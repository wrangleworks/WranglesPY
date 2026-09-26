"""Credential-free TypeSafe wire contracts; all HTTP calls are mocked."""

import copy
import traceback
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import pytest
import requests

from wrangles.clients import typesafe


QUESTIONS = {
    "route": {"type": "choice", "instructions": "Select a team", "criteria": {"billing": None, "sales": "Quotes"}},
    "urgency": {"type": "score", "instructions": "Rate urgency", "criteria": ["Normal", "Urgent", "Critical"]},
    "duplicate": {"type": "noul", "instructions": "Is this a duplicate?"},
}
RESPONSE = {
    "model": "jev-1.13.0",
    "answers": {
        "route": {"type": "choice", "choice": "billing", "confidence": 0.8, "probabilities": {"billing": 0.9, "sales": 0.1}},
        "urgency": {"type": "score", "score": 1.05, "confidence": 0.92, "legend": {"0": "Normal", "1": "Urgent", "2": "Critical"}, "probabilities": {"0": 0, "1": 0.95, "2": 0.05}},
        "duplicate": {"type": "noul", "noul": 0.7},
    },
    "usage": {"input_tokens": 42, "output_tokens": 8},
}


class Response:
    def __init__(self, payload=None, status=200, headers=None, error=None):
        self.payload = copy.deepcopy(RESPONSE if payload is None else payload)
        self.status_code = status
        self.headers = headers or {}
        self.error = error
        self.closed = False

    def json(self):
        if self.error is not None:
            raise self.error
        return self.payload

    def close(self):
        self.closed = True


@pytest.fixture
def transport(monkeypatch):
    calls, sleeps, results = [], [], []

    def post(url, **kwargs):
        calls.append({"url": url, **copy.deepcopy(kwargs)})
        result = results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(typesafe._requests, "post", post)
    monkeypatch.setattr(typesafe._time, "sleep", sleeps.append)
    return calls, sleeps, results


def call(**overrides):
    arguments = dict(
        state={"description": "Synthetic invoice question"}, questions=copy.deepcopy(QUESTIONS),
        model="jev-1.13.0", api_key="synthetic-private-key", url="https://typesafe.example/v1/systemone",
        timeout=7.5, retries=1,
    )
    return typesafe.call_systemone(**(arguments | overrides))


def test_typed_response_and_request_contract_are_preserved(transport):
    calls, sleeps, results = transport
    response = Response()
    results.append(response)
    state, questions = {"description": "Synthetic"}, copy.deepcopy(QUESTIONS)
    result = call(state=state, questions=questions)
    assert result is response.payload
    assert result == RESPONSE
    assert calls == [{
        "url": "https://typesafe.example/v1/systemone", "timeout": 7.5, "allow_redirects": False,
        "headers": {"Authorization": "Bearer synthetic-private-key", "Content-Type": "application/json"},
        "json": {"state": state, "model": "jev-1.13.0", "questions": QUESTIONS},
    }]
    assert questions == QUESTIONS
    assert sleeps == []
    assert response.closed


@pytest.mark.parametrize("status", [429, 500, 502, 503, 529])
@pytest.mark.parametrize("retries", [0, 1, 2])
def test_transient_status_retry_budget(status, retries, transport):
    calls, sleeps, results = transport
    responses = [Response(status=status) for _ in range(retries + 1)]
    results.extend(responses)
    with pytest.raises(typesafe.TypesafeError) as caught:
        call(retries=retries)
    assert caught.value.status_code == status
    assert caught.value.attempts == retries + 1
    assert len(calls) == retries + 1
    assert sleeps == [2 ** attempt for attempt in range(retries)]
    assert all(response.closed for response in responses)


@pytest.mark.parametrize("status", [301, 307, 400, 401, 403, 404, 422])
def test_permanent_status_and_redirects_fail_without_retry(status, transport):
    calls, sleeps, results = transport
    response = Response(status=status)
    results.append(response)
    with pytest.raises(typesafe.TypesafeError) as caught:
        call(retries=3)
    assert caught.value.status_code == status
    assert len(calls) == 1
    assert sleeps == []
    assert response.closed


@pytest.mark.parametrize("error_type", [requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError, requests.exceptions.ContentDecodingError])
def test_transient_transport_error_retries_and_recovers(error_type, transport):
    calls, sleeps, results = transport
    response = Response()
    results.extend([error_type("SECRET FROM TRANSPORT"), response])
    assert call() == RESPONSE
    assert len(calls) == 2
    assert [item["timeout"] for item in calls] == [7.5, 7.5]
    assert sleeps == [1]
    assert response.closed


@pytest.mark.parametrize("error_type", [requests.Timeout, requests.ConnectionError, requests.exceptions.InvalidURL, ValueError])
def test_transport_failure_cannot_expose_exception_contents(error_type, transport):
    calls, sleeps, results = transport
    results.extend([error_type("DO-NOT-EXPOSE-secret-and-request-body") for _ in range(3)])
    with pytest.raises(typesafe.TypesafeError) as caught:
        call(retries=2)
    rendered = "".join(traceback.format_exception(caught.type, caught.value, caught.tb))
    assert "DO-NOT-EXPOSE" not in rendered
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
    expected = 3 if error_type in (requests.Timeout, requests.ConnectionError) else 1
    assert len(calls) == expected
    assert len(sleeps) == expected - 1


@pytest.mark.parametrize("header,expected", [("2.5", 2.5), ("0", 0), ("900", 60), ("-1", 1), ("NaN", 1), ("inf", 1), ("invalid", 1)])
def test_retry_after_is_honored_and_bounded(header, expected, transport):
    calls, sleeps, results = transport
    results.extend([Response(status=429, headers={"Retry-After": header}), Response()])
    assert call() == RESPONSE
    assert sleeps == [expected]


def test_retry_after_http_date_and_backoff_are_bounded():
    future = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=25))
    assert 23 <= typesafe._retry_delay(future, 0) <= 25
    past = format_datetime(datetime.now(timezone.utc) - timedelta(seconds=25))
    assert typesafe._retry_delay(past, 0) == 0
    assert typesafe._retry_delay(None, 100000) == 60


def test_invalid_json_fails_without_retry_or_body_leak(transport):
    calls, sleeps, results = transport
    response = Response(error=ValueError("DO-NOT-EXPOSE-body"))
    results.append(response)
    with pytest.raises(typesafe.TypesafeResponseError) as caught:
        call(retries=2)
    assert "DO-NOT-EXPOSE" not in "".join(traceback.format_exception(caught.type, caught.value, caught.tb))
    assert len(calls) == 1
    assert sleeps == []
    assert response.closed


@pytest.mark.parametrize("modify", [
    lambda p: p.update(model=""),
    lambda p: p.update(model=None),
    lambda p: p.pop("usage"),
    lambda p: p["usage"].update(input_tokens=-1),
    lambda p: p["usage"].update(output_tokens=True),
    lambda p: p["usage"].update(input_tokens=1.5),
    lambda p: p["answers"].pop("duplicate"),
    lambda p: p["answers"].update(extra={"type": "noul", "noul": 0.5}),
    lambda p: p["answers"].update(duplicate=[]),
    lambda p: p["answers"]["duplicate"].update(type="score"),
    lambda p: p["answers"]["duplicate"].update(noul=None),
    lambda p: p["answers"]["duplicate"].update(noul=True),
    lambda p: p["answers"]["duplicate"].update(noul=float("nan")),
    lambda p: p["answers"]["duplicate"].update(noul=10 ** 1000),
    lambda p: p["answers"]["duplicate"].update(noul=1.01),
    lambda p: p["answers"]["route"].update(choice="DO-NOT-EXPOSE-unrequested"),
    lambda p: p["answers"]["route"].update(choice=[]),
    lambda p: p["answers"]["route"]["probabilities"].pop("sales"),
    lambda p: p["answers"]["route"]["probabilities"].update(other=0),
    lambda p: p["answers"]["route"]["probabilities"].update(sales=0.5),
    lambda p: p["answers"]["route"]["probabilities"].update(sales=-0.1),
    lambda p: p["answers"]["route"]["probabilities"].update(sales=float("inf")),
    lambda p: p["answers"]["route"]["probabilities"].update(sales=True),
    lambda p: p["answers"]["route"].update(confidence="0.9"),
    lambda p: p["answers"]["route"].update(confidence=float("nan")),
    lambda p: p["answers"]["urgency"].update(score=3),
    lambda p: p["answers"]["urgency"].update(score=-0.1),
    lambda p: p["answers"]["urgency"].update(score=float("inf")),
    lambda p: p["answers"]["urgency"].update(score=True),
    lambda p: p["answers"]["urgency"]["probabilities"].update({"3": 0}),
    lambda p: p["answers"]["urgency"]["legend"].pop("2"),
    lambda p: p["answers"]["urgency"]["legend"].update({"1": "DO-NOT-EXPOSE-wrong-rubric"}),
])
def test_invalid_typed_answers_fail_without_retry_or_values_in_error(modify, transport):
    calls, sleeps, results = transport
    payload = copy.deepcopy(RESPONSE)
    modify(payload)
    response = Response(payload)
    results.append(response)
    with pytest.raises(typesafe.TypesafeResponseError) as caught:
        call(retries=2)
    assert "DO-NOT-EXPOSE" not in str(caught.value)
    assert len(calls) == 1
    assert sleeps == []
    assert response.closed


@pytest.mark.parametrize("usage", [{}, {"input_tokens": None, "output_tokens": 0}])
def test_optional_usage_is_preserved_without_manufactured_counts(usage, transport):
    _, _, results = transport
    payload = copy.deepcopy(RESPONSE)
    payload["usage"] = usage
    results.append(Response(payload))
    assert call()["usage"] == usage


def test_rounded_probabilities_are_preserved_not_renormalized(transport):
    _, _, results = transport
    payload = copy.deepcopy(RESPONSE)
    payload["answers"]["route"]["probabilities"] = {"billing": 0.9, "sales": 0.099}
    results.append(Response(payload))
    assert call() == payload


@pytest.mark.parametrize("payload", [[], "not an object", False])
def test_non_object_response_is_rejected_and_closed(payload, transport):
    _, _, results = transport
    response = Response(payload)
    results.append(response)
    with pytest.raises(typesafe.TypesafeResponseError, match="expected an object"):
        call()
    assert response.closed


def test_failed_status_does_not_read_error_body_and_closes_response(transport):
    _, _, results = transport
    response = Response(status=401, error=AssertionError("error body must not be read"))
    results.append(response)
    with pytest.raises(typesafe.TypesafeError, match="HTTP 401"):
        call()
    assert response.closed


def test_error_response_cleanup_does_not_override_sanitized_error(transport):
    _, _, results = transport
    response = Response(status=401)

    def close():
        raise OSError("DO-NOT-EXPOSE-close-details")

    response.close = close
    results.append(response)
    with pytest.raises(typesafe.TypesafeError) as caught:
        call()
    assert "HTTP 401" in str(caught.value)
    assert "DO-NOT-EXPOSE" not in str(caught.value)
