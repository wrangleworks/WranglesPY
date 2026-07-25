import logging

import pandas as pd
import pytest
import wrangles

import wrangles.ai_definition as ai_definition
import wrangles.openai_responses as openai_responses


def _saved_model(*rows, settings=None, columns=None):
    return {
        "Settings": settings or {},
        "Columns": columns or [
            "Find",
            "Description",
            "Type",
            "Default",
            "Examples",
            "Enum",
            "Notes",
            "Properties",
        ],
        "Data": list(rows),
    }


def test_fixed_recipe_definition_remains_strict():
    compiled = ai_definition.compile_definition(
        {
            "Voltage": {
                "type": "object",
                "description": "Voltage and unit",
                "properties": {
                    "value": {"type": "number"},
                    "uom": {"type": "string"},
                },
            }
        },
        model="gpt-5.4-mini",
    )

    assert compiled.strict is True
    assert compiled.dynamic_paths == ()
    assert compiled.output["Voltage"]["additionalProperties"] is False
    assert compiled.root_schema["required"] == ["Voltage"]


def test_dynamic_dictionary_disables_strict_but_preserves_fixed_root(caplog):
    with caplog.at_level(logging.WARNING, logger="wrangles.ai_definition"):
        compiled = ai_definition.compile_definition(
            {
                "attributes": {
                    "type": "object",
                    "description": "Attributes whose names are discovered at runtime",
                    "additionalProperties": {"type": "string"},
                },
                "source": {"type": "string"},
            },
            model="gpt-5.4-mini",
            strict=True,
        )

    schema = openai_responses.sanitize_schema(
        compiled.root_schema,
        strict=compiled.strict,
    )

    assert compiled.strict_requested is True
    assert compiled.strict is False
    assert compiled.dynamic_paths == ("output.attributes",)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["attributes"]["additionalProperties"] == {
        "type": "string"
    }
    assert "strict mode was disabled" in caplog.text

    parsed = openai_responses.validate_structured_output(
        {
            "attributes": {"Voltage": "12 VDC", "Power Source": "Battery"},
            "source": "description",
        },
        schema,
    )
    assert parsed["attributes"]["Voltage"] == "12 VDC"


def test_object_without_named_properties_is_an_explicit_dynamic_migration(caplog):
    with caplog.at_level(logging.WARNING, logger="wrangles.ai_definition"):
        compiled = ai_definition.compile_definition(
            {"attributes": {"type": "object"}},
            model="gpt-5.4-mini",
        )

    assert compiled.strict is False
    assert compiled.output["attributes"]["additionalProperties"] is True
    assert "object without named properties as a dynamic dictionary" in caplog.text


def test_saved_and_recipe_definitions_compile_to_the_same_schema(caplog):
    saved = _saved_model(
        [
            "Voltage",
            "Voltage and unit",
            "object",
            "",
            "{value: 12, uom: VDC}",
            "",
            "",
            "value,uom",
        ],
        settings={
            "GPTModel": "gpt-5.4-mini",
            "AdditionalMessages": "Use normalized units.",
        },
    )

    with caplog.at_level(logging.WARNING, logger="wrangles.ai_definition"):
        from_saved = ai_definition.compile_definition(
            None,
            model="fallback",
            messages="Prefer explicit evidence.",
            saved_model_content=saved,
            source="saved model abc",
        )
        from_recipe = ai_definition.compile_definition(
            {
                "Voltage": {
                    "description": "Voltage and unit",
                    "type": "object",
                    "examples": "{value: 12, uom: VDC}",
                    "properties": "value,uom",
                }
            },
            model="gpt-5.4-mini",
            messages=[
                "Use normalized units.",
                "Prefer explicit evidence.",
            ],
        )

    assert from_saved.output == from_recipe.output
    assert from_saved.root_schema == from_recipe.root_schema
    assert from_saved.model == "gpt-5.4-mini"
    assert from_saved.messages == [
        "Use normalized units.",
        "Prefer explicit evidence.",
    ]
    assert "model_id.settings.gptmodel mapped to model" in caplog.text
    assert "model_id.settings.additionalmessages mapped to messages" in caplog.text


