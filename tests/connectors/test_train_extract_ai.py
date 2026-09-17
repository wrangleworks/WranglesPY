"""Offline #1182 regressions; all definitions below are small synthetic fixtures."""

import copy
import importlib
import json

import numpy as np
import pandas as pd
import pytest
import requests
import yaml

import wrangles
from wrangles.connectors import train as connector


sdk = importlib.import_module("wrangles.train")
LEGACY = ["Find", "Description", "Type", "Default", "Examples", "Enum", "Notes"]
KNOWN = LEGACY + [
    "Properties", "Items", "Required", "Additional Properties", "Nullable",
    "Example - Input", "Example - Output",
]
PAIRED = [column for column in KNOWN if column not in {"Examples", "Nullable"}]
MODEL_ID = "00000000-0000-0000"


@pytest.fixture
def service(monkeypatch):
    """Capture actual SDK serialization, blocking every unmocked HTTP request."""
    def unexpected_request(*args, **kwargs):
        pytest.fail("Unexpected network request in an offline training test")

    monkeypatch.setattr(requests.sessions.Session, "request", unexpected_request)
    monkeypatch.setattr(sdk._auth, "get_access_token", lambda: "synthetic-test-token")
    state = {
        "writes": [],
        "reads": [],
        "metadata": {"variant": "extract-ai", "settings": {}},
        "content": {
            "Columns": ["Find"],
            "Data": [["Old attribute"]],
            "Settings": {
                "variant": "extract-ai", "GPTModel": "gpt-5.4-mini",
                "ReasoningEffort": "low", "AdditionalMessages": "Keep these instructions.",
            },
        },
    }

    def metadata(model_id):
        assert model_id == MODEL_ID
        state["reads"].append("metadata")
        return copy.deepcopy(state["metadata"])

    def content(model_id):
        assert model_id == MODEL_ID
        state["reads"].append("content")
        return copy.deepcopy(state["content"])

    def submit(method, **kwargs):
        # Real JSON encoding catches pandas/NumPy sentinels and NaN leaks.
        payload = json.loads(json.dumps(kwargs["json"], allow_nan=False))
        state["writes"].append((method, kwargs["params"], payload))
        response = requests.Response()
        response.status_code = 202
        response._content = json.dumps({"model_id": MODEL_ID}).encode()
        return response

    monkeypatch.setattr(connector, "_model", metadata)
    monkeypatch.setattr(sdk._data, "model_content", content)
    monkeypatch.setattr(sdk._requests, "post", lambda url, **kwargs: submit("POST", **kwargs))
    monkeypatch.setattr(sdk._utils, "request_retries", lambda request_type, url, **kwargs: submit(request_type, **kwargs))
    return state


@pytest.mark.parametrize("columns", [
    ["Find"], ["Find", "Type", "Properties"], LEGACY, PAIRED, KNOWN,
    ["Customer Note", "Enum", "Find", "Type"],
])
def test_create_preserves_supported_column_layouts(service, columns):
    row = {"Find": "Voltage", "Type": "object", "Properties": "value: number | uom: string"}
    if "Properties" not in columns:
        row.update(Type="string", Enum="Corded | Battery")
    row["Customer Note"] = "Preserve this extra column"
    frame = pd.DataFrame([[row.get(column, "") for column in columns]], columns=columns)

    connector.extract.write(frame, name="Synthetic schema", variant="ai")

    method, params, payload = service["writes"][0]
    assert method == "POST"
    assert params == {"type": "extract", "name": "Synthetic schema", "variant": "extract-ai"}
    assert payload == {"Columns": columns, "Data": frame.values.tolist(), "Settings": {}}
    assert service["reads"] == []


def test_legacy_prefix_does_not_discard_appended_schema(service):
    frame = pd.DataFrame([["Voltage", "", "object", "", "", "", "", {
        "value": {"type": "number", "nullable": False},
        "uom": {"type": "string", "enum": ["VAC", "VDC"]},
    }, "keep me"]], columns=LEGACY + ["Properties", "Future Column"])
    connector.extract.write(frame, name="Synthetic schema", variant="ai")
    assert service["writes"][0][2]["Data"] == frame.values.tolist()
    assert service["writes"][0][2]["Columns"] == list(frame.columns)


