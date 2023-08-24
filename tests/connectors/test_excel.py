import time
import wrangles
from wrangles.connectors import memory


def test_excel():
    time.sleep(15)
    memory.dataframes = []
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
                header2: value2
        
        write:
          - excel: {}
        """
    )
    data = memory.dataframes
    assert (
        data[0]["columns"] == ["header1", "header2"] and
        len(data[0]["data"]) == 5
    )

def test_excel_args():
    time.sleep(20)
    memory.dataframes = []
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
                header2: value2
        
        write:
          - excel:
              sheet: test
              row: 5
        """
    )
    data = memory.dataframes
    assert (
        data[0]["columns"] == ["header1", "header2"] and
        data[0]["sheet"] == "test" and
        data[0]["row"] == 5
    )

def test_excel_multiple():
    time.sleep(25)
    memory.dataframes = []
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
                header2: value2
        
        write:
          - excel:
              sheet: test1

          - excel:
              sheet: test2
        """
    )
    data = memory.dataframes
    assert (
        data[0]["columns"] == ["header1", "header2"] and
        data[0]["sheet"] == "test1" and
        data[1]["columns"] == ["header1", "header2"] and
        data[1]["sheet"] == "test2"
    )
