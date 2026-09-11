import base64

import pandas as pd
import pytest

import wrangles.extract as extract
from wrangles import ai_attachments, ai_cache, openai_responses, recipe


class _Response:
    def __init__(self, body, ok=True, status_code=200, headers=None):
        self._body = body
        self.ok = ok
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._body


@pytest.fixture(autouse=True)
def _clear_result_cache():
    ai_cache.clear()
    yield
    ai_cache.clear()


def _png(path, tail=b"one"):
    data = b"\x89PNG\r\n\x1a\n" + tail
    path.write_bytes(data)
    return data


def _pdf(path):
    data = b"%PDF-1.4\n%test\n"
    path.write_bytes(data)
    return data


def _openai_success_response(payload):
    return _Response({
        "output": [{
            "type": "message",
            "content": [{
                "type": "output_text",
                "text": __import__("json").dumps(payload),
            }],
        }]
    })


def test_responses_payload_sends_text_and_image_attachment_content(
    monkeypatch, tmp_path
):
    image = tmp_path / "part.png"
    image_data = _png(image)
    calls = []

    monkeypatch.setattr(
        openai_responses._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or _openai_success_response({"part": "switch"}),
    )

    result = extract.ai(
        {"description": "read the label"},
        "test-key",
        output={"part": {"type": "string"}},
        attachments=[{"path": image, "id": "front", "detail": "high"}],
        model="gpt-5-mini",
        threads=1,
    )

    assert result == {"part": "switch"}
    content = calls[0]["json"]["input"][0]["content"]
    assert content[0] == {
        "type": "input_text",
        "text": 'DATA:\n{\n  "description": "read the label"\n}',
    }
    assert content[1] == {
        "type": "input_text",
        "text": 'DATA source: {"id": "front", "media_type": "image/png"}',
    }
    assert content[2] == {
        "type": "input_image",
        "image_url": "data:image/png;base64," + base64.b64encode(image_data).decode("ascii"),
        "detail": "high",
    }


def test_responses_payload_sends_pdf_only_attachment(
    monkeypatch, tmp_path
):
    pdf = tmp_path / "spec.pdf"
    pdf_data = _pdf(pdf)
    calls = []
    monkeypatch.setattr(
        openai_responses._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or _openai_success_response({"page": 1}),
    )

    result = extract.ai(
        None,
        "test-key",
        output={"page": {"type": "integer"}},
        attachments=[{"path": str(pdf), "id": "datasheet"}],
        model="gpt-5-mini",
        threads=1,
    )

    assert result == {"page": 1}
    assert calls[0]["json"]["input"][0]["content"] == [
        {
            "type": "input_text",
            "text": 'DATA source: {"id": "datasheet", "media_type": "application/pdf"}',
        },
        {
            "type": "input_file",
            "filename": "datasheet.pdf",
            "file_data": "data:application/pdf;base64," + base64.b64encode(pdf_data).decode("ascii"),
        },
    ]


def test_text_path_without_attachments_remains_plain_text(
    monkeypatch, tmp_path
):
    image = tmp_path / "plain.png"
    _png(image)
    calls = []
    monkeypatch.setattr(
        openai_responses._requests,
        "post",
        lambda **kwargs: calls.append(kwargs) or _openai_success_response({"seen": "text"}),
    )

    result = extract.ai(
        str(image),
        "test-key",
        output={"seen": {"type": "string"}},
        model="gpt-5-mini",
        threads=1,
    )

    assert result == {"seen": "text"}
    assert calls[0]["json"]["input"][0]["content"] == f"DATA:\n{image}"