def test_selection_preserves_wildcard_order_and_all_selected_values(service):
    frame = pd.DataFrame({"Find": ["Power"], "Type": ["number"], "Extra A": [0], "Extra B": [False], "Omit": ["no"]})
    connector.extract.write(frame, columns=["Extra*", "Find"], name="Synthetic schema", variant="ai")
    assert service["writes"][0][2]["Columns"] == ["Extra A", "Extra B", "Find"]
    assert service["writes"][0][2]["Data"] == [[0, False, "Power"]]


def test_selection_without_find_fails_before_write(service):
    with pytest.raises(ValueError, match="Find column is required"):
        connector.extract.write(pd.DataFrame({"Find": ["Voltage"], "Type": ["number"]}), columns=["Type"], name="Synthetic schema", variant="ai")
    assert service["writes"] == []


@pytest.mark.parametrize("settings", [None, {}, {"ReasoningEffort": "none", "AdditionalMessages": "", "FutureFlag": False}])
def test_update_preserves_content_settings_and_explicit_overrides(service, settings):
    original = copy.deepcopy(service["content"])
    frame = pd.DataFrame({"Find": ["New attribute"]})
    connector.extract.write(frame, model_id=MODEL_ID, settings=settings)
    method, params, payload = service["writes"][0]
    assert method == "PUT"
    assert params == {"type": "extract", "model_id": MODEL_ID}
    expected = {**original["Settings"], **(settings or {})}
    expected["GeneralInstructions"] = expected["AdditionalMessages"]
    assert payload["Settings"] == expected
    assert payload["Data"] == [["New attribute"]]
    assert service["content"] == original
    assert service["reads"] == ["metadata", "content"]


def test_read_write_round_trip_preserves_xl_table_and_settings(service):
    content = {
        "Columns": PAIRED,
        "Data": [[{
            "Find": "Voltage", "Type": "object", "Description": "Product’s voltage — µV",
            "Properties": {"value": {"type": "number"}, "uom": {"type": "string"}},
            "Required": ["value", "uom"], "Additional Properties": False,
            "Example - Input": "Voltage: 120 VAC", "Example - Output": {"value": 120, "uom": "VAC"},
        }.get(column, "") for column in PAIRED]],
        "Settings": copy.deepcopy(service["content"]["Settings"]),
    }
    service["content"] = copy.deepcopy(content)
    frame = connector.extract.read(MODEL_ID)
    connector.extract.write(frame, model_id=MODEL_ID)
    expected = copy.deepcopy(content)
    expected["Settings"]["GeneralInstructions"] = content["Settings"]["AdditionalMessages"]
    assert service["writes"][0][2] == expected
    assert service["content"] == content


def test_native_cells_missing_values_and_explicit_null_are_distinct(service):
    frame = pd.DataFrame([
        ["Enabled", "boolean", False, False, pd.NA, np.nan],
        ["Count", "integer", 0, np.int64(0), pd.NaT, ""],
        ["Unknown", "string", None, "null", None, ""],
        ["Modes", "array", ["AC", "DC"], ["AC", "DC"], "string", ""],
    ], columns=["Find", "Type", "Default", "Example - Output", "Items", "Notes"], dtype=object)
    original = frame.copy(deep=True)
    connector.extract.write(frame, name="Synthetic schema", variant="ai")
    assert service["writes"][0][2]["Data"] == [
        ["Enabled", "boolean", False, False, None, None],
        ["Count", "integer", 0, 0, None, ""],
        ["Unknown", "string", None, "null", None, ""],
        ["Modes", "array", ["AC", "DC"], ["AC", "DC"], "string", ""],
    ]
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("column,value", [
    ("Type", "decimal"), ("Properties", "{value: number, value: string}"),
    ("Properties", '{"value":"number","value":"string"}'),
    ("Properties", "{value: !!str number}"), ("Properties", "{value: &shared {type: number}}"),
    ("Properties", "value: unsupported"), ("Properties", "{value: 12}"),
    ("Properties", "{value: number"), ("Nullable", "yes"), ("Required", True),
    ("Additional Properties", 0),
    ("Enum", "[AC, DC"), ("Example - Output", "{value: 120"),
    ("Examples", "{value: 120},{value: [broken}"),
])
def test_invalid_cells_report_column_and_row(service, column, value):
    row = {"Find": "Voltage", "Type": "object", "Properties": "value: number"}
    row[column] = value
    with pytest.raises(ValueError, match=rf"{column} on row 2"):
        connector.extract.write(pd.DataFrame([row]), name="Synthetic schema", variant="ai")
    assert service["writes"] == []


