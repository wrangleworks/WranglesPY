import time
import wrangles
from wrangles.connectors import memory
import pandas as pd


def test_memory():
    """
    Test memory connector
    """
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
                header2: value2
        
        write:
          - memory: {}
        """
    )
    data = memory.dataframes
    assert (
        data[0]["columns"] == ["header1", "header2"] and
        len(data[0]["data"]) == 5
    )

def test_memory_args():
    """
    Test memory connector with custom arguments
    Sleep to prevent overlap with other tests
    """
    time.sleep(5)
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
          - memory:
              key: val
        """
    )
    data = memory.dataframes
    assert (
        data[0]["columns"] == ["header1", "header2"] and
        data[0]["key"] == "val"
    )

def test_memory_multiple():
    """
    Test memory connector with multiple outputs
    Sleep to prevent overlap with other tests
    """
    time.sleep(10)
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
          - memory:
              key: val1

          - memory:
              key: val2
        """
    )
    data = memory.dataframes
    assert (
        data[0]["columns"] == ["header1", "header2"] and
        data[0]["key"] == "val1" and
        data[1]["columns"] == ["header1", "header2"] and
        data[1]["key"] == "val2"
    )

def test_variables():
    """
    Test that memory variables are passed
    between functions
    """
    memory.variables["key"] = 1

    def _test():
        return pd.DataFrame({
            "col1": [memory.variables["key"]] * 5
        })
    
    df = wrangles.recipe.run(
        """
        read:
          - custom._test: {}
        """,
        functions=_test
    )
    assert df["col1"][0] == 1 and len(df) == 5