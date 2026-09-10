"""Offline diagnostics coverage for every Responses API request attempt."""

from copy import deepcopy
import base64
import hashlib
import json
import logging

import pytest
import requests

from wrangles import openai_responses


@pytest.fixture(autouse=True)
def _isolate_attempts(monkeypatch, caplog):
    openai_responses._SUCCESS_STATS.clear()
    monkeypatch.delenv("WRANGLES_OPENAI_LOG_METRICS", raising=False)
    monkeypatch.delenv("WRANGLES_OPENAI_LOG_RATE_LIMITS", raising=False)
    monkeypatch.setattr(openai_responses._time, "sleep", lambda delay: None)
    monkeypatch.setattr(openai_responses._random, "uniform", lambda *args: 0)
    caplog.set_level(logging.INFO, logger="wrangles.openai_responses")
    yield
    openai_responses._SUCCESS_STATS.clear()


@pytest.fixture
def payload():
    return {
        "model": "gpt-5-mini",
        "instructions": "Count products without disclosing confidential instructions.",
        "max_output_tokens": 256,
        "metadata": {"private": "do-not-log-metadata"},
        "text": {
            "format": {
                "type": "json_schema",
                "name": "result",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {"count": {"type": "integer"}},
                    "required": ["count"],
                    "additionalProperties": False,
                },
            },
        },
    }


def _response(body, status=200, headers=None):
    response = requests.Response()
    response.status_code = status
    response.headers.update(headers or {})
    response._content = json.dumps(body).encode("utf-8")
    return response


def _completed(**overrides):
    return {
        "id": "resp_test",
        "model": "gpt-5-mini-2025-08-07",
        "status": "completed",
        "output_text": '{"count":2}',
        **overrides,
    }


def _usage():
    return {
        "input_tokens": 100,
        "input_tokens_details": {
            "cached_tokens": 80,
            "cache_write_tokens": 10,
            "cache_creation_tokens": 10,
        },
        "output_tokens": 40,
        "output_tokens_details": {"reasoning_tokens": 30},
        "total_tokens": 140,
        "cache_creation_input_tokens": 10,
    }


def _call(
    payload, retries=0, data="confidential row", api_key="synthetic-private-key", request_key=None
):
    return openai_responses.call_structured(
        data=data,
        api_key=api_key,
        payload=payload,
        url="https://api.openai.com/v1/responses",
        timeout=12,
        retries=retries,
        required_fields=["count"],
        request_key=request_key,
    )


def _events(caplog, event="openai_request_attempt"):
    events = []
    for record in caplog.records:
        if record.name == "wrangles.openai_responses" and record.getMessage().startswith("{"):
            message = json.loads(record.getMessage())
            if message.get("event") == event:
                events.append(message)
    return events


