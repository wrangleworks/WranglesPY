import logging

import pandas as pd
import pytest
import wrangles

import wrangles.ai_definition as ai_definition
import wrangles.ai_cache as ai_cache
import wrangles.openai_responses as openai_responses


@pytest.fixture(autouse=True)
def _clear_result_cache():
    ai_cache.clear()
    yield
    ai_cache.clear()


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
    assert compiled.output["Voltage"]["type"] == ["object", "null"]
    assert compiled.output["Voltage"]["properties"]["value"]["type"] == [
        "number",
        "null",
    ]
    assert compiled.output["Voltage"]["properties"]["uom"]["type"] == [
        "string",
        "null",
    ]
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
    assert compiled.output["status"]["enum"] == ["active", None]
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

    assert compiled.output["attribute"]["type"] == ["object", "null"]
    assert compiled.output["tags"]["type"] == ["array", "null"]
    assert "inferred type 'object'" in caplog.text
    assert "inferred type 'array'" in caplog.text


def test_outputs_are_nullable_by_default_but_keys_remain_required():
    compiled = ai_definition.compile_definition(
        {
            "name": {"type": "string"},
            "count": {"type": "integer"},
            "available": {"type": "boolean"},
        },
        model="gpt-5.4-mini",
    )

    assert compiled.root_schema["required"] == ["name", "count", "available"]
    assert compiled.output["name"]["type"] == ["string", "null"]
    assert compiled.output["count"]["type"] == ["integer", "null"]
    assert compiled.output["available"]["type"] == ["boolean", "null"]

    schema = openai_responses.sanitize_schema(compiled.root_schema)
    parsed = openai_responses.validate_structured_output(
        {
            "name": None,
            "count": None,
            "available": None,
        },
        schema,
    )
    assert parsed == {
        "name": None,
        "count": None,
        "available": None,
    }
    with pytest.raises(ValueError):
        openai_responses.validate_structured_output(
            {
                "name": None,
                "count": None,
            },
            schema,
        )


def test_nullable_false_is_an_explicit_opt_out():
    compiled = ai_definition.compile_definition(
        {
            "required_name": {
                "type": "string",
                "nullable": False,
                "enum": ["active", "null"],
            }
        },
        model="gpt-5.4-mini",
    )

    assert compiled.output["required_name"]["type"] == "string"
    assert compiled.output["required_name"]["enum"] == ["active", "null"]


def test_saved_model_nullable_column_and_enum_string_null_are_normalized(caplog):
    saved = _saved_model(
        [
            "Power Source",
            "Only tools have a power source.",
            "string",
            "",
            "",
            "Corded, Battery, null",
            "",
            "",
            "",
        ],
        [
            "SKU",
            "Required identifier",
            "string",
            "",
            "",
            "",
            "",
            "",
            "FALSE",
        ],
        columns=[
            "Find",
            "Description",
            "Type",
            "Default",
            "Examples",
            "Enum",
            "Notes",
            "Properties",
            "Nullable",
        ],
    )

    with caplog.at_level(logging.WARNING, logger="wrangles.ai_definition"):
        compiled = ai_definition.compile_definition(
            None,
            model="gpt-5.4-mini",
            saved_model_content=saved,
            source="saved model nullable",
        )

    assert compiled.root_schema["required"] == ["Power_Source", "SKU"]
    assert compiled.output["Power_Source"]["type"] == ["string", "null"]
    assert compiled.output["Power_Source"]["enum"] == ["Corded", "Battery", None]
    assert compiled.output["SKU"]["type"] == "string"
    assert "converted the string 'null' to JSON null" in caplog.text


