import wrangles
import pandas as pd

def test_pd_copy_one_col():
    """
    Test one input and output (strings)
    """
    data = pd.DataFrame({
        'col': ['SuperMario']
    })
    recipe = """
    wrangles:
      - pd.copy:
          input: col
          output: col-copy
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert list(df.columns) == ['col', 'col-copy']
    
def test_pd_copy_multi_cols():
    """
    Test multiple inputs and outputs (list)
    """
    data = pd.DataFrame({
        'col': ['Mario'],
        'col2': ['Luigi']
    })
    recipe = """
    wrangles:
      - pd.copy:
          input:
            - col
            - col2
          output:
            - col1-copy
            - col2-copy
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert list(df.columns) == ['col', 'col2', 'col1-copy', 'col2-copy']

def test_pd_drop_one_col():
    """
    Test drop using one column (string)
    """
    data = pd.DataFrame({
        'col': ['Mario'],
        'col2': ['Luigi']
    })
    recipe = """
    wrangles:
      - pd.drop:
          column: col2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert list(df.columns) == ['col']

def test_pd_drop_multi_column():
    """
    Test multiple columns (list)
    """
    data = pd.DataFrame({
        'col': ['Mario'],
        'col2': ['Luigi'],
        'col3': ['Bowser'],
    })
    recipe = """
    wrangles:
      - pd.drop:
          column:
            - col2
            - col3
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert list(df.columns) == ['col']


def test_pd_transpose():
    """
    Test transpose
    """
    data = pd.DataFrame({
        'col': ['Mario'],
        'col2': ['Luigi'],
        'col3': ['Bowser'],
    }, index=['Characters'])
    recipe = """
    wrangles:
      - pd.transpose: {}
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert list(df.columns) == ['Characters']