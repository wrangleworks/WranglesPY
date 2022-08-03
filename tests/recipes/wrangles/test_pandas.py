import wrangles
import pandas as pd

recipe = """
read:
  file:
    name: tests/samples/data.csv
"""
df_base = wrangles.recipe.run(recipe)


def test_pandas_head():
    """
    Test using pandas head function
    """
    recipe = """
      wrangles:
        - pandas.head:
            parameters:
              n: 1
    """
    df = wrangles.recipe.run(recipe, dataframe=df_base)
    assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 1

def test_pandas_tail():
    """
    Test using pandas tail function
    """
    recipe = """
      wrangles:
        - pandas.tail:
            parameters:
              n: 1
    """
    df = wrangles.recipe.run(recipe, dataframe=df_base)
    assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 1
    
    
# pandas function, take in an input and create new column for output
def test_pandas_func_1():
    data = pd.DataFrame({
        'numbers': [3.14159265359, 2.718281828]
    })
    recipe = """
    wrangles:
      - pandas.round:
          input: numbers
          output: round_num
          decimals: 2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['round_num'].iloc[0] == 3