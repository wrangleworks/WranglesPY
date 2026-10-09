import wrangles
import pandas as pd
import pytest
from wrangles.connectors import memory


def test_default_write():
    """
    Test memory connector
    without setting an ID
    """
    memory.dataframes = {}
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
                header2: value2
        
        write:
          - excel.sheet: {}
        """
    )
    data = [
        v
        for _, v in memory.dataframes.items()
        if v.get("connector") == "excel.sheet.write"
    ][0]
    memory.clear()
    assert (
        data["columns"] == ["header1", "header2"] and
        len(data["data"]) == 5
    )


def test_recipe_wrangle_in_batch_writes_all_rows_to_excel_sheet():
    """
    Test the WranglesXL output connector path when a recipe wrangle is used
    inside a batch. The Excel sheet output should receive the full combined
    dataframe, not only one batch.
    """
    memory.clear()
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1000
              values:
                header1: value1
        wrangles:
          - batch:
              batch_size: 100
              wrangles:
                - recipe:
                    wrangles:
                      - convert.case:
                          input: header1
                          case: upper
                    write:
                      - excel.sheet:
                          name: Partial
        write:
          - excel.sheet:
              name: Final
        """
    )

    excel_outputs = [
        v
        for v in memory.dataframes.values()
        if v.get("connector") == "excel.sheet.write"
    ]
    memory.clear()

    assert len(excel_outputs) == 1
    assert excel_outputs[0]["name"] == "Final"
    assert len(excel_outputs[0]["data"]) == 1000


def test_excel_sheet_append_accumulates_repeated_writes():
    """
    WranglesXL may receive repeated writes to the same sheet when work is
    batched. Default append behavior should accumulate rows in one payload.
    """
    memory.clear()
    df = pd.DataFrame({"header1": ["value1"] * 1000})
    for start in range(0, 1000, 100):
        wrangles.connectors.excel.sheet.write(
            df.iloc[start:start + 100],
            name="Results"
        )

    excel_outputs = [
        v
        for v in memory.dataframes.values()
        if v.get("connector") == "excel.sheet.write"
    ]
    memory.clear()

    assert len(excel_outputs) == 1
    assert excel_outputs[0]["name"] == "Results"
    assert len(excel_outputs[0]["data"]) == 1000


def test_excel_sheet_write_preserves_column_formatting():
    """Formatting configured in a recipe is passed through for WranglesXL."""
    memory.clear()
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                ID: 1
                Amount: 12.5
                Verified: true
                Notes: some long text
        write:
          - excel.sheet:
              name: Results
              formatting:
                columns:
                  ID:
                    bold: true
                    align: center
                  Amount:
                    num_format: '$#,##0.00'
                  Verified:
                    checkbox: true
                  Notes:
                    text_wrap: true
        """
    )

    excel_outputs = [
        v
        for v in memory.dataframes.values()
        if v.get("connector") == "excel.sheet.write"
    ]
    memory.clear()

    assert len(excel_outputs) == 1
    assert excel_outputs[0]["formatting"] == {
        "columns": {
            "ID": {"bold": True, "align": "center"},
            "Amount": {"num_format": "$#,##0.00"},
            "Verified": {"checkbox": True},
            "Notes": {"text_wrap": True},
        }
    }


def test_excel_sheet_formatting_options_match_xlsxwriter_syntax():
    """
    excel.sheet is rendered by WranglesXL via the Office API, not
    XlsxWriter/Polars, but the recipe syntax must still match the
    Polars/XlsxWriter formatting syntax already used by the `file` connector
    (see connectors/_formatting.py) so authors don't learn two syntaxes for
    the same concept. `align`, `num_format`, `bold`, `checkbox`, and
    `text_wrap` must all be real XlsxWriter Format properties.
    """
    import inspect
    import typing
    import xlsxwriter
    from wrangles.connectors.excel import _FORMATTING_OPTIONS, _ALIGNMENTS

    format_setters = {
        name[len("set_"):]
        for name in dir(xlsxwriter.format.Format)
        if name.startswith("set_")
    }
    assert _FORMATTING_OPTIONS <= format_setters

    # "general" has no XlsxWriter equivalent - it matches Excel's unformatted
    # default, so it is intentionally excluded from the XlsxWriter check.
    align_param = inspect.signature(
        xlsxwriter.format.Format.set_align
    ).parameters["alignment"]
    valid_alignments = set(typing.get_args(align_param.annotation))
    assert (_ALIGNMENTS - {"general"}) <= valid_alignments


def test_excel_sheet_formatting_rejects_unsupported_options():
    """The first-draft contract accepts only its five formatting options."""
    with pytest.raises(ValueError, match="font_color"):
        wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 1
                  values:
                    ID: 1
            write:
              - excel.sheet:
                  formatting:
                    columns:
                      ID:
                        font_color: red
            """
        )


