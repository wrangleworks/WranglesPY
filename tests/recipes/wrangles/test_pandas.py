"""
Tests for passthrough pandas capabilities
"""
import wrangles
import pandas as pd


def test_pandas_head():
    """
    Test using pandas head function
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - pandas.head:
              parameters:
                n: 1
        """,
        dataframe=pd.DataFrame(
            {'header': [1, 2, 3, 4, 5]}
        )
    )
    assert df['header'].values[0] == 1 and len(df) == 1

def test_pandas_tail():
    """
    Test using pandas tail function
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - pandas.tail:
              parameters:
                n: 1
        """,
        dataframe=pd.DataFrame(
            {'header': [1, 2, 3, 4, 5]}
        )
    )
    assert df['header'].values[0] == 5 and len(df) == 1

def test_pandas_input_output():
    """
    Test a function that has an input and output
    """
    data = pd.DataFrame({
        'numbers': [3.14159265359, 2.718281828]
    })
    recipe = """
    wrangles:
      - pandas.round:
          input: numbers
          output: round_num
          parameters:
            decimals: 2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['round_num'].iloc[0] == 3.14