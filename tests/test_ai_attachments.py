"""Offline multimodal contract tests; fixtures contain only synthetic data."""
import base64
from contextlib import closing
from copy import deepcopy
import hashlib
import io
import json
import logging
import os
import struct
from types import SimpleNamespace
from unittest.mock import Mock, call
import zlib

import boto3
from botocore.exceptions import (
    ClientError, NoCredentialsError, PartialCredentialsError, ReadTimeoutError,
)
from botocore.response import StreamingBody
from botocore.stub import Stubber
import pytest
import requests

from wrangles import ai_attachments, ai_cache, extract


@pytest.fixture
def files(tmp_path):
    pdf = tmp_path / "specimen.pdf"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = b"BT /F1 16 Tf 20 100 Td (Synthetic RED specimen) Tj ET"
    objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    data = b"%PDF-1.4\n"
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n"
    data += b"".join(f"{offset:010} 00000 n \n".encode() for offset in offsets[1:])
    data += f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    pdf.write_bytes(data)

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))

    image = tmp_path / "red.png"
    image.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00" + b"\xff\x00\x00" * 2 + b"\x00" + b"\xff\x00\x00" * 2))
        + chunk(b"IEND", b"")
    )
    return pdf, image


@pytest.fixture(autouse=True)
def transport(monkeypatch):
    ai_cache.clear()
    calls = []

    def post(**kwargs):
        calls.append(deepcopy(kwargs))
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({
            "output_text": '{"color":"red"}',
            "status": "completed",
        }).encode()
        return response

    monkeypatch.setattr(extract._openai_responses._requests, "post", post)
    yield calls
    ai_cache.clear()


def run(input=None, **kwargs):
    return extract.ai(input, kwargs.pop("api_key", "test-tenant"), output={"color": "Color"}, **kwargs)


@pytest.fixture
def s3_store(monkeypatch):
    """Fake only AWS transport; real StreamingBody enforces its read contract."""
    state = SimpleNamespace(objects={}, requests=[], clients=[], sessions=[], streams=[])

    def get_object(**kwargs):
        state.requests.append(kwargs)
        entry = state.objects[(kwargs["Bucket"], kwargs["Key"])]
        if isinstance(entry, Exception):
            raise entry
        entry = {"data": entry} if isinstance(entry, bytes) else entry
        raw = io.BytesIO(entry["data"])
        size = entry.get("size", len(entry["data"]))
        # A bounded, nonempty read does not make StreamingBody verify this size.
        body = StreamingBody(raw, size)
        body.read = Mock(wraps=body.read, side_effect=entry.get("read_error"))
        body.close = Mock(wraps=body.close)
        state.streams.append((body, raw))
        return {"Body": body, "ContentLength": size}

    def session_factory():
        # Match botocore clients: close() exists, context-manager methods do not.
        client = SimpleNamespace(get_object=Mock(side_effect=get_object), close=Mock())
        session = SimpleNamespace(client=Mock(return_value=client))
        state.sessions.append(session)
        state.clients.append(client)
        return session

    state.factory = Mock(side_effect=session_factory)
    state.default_session = boto3.DEFAULT_SESSION
    monkeypatch.setattr(boto3, "Session", state.factory)
    monkeypatch.setattr(boto3, "client", Mock(side_effect=AssertionError("global boto3 client used")))
    monkeypatch.setattr(
        boto3, "setup_default_session",
        Mock(side_effect=AssertionError("global boto3 session changed")),
    )
    return state


def test_text_paths_urls_and_dicts_are_never_loaded(transport, s3_store):
    values = [
        "/missing/file.pdf", "https://example.test/image.png",
        {"path": "/missing/file.pdf"}, "s3://specimens/missing.pdf",
        {"path": "s3://specimens/missing.png"},
    ]
    assert run(values) == [{"color": "red"}] * len(values)
    assert all(isinstance(call["json"]["input"][0]["content"], str) for call in transport)
    assert run(None, attachments=[]) == {"color": "red"}
    assert transport[-1]["json"]["input"][0]["content"] == "DATA:\nNone"
    s3_store.factory.assert_not_called()