def test_excel_sheet_append_accumulates_matching_formatting():
    """Repeated writes with the same formatting remain one output payload."""
    memory.clear()
    formatting = {"columns": {"ID": {"bold": True}}}

    for value in (1, 2):
        wrangles.connectors.excel.sheet.write(
            pd.DataFrame({"ID": [value]}),
            name="Results",
            formatting=formatting
        )

    excel_outputs = [
        v
        for v in memory.dataframes.values()
        if v.get("connector") == "excel.sheet.write"
    ]
    memory.clear()

    assert len(excel_outputs) == 1
    assert excel_outputs[0]["data"] == [[1], [2]]
    assert excel_outputs[0]["formatting"] == formatting


def test_excel_sheet_append_keeps_different_formatting_separate():
    """Formatting changes form ordered output segments for the same target."""
    memory.clear()
    wrangles.connectors.excel.sheet.write(
        pd.DataFrame({"ID": [1]}),
        name="Results",
        formatting={"columns": {"ID": {"bold": True}}}
    )
    wrangles.connectors.excel.sheet.write(
        pd.DataFrame({"ID": [2]}),
        name="Results",
        formatting={"columns": {"ID": {"align": "center"}}}
    )
    wrangles.connectors.excel.sheet.write(
        pd.DataFrame({"ID": [3]}),
        name="Results",
        formatting={"columns": {"ID": {"bold": True}}}
    )

    excel_outputs = [
        v
        for v in memory.dataframes.values()
        if v.get("connector") == "excel.sheet.write"
    ]
    memory.clear()

    assert len(excel_outputs) == 3
    assert [output["data"] for output in excel_outputs] == [
        [[1]], [[2]], [[3]]
    ]


def test_excel_sheet_append_aligns_dynamic_batch_columns_by_name():
    """
    Dynamic dictionary keys can create different columns in each batch.
    Accumulated Excel output must union the columns and align values by name
    instead of stacking each batch positionally.
    """
    memory.clear()
    batches = [
        pd.DataFrame({"ID": [1], "A": [1], "X": [97]}),
        pd.DataFrame({"ID": [2], "B": [2], "Y": [98]}),
        pd.DataFrame({"ID": [3], "C": [3], "Z": [99]}),
        pd.DataFrame({"ID": [4], "D": [4], "Zz": [100]}),
    ]

    for df in batches:
        wrangles.connectors.excel.sheet.write(df, name="Results")

    excel_outputs = [
        v
        for v in memory.dataframes.values()
        if v.get("connector") == "excel.sheet.write"
    ]
    memory.clear()

    assert len(excel_outputs) == 1
    assert excel_outputs[0]["columns"] == [
        "ID", "A", "X", "B", "Y", "C", "Z", "D", "Zz"
    ]
    assert excel_outputs[0]["data"] == [
        [1, 1, 97, "", "", "", "", "", ""],
        [2, "", "", 2, 98, "", "", "", ""],
        [3, "", "", "", "", 3, 99, "", ""],
        [4, "", "", "", "", "", "", 4, 100],
    ]


def test_excel_sheet_overwrite_accumulates_repeated_writes():
    """
    Batched WranglesXL runs may emit repeated overwrite writes to the same
    sheet. The connector should still return one full payload so Excel replaces
    the sheet with all rows, not just the final batch.
    """
    memory.clear()
    df = pd.DataFrame({"header1": ["value1"] * 1000})
    for start in range(0, 1000, 100):
        wrangles.connectors.excel.sheet.write(
            df.iloc[start:start + 100],
            name="Results",
            action="overwrite"
        )

    excel_outputs = [
        v
        for v in memory.dataframes.values()
        if v.get("connector") == "excel.sheet.write"
    ]
    memory.clear()

    assert len(excel_outputs) == 1
    assert excel_outputs[0]["name"] == "Results"
    assert excel_outputs[0]["action"] == "overwrite"
    assert len(excel_outputs[0]["data"]) == 1000


