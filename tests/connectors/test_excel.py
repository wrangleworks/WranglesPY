import wrangles
import pandas as pd
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