@pytest.mark.parametrize("file_index", [0, 1])
def test_standalone_file_sends_actual_bytes_and_stable_source(files, transport, file_index):
    path = files[file_index]
    descriptor = {"path": path, "id": "specimen"}
    assert run(attachments=[descriptor]) == {"color": "red"}
    parts = transport[0]["json"]["input"][0]["content"]
    assert len(parts) == 2
    assert '"id": "specimen"' in parts[0]["text"]
    visual = parts[1]
    data_url = visual["file_data" if file_index == 0 else "image_url"]
    assert base64.b64decode(data_url.split(",", 1)[1]) == path.read_bytes()
    if file_index == 0:
        assert visual["type"] == "input_file"
        assert visual["filename"] == "specimen.pdf"
    else:
        assert visual["type"] == "input_image"
        assert visual["detail"] == "auto"
    assert descriptor == {"path": path, "id": "specimen"}
    assert transport[0]["json"]["store"] is True


def test_mixed_and_multiple_attachments_keep_source_order(files, transport):
    pdf, image = files
    assert run(
        {"context": "Compare the photo with the drawing"},
        attachments=[{"path": pdf, "id": "drawing"}, {"path": image, "id": "photo", "detail": "high"}],
        model="gpt-5.4", reasoning={"effort": "medium"}, timeout=180, threads=1, retries=0,
        max_output_tokens=16000, metadata={"batch": "synthetic"}, store=False,
    ) == {"color": "red"}
    call = transport[0]
    parts = call["json"]["input"][0]["content"]
    assert [part["type"] for part in parts] == ["input_text", "input_text", "input_file", "input_text", "input_image"]
    assert "Compare the photo" in parts[0]["text"]
    assert '"id": "drawing"' in parts[1]["text"]
    assert '"id": "photo"' in parts[3]["text"]
    assert parts[4]["detail"] == "high"
    assert call["timeout"] == 180
    assert call["json"]["max_output_tokens"] == 16000
    assert call["json"]["reasoning"] == {"effort": "medium"}
    assert call["json"]["metadata"]["batch"] == "synthetic"
    assert call["json"]["store"] is False


def test_batch_rows_are_not_reinterpreted_as_attachments(files, transport):
    pdf, image = files
    rows = [None, "text plus image", "plain"]
    assert run(rows, attachments=[[{"path": pdf}], [{"path": image}], []], threads=1) == [{"color": "red"}] * 3
    contents = [call["json"]["input"][0]["content"] for call in transport]
    assert contents[0][1]["type"] == "input_file"
    assert contents[1][0]["text"] == "DATA:\ntext plus image"
    assert contents[2] == "DATA:\nplain"
    assert run([], attachments=[]) == []


@pytest.mark.parametrize("attachments", [[{"path": "file.pdf"}], [], [[], []], None])
def test_batch_requires_explicit_aligned_lists(attachments, transport):
    if attachments is None:
        assert run(["a"]) == [{"color": "red"}]
    else:
        with pytest.raises(ValueError, match="one attachment list per input record"):
            run(["a"], attachments=attachments)
        assert transport == []


def test_cache_hashes_bytes_ids_order_detail_and_settings(files, transport):
    pdf, image = files
    descriptors = [{"path": pdf, "id": "doc"}, {"path": image, "id": "photo"}]
    for _ in range(2):
        run("same", attachments=descriptors)
    assert len(transport) == 1
    # Same path, same length, new bytes must miss even if filesystem timestamps don't help.
    pdf.write_bytes(pdf.read_bytes().replace(b"RED", b"TAN"))
    run("same", attachments=descriptors)
    run("same", attachments=list(reversed(descriptors)))
    run("same", attachments=[descriptors[0], {**descriptors[1], "detail": "high"}])
    run("same", attachments=[{**descriptors[0], "id": "other"}, descriptors[1]])
    run("same", attachments=descriptors, max_output_tokens=8000)
    run("same", attachments=descriptors, store=False)
    run("same", attachments=descriptors, metadata={"trial": "other"})
    run("changed text", attachments=descriptors)
    assert len(transport) == 9


def test_cache_is_tenant_isolated_and_deduplicates_records(files, transport, caplog):
    descriptor = {"path": files[1]}
    with caplog.at_level(logging.INFO):
        run(["same", "same"], attachments=[[descriptor], [descriptor]])
        run("same", attachments=[descriptor])
        run("same", attachments=[descriptor], api_key="other-test-tenant")
    assert len(transport) == 2
    assert transport[0]["headers"]["Authorization"] != transport[1]["headers"]["Authorization"]
    events = [json.loads(record.message) for record in caplog.records if record.message.startswith("{")]
    outcomes = {event["outcome"] for event in events if event["event"] == "extract_ai_cache_lookup"}
    assert {"hit", "miss", "batch_duplicate"} <= outcomes
    assert "other-test-tenant" not in caplog.text
    assert "base64" not in caplog.text


