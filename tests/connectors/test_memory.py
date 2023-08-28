import time
import wrangles
from wrangles.connectors import memory
import pandas as pd


def test_memory_write():
    """
    Test memory connector
    without setting an ID
    """
    time.sleep(10)
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
          - memory: {}
        """
    )
    data = list(memory.dataframes.values())[-1]
    assert (
        data["columns"] == ["header1", "header2"] and
        len(data["data"]) == 5
    )

def test_memory_write_id():
    """
    Test memory connector
    with setting an ID
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
          - memory:
              id: memory_id
        """
    )
    data = memory.dataframes["memory_id"]
    assert (
        data["columns"] == ["header1", "header2"] and
        len(data["data"]) == 5
    )

def test_memory_write_args():
    """
    Test memory connector with custom arguments
    Sleep to prevent overlap with other tests
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
          - memory:
              id: memory_args
              key: val
        """
    )
    data = memory.dataframes["memory_args"]
    assert (
        data["columns"] == ["header1", "header2"] and
        data["key"] == "val"
    )

def test_memory_write_multiple():
    """
    Test memory connector with multiple outputs
    Sleep to prevent overlap with other tests
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
          - memory:
              id: memory_multiple_1
              key: val1

          - memory:
              id: memory_multiple_2
              key: val2
        """
    )
    data_1 = memory.dataframes["memory_multiple_1"]
    data_2 = memory.dataframes["memory_multiple_2"]
    assert (
        data_1["columns"] == ["header1", "header2"] and
        data_1["key"] == "val1" and
        data_2["columns"] == ["header1", "header2"] and
        data_2["key"] == "val2"
    )

def test_memory_read_id():
    """
    Test memory connector
    with setting an ID
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
          - memory:
              id: memory_read_id
        """
    )
    df = wrangles.recipe.run(
        """
        read:
          - memory:
              id: memory_read_id
        """
    )
    assert (
        df["header1"][0] == "value1" and
        len(df) == 5
    )

def test_memory_read():
    """
    Test memory connector
    with setting an ID
    """
    time.sleep(5)
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
    df = wrangles.recipe.run(
        """
        read:
          - memory: {}
        """
    )
    assert (
        df["header1"][0] == "value1" and
        len(df) == 5
    )

def test_memory_read_dict():
    """
    Test memory connector
    with setting an ID
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
          - memory:
              id: memory_read_dict
              orient: dict
        """
    )
    df = wrangles.recipe.run(
        """
        read:
          - memory:
              id: memory_read_dict
              orient: dict
        """
    )
    assert (
        df["header1"][0] == "value1" and
        len(df) == 5
    )

def test_memory_read_list():
    """
    Test memory connector
    with setting an ID
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
          - memory:
              id: memory_read_list
              orient: list
        """
    )
    df = wrangles.recipe.run(
        """
        read:
          - memory:
              id: memory_read_list
              orient: list
        """
    )
    assert (
        df["header1"][0] == "value1" and
        len(df) == 5
    )

def test_memory_read_split():
    """
    Test memory connector
    with setting an ID
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
          - memory:
              id: memory_read_split
              orient: split
        """
    )
    df = wrangles.recipe.run(
        """
        read:
          - memory:
              id: memory_read_split
              orient: split
        """
    )
    assert (
        df["header1"][0] == "value1" and
        len(df) == 5
    )

def test_memory_read_tight():
    """
    Test memory connector
    with setting an ID
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
          - memory:
              id: memory_read_tight
              orient: tight
        """
    )
    df = wrangles.recipe.run(
        """
        read:
          - memory:
              id: memory_read_tight
              orient: tight
        """
    )
    assert (
        df["header1"][0] == "value1" and
        len(df) == 5
    )

def test_memory_read_index():
    """
    Test memory connector
    with setting an ID
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
          - memory:
              id: memory_read_index
              orient: index
        """
    )
    df = wrangles.recipe.run(
        """
        read:
          - memory:
              id: memory_read_index
              orient: index
        """
    )
    assert (
        df["header1"][0] == "value1" and
        len(df) == 5
    )

def test_memory_read_keys():
    """
    Test memory connector
    with setting an ID
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
          - memory:
             id: memory_read_keys
             key: val
        """
    )
    df = wrangles.recipe.run(
        """
        read:
          - memory:
              id: memory_read_keys
              key: val
        """
    )
    assert (
        df["header1"][0] == "value1" and
        len(df) == 5
    )

def test_memory_read_split_keys():
    """
    Test memory connector
    with setting an ID
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
          - memory:
             id: memory_read_split_keys
             key: val
             orient: split
        """
    )
    df = wrangles.recipe.run(
        """
        read:
          - memory:
              id: memory_read_split_keys
              key: val
              orient: split
        """
    )
    assert (
        df["header1"][0] == "value1" and
        len(df) == 5
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

def test_queue():
    """
    Test the memory queue
    """
    memory.queue.append("a")
    memory.queue.append("b")
    memory.queue.append("c")
    assert (
        memory.queue.popleft() == "a" and
        memory.queue.popleft() == "b"
    )