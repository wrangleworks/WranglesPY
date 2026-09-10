import base64
from copy import deepcopy
import json
import os
from pathlib import Path
import runpy
from types import SimpleNamespace
from unittest.mock import Mock

import jsonschema
import pandas as pd
import pytest
import requests

from wrangles import ai_cache, config, extract, recipe


@pytest.fixture
def local_files(tmp_path):
    png = tmp_path / "image.png"
    png.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
        "/x8AAwMCAO+aD1sAAAAASUVORK5CYII="
    ))
    pdf = tmp_path / "datasheet.pdf"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] >>",
    ]
    document = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(document))
        document += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(document)
    document += b"xref\n0 4\n0000000000 65535 f \n"
    document += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    document += f"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    pdf.write_bytes(document)
    return {"png": str(png.resolve()), "pdf": str(pdf.resolve())}


@pytest.fixture
def extract_ai(monkeypatch):
    mocked = Mock(side_effect=lambda records, **kwargs: [
        {"result": f"row-{index}"} for index in range(len(records))
    ])
    monkeypatch.setattr(extract, "ai", mocked)
    return mocked


def _definition(**settings):
    return {"wrangles": [{"extract.ai": {
        "api_key": "synthetic-test-key",
        "output": {"result": {"type": "string"}},
        **settings,
    }}]}


def _run(dataframe, **settings):
    return recipe.run(
        _definition(**settings),
        dataframe=dataframe,
        variables={"applied_permission_group": None},
    )


def test_literal_attachments_repeat_in_order_without_mutating_descriptors(local_files, extract_ai):
    data = pd.DataFrame({"Description": ["first", "second"]}, index=[91, 24])
    attachments = [
        {"path": local_files["pdf"], "id": "datasheet"},
        {"path": local_files["png"], "detail": "high"},
    ]
    original = deepcopy(attachments)

    result = _run(data, attachments=attachments)

    assert extract_ai.call_args.args[0] == [{"Description": "first"}, {"Description": "second"}]
    assert extract_ai.call_args.kwargs["attachments"] == [original, original]
    assert attachments == original
    assert result.index.tolist() == [91, 24]
    assert result["result"].tolist() == ["row-0", "row-1"]


@pytest.mark.parametrize("selected_input", ["Description", ["Description"], "Descrip*", 0])
def test_column_attachments_resolve_outside_selected_text_input(
    local_files, extract_ai, selected_input,
):
    data = pd.DataFrame({
        "Description": ["first", "second"],
        "PDF Path": [local_files["pdf"], local_files["png"]],
    }, index=["record-b", "record-a"])

    result = _run(
        data,
        input=selected_input,
        attachments=[
            {"column": "PDF Path", "id": "document"},
            {"path": local_files["png"], "id": "photo", "detail": "low"},
        ],
    )

    assert extract_ai.call_args.args[0] == [{"Description": "first"}, {"Description": "second"}]
    assert extract_ai.call_args.kwargs["attachments"] == [
        [
            {"path": path, "id": "document"},
            {"path": local_files["png"], "id": "photo", "detail": "low"},
        ]
        for path in data["PDF Path"]
    ]
    assert result.index.tolist() == ["record-b", "record-a"]
    assert result["result"].tolist() == ["row-0", "row-1"]


def test_attachments_do_not_change_default_all_column_input(local_files, extract_ai):
    data = pd.DataFrame({"Description": ["first"], "PDF Path": [local_files["pdf"]]})
    expected = data.to_dict(orient="records")

    _run(data, attachments=[{"column": "PDF Path"}])

    assert extract_ai.call_args.args[0] == expected
    assert extract_ai.call_args.kwargs["attachments"] == [[{"path": local_files["pdf"]}]]