def test_snapshot_used_for_cache_identity_and_sent_bytes(files):
    path = files[0]
    before = path.read_bytes()
    prepared = ai_attachments.prepare([None], [{"path": path}], True, str)[0]
    path.write_bytes(before.replace(b"RED", b"TAN"))
    assert prepared.identity()["attachments"][0]["sha256"] == hashlib.sha256(before).hexdigest()
    assert base64.b64decode(prepared.content()[1]["file_data"].split(",")[1]) == before
    assert "Synthetic" not in repr(prepared)


@pytest.mark.parametrize("descriptor, error", [
    ({}, "path is required"),
    ({"url": "https://example.test/file.pdf"}, "supported fields"),
    ({"path": "https://example.test/file.pdf"}, "URLs"),
    ({"path": "file-id"}, "supported formats"),
    ({"path": "missing.pdf"}, "missing or unreadable"),
    ({"path": b"bytes"}, "local filesystem path"),
    ({"path": "file.png", "id": "../bad"}, "id must"),
    ({"path": "file.png", "detail": "original"}, "detail must"),
    ({"path": "file.pdf", "detail": "high"}, "only to images"),
])
def test_descriptor_validation_before_request(descriptor, error, transport):
    with pytest.raises((ValueError, TypeError), match=error):
        run(attachments=[descriptor])
    assert transport == []


def test_rejects_empty_mismatched_directory_and_oversized_files(tmp_path, monkeypatch, transport):
    path = tmp_path / "file.png"
    path.write_bytes(b"")
    with pytest.raises(ValueError, match="empty"):
        run(attachments=[{"path": path}])
    path.write_bytes(b"not a PNG")
    with pytest.raises(ValueError, match="contents do not match"):
        run(attachments=[{"path": path}])
    monkeypatch.setattr(ai_attachments, "MAX_FILE_BYTES", 4)
    with pytest.raises(ValueError, match="file exceeds"):
        run(attachments=[{"path": path}])
    directory = tmp_path / "directory.pdf"
    directory.mkdir()
    with pytest.raises(ValueError, match="regular file"):
        run(attachments=[{"path": directory}])
    assert transport == []


def test_count_duplicate_id_record_and_batch_limits(files, monkeypatch, transport):
    descriptor = {"path": files[0]}
    with pytest.raises(ValueError, match="at most 16"):
        run(attachments=[descriptor] * 17)
    with pytest.raises(ValueError, match="unique"):
        run(attachments=[{**descriptor, "id": "same"}] * 2)
    monkeypatch.setattr(ai_attachments, "MAX_RECORD_BYTES", files[0].stat().st_size)
    with pytest.raises(ValueError, match="per-record"):
        run(attachments=[descriptor] * 2)
    monkeypatch.setattr(ai_attachments, "MAX_BATCH_BYTES", files[0].stat().st_size)
    with pytest.raises(ValueError, match="batch snapshot"):
        run([None, None], attachments=[[descriptor], [{"path": files[1]}]])
    assert transport == []


@pytest.mark.parametrize("settings", [
    {"protocol": "chat_completions"}, {"provider": "other"},
    {"model": "gpt-3.5-turbo"}, {"model": "o3-mini"},
    {"model": "gpt-4o-audio-preview"}, {"stream": True}, {"background": True},
])
def test_incompatible_settings_rejected_before_loading(settings, transport):
    with pytest.raises(ValueError):
        run(attachments=[{"path": "/does/not/exist.pdf"}], **settings)
    assert transport == []


def test_validates_all_records_before_sending_any(files, transport):
    with pytest.raises(ValueError, match="missing"):
        run([None, None], attachments=[[{"path": files[0]}], [{"path": "missing.pdf"}]])
    assert transport == []


def test_saved_schema_and_model_preserved(files, transport, monkeypatch):
    monkeypatch.setattr(extract._data, "model_content", lambda _: {
        "Settings": {"Model": "gpt-4.1"},
        "Columns": ["Find", "Type", "Description"],
        "data": [{"Find": "color", "Type": "string", "Description": "Color"}],
    })
    assert extract.ai(None, "test-tenant", model_id="synthetic-model", attachments=[{"path": files[0]}]) == {"color": "red"}
    assert transport[0]["json"]["model"] == "gpt-4.1"


