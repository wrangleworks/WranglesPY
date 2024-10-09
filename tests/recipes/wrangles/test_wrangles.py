"""
Test generic wrangles functionality, not specific
to an individual wrangle
"""
import wrangles
import pandas as pd
import numpy as np

class TestWhere:
    """
    Test general where behaviour
    """
    def test_double_where_input(self):
        """
        Test using multiple where on different rows
        overwriting the input
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.case:
                input: col2
                case: upper
                where: col1 = 1

            - convert.case:
                input: col2
                case: lower
                where: col1 = 2 
            """,
            dataframe= pd.DataFrame({
                'col1': [1, 2],
                'col2': ['HeLlO', 'WoRlD'],
            })
        )
        assert df['col2'][0] == 'HELLO' and df['col2'][1] == 'world'

    def test_double_where_output(self):
        """
        Test using multiple where on different rows
        with an output column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.case:
                input: col2
                output: results
                case: upper
                where: col1 = 1

            - convert.case:
                input: col2
                output: results
                case: lower
                where: col1 = 2 
            """,
            dataframe= pd.DataFrame({
                'col1': [1, 2],
                'col2': ['HeLlO', 'WoRlD'],
            })
        )
        assert df['results'][0] == 'HELLO' and df['results'][1] == 'world'

    def test_where_params(self):
        """
        Test using using a parameterized query
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.case:
                input: col2
                case: upper
                where: col1 = ?
                where_params:
                    - 1
            """,
            dataframe= pd.DataFrame({
                'col1': [1, 2],
                'col2': ['HeLlO', 'WoRlD'],
            })
        )
        assert df['col2'][0] == 'HELLO' and df['col2'][1] == 'WoRlD'

    def test_where_params_dict(self):
        """
        Test using using a parameterized query with dict
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.case:
                input: col2
                case: upper
                where: col1 = :key
                where_params:
                    key: 1
            """,
            dataframe= pd.DataFrame({
                'col1': [1, 2],
                'col2': ['HeLlO', 'WoRlD'],
            })
        )
        assert df['col2'][0] == 'HELLO' and df['col2'][1] == 'WoRlD'

    def test_where_params_variable(self):
        """
        Test using using a parameterized query
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.case:
                input: col2
                case: upper
                where: col1 = ?
                where_params:
                    - ${var}
            """,
            dataframe= pd.DataFrame({
                'col1': [1, 2],
                'col2': ['HeLlO', 'WoRlD'],
            }),
            variables={'var': 1}
        )
        assert df['col2'][0] == 'HELLO' and df['col2'][1] == 'WoRlD'

    def test_where_unsupported_sql_type(self):
        """
        Test using a value that isn't supported by SQL
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.case:
                input: col2
                case: upper
                where: col1 = 1
            """,
            dataframe= pd.DataFrame({
                'col1': [1, 2],
                'col2': ['HeLlO', 'WoRlD'],
                "col3": [np.array([1,2,3]), np.array([4,5,6])]
            }),
            variables={'var': 1}
        )
        assert (
            type(df["col3"][0]).__name__ == "ndarray" and
            list(df["col3"][0]) == [1,2,3]
        )

    def test_where_lists(self):
        """
        Test using where for columns that contain lists
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.case:
                input: col2
                case: upper
                where: col1 = 1
            """,
            dataframe= pd.DataFrame({
                'col1': [1, 2],
                'col2': ['HeLlO', 'WoRlD'],
                "col3": [[1,2,3], [4,5,6]]
            })
        )
        assert (
            df["col2"][0] == "HELLO" and
            df["col3"][0] == [1,2,3]
        )

    def test_where_sqlite_incompatible_fallback(self):
        """
        Test that where checks the whole dataframe if necessary
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.case:
                input: column
                case: upper
                where: column = 'a'
            """,
            dataframe= pd.DataFrame({
                'column': ["a"] * 20 + [["bad", "list"]],
            })
        )
        assert df["column"][0] == "A" and df["column"][20] == ["bad", "list"]

    def test_where_data_types_preserved(self):
        """
        Test that data types are preserved when using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - math:
                input: (Column2 - Column1)/Column1
                output: Column3
                where: NULLIF(Column1, '') IS NOT NULL
            """,
            dataframe= pd.DataFrame({
                'Column1': [65, 72, '', 92, 87, 79],
                'Column2': [2, 5, 4, 2, 1, 6]
            })
        )
        assert (
            df["Column1"].values.tolist() == [65, 72, '', 92, 87, 79] and
            df["Column3"][2] == ""
        )

    def test_where_falsy_value(self):
        """
        Ensure that falsy values from the original dataframe
        are not removed by the where clause
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - math:
                input: Column1 + 1
                output: Column1
                where: Column1 != 0
            """,
            dataframe= pd.DataFrame({
                'Column1': [0, 1, 2, 3],
            })
        )
        assert df["Column1"].values.tolist() == [0, 2, 3, 4]

    def test_where_input_wildcard(self):
        """
        Test that where works correct with an input
        column identified by a wildcard
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.case:
                input:
                - Column*
                case: upper
                where: clause = 'a'
            """,
            dataframe= pd.DataFrame({
                'Column1': ["a,b,c", "x,y,z"],
                "clause": ["a", "b"]
            })
        )
        assert df["Column1"][0] == "A,B,C" and df["Column1"][1] == "x,y,z"

    def test_where_preserves_column_order(self):
        """
        Test that where preserves the order of columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.case:
                input: col2
                case: upper
                where: col1 = 1
            """,
            dataframe= pd.DataFrame({
                'col1': [1, 2],
                'col2': ['HeLlO', 'WoRlD'],
                "col3": [[1,2,3], [4,5,6]]
            })
        )
        assert df.columns.tolist() == ["col1", "col2", "col3"]

def test_if_true():
    """
    Test that a wrangle is triggered
    when an if statement is true
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: value
        wrangles:
          - convert.case:
              input: header
              case: upper
              if: 1 == 1
        """
    )
    assert df["header"][0] == "VALUE"

def test_if_false():
    """
    Test that a wrangle is triggered
    when an if statement is true
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: value
        wrangles:
          - convert.case:
              input: header
              case: upper
              if: 1 == 2
        """
    )
    assert df["header"][0] == "value"

def test_if_template_variable():
    """
    Test that an if statement evaluates
    correctly with a template variable
    of the form ${variable}
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: value
        wrangles:
          - convert.case:
              input: header
              case: upper
              if: ${var} == 1
        """,
        variables={"var": 1}
    )
    assert df["header"][0] == "VALUE"

def test_if_variable_no_execution():
    """
    Test that an if statement parameterizes
    variables correctly and does not execute
    the values
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: value
        wrangles:
          - convert.case:
              input: header
              case: upper
              if: not(1 == 1 and should_be_parameterized)
        """,
        variables={"should_be_parameterized": "1 == 2"}
    )
    assert df["header"][0] == "value"
