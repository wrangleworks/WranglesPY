import wrangles
import pandas as pd

def test_read():
    """
    Test an unmodified read
    """
    df = wrangles.recipe.run(
        """
        read:
          - input
        """,
        dataframe=pd.DataFrame({"header": ["value"]})
    )
    assert df["header"][0] == "value"

def test_read_columns():
    """
    Test that only the specified columns are read
    """
    df = wrangles.recipe.run(
        """
        read:
          - input:
              columns: header1
        """,
        dataframe=pd.DataFrame({
            "header1": ["value1"],
            "header2": ["value2"]
        })
    )
    assert df.columns.tolist() == ["header1"] and df["header1"][0] == "value1"

def test_read_where():
    """
    Test a read with a where
    """
    df = wrangles.recipe.run(
        """
        read:
          - input:
              where: idx < 2
        """,
        dataframe=pd.DataFrame({
            "idx": [0, 1, 2],
            "header1": ["a", "b", "c"],
            "header2": [1,2,3]
        })
    )
    assert (
        df.columns.tolist() == ["idx", "header1", "header2"] and
        df["header1"][0] == "a" and
        len(df) == 2
    )

def test_read_union():
    """
    Test as part of a union
    """
    df = wrangles.recipe.run(
        """
        read:
          - union:
              sources:
                - test:
                    rows: 1
                    values:
                      idx: 0
                      header1: a
                - input
        """,
        dataframe=pd.DataFrame({
            "idx": [1, 2, 3],
            "header1": ["b", "c", "d"],
        })
    )
    assert (
        df.columns.tolist() == ["idx", "header1"] and
        df["header1"].values.tolist() == ["a", "b", "c", "d"] and
        len(df) == 4
    )

def test_read_no_dataframe():
    """
    Test that reading input without a dataframe being
    passed in returns an empty dataframe instead of erroring
    https://github.com/wrangleworks/WranglesPY/issues/943
    """
    df = wrangles.recipe.run(
        """
        read:
          - input
        """
    )
    assert df.empty

def test_read_union_no_dataframe():
    """
    Test that a union with input as a source falls back to
    the other source(s) when no dataframe is passed in
    https://github.com/wrangleworks/WranglesPY/issues/943
    """
    df = wrangles.recipe.run(
        """
        read:
          - union:
              sources:
                - test:
                    rows: 1
                    values:
                      idx: 0
                      header1: a
                - input
        """
    )
    assert (
        df.columns.tolist() == ["idx", "header1"] and
        df["header1"].values.tolist() == ["a"] and
        len(df) == 1
    )