def test_generic_output_keeps_scalar_and_list_return_shapes(files, monkeypatch):
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"output_text":"{\\"output\\":\\"red\\"}"}'
    monkeypatch.setattr(extract._openai_responses._requests, "post", lambda **_: response)
    arguments = {"api_key": "test-tenant", "output": "What color?"}
    descriptor = {"path": files[1]}
    assert extract.ai(None, attachments=[descriptor], **arguments) == "red"
    assert extract.ai([None, None], attachments=[[descriptor], [descriptor]], **arguments) == ["red", "red"]


def test_retry_keeps_snapshot_and_logs_usage_once_per_attempt(files, monkeypatch, caplog):
    path = files[0]
    before = path.read_bytes()
    calls = []

    def post(**kwargs):
        calls.append(deepcopy(kwargs))
        response = requests.Response()
        response.status_code = 200
        body = {
            "id": f"resp_{len(calls)}",
            "model": "gpt-5.4",
            "status": "completed",
            "output_text": '{"color":"red"}',
            "usage": {"input_tokens": 100, "output_tokens": 80, "output_tokens_details": {"reasoning_tokens": 60}},
        }
        if len(calls) == 1:
            body.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"})
            path.write_bytes(before.replace(b"RED", b"TAN"))
        response._content = json.dumps(body).encode()
        return response

    monkeypatch.setattr(extract._openai_responses._requests, "post", post)
    monkeypatch.setattr(extract._openai_responses, "_sleep_for_retry", lambda *args: None)
    with caplog.at_level(logging.INFO):
        assert run(attachments=[{"path": path}], retries=1) == {"color": "red"}
    assert len(calls) == 2
    assert calls[0]["json"] == calls[1]["json"]
    assert base64.b64decode(calls[1]["json"]["input"][0]["content"][1]["file_data"].split(",")[1]) == before
    events = [json.loads(record.message) for record in caplog.records if record.message.startswith("{")]
    attempts = [event for event in events if event["event"] == "openai_request_attempt"]
    lookup = next(event for event in events if event["event"] == "extract_ai_cache_lookup")
    assert [attempt["attempt"] for attempt in attempts] == [1, 2]
    assert [attempt["response_status"] for attempt in attempts] == ["incomplete", "completed"]
    assert {attempt["request_key"] for attempt in attempts} == {lookup["request_key"]}
    assert sum(attempt["usage"]["output_tokens"] for attempt in attempts) == 160
    run(attachments=[{"path": path}], retries=1)
    assert len(calls) == 3


@pytest.mark.parametrize("file_index, key, field, media_type", [
    (0, "nested/literal%2Fname%20with space.PDF", "file_data", "application/pdf"),
    (1, "nested//./red%23%3F.png", "image_url", "image/png"),
])
def test_s3_attachment_sends_exact_inline_bytes_and_literal_key(
    files, s3_store, transport, file_index, key, field, media_type,
):
    data = files[file_index].read_bytes()
    s3_store.objects[("specimens", key)] = data
    descriptor = {"path": f"s3://specimens/{key}", "id": "specimen"}
    original = deepcopy(descriptor)

    result = run(attachments=[descriptor])

    assert result == {"color": "red"}, "S3 attachments must preserve scalar results"
    assert s3_store.requests == [{"Bucket": "specimens", "Key": key}]
    parts = transport[0]["json"]["input"][0]["content"]
    assert parts[1][field] == f"data:{media_type};base64,{base64.b64encode(data).decode()}"
    assert json.loads(parts[0]["text"].removeprefix("DATA source: ")) == {
        "id": "specimen", "media_type": media_type,
    }
    assert "s3://" not in json.dumps(parts), "Source locations must not be sent to OpenAI"
    assert descriptor == original, "Preparation must not mutate descriptors"
    body, raw = s3_store.streams[0]
    body.read.assert_called_once_with(ai_attachments.MAX_FILE_BYTES + 1)
    body.close.assert_called_once_with()
    assert raw.closed, "Downloaded stream must be closed after success"
    s3_store.clients[0].close.assert_called_once_with()


