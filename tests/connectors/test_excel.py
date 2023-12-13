import wrangles
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