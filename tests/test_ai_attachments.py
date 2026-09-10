"""Offline multimodal contract tests; fixtures contain only synthetic data."""
import base64
from copy import deepcopy
import hashlib
import json
import logging
import struct
import zlib

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


def test_text_paths_urls_and_dicts_are_never_loaded(transport):
    values = ["/missing/file.pdf", "https://example.test/image.png", {"path": "/missing/file.pdf"}]
    assert run(values) == [{"color": "red"}] * 3
    assert all(isinstance(call["json"]["input"][0]["content"], str) for call in transport)
    assert run(None, attachments=[]) == {"color": "red"}
    assert transport[-1]["json"]["input"][0]["content"] == "DATA:\nNone"


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