def test_saved_model_examples_accept_human_entered_pseudo_json():
    saved = _saved_model(
        [
            "Voltage",
            "Voltage and unit",
            "object",
            "",
            "{value: 12, uom: VDC},{value: 110, uom: VAC}",
            "",
            "",
            "value,uom",
        ],
        [
            "Application",
            "Explicit uses",
            "array",
            "",
            "Ceramic Tile, Slate",
            "",
            "",
            "",
        ],
        [
            "Dust Blower",
            "Explicit blower availability",
            "boolean",
            "",
            "true",
            "",
            "",
            "",
        ],
    )

    compiled = ai_definition.compile_definition(
        None,
        model="gpt-5.4-mini",
        saved_model_content=saved,
    )

    assert compiled.output["Voltage"]["examples"] == [
        {"value": 12, "uom": "VDC"},
        {"value": 110, "uom": "VAC"},
    ]
    assert compiled.output["Application"]["examples"] == [
        "Ceramic Tile",
        "Slate",
    ]
    assert compiled.output["Dust_Blower"]["examples"] == [True]


def test_saved_model_compiles_new_field_example_columns_and_legacy_examples():
    saved = _saved_model(
        [
            "Voltage",
            "Voltage and unit",
            "object",
            "",
            "",
            "",
            "",
            "value,uom",
            "Rating 120V",
            "{value: 120, uom: V}",
        ],
        [
            "Power Source",
            "How the tool is powered",
            "string",
            "",
            "Corded",
            "",
            "",
            "",
            "",
            "Battery",
        ],
        columns=[
            "Find",
            "Description",
            "Type",
            "Default",
            "Examples",
            "Enum",
            "Notes",
            "Properties",
            "Example - Input",
            "Example - Output",
        ],
    )

    compiled = ai_definition.compile_definition(
        None,
        model="gpt-5.4-mini",
        saved_model_content=saved,
    )

    assert compiled.field_examples == (
        ai_definition.CompiledFieldExample(
            field="Voltage",
            input="Rating 120V",
            output={"value": 120, "uom": "V"},
        ),
    )
    assert compiled.output["Power_Source"]["examples"] == ["Corded", "Battery"]


def test_recipe_field_pairs_and_record_examples_compile_to_stable_guidance():
    compiled = ai_definition.compile_definition(
        {
            "Power Source": {
                "type": "string",
                "examples": [
                    {
                        "name": "cordless tool",
                        "notes": "Voltage without a cord indicates a battery.",
                        "input": "18V cordless drill",
                        "output": "Battery",
                    },
                    "Corded",
                ],
            },
            "Voltage": {"type": "number"},
        },
        model="gpt-5.4-mini",
        examples=[
            {
                "name": "corded saw",
                "notes": "Use both fields from this complete record example.",
                "input": "120V corded jig saw",
                "output": {"Power Source": "Corded", "Voltage": 120},
            },
            {
                "input": "No electrical specifications",
                "output": {},
            },
        ],
    )

    assert compiled.output["Power_Source"]["examples"] == ["Corded"]
    assert compiled.field_examples[0].field == "Power_Source"
    assert compiled.field_examples[0].output == "Battery"
    assert compiled.field_examples[0].name == "cordless tool"
    assert compiled.field_examples[0].notes == "Voltage without a cord indicates a battery."
    assert compiled.record_examples[0].output == {
        "Power_Source": "Corded",
        "Voltage": 120,
    }
    assert compiled.record_examples[0].notes == (
        "Use both fields from this complete record example."
    )
    assert compiled.record_examples[1].output == {
        "Power_Source": None,
        "Voltage": None,
    }

    guidance = ai_definition.render_example_guidance(compiled)
    assert "<field_example" in guidance
    assert "<record_example" in guidance
    assert 'name="cordless tool"' in guidance
    assert "Voltage without a cord indicates a battery." in guidance
    assert "Use both fields from this complete record example." in guidance
    assert '"Power_Source": null' in guidance


def test_saved_model_can_supply_record_examples():
    saved = _saved_model(
        ["Color", "Explicit color", "string", "", "", "", "", ""],
    )
    saved["Examples"] = [{
        "input": "bright yellow handle",
        "output": {"Color": "yellow"},
    }]

    compiled = ai_definition.compile_definition(
        None,
        model="gpt-5.4-mini",
        saved_model_content=saved,
    )

    assert compiled.record_examples[0].input == "bright yellow handle"
    assert compiled.record_examples[0].output == {"Color": "yellow"}