@pytest.mark.parametrize("kind,column,value", [
    ("string", "Properties", "value: number"), ("object", "Items", "string"),
    ("array", "Required", "value"), ("number", "Additional Properties", False),
])
def test_schema_keywords_reject_incompatible_types(service, kind, column, value):
    with pytest.raises(ValueError, match=rf"{column} on row 2.*applies only"):
        connector.extract.write(pd.DataFrame([{"Find": "Attribute", "Type": kind, column: value}]), name="Synthetic schema", variant="ai")
    assert service["writes"] == []


def test_absent_object_properties_column_is_distinct_from_blank_cell(service):
    connector.extract.write(pd.DataFrame({"Find": ["Attributes"], "Type": ["object"]}), name="Legacy object", variant="ai")
    with pytest.raises(ValueError, match="Properties on row 2.*required"):
        connector.extract.write(pd.DataFrame({"Find": ["Attributes"], "Type": ["object"], "Properties": [""]}), name="Invalid object", variant="ai")
    assert len(service["writes"]) == 1


def test_blank_rows_are_preserved_but_populated_rows_require_find(service):
    frame = pd.DataFrame([["", ""], ["Voltage", "number"]], columns=["Find", "Type"])
    connector.extract.write(frame, name="Synthetic schema", variant="ai")
    assert service["writes"][0][2]["Data"] == frame.values.tolist()
    with pytest.raises(ValueError, match="Find is required on row 3"):
        connector.extract.write(pd.DataFrame([["", ""], [" ", "number"]], columns=frame.columns), name="Invalid schema", variant="ai")


@pytest.mark.parametrize("output", ["", None, pd.NA])
def test_paired_example_requires_output(service, output):
    with pytest.raises(ValueError, match="Example - Input on row 2.*requires Example - Output"):
        connector.extract.write(pd.DataFrame({"Find": ["Voltage"], "Example - Input": ["120 VAC"], "Example - Output": [output]}), name="Synthetic schema", variant="ai")
    assert service["writes"] == []


@pytest.mark.parametrize("columns", [["Find", "Output", "Notes"], ["Find", "Output (Optional)", "Notes"], ["Entity to Find", "Variation (Optional)", "Notes"]])
def test_pattern_creation_remains_unchanged(service, columns):
    connector.extract.write(pd.DataFrame([["AC", "Alternating current", ""]], columns=columns), name="Synthetic pattern")
    method, params, payload = service["writes"][0]
    assert method == "POST"
    assert params == {"type": "extract", "name": "Synthetic pattern"}
    assert payload == [["Find", "Output", "Notes"], ["AC", "Alternating current", ""]]
    assert service["reads"] == []


def test_legacy_ai_sdk_list_and_response_contract_remain_supported(service):
    rows = [["Power", "", "number", "", "", "", ""]]
    original = copy.deepcopy(rows)
    response = wrangles.train.extract(rows, name="Legacy AI", variant="extract-ai")
    assert isinstance(response, requests.Response)
    assert service["writes"][0][2] == [LEGACY, *rows]
    assert rows == original


def test_sdk_full_content_and_connector_share_authoring_validation(service):
    content = {"Columns": ["Find", "Type"], "Data": [["Voltage", "invalid"]]}
    with pytest.raises(ValueError, match="Type on row 2"):
        wrangles.train.extract(content, name="Invalid AI", variant="extract-ai")
    assert service["writes"] == []


