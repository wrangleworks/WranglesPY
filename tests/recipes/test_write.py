"""
Tests for generic write functionality.
"""

import wrangles
import pandas as pd


def test_specify_columns():
    """
    Test writing and selecting only a subset of columns
    """
    data = pd.DataFrame({"col1": ["val1"], "col2": ["val2"]})
    recipe = """
    write:
      - dataframe: 
          columns:
            - col1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.columns == ["col1"]


def test_specify_columns_wildcard():
    """
    Test writing and selecting only a subset of columns using a wildcard
    """
    data = pd.DataFrame({"col1": ["val1"], "col2": ["val2"]})
    recipe = """
    write:
      - dataframe: 
          columns:
            - col*
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.columns.tolist() == ["col1", "col2"]


def test_specify_columns_regex():
    """
    Test writing and selecting only a subset of columns using regex
    """
    data = pd.DataFrame({"col1": ["val1"], "col2": ["val2"], "col3a": ["val3"]})
    recipe = """
    write:
      - dataframe: 
          columns:
            - "regex: col."
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.columns.tolist() == ["col1", "col2"]


def test_specify_not_columns():
    """
    Test writing and excluding a subset of columns
    """
    data = pd.DataFrame({"col1": ["val1"], "col2": ["val2"]})
    recipe = """
    write:
      - dataframe: 
          not_columns:
            - col2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.columns == ["col1"]


def test_specify_not_columns_wildcard():
    """
    Test writing and excluding a subset of columns using a wildcard
    """
    data = pd.DataFrame({"col1": ["val1"], "col2": ["val2"], "3col": ["val3"]})
    recipe = """
    write:
      - dataframe: 
          not_columns:
            - col*
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.columns == ["3col"]


def test_specify_not_columns_regex():
    """
    Test writing and excluding a subset of columns using a regex
    """
    data = pd.DataFrame({"col1": ["val1"], "col2": ["val2"], "3col": ["val3"]})
    recipe = """
    write:
      - dataframe: 
          not_columns:
            - "regex: col."
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.columns == ["3col"]