def test_s3_mixed_batch_preserves_order_and_deduplicates_bucket_key(
    files, s3_store, transport, monkeypatch,
):
    pdf, image = files
    s3_store.objects[("specimens", "red.png")] = image.read_bytes()
    s3_store.objects[("other-bucket", "red.png")] = image.read_bytes()
    monkeypatch.setattr(
        ai_attachments, "MAX_BATCH_BYTES",
        len(pdf.read_bytes()) + 2 * len(image.read_bytes()),
    )
    remote = {"path": "s3://specimens/red.png", "id": "remote"}
    groups = [
        [{"path": pdf, "id": "local"}, remote],
        [{**remote, "id": "again", "detail": "high"}, {"path": pdf, "id": "local"}],
        [{"path": "s3://other-bucket/red.png", "id": "other"}],
    ]

    result = run(["first", "second", "third"], attachments=groups, threads=1)

    assert result == [{"color": "red"}] * 3
    assert s3_store.requests == [
        {"Bucket": "specimens", "Key": "red.png"},
        {"Bucket": "other-bucket", "Key": "red.png"},
    ], "Snapshots must deduplicate the bucket/key pair, not just the key"
    expected = [
        [pdf.read_bytes(), image.read_bytes()],
        [image.read_bytes(), pdf.read_bytes()],
        [image.read_bytes()],
    ]
    for index, (request, expected_bytes) in enumerate(zip(transport, expected)):
        parts = request["json"]["input"][0]["content"]
        assert parts[0]["text"] == f"DATA:\n{['first', 'second', 'third'][index]}"
        visual = parts[2::2]
        assert [
            base64.b64decode(part.get("file_data", part.get("image_url")).split(",", 1)[1])
            for part in visual
        ] == expected_bytes, "Mixed local and S3 attachment order must match each row"
    assert transport[1]["json"]["input"][0]["content"][2]["detail"] == "high"


def test_s3_cache_rereads_and_changed_bytes_create_new_request_key(
    files, s3_store, transport, caplog,
):
    before = files[0].read_bytes()
    after = before.replace(b"RED", b"TAN")
    s3_store.objects[("specimens", "same.pdf")] = before
    descriptor = {"path": "s3://specimens/same.pdf"}

    with caplog.at_level(logging.INFO):
        run("same", attachments=[descriptor])
        run("same", attachments=[descriptor])
        s3_store.objects[("specimens", "same.pdf")] = after
        run("same", attachments=[descriptor])

    assert len(s3_store.requests) == 3, "Every invocation must GET even with a warm result cache"
    assert len(transport) == 2, "Only unchanged attachment bytes may reuse a result"
    events = [json.loads(record.message) for record in caplog.records if record.message.startswith("{")]
    lookups = [event for event in events if event["event"] == "extract_ai_cache_lookup"]
    assert [event["outcome"] for event in lookups] == ["miss", "hit", "miss"]
    assert lookups[0]["request_key"] == lookups[1]["request_key"]
    assert lookups[0]["request_key"] != lookups[2]["request_key"]
    assert base64.b64decode(
        transport[1]["json"]["input"][0]["content"][2]["file_data"].split(",", 1)[1]
    ) == after


def test_s3_access_revoked_after_cache_warmup_does_not_reuse_result(files, s3_store, transport):
    s3_store.objects[("specimens", "same.pdf")] = files[0].read_bytes()
    descriptor = {"path": "s3://specimens/same.pdf"}
    run(attachments=[descriptor])
    s3_store.objects[("specimens", "same.pdf")] = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "private service detail"}}, "GetObject",
    )

    with pytest.raises(ValueError, match="S3 access denied"):
        run(attachments=[descriptor])

    assert len(s3_store.requests) == 2
    assert len(transport) == 1, "Denied access must not reach the model or return a cached result"
    assert all(client.close.call_count == 1 for client in s3_store.clients)


def test_s3_uses_fresh_sessions_standard_credentials_and_bounded_config(
    files, s3_store, monkeypatch,
):
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.setenv(name, "synthetic-test-value")
    monkeypatch.setenv("AWS_PROFILE", "synthetic-profile")
    environment_before = dict(os.environ)
    s3_store.objects[("specimens", "same.png")] = files[1].read_bytes()

    for _ in range(2):
        run(attachments=[{"path": "s3://specimens/same.png"}])

    assert s3_store.factory.call_args_list == [call(), call()], (
        "The standard AWS credential chain must receive no explicit session credentials"
    )
    assert s3_store.sessions[0] is not s3_store.sessions[1]
    for session in s3_store.sessions:
        args, kwargs = session.client.call_args
        assert args == ("s3",)
        assert set(kwargs) == {"config"}, "AWS credentials must not be overridden on the client"
        configuration = kwargs["config"]
        assert configuration.connect_timeout == 10
        assert configuration.read_timeout == 30
        assert configuration.retries == {"mode": "standard", "total_max_attempts": 3}
    assert boto3.DEFAULT_SESSION is s3_store.default_session
    boto3.client.assert_not_called()
    boto3.setup_default_session.assert_not_called()
    assert dict(os.environ) == environment_before, "AWS configuration must not mutate the environment"