def test_success_logs_provider_identity_and_usage_without_double_counting(
    monkeypatch, caplog, payload
):
    clock = iter([10.0, 10.25])
    monkeypatch.setattr(openai_responses._time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(
        openai_responses._requests,
        "post",
        lambda **kwargs: _response(
            _completed(usage=_usage()), headers={"X-Request-ID": "req_test"}
        ),
    )

    assert _call(payload) == {"count": 2}

    event, = _events(caplog)
    assert event["attempt"] == 1
    assert len(event["call_id"]) == 32
    assert event["requested_model"] == "gpt-5-mini"
    assert event["response_model"] == "gpt-5-mini-2025-08-07"
    assert event["response_id"] == "resp_test"
    assert event["request_id"] == "req_test"
    assert event["response_status"] == "completed"
    assert event["status_code"] == 200
    assert event["elapsed_seconds"] == 0.25
    assert event["outcome"] == "success"
    assert event["usage"]["input_tokens"] == 100
    assert event["usage"]["output_tokens"] == 40
    assert event["usage"]["total_tokens"] == 140
    assert event["usage"]["input_tokens_details"]["cached_tokens"] == 80
    assert event["usage"]["input_tokens_details"]["cache_write_tokens"] == 10
    assert event["usage"]["cache_creation_input_tokens"] == 10
    assert event["usage"]["output_tokens_details"]["reasoning_tokens"] == 30
    assert event["usage"]["cache_read_input_tokens"] is None
    assert event["usage"]["cache_write_tokens"] is None
    assert "synthetic-private-key" not in caplog.text
    assert "confidential" not in caplog.text
    assert "do-not-log-metadata" not in caplog.text
    assert "output_text" not in event


@pytest.mark.parametrize(
    "body,outcome",
    [
        (
            _completed(
                status="incomplete",
                incomplete_details={"reason": "max_output_tokens"},
                output_text="",
            ),
            "incomplete",
        ),
        (_completed(output_text="not JSON"), "json_error"),
        (_completed(output_text='{"count":"not an integer"}'), "schema_error"),
        (_completed(output_text='["not an object"]'), "schema_error"),
        (_completed(error={"message": "provider-private-error"}), "api_error"),
        ({"output": [None, {"type": "message", "content": None}]}, "invalid_response"),
    ],
)
def test_unsuccessful_http_200_attempts_keep_usage(monkeypatch, caplog, payload, body, outcome):
    body = {**body, "usage": _usage()}
    monkeypatch.setattr(openai_responses._requests, "post", lambda **kwargs: _response(body))

    result = _call(payload)

    assert result["count"].startswith("Invalid structured response")
    event, = _events(caplog)
    assert event["outcome"] == outcome
    assert event["status_code"] == 200
    assert event["usage"]["input_tokens"] == 100
    assert event["usage"]["output_tokens_details"]["reasoning_tokens"] == 30
    if outcome == "incomplete":
        assert event["incomplete_reason"] == "max_output_tokens"
        assert "max_output_tokens" in result["count"]


def test_retry_attempts_share_id_and_count_all_http_usage_once(monkeypatch, caplog, payload):
    responses = iter([
        _response(_completed(status="incomplete", usage=_usage())),
        _response(_completed(output_text="not JSON", usage=_usage())),
        _response(_completed(output_text='{"count":"invalid"}', usage=_usage())),
        _response(
            {"error": {"message": "Rate limit reached"}, "usage": _usage()},
            status=429,
            headers={"retry-after": "3"},
        ),
        _response(_completed(usage=_usage())),
    ])
    calls = []
    sleeps = []

    def post(**kwargs):
        calls.append(deepcopy(kwargs))
        return next(responses)

    monkeypatch.setenv("WRANGLES_OPENAI_LOG_METRICS", "true")
    monkeypatch.setenv("WRANGLES_OPENAI_LOG_EVERY", "5")
    monkeypatch.setattr(openai_responses._requests, "post", post)
    monkeypatch.setattr(openai_responses._time, "sleep", sleeps.append)

    assert _call(payload, retries=4) == {"count": 2}

    events = _events(caplog)
    assert [event["attempt"] for event in events] == [1, 2, 3, 4, 5]
    assert len({event["call_id"] for event in events}) == 1
    assert [event["outcome"] for event in events] == [
        "incomplete", "json_error", "schema_error", "http_error", "success"
    ]
    assert sleeps == [1, 2, 4, 3.0]
    assert [call["timeout"] for call in calls] == [12] * 5
    assert all(call["json"] == calls[0]["json"] for call in calls)
    assert all(call["json"]["max_output_tokens"] == 256 for call in calls)
    summary, = _events(caplog, "openai_rate_limit_summary")
    assert summary["responses"] == 5
    assert summary["input_tokens"] == 500
    assert summary["output_tokens"] == 200
    assert summary["cached_tokens"] == 400
    assert summary["cache_hit_responses"] == 5


def test_malformed_response_json_counts_http_attempt_without_inventing_usage(
    monkeypatch, caplog, payload
):
    response = _response({})
    response._content = b"<not-json>"
    monkeypatch.setattr(openai_responses._requests, "post", lambda **kwargs: response)
    monkeypatch.setenv("WRANGLES_OPENAI_LOG_METRICS", "true")
    monkeypatch.setenv("WRANGLES_OPENAI_LOG_EVERY", "1")

    result = _call(payload)

    assert result["count"].startswith("Invalid structured response")
    event, = _events(caplog)
    assert event["outcome"] == "json_error"
    assert event["usage"]["input_tokens"] is None
    assert event["usage"]["output_tokens"] is None
    assert event["usage"]["input_tokens_details"]["cached_tokens"] is None
    assert event["usage"]["output_tokens_details"]["reasoning_tokens"] is None
    summary, = _events(caplog, "openai_rate_limit_summary")
    assert summary["responses"] == 1


@pytest.mark.parametrize("error_type,outcome", [
    (requests.exceptions.Timeout, "timeout"),
    (requests.exceptions.ConnectionError, "transport_error"),
    (RuntimeError, "transport_error"),
])
def test_transport_attempts_are_logged_with_monotonic_elapsed_and_no_stale_response(
    monkeypatch, caplog, payload, error_type, outcome
):
    calls = []
    clock = iter([10, 10.5, 20, 22])

    def post(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _response(_completed(status="incomplete", usage=_usage()))
        raise error_type("synthetic-private-key data:image/png;base64," + "A" * 500)

    monkeypatch.setattr(openai_responses._requests, "post", post)
    monkeypatch.setattr(openai_responses._time, "monotonic", lambda: next(clock))
    monkeypatch.setenv("WRANGLES_OPENAI_LOG_METRICS", "true")
    monkeypatch.setenv("WRANGLES_OPENAI_LOG_EVERY", "1")

    result = _call(payload, retries=1)

    first, last = _events(caplog)
    assert last["call_id"] == first["call_id"]
    assert last["attempt"] == 2
    assert last["outcome"] == outcome
    assert last["elapsed_seconds"] == 2
    assert last["response_id"] is None
    assert last["response_status"] is None
    assert last["status_code"] is None
    assert last["usage"]["input_tokens"] is None
    assert len(_events(caplog, "openai_rate_limit_summary")) == 1
    assert "synthetic-private-key" not in caplog.text + str(result)
    assert "A" * 500 not in caplog.text + str(result)
    if outcome == "timeout":
        assert result["count"] == "Timed Out"
    else:
        assert "[REDACTED]" in result["count"]
        assert len(result["count"]) <= 512


@pytest.mark.parametrize("code,message,expected", [
    ("model_not_found", "No such model", "does not exist or is not accessible"),
    ("invalid_schema", "Invalid schema: private request", "schema submitted for output"),
    ("invalid_api_key", "Incorrect API key: synthetic-private-key", "missing or invalid"),
])
def test_fatal_http_errors_log_attempt_before_raising_without_retry(
    monkeypatch, caplog, payload, code, message, expected
):
    calls = []
    sleeps = []

    def post(**kwargs):
        calls.append(kwargs)
        return _response(
            {"error": {"code": code, "message": message}, "usage": _usage()},
            status=404 if code == "model_not_found" else 400,
        )

    monkeypatch.setattr(openai_responses._requests, "post", post)
    monkeypatch.setattr(openai_responses._time, "sleep", sleeps.append)

    with pytest.raises(ValueError, match=expected):
        _call(payload, retries=3)

    event, = _events(caplog)
    assert event["outcome"] == "http_error"
    assert event["usage"]["input_tokens"] == 100
    assert len(calls) == 1
    assert sleeps == []
    assert "private request" not in caplog.text
    assert "synthetic-private-key" not in caplog.text


@pytest.mark.parametrize("mode", ["http", "schema", "json", "refusal", "incomplete"])
def test_error_text_never_echoes_credentials_or_base64(monkeypatch, caplog, payload, mode):
    private = "synthetic-private-key"
    encoded = "QUJD" * 256
    echoed = f'Authorization: ****** data:image/png;base64,{encoded}'
    if mode == "http":
        body = {"error": {"message": echoed, "param": echoed, "type": echoed}}
        status = 400
    elif mode == "schema":
        body = _completed(output_text=json.dumps({"count": echoed}))
        status = 200
    elif mode == "json":
        body = _completed(output_text=echoed)
        status = 200
    elif mode == "incomplete":
        body = _completed(status="incomplete", incomplete_details={"reason": echoed})
        status = 200
    else:
        body = {
            "output": [{"type": "message", "content": [{"type": "refusal", "refusal": echoed}]}]
        }
        status = 200
    monkeypatch.setattr(
        openai_responses._requests, "post", lambda **kwargs: _response(body, status=status)
    )

    result = _call(payload)

    assert private not in caplog.text + str(result)
    assert encoded not in caplog.text + str(result)
    assert "Authorization: Bearer" not in caplog.text + str(result)
    assert len(_events(caplog)) == 1


def test_diagnostic_fields_are_bounded_and_whitelisted(monkeypatch, caplog, payload):
    private = "synthetic-private-key"
    body = _completed(
        id=private,
        model="A" * 4096,
        status={"secret": private},
        usage={
            "input_tokens": private,
            "output_tokens": False,
            "total_tokens": 10**100,
            "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": -1},
            "output_tokens_details": {"reasoning_tokens": 2},
            "provider_request_echo": private,
        },
    )
    monkeypatch.setattr(
        openai_responses._requests,
        "post",
        lambda **kwargs: _response(body, headers={"x-request-id": private}),
    )

    assert _call(payload) == {"count": 2}

    event, = _events(caplog)
    assert event["response_model"] is None
    assert event["response_id"] is None
    assert event["request_id"] is None
    assert event["response_status"] is None
    assert event["usage"]["input_tokens"] is None
    assert event["usage"]["output_tokens"] is None
    assert event["usage"]["total_tokens"] is None
    assert event["usage"]["input_tokens_details"]["cached_tokens"] == 0
    assert event["usage"]["input_tokens_details"]["cache_write_tokens"] is None
    assert event["usage"]["output_tokens_details"]["reasoning_tokens"] == 2
    assert event["usage"]["provider_request_echo"] is None
    assert private not in caplog.text
    assert len(json.dumps(event)) < 2000


@pytest.mark.parametrize("data", ["bolt", {"description": "é bolt", "quantity": 2}, ["a", "b"]])
def test_text_only_requests_remain_exactly_unchanged(monkeypatch, caplog, payload, data):
    calls = []
    original = deepcopy(payload)
    monkeypatch.setattr(
        openai_responses._requests,
        "post",
        lambda **kwargs: calls.append(deepcopy(kwargs)) or _response(_completed()),
    )

    assert _call(payload, data=data) == {"count": 2}
    assert _call(payload, data=data) == {"count": 2}

    expected_content = (
        json.dumps(data, ensure_ascii=False, default=str, indent=2)
        if isinstance(data, (dict, list)) else str(data)
    )
    assert calls[0]["json"] == {
        **original, "input": [{"role": "user", "content": f"DATA:\n{expected_content}"}]
    }
    assert calls[0] == calls[1]
    assert payload == original
    assert len({event["call_id"] for event in _events(caplog)}) == 2


def test_prepared_records_use_content_without_stringifying_attachments(monkeypatch, payload):
    content = [
        {"type": "input_text", "text": "DATA:\nbolt"},
        {"type": "input_image", "image_url": "https://example.test/bolt.png"},
    ]

    class PreparedRecord:
        text = "bolt"
        attachments = ()

        def content(self):
            return deepcopy(content)

        def __str__(self):
            pytest.fail("Prepared records must not be stringified")

    calls = []
    monkeypatch.setattr(openai_responses._ai_attachments, "PreparedRecord", PreparedRecord)
    monkeypatch.setattr(
        openai_responses._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or _response(_completed()),
    )

    assert _call(payload, data=PreparedRecord()) == {"count": 2}
    assert calls[0]["json"]["input"] == [{"role": "user", "content": content}]


@pytest.mark.parametrize("status", [400, 404, 415, 422])
@pytest.mark.parametrize("prepared", [False, True], ids=["text", "attachments"])
def test_attachment_rejections_raise_actionable_errors_after_attempt_accounting(
    monkeypatch, caplog, payload, status, prepared
):
    calls = []
    sleeps = []
    encoded = "QUJD" * 256
    body = {
        "error": {
            "message": f"Rejected request: synthetic-private-key data:image/png;base64,{encoded}",
        },
        "usage": _usage(),
    }

    def post(**kwargs):
        calls.append(kwargs)
        return _response(body, status=status)

    monkeypatch.setattr(openai_responses._requests, "post", post)
    monkeypatch.setattr(openai_responses._time, "sleep", sleeps.append)
    monkeypatch.setenv("WRANGLES_OPENAI_LOG_METRICS", "true")
    monkeypatch.setenv("WRANGLES_OPENAI_LOG_EVERY", "1")
    data = (
        openai_responses._ai_attachments.PreparedRecord(text="bolt", attachments=())
        if prepared else "bolt"
    )

    if prepared:
        with pytest.raises(ValueError, match="attachment request") as error:
            _call(payload, data=data, retries=2)
        assert f"HTTP {status}" in str(error.value)
        assert "model" in str(error.value)
        assert "format, size, and model context limits" in str(error.value)
        assert "synthetic-private-key" not in str(error.value)
        assert encoded not in str(error.value)
    else:
        result = _call(payload, data=data, retries=2)
        assert f"status={status}" in result["count"]

    event, = _events(caplog)
    assert event["outcome"] == "http_error"
    assert event["status_code"] == status
    assert event["usage"]["input_tokens"] == 100
    assert event["call_id"]
    summary, = _events(caplog, "openai_rate_limit_summary")
    assert summary["responses"] == 1
    assert summary["input_tokens"] == 100
    assert len(calls) == 1
    assert sleeps == []
    assert encoded not in caplog.text
    assert "synthetic-private-key" not in caplog.text


@pytest.mark.parametrize("request_key", ["a" * 64, "synthetic-private-key"])
def test_request_key_correlation_accepts_only_hashed_identity(
    monkeypatch, caplog, payload, request_key
):
    monkeypatch.setattr(
        openai_responses._requests, "post", lambda **kwargs: _response(_completed())
    )

    assert _call(payload, request_key=request_key) == {"count": 2}

    event, = _events(caplog)
    assert event["call_id"]
    assert event["request_key"] == ("a" * 64 if request_key == "a" * 64 else None)
    assert "synthetic-private-key" not in caplog.text


def test_prepared_record_source_identity_is_associated_with_every_retry(
    monkeypatch, caplog, payload
):
    module = openai_responses._ai_attachments
    contents = [b"%PDF-private-document-data", b"\x89PNG\r\n\x1a\nprivate-image-data"]
    attachments = tuple(
        module._Attachment(
            id=source_id,
            media_type=media_type,
            data=content,
            sha256=hashlib.sha256(content).hexdigest(),
        )
        for source_id, media_type, content in zip(
            ["spec-sheet", "photo"], ["application/pdf", "image/png"], contents
        )
    )
    data = module.PreparedRecord(text="confidential attached row", attachments=attachments)
    calls = []
    responses = iter([
        _response({"error": {"message": "Rate limit reached"}}, status=429),
        _response(_completed()),
    ])

    def post(**kwargs):
        calls.append(deepcopy(kwargs))
        return next(responses)

    monkeypatch.setattr(openai_responses._requests, "post", post)

    assert _call(payload, data=data, retries=1) == {"count": 2}

    events = _events(caplog)
    expected = [
        {key: value for key, value in attachment.identity().items() if key != "detail"}
        for attachment in attachments
    ]
    assert len(events) == 2
    assert all(event["attachments"] == expected for event in events)
    assert len({event["call_id"] for event in events}) == 1
    assert calls[0]["json"] == calls[1]["json"]
    assert calls[0]["json"]["input"] == [{"role": "user", "content": data.content()}]
    for content in contents:
        assert base64.b64encode(content).decode() not in caplog.text
    assert "private-document-data" not in caplog.text
    assert "private-image-data" not in caplog.text
    assert "confidential attached row" not in caplog.text


def test_attachment_source_diagnostics_bound_and_filter_identity_fields(
    monkeypatch, caplog, payload
):
    module = openai_responses._ai_attachments
    attachment = module._Attachment(
        id="private/folder/specification.pdf",
        media_type="data:synthetic-private-key",
        data=b"private-document-data",
        sha256="synthetic-private-key",
    )
    data = module.PreparedRecord(
        text="confidential attached row",
        attachments=(attachment,) * (module.MAX_ATTACHMENTS + 2),
    )
    monkeypatch.setattr(
        openai_responses._requests, "post", lambda **kwargs: _response(_completed())
    )

    assert _call(payload, data=data) == {"count": 2}

    event, = _events(caplog)
    assert event["attachments"] == [
        {"id": None, "media_type": None, "sha256": None}
    ] * module.MAX_ATTACHMENTS
    assert "private/folder" not in caplog.text
    assert "private-document-data" not in caplog.text
    assert "synthetic-private-key" not in caplog.text


@pytest.mark.parametrize("prepared", [False, True], ids=["text", "attachments"])
def test_provider_error_guidance_survives_general_credential_and_binary_sanitizing(
    monkeypatch, caplog, payload, prepared
):
    encoded = "QUJD" * 1024
    guidance = "Maximum context length is 4096 tokens; reduce max_output_tokens or attachment size."
    message = (
        f"{guidance} Authorization: ******; "
        "API key provided: synthetic-private-key; password='other password'; "
        "client_secret=other-secret; "
        f"file_data=data:application/pdf;base64,{encoded}"
    )
    monkeypatch.setattr(
        openai_responses._requests,
        "post",
        lambda **kwargs: _response({"error": {"message": message}}, status=400),
    )
    if prepared:
        data = openai_responses._ai_attachments.PreparedRecord(text="bolt", attachments=())
        with pytest.raises(ValueError) as error:
            _call(payload, data=data)
        result = str(error.value)
    else:
        result = _call(payload)["count"]

    assert guidance in result
    for private in [
        encoded, "synthetic-private-key", "other-private-token", "other password", "other-secret"
    ]:
        assert private not in result + caplog.text
    assert len(result) < 1000


def test_arbitrary_transport_guidance_is_sanitized_without_test_specific_messages(
    monkeypatch, caplog, payload
):
    guidance = "TLS negotiation failed; use an endpoint that supports TLS 1.2."

    def post(**kwargs):
        raise requests.exceptions.SSLError(
            f"{guidance} api_key=synthetic-private-key; ******"
        )

    monkeypatch.setattr(openai_responses._requests, "post", post)

    result = _call(payload)["count"]

    assert guidance in result
    assert "synthetic-private-key" not in result + caplog.text
    assert "unrelated-private-token" not in result + caplog.text
    assert _events(caplog)[0]["outcome"] == "transport_error"


@pytest.mark.parametrize("echo", [
    '{"input":[{"file_data":"QUJD"}],"instructions":"private input text"}',
    "data:image/png;base64," + "QUJD" * 50000,
    "file_data=QUJD",
    "data:image/png;base64,QUJD\nQUJD\nQUJD",
    "QUJD" * 50000,
])
def test_huge_provider_bodies_and_small_labeled_binary_are_not_logged(
    monkeypatch, caplog, payload, echo
):
    guidance = "Unsupported content format; supply a PNG image."
    monkeypatch.setattr(
        openai_responses._requests,
        "post",
        lambda **kwargs: _response(
            {"error": {"message": f"{guidance} {echo}"}}, status=400
        ),
    )

    result = _call(payload)["count"]

    assert guidance in result
    assert "QUJD" not in result + caplog.text
    assert "private input text" not in result + caplog.text
    assert len(result) < 1000
    assert all(len(record.getMessage()) < 3000 for record in caplog.records)


def test_usage_retains_future_numeric_fields_and_nested_breakdowns(
    monkeypatch, caplog, payload
):
    usage = _usage()
    usage.update({
        "future_tokens": 7,
        "future_cost": 0.125,
        "future_missing": None,
        "future_text": "private-provider-data",
        "modalities": [{"tokens": 5}, 2, None],
        "privatecredential": 999,
    })
    usage["input_tokens_details"]["future_cache_write"] = {
        "short_lived": 3, "long_lived": 2, "unknown": None,
    }
    usage["output_tokens_details"]["future_tool_tokens"] = 4
    monkeypatch.setattr(
        openai_responses._requests,
        "post",
        lambda **kwargs: _response(_completed(usage=usage)),
    )

    assert _call(payload, api_key="privatecredential") == {"count": 2}

    event, = _events(caplog)
    assert event["usage"]["future_tokens"] == 7
    assert event["usage"]["future_cost"] == 0.125
    assert event["usage"]["future_missing"] is None
    assert event["usage"]["future_text"] is None
    assert event["usage"]["modalities"] == [{"tokens": 5}, 2, None]
    assert event["usage"]["input_tokens_details"]["future_cache_write"] == {
        "short_lived": 3, "long_lived": 2, "unknown": None,
    }
    assert event["usage"]["output_tokens_details"]["future_tool_tokens"] == 4
    assert event["usage"]["input_tokens_details"]["cache_write_tokens"] == 10
    assert event["usage"]["output_tokens_details"]["reasoning_tokens"] == 30
    assert event["usage"]["total_tokens"] == 140
    assert "privatecredential" not in event["usage"]
    assert "private-provider-data" not in caplog.text


def test_future_usage_fields_have_bounded_key_count_and_depth(monkeypatch, caplog, payload):
    usage = {
        "deep": {"a": {"b": {"c": {"d": {"tokens": 1}}}}},
        "modalities": list(range(100)),
        **{f"future_{index}": index for index in range(1000)},
        **_usage(),
    }
    monkeypatch.setattr(
        openai_responses._requests,
        "post",
        lambda **kwargs: _response(_completed(usage=usage)),
    )

    assert _call(payload) == {"count": 2}

    event, = _events(caplog)
    assert event["usage"]["deep"] == {"a": {"b": {"c": None}}}
    assert event["usage"]["modalities"] == list(range(16))
    assert "future_999" not in event["usage"]
    assert len(event["usage"]) <= 64 + len(openai_responses._USAGE_TOKEN_FIELDS) + 2
    assert event["usage"]["input_tokens"] == 100
    assert event["usage"]["input_tokens_details"]["cached_tokens"] == 80
    assert len(json.dumps(event)) < 10000


@pytest.mark.parametrize("usage,expected,missing,cache_hits", [
    (None, {"input_tokens": None, "output_tokens": None, "cached_tokens": None}, 1, None),
    (
        {"input_tokens": 0, "output_tokens": 0, "input_tokens_details": {"cached_tokens": 0}},
        {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0},
        0,
        0,
    ),
    (_usage(), {"input_tokens": 100, "output_tokens": 40, "cached_tokens": 80}, 0, 1),
])
def test_aggregate_totals_distinguish_unknown_from_observed_zero(
    monkeypatch, caplog, payload, usage, expected, missing, cache_hits
):
    monkeypatch.setenv("WRANGLES_OPENAI_LOG_METRICS", "true")
    monkeypatch.setenv("WRANGLES_OPENAI_LOG_EVERY", "1")
    monkeypatch.setattr(
        openai_responses._requests,
        "post",
        lambda **kwargs: _response(_completed(usage=usage)),
    )

    assert _call(payload) == {"count": 2}

    summary, = _events(caplog, "openai_rate_limit_summary")
    for name, value in expected.items():
        assert summary[name] == value
        assert summary[f"{name}_missing_responses"] == missing
    assert summary["responses"] == 1
    assert summary["usage_totals_partial"] is bool(missing)
    assert summary["cache_hit_responses"] == cache_hits


def test_aggregate_partial_sums_include_per_count_missing_response_totals(
    monkeypatch, caplog, payload
):
    responses = iter([
        _response(_completed()),
        _response(_completed(usage=_usage())),
        _response(_completed(usage={
            "output_tokens": 0, "input_tokens_details": {"cached_tokens": 0},
        })),
    ])
    monkeypatch.setenv("WRANGLES_OPENAI_LOG_METRICS", "true")
    monkeypatch.setenv("WRANGLES_OPENAI_LOG_EVERY", "1")
    monkeypatch.setattr(openai_responses._requests, "post", lambda **kwargs: next(responses))

    for _ in range(3):
        assert _call(payload) == {"count": 2}

    first, second, last = _events(caplog, "openai_rate_limit_summary")
    assert first["input_tokens"] is None
    assert first["output_tokens"] is None
    assert first["cached_tokens"] is None
    assert second["input_tokens"] == 100
    assert second["usage_totals_partial"] is True
    assert last["responses"] == 3
    assert last["input_tokens"] == 100
    assert last["input_tokens_missing_responses"] == 2
    assert last["output_tokens"] == 40
    assert last["output_tokens_missing_responses"] == 1
    assert last["cached_tokens"] == 80
    assert last["cached_tokens_missing_responses"] == 1
    assert last["cache_hit_responses"] == 1
    assert last["usage_totals_partial"] is True