def test_excel_sheet_overwrite_aligns_reordered_columns_by_name():
    """
    Overwrite batches with the same columns in a different order must retain
    the first payload's column order without shifting values.
    """
    memory.clear()
    wrangles.connectors.excel.sheet.write(
        pd.DataFrame({"ID": [1], "A": [1], "X": [97]}),
        name="Results",
        action="overwrite"
    )
    wrangles.connectors.excel.sheet.write(
        pd.DataFrame({"X": [98], "ID": [2], "A": [2]}),
        name="Results",
        action="overwrite"
    )

    excel_outputs = [
        v
        for v in memory.dataframes.values()
        if v.get("connector") == "excel.sheet.write"
    ]
    memory.clear()

    assert len(excel_outputs) == 1
    assert excel_outputs[0]["columns"] == ["ID", "A", "X"]
    assert excel_outputs[0]["data"] == [
        [1, 1, 97],
        [2, 2, 98],
    ]
    assert excel_outputs[0]["action"] == "overwrite"


def test_excel_sheet_overwrite_uses_append_after_first_external_batch():
    """
    WranglesXL can execute each batch as a separate Python run. In that case,
    in-memory accumulation is not available, so later overwrite batches must be
    returned as append actions.
    """
    df = pd.DataFrame({"header1": ["value1"] * 100})

    memory.clear()
    wrangles.connectors.excel.sheet.write(
        df,
        name="Results",
        action="overwrite",
        variables={"batch_number": 1, "batch_total": 10}
    )
    first_batch = [
        v
        for v in memory.dataframes.values()
        if v.get("connector") == "excel.sheet.write"
    ][0]

    memory.clear()
    wrangles.connectors.excel.sheet.write(
        df,
        name="Results",
        action="overwrite",
        variables={"batch_number": 2, "batch_total": 10}
    )
    second_batch = [
        v
        for v in memory.dataframes.values()
        if v.get("connector") == "excel.sheet.write"
    ][0]
    memory.clear()

    assert first_batch["action"] == "overwrite"
    assert second_batch["action"] == "append"


@pytest.fixture
def table_memory():
    memory.clear()
    yield
    memory.clear()


def test_table_recipe_reads_named_snapshot_and_emits_only_output(table_memory):
    snapshots = {"Products": {"columns": ["ID", "Price"], "data": [[1, 10], [2, 20]]}}
    result = wrangles.recipe.run(
        {"read": [{"excel.table": {"name": "products"}}],
         "wrangles": [{"math": {"output": "Price", "input": "Price * 2"}}],
         "write": [{"excel.table": {"name": "Results"}}]},
        variables={"__excel_tables": snapshots},
        dataframe=pd.DataFrame({"UnrelatedSelection": [999]}),
    )
    assert result.to_dict("list") == {"ID": [1, 2], "Price": [20, 40]}
    assert list(memory.dataframes.values()) == [{
        "index": [0, 1], "columns": ["ID", "Price"], "data": [[1, 20], [2, 40]],
        "connector": "excel.table.write", "name": "Results", "action": "replace",
        "sheet": "Recipe-Res", "cell": "A1",
    }]
    assert snapshots == {"Products": {"columns": ["ID", "Price"], "data": [[1, 10], [2, 20]]}}


def test_table_composed_read_uses_multiple_named_tables(table_memory):
    result = wrangles.recipe.run(
        {"read": [{"union": {"sources": [
            {"excel.table": {"name": "A"}}, {"excel.table": {"name": "B"}},
        ]}}]},
        variables={"__excel_tables": {
            "A": {"columns": ["ID"], "data": [[1]]},
            "B": {"columns": ["ID"], "data": [[2], [3]]},
        }},
    )
    assert result.to_dict("list") == {"ID": [1, 2, 3]}
    assert memory.dataframes == {}