def test_where_keeps_attachments_aligned_and_ignores_unselected_rows(local_files, extract_ai):
    data = pd.DataFrame({
        "Description": ["first", "skip", "third"],
        "PDF Path": [local_files["pdf"], None, local_files["png"]],
        "Selected": [1, 0, 1],
    }, index=[83, 12, 57])

    result = _run(
        data,
        input="Description",
        where="Selected = 1",
        attachments=[{"column": "PDF Path"}],
    )

    assert extract_ai.call_args.args[0] == [{"Description": "first"}, {"Description": "third"}]
    assert extract_ai.call_args.kwargs["attachments"] == [
        [{"path": local_files["pdf"]}],
        [{"path": local_files["png"]}],
    ]
    assert result.index.tolist() == [83, 12, 57]
    assert result["result"].tolist() == ["row-0", "", "row-1"]


@pytest.mark.parametrize("literal", [False, True])
def test_explicit_empty_input_preserves_attachment_only_rows(local_files, extract_ai, literal):
    data = pd.DataFrame({"PDF Path": [local_files["pdf"], local_files["png"]]}, index=[8, 3])
    attachments = [{"path": local_files["png"]}] if literal else [{"column": "PDF Path"}]

    result = _run(data, input=[], attachments=attachments)

    assert extract_ai.call_args.args[0] == [None, None]
    assert extract_ai.call_args.kwargs["attachments"] == [
        [{"path": local_files["png"] if literal else path}]
        for path in data["PDF Path"]
    ]
    assert result["result"].tolist() == ["row-0", "row-1"]
    assert result.index.tolist() == [8, 3]


def test_explicit_empty_attachments_forward_aligned_empty_lists(extract_ai):
    _run(pd.DataFrame({"Description": ["first", "second"]}), attachments=[])

    assert extract_ai.call_args.kwargs["attachments"] == [[], []]


@pytest.mark.parametrize("attachments, error, message", [
    ("file.pdf", TypeError, "ordered list"),
    ({"path": "/local/file.pdf"}, TypeError, "ordered list"),
    (["/local/file.pdf"], TypeError, "descriptor"),
    ([None], TypeError, "descriptor"),
    ([{}], ValueError, "exactly one"),
    ([{"path": "/local/file.pdf", "column": "PDF Path"}], ValueError, "exactly one"),
    ([{"path": "/local/file.pdf", "extra": True}], ValueError, "only accept"),
    ([{"column": "missing"}], ValueError, "does not exist"),
    ([{"column": 0}], ValueError, "column name"),
    ([{"column": ["PDF Path"]}], ValueError, "column name"),
    ([{"column": ""}], ValueError, "column name"),
    ([{"path": "/local/file.pdf"}] * 17, ValueError, "at most 16"),
])
def test_invalid_attachment_descriptors_fail_before_extraction(
    extract_ai, attachments, error, message,
):
    with pytest.raises(error, match=message):
        _run(pd.DataFrame({"Description": ["first"]}), attachments=attachments)

    extract_ai.assert_not_called()


@pytest.mark.parametrize("path", [None, "", 12, float("nan"), ["/local/file.pdf"], {"path": "/local/file.pdf"}])
def test_column_must_resolve_to_one_path_string(extract_ai, path):
    data = pd.DataFrame({"Description": ["first"], "PDF Path": [path]})

    with pytest.raises(ValueError, match="local path string"):
        _run(data, input="Description", attachments=[{"column": "PDF Path"}])

    extract_ai.assert_not_called()


def test_duplicate_attachment_column_is_rejected(local_files, extract_ai):
    data = pd.DataFrame(
        [["first", local_files["pdf"], local_files["png"]]],
        columns=["Description", "PDF Path", "PDF Path"],
    )

    with pytest.raises(ValueError, match="duplicated"):
        _run(data, input="Description", attachments=[{"column": "PDF Path"}])

    extract_ai.assert_not_called()


def test_wrapper_rejects_non_list_attachments_before_recipe_normalization(extract_ai):
    with pytest.raises(TypeError, match="ordered list"):
        recipe._recipe_wrangles.extract.ai(
            pd.DataFrame({"Description": ["first"]}),
            api_key="synthetic-test-key",
            output="result",
            attachments=({"path": "/local/file.pdf"},),
        )

    extract_ai.assert_not_called()