def test_specify_where():
    """
    Test writing and applying a WHERE sql criteria
    """
    data = pd.DataFrame(
        {"col1": ["val1", "val2", "val3"], "col2": ["vala", "valb", "valc"]}
    )
    recipe = """
    write:
      - dataframe: 
          where: |
            col1 = 'val1'
            or col2 = 'valc'
            
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df["col1"].values.tolist() == ["val1", "val3"]


def test_specify_where_params():
    """
    Test writing and applying a parameterized WHERE sql criteria
    """
    df = wrangles.recipe.run(
        """
        write:
          - dataframe: 
              where: col1 = ?
              where_params:
                - val1
        """,
        dataframe=pd.DataFrame(
            {"col1": ["val1", "val2", "val3"], "col2": ["vala", "valb", "valc"]}
        ),
    )
    assert df["col2"][0] == "vala" and len(df) == 1


def test_specify_where_params_dict():
    """
    Test writing and applying a parameterized WHERE sql criteria
    """
    df = wrangles.recipe.run(
        """
        write:
          - dataframe: 
              where: col1 = :var
              where_params:
                var: val1
        """,
        dataframe=pd.DataFrame(
            {"col1": ["val1", "val2", "val3"], "col2": ["vala", "valb", "valc"]}
        ),
    )
    assert df["col2"][0] == "vala" and len(df) == 1


def test_where_no_results():
    """
    Test a where that filters out all rows
    """
    df = wrangles.recipe.run(
        """
        write:
          - dataframe:
              where: col1 = 3
        """,
        dataframe=pd.DataFrame(
            {
                "col1": [1, 2],
                "col2": ["HeLlO", "WoRlD"],
            }
        ),
    )
    assert df.columns.tolist() == ["col1", "col2"] and len(df) == 0


def test_multiple():
    """
    Test writing more than one output
    """
    wrangles.recipe.run(
        """
        read:
          test:
            rows: 3
            values:
              Column1: aaa
              Column2: bbb
        write:
          - file:
              name: tests/temp/temp.txt
          - file:
              name: tests/temp/temp.csv
        """
    )
    df1 = wrangles.recipe.run(
        """
        read:
          file:
              name: tests/temp/temp.txt
        """
    )
    df2 = wrangles.recipe.run(
        """
        read:
          file:
            name: tests/temp/temp.csv
        """
    )
    assert (
        df1.columns.tolist() == ["Column1", "Column2"]
        and len(df1) == 3
        and df1["Column1"][0] == "aaa"
        and df2.columns.tolist() == ["Column1", "Column2"]
        and len(df2) == 3
        and df2["Column2"][0] == "bbb"
    )


def test_order_by():
    """
    Test writing and ordering by a column
    """
    df = wrangles.recipe.run(
        """
        write:
        - dataframe: 
            order_by: col1
        """,
        dataframe=pd.DataFrame({"col1": [3, 2, 1]}),
    )
    assert df["col1"].values.tolist() == [1, 2, 3]


def test_order_by_desc():
    """
    Test writing and ordering by a column in descending order
    """
    df = wrangles.recipe.run(
        """
        write:
        - dataframe: 
            order_by: col1 DESC
        """,
        dataframe=pd.DataFrame({"col1": [1, 2, 3]}),
    )
    assert df["col1"].values.tolist() == [3, 2, 1]


def test_order_two_column():
    """
    Test writing and ordering by two columns
    """
    df = wrangles.recipe.run(
        """
        write:
        - dataframe: 
            order_by: col1 DESC, col2
        """,
        dataframe=pd.DataFrame({"col1": [1, 1, 2, 2], "col2": ["b", "a", "d", "c"]}),
    )
    assert df["col1"].values.tolist() == [2, 2, 1, 1] and df[
        "col2"
    ].values.tolist() == ["c", "d", "a", "b"]


def test_order_by_column_with_space():
    """
    Test writing and ordering by a column
    """
    df = wrangles.recipe.run(
        """
        write:
        - dataframe: 
            order_by: '"col 1"'
        """,
        dataframe=pd.DataFrame({"col 1": [3, 2, 1]}),
    )
    assert df["col 1"].values.tolist() == [1, 2, 3]


def test_order_by_independence():
    """
    Test 2 writes maintain independence when ordered
    """
    df = wrangles.recipe.run(
        """
        write:
        - memory:
            id: test_independence_ordered
            order_by: col1
        - memory:
            id: test_independence_unordered
        """,
        dataframe=pd.DataFrame({"col1": [3, 2, 1]}),
    )
    assert wrangles.connectors.memory.dataframes["test_independence_unordered"][
        "data"
    ] == [[3], [2], [1]] and wrangles.connectors.memory.dataframes[
        "test_independence_ordered"
    ][
        "data"
    ] == [
        [1],
        [2],
        [3],
    ]


def test_write_order_by_and_where():
    """
    Test a writes that includes an order by and a where condition
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 10000
              values:
                header: <number(0-100)>
        write:
          - dataframe:
              where: header > 50
              order_by: header
        """
    )
    assert (
        df.tail(1)["header"].iloc[0] == max(df["header"].values)
        and df.head(1)["header"].iloc[0] == min(df["header"].values)
        and df.head(1)["header"].iloc[0] > 50
    )


def test_write_if_true():
    """
    Test a write that uses an
    if statement that is true
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header1: value1
                header2: value2
        write:
          - dataframe:
              if: 1 == 1
              columns:
                - header1
        """
    )
    assert df.columns.tolist() == ["header1"]


def test_write_if_false():
    """
    Test a write that uses an
    if statement that is false
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header1: value1
                header2: value2
        write:
          - dataframe:
              if: 1 == 2
              columns:
                - header1
        """
    )
    assert df.columns.tolist() == ["header1", "header2"]


def test_write_if_template_variable():
    """
    Test a write that uses a template
    variable as part of an if statement
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header1: value1
                header2: value2
        write:
          - dataframe:
              if: ${var} == 1
              columns:
                - header1
        """,
        variables={"var": 1},
    )
    assert df.columns.tolist() == ["header1"]


def test_write_if_columns_variable():
    """
    Test a write that uses the columns variable
    that gives a list of the columns
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header1: value1
                header2: value2
        write:
          - dataframe:
              if: '"header2" in columns'
              columns:
                - header1
        """
    )
    assert df.columns.tolist() == ["header1", "header2"]


def test_write_if_column_count_variable():
    """
    Test a write that uses the column_count variable
    that gives the number of columns in the dataframe
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header1: value1
                header2: value2
        write:
          - dataframe:
              if: column_count > 1
              columns:
                - header1
        """
    )
    assert df.columns.tolist() == ["header1", "header2"]


def test_write_if_row_count_variable():
    """
    Test a write that uses the row_count variable
    that gives the number of rows in the dataframe
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 100000
              values:
                header: <number(0-100)>
        write:
          - dataframe:
              where: header > 90
              if: row_count > 50000
        """
    )
    assert len(df) == 100000


def test_write_if_dataframe_access():
    """
    Test a write that uses the dataframe variable
    to access dataframe content for conditional logic
    """
    df = wrangles.recipe.run(
        """
        write:
          - dataframe:
              if: df.loc[0, 'header'] == 'hello'
              columns:
                - header
        """,
        dataframe=pd.DataFrame({"header": ["hello", "world"], "other": ["a", "b"]}),
    )
    assert df.columns.tolist() == ["header"]
    assert len(df) == 2


def test_write_if_dataframe_access_false():
    """
    Test a write that uses the dataframe variable
    where the condition is false
    """
    df = wrangles.recipe.run(
        """
        write:
          - dataframe:
              if: df.loc[0, 'header'] == 'goodbye'
              columns:
                - header
        """,
        dataframe=pd.DataFrame({"header": ["hello", "world"], "other": ["a", "b"]}),
    )
    # When write condition is false, it returns the original dataframe
    assert df.columns.tolist() == ["header", "other"]
    assert len(df) == 2


def test_overwrite_write():
    """
    Test using a custom function to overwrite a standard connector for write
    """
    check_var = {}

    class file:
        def write(df, name):
            check_var["len"] = len(df)
            check_var["columns"] = df.columns.tolist()
            check_var["name"] = name

    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 10
              values:
                header: value
        write:
          - file:
              name: abc
        """,
        functions=file,
    )

    assert (
        check_var["len"] == 10
        and check_var["columns"] == ["header"]
        and check_var["name"] == "abc"
    )
