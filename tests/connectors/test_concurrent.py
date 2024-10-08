import wrangles
from datetime import datetime
import time
import pandas as pd

def wait_and_read(duration):
    time.sleep(duration)
    return pd.DataFrame({"column": [f"value{str(duration)}"]})

def test_read_multithread():
    """
    Test using the concurrent connector to read multithreaded
    """    
    start = datetime.now()

    df = wrangles.recipe.run(
        """
        read:
          - union:
              sources:
                - concurrent:
                    read:
                    - custom.wait_and_read:
                        duration: 5
                    - custom.wait_and_read:
                        duration: 2
                    - custom.wait_and_read:
                        duration: 3
        """,
        functions=wait_and_read
    )

    end = datetime.now()

    assert (
        5 <= (end - start).seconds < 10 and
        len(df) == 3
    )

def test_read_multiprocess():
    """
    Test using the concurrent connector to read using multiprocessing
    """    
    start = datetime.now()

    df = wrangles.recipe.run(
        """
        read:
          - union:
              sources:
                - concurrent:
                    use_multiprocessing: true
                    read:
                    - custom.wait_and_read:
                        duration: 5
                    - custom.wait_and_read:
                        duration: 2
                    - custom.wait_and_read:
                        duration: 3
        """,
        functions=wait_and_read
    )

    end = datetime.now()

    assert (
        5 <= (end - start).seconds < 10 and
        len(df) == 3
    )

test_vals = {
    "multithread": [],
    "multiprocess": []
}
def wait_and_append(df, wait, test_vals_key):
    time.sleep(wait)
    test_vals[test_vals_key].append(wait)

def test_write_multithread():
    """
    Test using the concurrent connector to write
    """
    start = datetime.now()

    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: value
        write:
          - concurrent:
              write:
                - custom.wait_and_append:
                     wait: 5
                     test_vals_key: multithread
                - custom.wait_and_append:
                     wait: 2
                     test_vals_key: multithread
                - custom.wait_and_append:
                     wait: 3
                     test_vals_key: multithread
        """,
        functions=wait_and_append
    )

    end = datetime.now()

    assert (
        5 <= (end - start).seconds < 10 and
        test_vals["multithread"] == [1,3,5]
    )

def sleep(seconds):
    """
    As a builtin function implemented in C,
    time.sleep() is not directly accessible to the recipe engine.
    Wrap as a python function to make the function definition available.
    """
    time.sleep(seconds)

def test_run_multithread():
    """
    Test using the concurrent connector to run
    using multithreading
    """
    start = datetime.now()

    wrangles.recipe.run(
        """
        run:
          on_start:
          - concurrent:
              run:
                - custom.sleep:
                     seconds: 5
                - custom.sleep:
                     seconds: 2
                - custom.sleep:
                     seconds: 3
        """,
        functions=sleep
    )

    end = datetime.now()

    assert 5 <= (end - start).seconds < 10

def test_run_multiprocess():
    """
    Test using the concurrent connector to run
    using multiprocessing
    """
    start = datetime.now()

    wrangles.recipe.run(
        """
        run:
          on_start:
          - concurrent:
              use_multiprocessing: true
              run:
                - custom.sleep:
                     seconds: 5
                - custom.sleep:
                     seconds: 2
                - custom.sleep:
                     seconds: 3
        """,
        functions=sleep
    )

    end = datetime.now()

    assert 5 <= (end - start).seconds < 10