def test_text_only_does_not_add_attachment_keyword_or_open_input_paths(monkeypatch):
    calls = []

    def text_only(records, api_key, output, model_id, record_examples, web_search, instructions):
        calls.append(records)
        return [{"result": "text"} for _ in records]

    monkeypatch.setattr(extract, "ai", text_only)
    data = pd.DataFrame({
        "Description": ["/local/not-an-attachment.pdf", "https://example.test/image.png"],
        "Other": ["first", "second"],
    })
    expected = data.to_dict(orient="records")

    result = _run(data)

    assert calls == [expected]
    assert result["result"].tolist() == ["text", "text"]


def test_text_only_empty_input_behavior_is_unchanged(extract_ai):
    data = pd.DataFrame({"Description": ["first", "second"]})
    expected = data.to_dict(orient="records")
    extract_ai.side_effect = None
    extract_ai.return_value = [{"result": "first"}, {"result": "second"}]

    _run(data, input=[])

    assert extract_ai.call_args.args[0] == expected
    assert "attachments" not in extract_ai.call_args.kwargs


def test_wrapper_empty_text_input_still_uses_pandas_record_behavior(extract_ai):
    data = pd.DataFrame({"Description": ["first", "second"]})
    expected = data[[]].to_dict(orient="records")
    extract_ai.side_effect = None
    extract_ai.return_value = [{"result": "first"}, {"result": "second"}]

    recipe._recipe_wrangles.extract.ai(
        data, api_key="synthetic-test-key", input=[], output="result",
    )

    assert extract_ai.call_args.args[0] == expected
    assert "attachments" not in extract_ai.call_args.kwargs


@pytest.mark.parametrize("output_format, expected", [
    ("columns", "row-0"),
    ("dictionary", {"result": "row-0"}),
    ("concatenate", "row-0"),
])
def test_saved_model_output_formats_and_budget_forwarding(
    local_files, extract_ai, output_format, expected,
):
    result = _run(
        pd.DataFrame({"Description": ["first"]}),
        attachments=[{"path": local_files["pdf"]}],
        model_id="saved-model",
        output="renamed",
        output_format=output_format,
        max_output_tokens=4096,
    )

    assert result["renamed"].tolist() == [expected]
    assert extract_ai.call_args.kwargs["output"] is None
    assert extract_ai.call_args.kwargs["model_id"] == "saved-model"
    assert extract_ai.call_args.kwargs["max_output_tokens"] == 4096


@pytest.mark.parametrize("selected_input", [[], "Description"], ids=["attachment-only", "text-and-attachment"])
@pytest.mark.parametrize("include_new_field", [False, True], ids=["overwrite-only", "overwrite-and-new"])
def test_saved_model_where_preserves_existing_and_new_fields(
    monkeypatch, local_files, selected_input, include_new_field,
):
    fields = ["Existing", "New"] if include_new_field else ["Existing"]
    monkeypatch.setattr(extract._data, "model_content", lambda model_id: {
        "Settings": {"GPTModel": "gpt-4.1-mini"},
        "Columns": ["Find", "Description", "Type"],
        "Data": [[field, f"Extract {field}", "string"] for field in fields],
    })
    outputs = [
        {field: f"{field}-first" for field in fields},
        {field: f"{field}-third" for field in fields},
    ]
    calls = []

    def post(**kwargs):
        output = outputs[len(calls)]
        calls.append(kwargs["json"])
        return SimpleNamespace(
            ok=True,
            status_code=200,
            headers={},
            json=lambda: {"output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(output)}],
            }]},
        )

    monkeypatch.setattr(extract._openai_responses._requests, "post", post)
    data = pd.DataFrame({
        "Description": ["first", "skip", "third"],
        "PDF Path": [local_files["pdf"], None, local_files["png"]],
        "Selected": [1, 0, 1],
        "Existing": ["old-first", "keep-existing", "old-third"],
    }, index=[83, 12, 57])
    definition = _definition(
        input=selected_input,
        model_id="saved-model",
        where="Selected = 1",
        attachments=[{"column": "PDF Path"}],
        threads=1,
        cache=False,
    )
    del definition["wrangles"][0]["extract.ai"]["output"]

    result = recipe.run(
        definition,
        dataframe=data.copy(),
        variables={"applied_permission_group": None},
    )

    assert len(calls) == 2
    assert result.index.tolist() == [83, 12, 57]
    assert result["Existing"].tolist() == ["Existing-first", "keep-existing", "Existing-third"]
    assert result.columns.tolist() == list(data.columns) + (["New"] if include_new_field else [])
    pd.testing.assert_frame_equal(result[data.columns[:-1]], data[data.columns[:-1]].fillna(""))
    if include_new_field:
        assert result["New"].tolist() == ["New-first", "", "New-third"]