@pytest.mark.parametrize("truncated", [False, True], ids=["complete", "truncated-valid-pdf"])
def test_s3_real_botocore_client_stubber_reads_and_closes_without_context_manager(
    files, transport, monkeypatch, tmp_path, truncated,
):
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.setenv(name, "synthetic-test-value")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "unused-aws-config"))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "unused-aws-credentials"))
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_PROFILE", raising=False)
    environment_before = dict(os.environ)
    default_session_before = boto3.DEFAULT_SESSION
    # Construct real SDK objects through the standard environment credential chain;
    # Stubber intercepts GetObject before any network request or request signing.
    session = boto3.Session()
    client = session.client("s3")
    monkeypatch.setattr(client, "close", Mock(wraps=client.close))
    monkeypatch.setattr(session, "client", Mock(return_value=client))
    factory = Mock(return_value=session)
    monkeypatch.setattr(boto3, "Session", factory)
    data = files[0].read_bytes()
    raw = io.BytesIO(data[:-8] if truncated else data)
    body = StreamingBody(raw, len(data))
    body.close = Mock(wraps=body.close)

    # Outer closers protect test cleanup even if an assertion fails. Assertions
    # inside this block verify production closed both resources first.
    with closing(client), closing(body), Stubber(client) as stubber:
        stubber.add_response(
            "get_object",
            {"Body": body, "ContentLength": len(data)},
            {"Bucket": "specimens", "Key": "literal%20key.pdf"},
        )

        if truncated:
            with pytest.raises(ValueError, match="download size did not match"):
                run(attachments=[{"path": "s3://specimens/literal%20key.pdf"}])
            assert transport == [], "Truncated content must not reach OpenAI"
        else:
            assert run(attachments=[{"path": "s3://specimens/literal%20key.pdf"}]) == {"color": "red"}
            part = transport[0]["json"]["input"][0]["content"][1]
            assert base64.b64decode(part["file_data"].split(",", 1)[1]) == data

        stubber.assert_no_pending_responses()
        client.close.assert_called_once_with()
        body.close.assert_called_once_with()
        assert raw.closed, "Production must close the real SDK response stream"
        factory.assert_called_once_with()
        assert session.get_credentials().method == "env"
        assert session.get_credentials().token == "synthetic-test-value"
        assert boto3.DEFAULT_SESSION is default_session_before
        assert dict(os.environ) == environment_before


@pytest.mark.parametrize("path", [
    "https://example.test/file.pdf", "http://example.test/file.png",
    "file:///local/file.pdf", "ftp://example.test/file.pdf", "data:application/pdf;base64,AAAA",
    "s3://", "s3:///file.pdf", "s3://specimens/", "s3://specimens",
    "s3://user@specimens/file.pdf", "s3://specimens:443/file.pdf",
    "s3://specimens/file.pdf?versionId=private", "s3://specimens/file.pdf#fragment",
    "s3://specimens/file.pdf?versionId=other.pdf", "s3://specimens/file.pdf#other.pdf",
    "s3://specimens/line\nbreak.pdf", "s3://specimens/null\x00.pdf",
    "s3://specimens/control\x7f.pdf", "s3://UPPERCASE/file.pdf",
    pytest.param("s3://specimens/" + "a" * 1021 + ".pdf", id="key-exceeds-1024-ascii-bytes"),
    pytest.param("s3://specimens/" + "é" * 511 + ".pdf", id="key-exceeds-1024-utf8-bytes"),
    "s3://specimens/file.gif", "s3://specimens/file", "S3://specimens/file.pdf",
])
def test_s3_invalid_or_unsupported_paths_fail_before_boto_calls(path, s3_store, transport):
    with pytest.raises(ValueError):
        run(attachments=[{"path": path}])

    s3_store.factory.assert_not_called()
    assert transport == [], "Invalid attachment locations must never call the model"


@pytest.mark.parametrize("size", [None, -1, True, "10"])
def test_s3_invalid_content_length_closes_body_and_client(size, s3_store, transport, files):
    s3_store.objects[("specimens", "file.pdf")] = {"data": files[0].read_bytes(), "size": size}

    with pytest.raises(ValueError, match="invalid object size"):
        run(attachments=[{"path": "s3://specimens/file.pdf"}])

    body, raw = s3_store.streams[0]
    body.read.assert_not_called()
    body.close.assert_called_once_with()
    assert raw.closed
    s3_store.clients[0].close.assert_called_once_with()
    assert transport == []