def test_field_example_input_requires_output_but_explicit_null_is_valid():
    invalid = _saved_model(
        ["Color", "Explicit color", "string", "yellow handle", ""],
        columns=[
            "Find",
            "Description",
            "Type",
            "Example - Input",
            "Example - Output",
        ],
    )
    with pytest.raises(ValueError, match="Example - Input requires Example - Output"):
        ai_definition.compile_definition(
            None,
            model="gpt-5.4-mini",
            saved_model_content=invalid,
        )

    compiled = ai_definition.compile_definition(
        {
            "Color": {
                "type": "string",
                "examples": [{"input": "No color stated", "output": None}],
            }
        },
        model="gpt-5.4-mini",
    )
    assert compiled.field_examples[0].output is None


def test_record_example_rejects_unknown_output_field():
    with pytest.raises(ValueError, match="unknown output field 'Mystery'"):
        ai_definition.compile_definition(
            {"Color": {"type": "string"}},
            model="gpt-5.4-mini",
            examples=[{
                "input": "yellow",
                "output": {"Mystery": "yellow"},
            }],
        )


def test_human_value_parser_uses_safe_yaml_loader():
    dangerous = "!!python/object/apply:builtins.str [unsafe]"

    assert ai_definition._Compiler._parse_json_value(dangerous) == dangerous
    assert ai_definition._Compiler._parse_examples_value(dangerous) == dangerous


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


def test_field_and_record_examples_flow_through_yaml_recipe(monkeypatch):
    calls = []

    def call_structured(data, api_key, payload, *args):
        calls.append(payload)
        return {"Color": "yellow", "Voltage": None}

    monkeypatch.setattr(openai_responses, "call_structured", call_structured)

    result = wrangles.recipe.run(
        """
        wrangles:
        - extract.ai:
            input: Description
            api_key: dummy
            threads: 1
            instructions: Prefer explicit source values.
            output:
              Color:
                type: string
                examples:
                  - name: explicit field color
                    notes: This example guides only the Color field.
                    input: yellow handle
                    output: yellow
              Voltage:
                type: number
            record_examples:
              - name: complete yellow example
                notes: The voltage is intentionally absent.
                input: yellow manual tool
                output:
                  Color: yellow
        """,
        dataframe=pd.DataFrame({"Description": ["yellow manual tool"]}),
    )

    assert result["Color"].tolist() == ["yellow"]
    assert result["Voltage"].tolist() == [""]
    assert "<field_example" in calls[0]["instructions"]
    assert "<record_example" in calls[0]["instructions"]
    assert "Prefer explicit source values." in calls[0]["instructions"]
    assert "explicit field color" in calls[0]["instructions"]
    assert "This example guides only the Color field." in calls[0]["instructions"]
    assert "complete yellow example" in calls[0]["instructions"]
    assert "The voltage is intentionally absent." in calls[0]["instructions"]
    assert '"Voltage": null' in calls[0]["instructions"]


def test_recipe_messages_remains_a_compatibility_alias(monkeypatch):
    calls = []

    def call_structured(data, api_key, payload, *args):
        calls.append(payload)
        return {"Color": "yellow"}

    monkeypatch.setattr(openai_responses, "call_structured", call_structured)

    result = wrangles.recipe.run(
        """
        wrangles:
        - extract.ai:
            input: Description
            api_key: dummy
            threads: 1
            messages: Legacy recipe guidance.
            output:
              Color:
                type: string
        """,
        dataframe=pd.DataFrame({"Description": ["yellow handle"]}),
    )

    assert result["Color"].tolist() == ["yellow"]
    assert "Legacy recipe guidance." in calls[0]["instructions"]