@pytest.fixture(scope="module")
def generated_schema(tmp_path_factory):
    schema_directory = Path(__file__).resolve().parents[1] / "schema"
    output_directory = tmp_path_factory.mktemp("recipe-attachment-schema")
    (output_directory / "recipe_base_schema.json").write_bytes(
        (schema_directory / "recipe_base_schema.json").read_bytes()
    )
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.chdir(output_directory)
        monkeypatch.setattr(
            requests, "get",
            lambda url: SimpleNamespace(json=lambda: jsonschema.Draft7Validator.META_SCHEMA),
        )
        generated = runpy.run_path(str(schema_directory / "generate_recipe_schema.py"))
    schema = generated["recipe_schema"]
    jsonschema.Draft7Validator.check_schema(schema)
    return schema


def test_generated_schema_accepts_attachments_and_output_budget(generated_schema, local_files):
    for attachments in (
        [],
        [{"path": local_files["pdf"], "id": "datasheet"}],
        [{"column": "PDF Path"}, {"path": local_files["png"], "detail": "high"}],
        [{"path": local_files["png"], "id": f"source-{index}", "detail": "auto"} for index in range(16)],
        [{"path": local_files["png"], "id": "a" * 64, "detail": "low"}],
    ):
        jsonschema.validate(
            _definition(input=[], attachments=attachments, max_output_tokens=4096),
            generated_schema,
        )


@pytest.mark.parametrize("attachments", [
    "file.pdf",
    {"path": "/local/file.pdf"},
    ["/local/file.pdf"],
    [{}],
    [{"path": "/local/file.pdf", "column": "PDF Path"}],
    [{"path": "/local/file.pdf", "file_id": "file-provider"}],
    [{"file_id": "file-provider"}],
    [{"path": "/local/file.gif"}],
    [{"path": "https://example.test/file.pdf"}],
    [{"path": "file:///local/file.pdf"}],
    [{"path": "file-provider"}],
    [{"path": "/local/file.pdf", "detail": "auto"}],
    [{"path": "/local/file.PDF", "detail": "high"}],
    [{"path": "/local/file.png", "detail": "invalid"}],
    [{"path": "/local/file.png", "id": ""}],
    [{"path": "/local/file.png", "id": "-invalid"}],
    [{"path": "/local/file.png", "id": "two words"}],
    [{"path": "/local/file.png", "id": "a" * 65}],
    [{"column": ""}],
    [{"column": 1}],
    [{"path": "/local/file.pdf"}] * 17,
])
def test_generated_schema_rejects_unsupported_attachments(generated_schema, attachments):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_definition(attachments=attachments), generated_schema)


@pytest.mark.parametrize("max_output_tokens", [0, -1, 1.5, True, "4096"])
def test_generated_schema_requires_positive_integer_budget(generated_schema, max_output_tokens):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_definition(max_output_tokens=max_output_tokens), generated_schema)