def test_table_empty_read_and_replace_keep_headers(table_memory):
    df = wrangles.recipe.run(
        {"read": [{"excel.table": {"name": "Empty"}}],
         "write": [{"excel.table": {"name": "Results"}}]},
        variables={"__excel_tables": {"Empty": {"columns": ["ID"], "data": []}}},
    )
    assert df.shape == (0, 1)
    assert df.columns.tolist() == ["ID"]
    assert list(memory.dataframes.values())[0] == {
        "columns": ["ID"], "index": [], "data": [],
        "connector": "excel.table.write", "name": "Results", "action": "replace",
        "sheet": "Recipe-Res", "cell": "A1",
    }


@pytest.mark.parametrize("variables, message", [
    ({}, "supplied by WranglesXL"),
    ({"__excel_tables": {}}, "not found"),
    ({"__excel_tables": {"T": {}, "t": {}}}, "ambiguous"),
    ({"__excel_tables": {"T": []}}, "invalid data payload"),
    ({"__excel_tables": {"T": {"columns": ["ID"], "data": [[1, 2]]}}}, "match its headers"),
    ({"__excel_tables": {"T": {"columns": ["ID"], "data": None}}}, "match its headers"),
])
def test_table_read_rejects_missing_or_malformed_workbook_data(variables, message, table_memory):
    with pytest.raises((ValueError, RuntimeError), match=message):
        wrangles.connectors.excel.table.read("T", variables)
    assert memory.dataframes == {}


@pytest.mark.parametrize("name", [None, "", " ", " T", 5])
def test_table_rejects_invalid_names(name, table_memory):
    with pytest.raises(ValueError, match="name must"):
        wrangles.connectors.excel.table.read(name)
    with pytest.raises(ValueError, match="name must"):
        wrangles.connectors.excel.table.write(pd.DataFrame({"ID": [1]}), name)
    assert memory.dataframes == {}


@pytest.mark.parametrize("columns", [[], [""], [1], ["ID", "id"]])
def test_table_rejects_invalid_headers(columns, table_memory):
    with pytest.raises(ValueError, match="headers must"):
        wrangles.connectors.excel.table.read("T", {"__excel_tables": {
            "T": {"columns": columns, "data": []},
        }})
    with pytest.raises(ValueError, match="headers must"):
        wrangles.connectors.excel.table.write(pd.DataFrame(columns=columns), "T")
    assert memory.dataframes == {}


@pytest.mark.parametrize("action, number, total, expected", [
    ("replace", 1, 1, "replace"), ("append", 1, 1, "append"),
    ("replace", 1, 3, "replace"), ("replace", 2, 3, "append"),
    ("replace", 3, 3, "append"), ("append", 2, 3, "append"),
])
def test_table_write_normalizes_external_batch_action(action, number, total, expected, table_memory):
    wrangles.connectors.excel.table.write(
        pd.DataFrame({"ID": [number]}), "T", action,
        {"batch_number": number, "batch_total": total},
    )
    assert list(memory.dataframes.values()) == [{
        "columns": ["ID"], "index": [0], "data": [[number]],
        "name": "T", "action": expected, "connector": "excel.table.write",
        "sheet": "Recipe-T", "cell": "A1",
    }]


@pytest.mark.parametrize("action, variables, message", [
    ("create", {}, "action must"), ("overwrite", {}, "action must"),
    ("replace", {"batch_number": 0}, "positive integers"),
    ("replace", {"batch_total": "2"}, "positive integers"),
    ("replace", {"batch_number": True}, "positive integers"),
    ("replace", {"batch_number": 2, "batch_total": 1}, "exceeds"),
])
def test_table_write_rejects_invalid_action_or_batch_metadata(action, variables, message, table_memory):
    with pytest.raises(ValueError, match=message):
        wrangles.connectors.excel.table.write(pd.DataFrame({"ID": [1]}), "T", action, variables)
    assert memory.dataframes == {}