@pytest.mark.parametrize("truncated", [True, False], ids=["truncated-valid-pdf", "too-small-header"])
def test_s3_download_size_mismatch_closes_resources_and_rejects_partial_data(
    truncated, files, s3_store, transport,
):
    data = files[0].read_bytes()
    s3_store.objects[("specimens", "file.pdf")] = {
        "data": data[:-8] if truncated else data,
        "size": len(data) if truncated else len(data) - 1,
    }

    with pytest.raises(ValueError, match="download size did not match"):
        run(attachments=[{"path": "s3://specimens/file.pdf"}])

    body, raw = s3_store.streams[0]
    body.read.assert_called_once_with(ai_attachments.MAX_FILE_BYTES + 1)
    body.close.assert_called_once_with()
    assert raw.closed
    s3_store.clients[0].close.assert_called_once_with()
    assert transport == [], "A partial or inconsistent download must never reach the model"


@pytest.mark.parametrize("header_oversize", [True, False], ids=["header", "actual-bytes"])
def test_s3_file_limit_checks_header_and_bounded_actual_bytes(
    files, s3_store, transport, monkeypatch, header_oversize,
):
    data = files[0].read_bytes()
    limit = len(data) - 1
    monkeypatch.setattr(ai_attachments, "MAX_FILE_BYTES", limit)
    s3_store.objects[("specimens", "file.pdf")] = {
        "data": data, "size": len(data) if header_oversize else limit,
    }

    with pytest.raises(ValueError, match="file exceeds"):
        run(attachments=[{"path": "s3://specimens/file.pdf"}])

    body, raw = s3_store.streams[0]
    if header_oversize:
        body.read.assert_not_called()
    else:
        body.read.assert_called_once_with(limit + 1)
    body.close.assert_called_once_with()
    assert raw.closed
    s3_store.clients[0].close.assert_called_once_with()
    assert transport == []


@pytest.mark.parametrize("remote_first", [False, True])
@pytest.mark.parametrize("limit_name, message", [
    ("MAX_RECORD_BYTES", "per-record"),
    ("MAX_BATCH_BYTES", "batch snapshot"),
])
def test_s3_and_local_files_share_record_and_batch_limits(
    files, s3_store, transport, monkeypatch, remote_first, limit_name, message,
):
    pdf, image = files
    s3_store.objects[("specimens", "red.png")] = image.read_bytes()
    groups = [{"path": pdf}, {"path": "s3://specimens/red.png"}]
    if remote_first:
        groups.reverse()
    monkeypatch.setattr(ai_attachments, limit_name, pdf.stat().st_size + image.stat().st_size - 1)

    with pytest.raises(ValueError, match=message):
        if limit_name == "MAX_BATCH_BYTES":
            run([None, None], attachments=[[descriptor] for descriptor in groups])
        else:
            run(attachments=groups)

    assert transport == [], "All mixed-source limits must be checked before any model call"
    assert all(raw.closed for _, raw in s3_store.streams)
    assert all(client.close.call_count == 1 for client in s3_store.clients)


def test_s3_actual_bytes_respect_remaining_mixed_batch_budget(
    files, s3_store, transport, monkeypatch,
):
    pdf, image = files
    remaining = image.stat().st_size - 1
    monkeypatch.setattr(ai_attachments, "MAX_BATCH_BYTES", pdf.stat().st_size + remaining)
    s3_store.objects[("specimens", "red.png")] = {"data": image.read_bytes(), "size": remaining}

    with pytest.raises(ValueError, match="batch snapshot"):
        run([None, None], attachments=[[{"path": pdf}], [{"path": "s3://specimens/red.png"}]])

    body, raw = s3_store.streams[0]
    body.read.assert_called_once_with(remaining + 1)
    assert raw.closed
    s3_store.clients[0].close.assert_called_once_with()
    assert transport == []


def test_s3_exact_limits_and_repeated_rows_share_one_snapshot_and_result(
    files, s3_store, transport, monkeypatch,
):
    data = files[0].read_bytes()
    key = "a" * 1020 + ".pdf"
    s3_store.objects[("specimens", key)] = data
    for limit in ("MAX_FILE_BYTES", "MAX_RECORD_BYTES", "MAX_BATCH_BYTES"):
        monkeypatch.setattr(ai_attachments, limit, len(data))
    descriptor = {"path": f"s3://specimens/{key}"}

    result = run([None, None, None], attachments=[[descriptor]] * 3, threads=1)

    assert result == [{"color": "red"}] * 3
    assert s3_store.requests == [{"Bucket": "specimens", "Key": key}]
    assert len(transport) == 1, "Duplicate rows must reuse the result as well as downloaded bytes"
    s3_store.streams[0][0].read.assert_called_once_with(len(data) + 1)