def test_connector_schema_and_recipe_support_new_arguments(service):
    schema = yaml.safe_load(connector.extract._schema["write"])
    assert schema["properties"]["settings"]["type"] == "object"
    instructions = schema["properties"]["settings"]["properties"]["GeneralInstructions"]
    assert instructions["title"] == "General Instructions"
    assert instructions["type"] == ["string", "array", "null"]
    assert schema["properties"]["variant"]["enum"] == ["pattern", "ai"]
    wrangles.recipe.run("""
write:
  - train.extract:
      name: Synthetic recipe schema
      variant: ai
      settings:
        ReasoningEffort: none
        GeneralInstructions: Extract the primary product only.
""", dataframe=pd.DataFrame({"Find": ["Voltage"], "Type": ["number"]}))
    assert service["writes"][0][2]["Settings"] == {
        "ReasoningEffort": "none",
        "GeneralInstructions": "Extract the primary product only.",
        "AdditionalMessages": "Extract the primary product only.",
    }


@pytest.mark.parametrize("row", [
    {"Find": "Voltage", "Type": "object", "Properties": "value: number | uom: string", "Examples": "{value: 12, uom: VDC},{value: 120, uom: VAC}"},
    {"Find": "Modes", "Type": "array", "Items": "value: number | uom: string", "Examples": [{"value": 24, "uom": "VDC"}]},
    {"Find": "Modes", "Type": "array", "Items": {"type": "object", "properties": {"value": {"type": "number"}}}},
    {"Find": "Voltage", "Type": "object", "Properties": "- value\n- uom", "Required": "value | uom", "Additional Properties": "FALSE", "Nullable": "true"},
    {"Find": "Voltage", "Type": "object", "Properties": "value: number\nuom: string", "Required": "[value, uom]"},
    {"Find": "Voltage", "Type": "object", "Properties": {"value": "float", "uom": "text"}, "Additional Properties": "string"},
    {"Find": "Other", "Type": "object", "Additional Properties": True},
    {"Find": "Other", "Type": "object", "Additional Properties": {"type": "string"}},
    {"Find": "Available", "Type": "boolean", "Example - Input": "No output", "Example - Output": False},
    {"Find": "Count", "Type": "integer", "Example - Input": "No outputs", "Example - Output": 0},
    {"Find": "Unknown", "Example - Input": "Not specified", "Example - Output": "null"},
    {"Find": "Word", "Type": "object", "Properties": "value: string", "Default": '{"value": NaN}'},
    {"Enum": ["AC", "DC", None], "FIND": "Mode", "tYpE": "string", "Example_Output": "AC", "Customer Column": {"keep": [False, 0, None]}},
])
def test_friendly_and_native_cell_forms_are_preserved(service, row):
    frame = pd.DataFrame([row])
    connector.extract.write(frame, name="Synthetic schema", variant="ai")
    assert service["writes"][0][2]["Data"] == frame.values.tolist()
    assert service["writes"][0][2]["Columns"] == list(frame.columns)


@pytest.mark.parametrize("metadata", [{}, {"variant": "pattern"}])
def test_pattern_update_keeps_legacy_variant_resolution(service, metadata):
    service["metadata"] = metadata
    frame = pd.DataFrame([["AC", "Alternating current", ""]], columns=["Find", "Output", "Notes"])
    connector.extract.write(frame, model_id=MODEL_ID)
    assert service["writes"][0][0] == "PUT"
    assert service["writes"][0][2] == [["Find", "Output", "Notes"], *frame.values.tolist()]
    assert service["reads"] == ["metadata"]


@pytest.mark.parametrize("arguments, message", [
    ({}, "name or a model id"),
    ({"name": "Invalid", "model_id": MODEL_ID}, "cannot both be provided"),
    ({"model_id": MODEL_ID, "variant": "ai"}, "not possible to set the variant"),
    ({"name": "Invalid", "variant": "extract-ai"}, "either 'pattern' or 'ai'"),
])
def test_connector_argument_rules_are_unchanged(service, arguments, message):
    with pytest.raises(ValueError, match=message):
        connector.extract.write(pd.DataFrame({"Find": ["Voltage"]}), **arguments)
    assert service["reads"] == []
    assert service["writes"] == []