def test_table_multiple_writes_preserve_order_and_target_metadata(table_memory):
    wrangles.recipe.run(
        {"read": [{"excel.table": {"name": "${source}"}}],
         "write": [{"excel.table": {"name": "T", "action": "replace"}},
                   {"excel.table": {"name": "T", "action": "append"}},
                   {"excel.sheet": {"name": "Sheet"}}]},
        variables={"source": "A", "__excel_tables": {"A": {"columns": ["ID"], "data": [[1]]}}},
    )
    payloads = list(memory.dataframes.values())
    assert [(p["connector"], p["name"], p.get("action")) for p in payloads] == [
        ("excel.table.write", "T", "replace"), ("excel.table.write", "T", "append"),
        ("excel.sheet.write", "Sheet", None),
    ]
    assert [p["data"] for p in payloads] == [[[1]], [[1]], [[1]]]


def test_table_schema_requires_name_and_only_supported_actions():
    import yaml
    import jsonschema
    read = yaml.safe_load(wrangles.connectors.excel.table._schema["read"])
    write = yaml.safe_load(wrangles.connectors.excel.table._schema["write"])
    jsonschema.validate({"name": "Products"}, read)
    jsonschema.validate({"name": "Results", "action": "append"}, write)
    jsonschema.validate({"name": "Results", "sheet": "Sheet1", "cell": "C3"}, write)
    for value, schema in [({}, read), ({"name": ""}, read),
                          ({"name": "T", "action": "create"}, write),
                          ({"name": "T", "sheet": ""}, write)]:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(value, schema)



def test_table_is_discovered_in_generated_recipe_schema(monkeypatch, tmp_path):
    import json
    import runpy
    import shutil
    import requests
    import jsonschema
    from pathlib import Path
    from types import SimpleNamespace
    root = Path(__file__).resolve().parents[2]
    shutil.copy(root / "schema/recipe_base_schema.json", tmp_path / "recipe_base_schema.json")
    monkeypatch.chdir(tmp_path)
    def get_meta_schema(url):
        assert url == "http://json-schema.org/draft-07/schema#"
        return SimpleNamespace(json=lambda: jsonschema.Draft7Validator.META_SCHEMA)
    monkeypatch.setattr(requests, "get", get_meta_schema)
    runpy.run_path(str(root / "schema/generate_recipe_schema.py"))
    schema = json.loads((tmp_path / "schema.json").read_text())
    jsonschema.validate({
        "read": [{"excel.table": {"name": "Products", "columns": ["ID"]}}],
        "write": [{"excel.table": {"name": "Results", "action": "append", "columns": ["ID"]}}],
    }, schema)
    for recipe in [
        {"read": [{"excel.table": {}}]},
        {"write": [{"excel.table": {"name": "T", "action": "create"}}]},
    ]:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(recipe, schema)


@pytest.mark.parametrize("recipe_name, expected", [
    ("Clean", "Clean-Resu"), (None, "Recipe-Res"),
    ("A", "A-Results"), ("1234567890X", "1234567890"),
    ("A/B:C", "A_B_C-Resu"),
])
def test_table_write_default_sheet_and_cell(recipe_name, expected, table_memory):
    variables = {"recipe_name": recipe_name}
    wrangles.recipe.run(
        {"read": [{"test": {"rows": 1, "values": {"ID": 7}}}],
         "write": [{"excel.table": {"name": "Results"}}]},
        variables=variables,
    )
    payload, = memory.dataframes.values()
    assert payload == {"columns": ["ID"], "index": [0], "data": [[7]],
                       "connector": "excel.table.write", "name": "Results",
                       "action": "replace", "sheet": expected, "cell": "A1"}


def test_table_write_preserves_explicit_sheet_and_normalizes_cell(table_memory):
    wrangles.recipe.run(
        {"read": [{"test": {"rows": 1, "values": {"ID": 7}}}],
         "write": [{"excel.table": {"name": "Results", "sheet": "Manual output", "cell": "$c$3"}}]},
        variables={"recipe_name": "Other"},
    )
    payload, = memory.dataframes.values()
    assert (payload["sheet"], payload["cell"], payload["data"]) == ("Manual output", "C3", [[7]])


