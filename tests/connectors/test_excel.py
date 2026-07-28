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
