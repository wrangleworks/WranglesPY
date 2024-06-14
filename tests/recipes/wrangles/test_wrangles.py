"""
Test generic wrangles functionality, not specific
to an individual wrangle
"""
import wrangles
import pandas as pd
import numpy as np
import pytest


def test_double_where_input():
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

def test_double_where_output():
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

def test_where_params():
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

def test_where_params_dict():
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

def test_where_params_variable():
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

def test_where_unsupported_sql_type():
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

def test_where_data_types_preserved():
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

def test_where_empty_case_df():
    """
    Test using where on an empty dataframe
    """
    with pytest.raises(ValueError, match="No rows found for where clause:"):
        wrangles.recipe.run(
            """
            wrangles:
              - convert.case:
                  input: col2
                  case: upper
                  where: col1 = 2
            """,
            dataframe=pd.DataFrame({
                'col1': ['1', '0', '1', '0', '1'],
                'col2': ['python', 'java', 'sql', 'r', 'c++'],
            })
        )

def test_where_empty_prefix_df():
    """
    Test using where on an empty dataframe
    """
    with pytest.raises(ValueError, match="No rows found for where clause:"):
        wrangles.recipe.run(
            """
            wrangles:
              - format.prefix:
                  input: col2
                  value: test-
                  where: col1 = 2
            """,
            dataframe=pd.DataFrame({
                'col1': ['1', '0', '1', '0', '1'],
                'col2': ['python', 'java', 'sql', 'r', 'c++'],
            })
        )

def test_where_empty_suffix_df():
    """
    Test using where on an empty dataframe
    """
    with pytest.raises(ValueError, match="No rows found for where clause:"):
        wrangles.recipe.run(
            """
            wrangles:
              - format.suffix:
                  input: col2
                  value: test-
                  where: col1 = 2
            """,
            dataframe=pd.DataFrame({
                'col1': ['1', '0', '1', '0', '1'],
                'col2': ['python', 'java', 'sql', 'r', 'c++'],
            })
        )

def test_where_pad_df():
    """
    Test using where on an empty dataframe
    """
    with pytest.raises(ValueError, match="No rows found for where clause:"):
        wrangles.recipe.run(
            """
            wrangles:
                - format.prefix:
                    input: col2
                    side: right
                    char: ~
                    where: col1 = 2
            """,
            dataframe=pd.DataFrame({
                'col1': ['1', '0', '1', '0', '1'],
                'col2': ['python', 'java', 'sql', 'r', 'c++'],
            })
        )