def test_saved_model_rejects_unknown_populated_columns():
    saved = _saved_model(
        ["Voltage", "Voltage", "string", "unexpected"],
        columns=["Find", "Description", "Type", "Mystery Column"],
    )

    with pytest.raises(ValueError, match="unsupported saved-model column 'mysterycolumn'"):
        ai_definition.compile_definition(
            None,
            model="gpt-5.4-mini",
            saved_model_content=saved,
            source="saved model abc",
        )


def test_compiler_maps_safe_legacy_schema_forms_and_rejects_unsupported_ones(caplog):
    with caplog.at_level(logging.WARNING, logger="wrangles.ai_definition"):
        compiled = ai_definition.compile_definition(
            {
                "count": {
                    "type": "int",
                    "nullable": True,
                },
                "status": {
                    "const": "active",
                },
            },
            model="gpt-5.4-mini",
        )

    assert compiled.output["count"]["type"] == ["integer", "null"]
    assert compiled.output["status"]["enum"] == ["active"]
    assert "mapped legacy type 'int' to 'integer'" in caplog.text
    assert "mapped nullable: true to a null type union" in caplog.text
    assert "mapped const to a single-value enum" in caplog.text

    with pytest.raises(ValueError, match="patternProperties"):
        ai_definition.compile_definition(
            {
                "attributes": {
                    "type": "object",
                    "patternProperties": {".*": {"type": "string"}},
                }
            },
            model="gpt-5.4-mini",
        )

    with pytest.raises(ValueError, match="unsupported structured-output keyword.*format"):
        ai_definition.compile_definition(
            {"date": {"type": "string", "format": "date"}},
            model="gpt-5.4-mini",
        )


def test_compiler_infers_container_types_from_schema_keywords(caplog):
    with caplog.at_level(logging.WARNING, logger="wrangles.ai_definition"):
        compiled = ai_definition.compile_definition(
            {
                "attribute": {
                    "properties": {
                        "value": {"type": "number"},
                    }
                },
                "tags": {
                    "items": {"type": "string"},
                },
            },
            model="gpt-5.4-mini",
        )

    assert compiled.output["attribute"]["type"] == "object"
    assert compiled.output["tags"]["type"] == "array"
    assert "inferred type 'object'" in caplog.text
    assert "inferred type 'array'" in caplog.text


def test_dynamic_dictionary_flows_through_yaml_recipe(monkeypatch):
    calls = []

    def call_structured(data, api_key, payload, *args):
        calls.append((data, api_key, payload))
        return {
            "attributes": {"Voltage": "12 VDC"},
            "source": "description",
        }

    monkeypatch.setattr(openai_responses, "call_structured", call_structured)

    result = wrangles.recipe.run(
        """
        wrangles:
        - extract.ai:
            input: Description
            api_key: dummy
            threads: 1
            output:
              attributes:
                type: object
                additionalProperties:
                  type: string
              source:
                type: string
        """,
        dataframe=pd.DataFrame({"Description": ["Voltage: 12 VDC"]}),
    )

    text_format = calls[0][2]["text"]["format"]
    assert result["attributes"].tolist() == [{"Voltage": "12 VDC"}]
    assert result["source"].tolist() == ["description"]
    assert text_format["strict"] is False
    assert text_format["schema"]["properties"]["attributes"]["additionalProperties"] == {
        "type": "string"
    }


def test_saved_model_without_inline_output_flows_through_yaml_recipe(monkeypatch):
    saved = _saved_model(
        ["Color", "Named color", "string", "", "", "", "", ""],
        settings={
            "GPTModel": "gpt-5-mini",
            "AdditionalMessages": "Return the explicit color.",
        },
    )
    calls = []

    monkeypatch.setattr(
        wrangles.extract._data,
        "model_content",
        lambda model_id: saved,
    )

    def call_structured(data, api_key, payload, *args):
        calls.append(payload)
        return {"Color": "yellow"}

    monkeypatch.setattr(openai_responses, "call_structured", call_structured)

    result = wrangles.recipe.run(
        """
        wrangles:
        - extract.ai:
            input: Description
            model_id: saved-model
            api_key: dummy
            threads: 1
        """,
        dataframe=pd.DataFrame({"Description": ["yellow square"]}),
    )

    assert result["Color"].tolist() == ["yellow"]
    assert calls[0]["model"] == "gpt-5-mini"
    assert "Return the explicit color." in calls[0]["instructions"]