def test_attachment_cache_identity_changes_when_file_bytes_change(
    monkeypatch, tmp_path
):
    image = tmp_path / "part.png"
    _png(image, b"first")
    calls = []

    def post(**kwargs):
        calls.append(kwargs)
        return _openai_success_response({"call": len(calls)})

    monkeypatch.setattr(openai_responses._requests, "post", post)
    arguments = {
        "input": "read label",
        "api_key": "test-key",
        "output": {"call": {"type": "integer"}},
        "attachments": [{"path": image}],
        "model": "gpt-5-mini",
        "threads": 1,
    }

    assert extract.ai(**arguments) == {"call": 1}
    assert extract.ai(**arguments) == {"call": 1}
    _png(image, b"second")
    assert extract.ai(**arguments) == {"call": 2}
    assert len(calls) == 2


@pytest.mark.parametrize(
    "attachments, error",
    [
        ([{"path": "missing.png"}], "missing or unreadable"),
        ([{"path": "https://example.test/image.png"}], "only local filesystem paths"),
        ([{"path": ""}], "non-empty local filesystem path"),
    ],
)
def test_attachment_validation_failures_are_actionable(attachments, error):
    with pytest.raises((TypeError, ValueError), match=error):
        extract.ai(
            "data",
            "test-key",
            output={"value": {"type": "string"}},
            attachments=attachments,
            model="gpt-5-mini",
            threads=1,
        )


def test_pdf_rejects_image_detail(tmp_path):
    pdf = tmp_path / "spec.pdf"
    _pdf(pdf)

    with pytest.raises(ValueError, match="detail applies only to images"):
        ai_attachments.prepare(
            ["data"],
            [[{"path": pdf, "detail": "high"}]],
            False,
            openai_responses.format_input_data,
        )


def test_attachments_are_rejected_for_chat_completions(tmp_path):
    image = tmp_path / "part.png"
    _png(image)

    with pytest.raises(ValueError, match="only with protocol='responses'"):
        extract.ai(
            "data",
            "test-key",
            output={"value": {"type": "string"}},
            attachments=[{"path": image}],
            protocol="chat_completions",
            model="gpt-5-mini",
            threads=1,
        )


def test_recipe_maps_literal_and_column_attachments_by_row(monkeypatch, tmp_path):
    shared = tmp_path / "shared.png"
    row_pdf = tmp_path / "row.pdf"
    _png(shared)
    _pdf(row_pdf)
    calls = []

    def call_ai(input, **kwargs):
        calls.append((input, kwargs))
        return [{"kind": "ok"}]

    monkeypatch.setattr("wrangles.recipe_wrangles.extract._extract.ai", call_ai)

    result = recipe.run(
        {
            "wrangles": [{
                "extract.ai": {
                    "input": "description",
                    "api_key": "test-key",
                    "output": {"kind": {"type": "string"}},
                    "attachments": [
                        {"path": str(shared), "id": "photo"},
                        {"column": "pdf_path", "id": "sheet"},
                    ],
                }
            }]
        },
        dataframe=pd.DataFrame({
            "description": ["read row"],
            "pdf_path": [str(row_pdf)],
        }),
    )

    assert result["kind"].tolist() == ["ok"]
    assert calls[0][0] == [{"description": "read row"}]
    assert calls[0][1]["attachments"] == [[
        {"path": str(shared), "id": "photo"},
        {"id": "sheet", "path": str(row_pdf)},
    ]]


def test_recipe_supports_attachment_only_input(monkeypatch, tmp_path):
    image = tmp_path / "part.png"
    _png(image)
    calls = []

    monkeypatch.setattr(
        "wrangles.recipe_wrangles.extract._extract.ai",
        lambda input, **kwargs: calls.append((input, kwargs)) or [{"value": "ok"}],
    )

    result = recipe.run(
        {
            "wrangles": [{
                "extract.ai": {
                    "input": [],
                    "api_key": "test-key",
                    "output": {"value": {"type": "string"}},
                    "attachments": [{"path": str(image)}],
                }
            }]
        },
        dataframe=pd.DataFrame({"ignored": ["x"]}),
    )

    assert result["value"].tolist() == ["ok"]
    assert calls[0][0] == [None]