@pytest.mark.parametrize("options", [
    {"sheet": ""}, {"sheet": "a" * 32}, {"sheet": "bad/name"},
    {"sheet": "'quoted"}, {"sheet": 7}, {"cell": "A0"},
    {"cell": "A1:B2"}, {"cell": "Sheet1!A1"}, {"cell": "XFE1"},
    {"cell": "A1048577"}, {"cell": ""}, {"cell": 7},
])
def test_table_write_rejects_invalid_locations_before_output(options, table_memory):
    with pytest.raises(ValueError, match="excel.table (sheet|cell)"):
        wrangles.connectors.excel.table.write(pd.DataFrame({"ID": [1]}), "Results", **options)
    assert memory.dataframes == {}


def test_table_write_accepts_last_excel_cell(table_memory):
    wrangles.connectors.excel.table.write(pd.DataFrame(columns=["ID"]), "Results", cell="XFD1048576")
    payload, = memory.dataframes.values()
    assert payload["cell"] == "XFD1048576" and payload["data"] == []


@pytest.mark.parametrize("composition, columns, rows", [
    ({"union": {"sources": [{"excel.table": {"name": "Products"}}, {"excel.table": {"name": "Extra"}}]}},
     ["ID", "Value", "Category"], [[1, "alpha", None], [2, "bravo", None], [3, None, "external"]]),
    ({"join": {"how": "left", "left_on": "ID", "right_on": "ID", "sources": [{"excel.table": {"name": "Products"}}, {"excel.table": {"name": "Lookup"}}]}},
     ["ID", "Value", "Category"], [[1, "alpha", None], [2, "bravo", "tools"]]),
    ({"concatenate": {"sources": [{"excel.table": {"name": "Products"}}, {"excel.table": {"name": "Marker"}}]}},
     ["ID", "Value", "Marker"], [[1, "alpha", "a"], [2, "bravo", "b"]]),
    ([{"excel.table": {"name": "Products"}}, {"excel.table": {"name": "Extra"}}],
     ["ID", "Value", "Category"], [[1, "alpha", None], [2, "bravo", None], [3, None, "external"]]),
])
def test_table_composed_reads_emit_json_safe_output_and_location(composition, columns, rows, table_memory):
    import copy
    import json
    snapshots = {
        "Products": {"columns": ["ID", "Value"], "data": [[1, "alpha"], [2, "bravo"]]},
        "Extra": {"columns": ["ID", "Category"], "data": [[3, "external"]]},
        "Lookup": {"columns": ["ID", "Category"], "data": [[2, "tools"]]},
        "Marker": {"columns": ["Marker"], "data": [["a"], ["b"]]},
    }
    original = copy.deepcopy(snapshots)
    result = wrangles.recipe.run(
        {"read": composition, "write": [{"excel.table": {"name": "Results", "cell": "D4"}}]},
        variables={"__excel_tables": snapshots, "recipe_name": "Clean"},
    )
    payload, = memory.dataframes.values()
    assert json.loads(json.dumps(payload, allow_nan=False))["data"] == rows
    assert payload["columns"] == columns
    assert (payload["sheet"], payload["cell"]) == ("Clean-Resu", "D4")
    assert result.columns.tolist() == columns and len(result) == len(rows)
    assert snapshots == original


def test_table_write_normalizes_nullable_values_without_mutating_input(table_memory):
    import json
    frame = pd.DataFrame({"ID": [1, 2, 3], "Value": [float("nan"), pd.NA, pd.NaT]})
    original = frame.copy(deep=True)
    wrangles.connectors.excel.table.write(frame, "Results")
    payload, = memory.dataframes.values()
    assert json.loads(json.dumps(payload, allow_nan=False))["data"] == [[1, None], [2, None], [3, None]]
    pd.testing.assert_frame_equal(frame, original)


def test_table_write_keeps_default_location_across_external_batches(table_memory):
    for number in (1, 2):
        wrangles.connectors.excel.table.write(
            pd.DataFrame({"ID": [number]}), "Results",
            variables={"recipe_name": "Clean", "batch_number": number, "batch_total": 2},
        )
    assert [(p["sheet"], p["cell"], p["action"], p["data"]) for p in memory.dataframes.values()] == [
        ("Clean-Resu", "A1", "replace", [[1]]), ("Clean-Resu", "A1", "append", [[2]]),
    ]