def test_recipe_loads_row_attachments_for_mocked_responses(monkeypatch, local_files):
    calls = []

    def post(**kwargs):
        calls.append(kwargs["json"])
        return SimpleNamespace(
            ok=True,
            status_code=200,
            headers={},
            json=lambda: {"output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": '{"result":"extracted"}'}],
            }]},
        )

    monkeypatch.setattr(extract._openai_responses._requests, "post", post)
    data = pd.DataFrame({"PDF Path": [local_files["png"], local_files["pdf"]]}, index=[44, 19])

    result = _run(
        data,
        input=[],
        attachments=[{"column": "PDF Path"}],
        model="gpt-4.1-mini",
        threads=1,
        cache=False,
        max_output_tokens=4096,
    )

    assert result.index.tolist() == [44, 19]
    assert result["result"].tolist() == ["extracted", "extracted"]
    assert len(calls) == 2
    for payload, path in zip(calls, data["PDF Path"]):
        assert payload["max_output_tokens"] == 4096
        assert base64.b64encode(Path(path).read_bytes()).decode() in json.dumps(payload["input"])


def test_saved_recipe_group_credentials_isolate_attachment_cache(monkeypatch, local_files):
    model_groups = {
        "11111111-1111-1111": "groupA",
        "22222222-2222-2222": "groupB",
    }
    group_keys = {
        "groupA": "synthetic-group-a-key",
        "groupB": "synthetic-group-b-key",
    }
    resolved_groups = []
    calls = []
    environment_before = dict(os.environ)
    configuration_before = (config.api_host, config.api_user, config.api_password)
    saved_recipe = """
    wrangles:
      - extract.ai:
          input: Description
          api_key: ${SCOPED_KEY}
          attachments:
            - column: PDF Path
          output:
            result:
              type: string
          model: gpt-4.1-mini
          threads: 1
          cache: true
    """

    def resolve_key(applied_permission_group):
        resolved_groups.append(applied_permission_group)
        return group_keys[applied_permission_group]

    def post(**kwargs):
        calls.append(kwargs)
        group = next(
            group for group, key in group_keys.items()
            if kwargs["headers"]["Authorization"].removeprefix("Bearer ") == key
        )
        return SimpleNamespace(
            ok=True,
            status_code=200,
            headers={},
            json=lambda: {"output": [{
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": json.dumps({"result": group}),
                }],
            }]},
        )

    monkeypatch.setattr(recipe._auth, "get_applied_permission_group", lambda: None)
    monkeypatch.setattr(recipe._data, "model", lambda model_id: {
        "purpose": "recipe",
        "name": "Shared attachment recipe",
        "applied_permission_group": model_groups[model_id],
    })
    monkeypatch.setattr(recipe._data, "model_content", lambda model_id, version_id=None: {
        "recipe": saved_recipe,
    })
    monkeypatch.setattr(extract._openai_responses._requests, "post", post)
    data = pd.DataFrame({"Description": ["same content"], "PDF Path": [local_files["pdf"]]})

    ai_cache.clear()
    try:
        for model_id in list(model_groups) * 2:
            result = recipe.run(
                model_id,
                dataframe=data.copy(),
                variables={"SCOPED_KEY": "custom.resolve_key"},
                functions={"resolve_key": resolve_key},
            )
            assert result["result"].tolist() == [model_groups[model_id]]

        assert resolved_groups == ["groupA", "groupB", "groupA", "groupB"]
        assert len(calls) == 2
        assert [call["headers"]["Authorization"].split(" ", 1) for call in calls] == [
            ["Bearer", group_keys["groupA"]],
            ["Bearer", group_keys["groupB"]],
        ]
        assert calls[0]["json"] == calls[1]["json"]
        assert set(os.environ) == set(environment_before)
        assert all(os.environ[name] == value for name, value in environment_before.items())
        assert all(
            current == previous for current, previous in zip(
                (config.api_host, config.api_user, config.api_password),
                configuration_before,
            )
        )
    finally:
        ai_cache.clear()