@pytest.mark.parametrize("settings", [[], False, "invalid", {"variant": "pattern"}])
def test_invalid_settings_do_not_write_or_read_content(service, settings):
    with pytest.raises(ValueError, match="Settings"):
        connector.extract.write(pd.DataFrame({"Find": ["Voltage"]}), name="Invalid", variant="ai", settings=settings)
    assert service["reads"] == []
    assert service["writes"] == []


def test_failed_settings_read_does_not_reset_or_write_model(service, monkeypatch):
    def denied(model_id):
        raise wrangles.data.AuthorizationError("Synthetic denied response")

    monkeypatch.setattr(sdk._data, "model_content", denied)
    with pytest.raises(wrangles.data.AuthorizationError):
        connector.extract.write(pd.DataFrame({"Find": ["Voltage"]}), model_id=MODEL_ID)
    assert service["writes"] == []


def test_sdk_dictionary_update_copies_settings_without_mutating_input(service):
    content = {"Columns": ["Find"], "Data": [["Voltage"]], "Settings": {"AdditionalMessages": "Updated", "Extra": {"enabled": False, "limit": 0, "value": None}}}
    original = copy.deepcopy(content)
    response = wrangles.train.extract(content, model_id=MODEL_ID, variant="extract-ai")
    assert response.status_code == 202
    assert service["writes"][0][2]["Settings"] == {
        **service["content"]["Settings"], **original["Settings"],
        "GeneralInstructions": "Updated",
    }
    assert content == original
    assert service["reads"] == ["content"]


@pytest.mark.parametrize("settings,value", [
    ({"GeneralInstructions": "Primary product only."}, "Primary product only."),
    ({"AdditionalMessages": "Legacy guidance."}, "Legacy guidance."),
    ({"general instructions": ["First rule.", "Second rule."]}, ["First rule.", "Second rule."]),
    ({"instructions": "Recipe-style alias."}, "Recipe-style alias."),
    ({"messages": ["Legacy list."]}, ["Legacy list."]),
    ({"GeneralInstructions": "New", "AdditionalMessages": "Old"}, "New"),
    ({"GeneralInstructions": "Same", "AdditionalMessages": "Same"}, "Same"),
    ({"GeneralInstructions": "", "AdditionalMessages": "Stale", "messages": "Stale"}, ""),
    ({"GeneralInstructions": None, "AdditionalMessages": "Stale"}, None),
    ({"GeneralInstructions": [], "instructions": "Stale"}, []),
])
def test_create_normalizes_instruction_aliases_for_old_and_new_readers(service, settings, value):
    settings = {**settings, "FutureSetting": {"enabled": False}}
    original = copy.deepcopy(settings)
    connector.extract.write(
        pd.DataFrame({"Find": ["Voltage"]}), name="Instruction compatibility",
        variant="ai", settings=settings,
    )
    assert service["writes"][0][2]["Settings"] == {
        "GeneralInstructions": value, "AdditionalMessages": value,
        "FutureSetting": {"enabled": False},
    }
    assert settings == original


@pytest.mark.parametrize("key", ["GeneralInstructions", "AdditionalMessages", "instructions", "messages", "ADDITIONAL Messages"])
@pytest.mark.parametrize("value", ["Updated guidance.", "", None, []])
def test_explicit_instruction_alias_overrides_existing_canonical_setting(service, key, value):
    service["content"]["Settings"].update({
        "GeneralInstructions": "Previous canonical value.",
        "instructions": "Stale alias.",
        "messages": "Another stale alias.",
    })
    original = copy.deepcopy(service["content"])
    settings = {key: value}
    connector.extract.write(
        pd.DataFrame({"Find": ["Voltage"]}), model_id=MODEL_ID, settings=settings,
    )
    assert service["writes"][0][2]["Settings"] == {
        "variant": "extract-ai", "GPTModel": "gpt-5.4-mini", "ReasoningEffort": "low",
        "GeneralInstructions": value, "AdditionalMessages": value,
    }
    assert service["content"] == original
    assert settings == {key: value}


