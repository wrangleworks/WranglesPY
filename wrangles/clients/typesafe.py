"""Small HTTP adapter for TypeSafe's typed System One responses.

Public wrangles own input normalization, configuration, and row concurrency.
This adapter validates one response and never includes request or response
content in errors. See https://docs.typesafe.ai/api for the wire contract.
"""

import math as _math
import time as _time
from datetime import datetime as _datetime, timezone as _timezone
from email.utils import parsedate_to_datetime as _parsedate_to_datetime

import requests as _requests


class TypesafeError(RuntimeError):
    """A sanitized provider failure, without request, response, or credentials."""

    def __init__(self, message, *, status_code=None, attempts=None):
        super().__init__(message)
        self.status_code = status_code
        self.attempts = attempts


class TypesafeResponseError(TypesafeError):
    """The provider returned an invalid typed response; retrying is unsafe."""


def _invalid(reason):
    raise TypesafeResponseError(f"Invalid Typesafe response: {reason}.") from None


def _number(value, low, high):
    # Compare integers directly: coercing an unusually large JSON integer to
    # float inside isfinite() can overflow instead of rejecting the response.
    return (
        type(value) is int and low <= value <= high
        or type(value) is float and _math.isfinite(value) and low <= value <= high
    )


def _probabilities(answer, expected):
    probabilities = answer.get("probabilities")
    if not isinstance(probabilities, dict) or set(probabilities) != expected:
        _invalid("probability keys do not match the requested criteria")
    if any(not _number(value, 0, 1) for value in probabilities.values()):
        _invalid("probabilities must be finite numbers between zero and one")
    # The documented distribution sums approximately to one. Allow rounding,
    # but neither renormalize provider values nor accept incomplete mass.
    if not _math.isclose(_math.fsum(probabilities.values()), 1, rel_tol=0, abs_tol=0.01):
        _invalid("probabilities do not sum approximately to one")
    if not _number(answer.get("confidence"), 0, 1):
        _invalid("confidence must be a finite number between zero and one")


def _validate_response(payload, questions):
    if not isinstance(payload, dict):
        _invalid("expected an object")
    if not isinstance(payload.get("model"), str) or not payload["model"].strip():
        _invalid("model must be a non-empty string")
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        _invalid("usage must be an object")
    # The current official SDK permits missing/null usage counts. Preserve
    # those values instead of inventing zero counts for unreported usage.
    for key in ("input_tokens", "output_tokens"):
        value = usage.get(key)
        if value is not None and (type(value) is not int or value < 0):
            _invalid("reported token counts must be non-negative integers")
    answers = payload.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(questions):
        _invalid("answer IDs do not match the requested questions")
    for question_id, question in questions.items():
        answer = answers[question_id]
        kind = question["type"]
        if not isinstance(answer, dict) or answer.get("type") != kind:
            _invalid("answer type does not match its question")
        if kind == "noul":
            if not _number(answer.get("noul"), 0, 1):
                _invalid("noul must be a finite number between zero and one")
        elif kind == "choice":
            expected = set(question["criteria"])
            if not isinstance(answer.get("choice"), str) or answer["choice"] not in expected:
                _invalid("choice is not one of the requested options")
            _probabilities(answer, expected)
        elif kind == "score":
            criteria = question["criteria"]
            expected = {str(index) for index in range(len(criteria))}
            if not _number(answer.get("score"), 0, len(criteria) - 1):
                _invalid("score is outside the requested rubric")
            legend = answer.get("legend")
            if not isinstance(legend, dict) or set(legend) != expected:
                _invalid("score legend does not match the requested levels")
            if any(legend[str(index)] != description for index, description in enumerate(criteria)):
                _invalid("score legend descriptions do not match the requested rubric")
            _probabilities(answer, expected)
        else:
            _invalid("unsupported question type")
    return payload


def _retry_delay(header, attempt):
    """Honor numeric/HTTP-date Retry-After, bounded to sixty seconds."""
    fallback = min(2 ** min(attempt, 6), 60)
    if not isinstance(header, str) or not header.strip():
        return fallback
    try:
        delay = float(header)
    except ValueError:
        try:
            retry_at = _parsedate_to_datetime(header)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=_timezone.utc)
            delay = max(0, (retry_at - _datetime.now(_timezone.utc)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return fallback
    if not _math.isfinite(delay) or delay < 0:
        return fallback
    return min(delay, 60)


def _close_response(response):
    try:
        response.close()
    except (OSError, _requests.exceptions.RequestException):
        # A failed cleanup must not replace a sanitized provider error with
        # an exception that may contain connection details or credentials.
        pass


def call_systemone(*, state, questions, model, api_key, url, timeout, retries):
    """Evaluate one state and return the validated, unmodified response.

    ``retries`` counts additional attempts. ``timeout`` applies to each HTTP
    attempt; it is not a deadline for the complete operation. HTTP 429 and 5xx,
    timeouts, and connection failures retry; invalid answers and other statuses
    fail immediately. Redirects are disabled so credentials stay at the chosen
    endpoint. All raised provider errors omit bodies and low-level causes.
    """
    if type(retries) is not int or retries < 0:
        raise ValueError("retries must be a non-negative integer.")
    if type(timeout) not in (int, float) or not _math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number.")
    payload = {"state": state, "model": model, "questions": questions}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    transient_errors = (
        _requests.exceptions.Timeout,
        _requests.exceptions.ConnectionError,
        _requests.exceptions.ChunkedEncodingError,
        _requests.exceptions.ContentDecodingError,
    )
    for attempt in range(retries + 1):
        response = None
        delay = _retry_delay(None, attempt)
        try:
            try:
                response = _requests.post(
                    url, headers=headers, json=payload, timeout=timeout,
                    allow_redirects=False,
                )
            except (_requests.exceptions.RequestException, ValueError) as error:
                # RequestException may contain a URL, headers, or body. Never
                # retain it in the surfaced error's message or displayed chain.
                error_response = getattr(error, "response", None)
                if error_response is not None:
                    _close_response(error_response)
                if isinstance(error, transient_errors) and attempt < retries:
                    pass
                else:
                    raise TypesafeError(
                        "Typesafe request failed during transport.", attempts=attempt + 1,
                    ) from None
            if response is not None:
                status = response.status_code
                if 200 <= status < 300:
                    try:
                        result = response.json()
                    except (ValueError, _requests.exceptions.RequestException):
                        raise TypesafeResponseError(
                            "Invalid Typesafe response: expected valid JSON.",
                            status_code=status, attempts=attempt + 1,
                        ) from None
                    return _validate_response(result, questions)
                if (status == 429 or 500 <= status < 600) and attempt < retries:
                    delay = _retry_delay(response.headers.get("Retry-After"), attempt)
                else:
                    raise TypesafeError(
                        f"Typesafe request failed with HTTP {status}.",
                        status_code=status, attempts=attempt + 1,
                    ) from None
        finally:
            if response is not None:
                _close_response(response)
        _time.sleep(delay)