def test_s3_duplicate_snapshot_still_counts_each_attachment_against_record_limit(
    files, s3_store, transport, monkeypatch,
):
    data = files[1].read_bytes()
    s3_store.objects[("specimens", "red.png")] = data
    monkeypatch.setattr(ai_attachments, "MAX_RECORD_BYTES", len(data))
    descriptors = [
        {"path": "s3://specimens/red.png", "id": "first"},
        {"path": "s3://specimens/red.png", "id": "second"},
    ]

    with pytest.raises(ValueError, match="per-record"):
        run(attachments=descriptors)

    assert len(s3_store.requests) == 1, "The snapshot is unique even when attached more than once"
    assert transport == [], "Repeated attachment bytes must still count toward a record's limit"


@pytest.mark.parametrize("data, message", [(b"", "empty"), (b"not a PDF", "contents do not match")])
def test_s3_empty_or_wrong_format_fails_and_closes_resources(data, message, s3_store, transport):
    s3_store.objects[("specimens", "file.pdf")] = data

    with pytest.raises(ValueError, match=message):
        run(attachments=[{"path": "s3://specimens/file.pdf"}])

    assert s3_store.streams[0][1].closed
    s3_store.clients[0].close.assert_called_once_with()
    assert transport == []


@pytest.mark.parametrize("error, message, during_read", [
    (ClientError({"Error": {"Code": "AccessDenied", "Message": "private service detail"}}, "GetObject"), "access denied", False),
    (ClientError({"Error": {"Code": "NoSuchKey", "Message": "private service detail"}}, "GetObject"), "missing", False),
    (ClientError({"Error": {"Code": "NoSuchBucket", "Message": "private service detail"}}, "GetObject"), "missing", False),
    (ClientError({"Error": {"Code": "InvalidAccessKeyId", "Message": "private service detail"}}, "GetObject"), "request failed", False),
    (NoCredentialsError(), "credentials are missing or incomplete", False),
    (PartialCredentialsError(provider="private service detail", cred_var="private service detail"), "credentials are missing or incomplete", False),
    (ReadTimeoutError(endpoint_url="https://private-service-detail.test"), "unable to read S3 object", True),
    (OSError("private service detail"), "unable to read S3 object", True),
])
def test_s3_errors_are_safe_close_resources_and_never_call_model(
    error, message, during_read, files, s3_store, transport, caplog,
):
    s3_store.objects[("specimens", "private-object.pdf")] = (
        {"data": files[0].read_bytes(), "read_error": error} if during_read else error
    )

    with caplog.at_level(logging.INFO), pytest.raises(ValueError, match=message) as caught:
        run(attachments=[{"path": "s3://specimens/private-object.pdf"}])

    exposed = str(caught.value) + caplog.text
    assert "private service detail" not in exposed
    assert "private-service-detail" not in exposed
    assert "private-object.pdf" not in exposed
    assert "Record 0, attachment 1" in str(caught.value)
    assert caught.value.__suppress_context__, "Raw AWS exceptions must not leak through tracebacks"
    s3_store.clients[0].close.assert_called_once_with()
    if during_read:
        body, raw = s3_store.streams[0]
        body.close.assert_called_once_with()
        assert raw.closed
    assert transport == []


def test_s3_model_retries_reuse_original_snapshot(files, s3_store, monkeypatch):
    before = files[0].read_bytes()
    s3_store.objects[("specimens", "file.pdf")] = before
    calls = []

    def post(**kwargs):
        calls.append(deepcopy(kwargs))
        body = {"status": "completed", "output_text": '{"color":"red"}'}
        if len(calls) == 1:
            body.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"})
            s3_store.objects[("specimens", "file.pdf")] = before.replace(b"RED", b"TAN")
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(body).encode()
        return response

    monkeypatch.setattr(extract._openai_responses._requests, "post", post)
    monkeypatch.setattr(extract._openai_responses, "_sleep_for_retry", lambda *args: None)

    result = run(attachments=[{"path": "s3://specimens/file.pdf"}], retries=1)

    assert result == {"color": "red"}
    assert len(calls) == 2
    assert calls[0]["json"] == calls[1]["json"], "Model retries must use an immutable byte snapshot"
    assert base64.b64decode(
        calls[1]["json"]["input"][0]["content"][1]["file_data"].split(",", 1)[1]
    ) == before
    assert len(s3_store.requests) == 1, "A model retry must not download the object again"