def test_blank_defaults_are_materialized_only_when_compiling(service):
    from wrangles import ai_definition

    frame = pd.DataFrame({"Find": ["Voltage"], "Type": ["object"], "Properties": ["value: number | uom: string"], "Required": [""], "Additional Properties": [""], "Nullable": [""]})
    connector.extract.write(frame, name="Synthetic schema", variant="ai")
    content = service["writes"][0][2]
    assert content["Data"] == frame.values.tolist()
    compiled = ai_definition.compile_definition(None, saved_model_content=content, model="gpt-5.4-mini")
    voltage = compiled.root_schema["properties"]["Voltage"]
    assert voltage["required"] == ["value", "uom"]
    assert voltage["additionalProperties"] is False
    assert voltage["type"] == ["object", "null"]
    assert voltage["properties"]["value"]["type"] == "number"


@pytest.mark.parametrize("value", [float("inf"), {"value": float("nan")}, {"value": pd.NA}])
def test_invalid_json_values_fail_before_submission(service, value):
    with pytest.raises(ValueError, match="Default on row 2"):
        connector.extract.write(pd.DataFrame({"Find": ["Voltage"], "Default": [value]}), name="Invalid", variant="ai")
    assert service["writes"] == []


def test_prepare_content_is_reusable_without_a_service_and_copies_inputs(service):
    from wrangles import ai_saved_model

    content = {"Columns": ["Find", "Future Column"], "Data": [["Voltage", {"keep": [1, False, None]}]]}
    original = copy.deepcopy(content)
    prepared = ai_saved_model.prepare_content(content)
    assert prepared == {**content, "Settings": {}}
    prepared["Data"][0][1]["keep"].append(2)
    assert content == original
    assert service["reads"] == service["writes"] == []


def test_xl_authoring_parser_does_not_change_runtime_interpretation(service):
    from wrangles import ai_definition, ai_saved_model

    content = {"Columns": ["Find", "Default"], "Data": [["Word", '{"value": NaN}']]}
    assert ai_saved_model.prepare_content(content)["Data"] == content["Data"]
    with pytest.raises(ValueError, match="finite number"):
        ai_definition._load_json_like('{"value": NaN}')


@pytest.mark.parametrize("content", [
    {"Columns": ["Find"]},
    {"Columns": "Find", "Data": [["Voltage"]]},
    {"Columns": ["Find"], "Data": ["Voltage"]},
    {"Columns": ["Find"], "Data": [["Voltage", "extra"]]},
])
def test_invalid_content_shape_never_submits(service, content):
    with pytest.raises(ValueError, match="Columns and Data arrays|Data on row 2"):
        wrangles.train.extract(content, name="Invalid", variant="extract-ai")
    assert service["writes"] == []


def test_invalid_existing_settings_never_submit_a_reset(service):
    service["content"]["Settings"] = []
    with pytest.raises(ValueError, match="Settings must be an object"):
        connector.extract.write(pd.DataFrame({"Find": ["Voltage"]}), model_id=MODEL_ID)
    assert service["writes"] == []


def test_pattern_does_not_silently_discard_ai_settings(service):
    with pytest.raises(ValueError, match="Settings are supported only for Extract-AI"):
        connector.extract.write(pd.DataFrame({"Find": ["Voltage"]}), name="Invalid", settings={"GPTModel": "gpt-5.4-mini"})
    assert service["writes"] == []


def test_sdk_creation_retains_name_precedence_and_logs_returned_id(service, caplog):
    # The connector rejects both arguments; the legacy SDK gives name precedence.
    content = {"Columns": ["Find"], "Data": [["Voltage"]]}
    with caplog.at_level("INFO"):
        wrangles.train.extract(content, name="Synthetic schema", model_id=MODEL_ID, variant="extract-ai")
    assert service["reads"] == []
    assert service["writes"][0][0] == "POST"
    assert f"New extract model created :: {MODEL_ID}" in caplog.text


def test_sdk_allows_absent_trailing_optional_cells(service):
    content = {"Columns": ["Find", "Type", "Notes"], "Data": [["Voltage", "number"], []]}
    wrangles.train.extract(content, name="Synthetic schema", variant="extract-ai")
    assert service["writes"][0][2] == {**content, "Settings": {}}
