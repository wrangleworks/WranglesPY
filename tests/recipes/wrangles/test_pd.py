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
      - copy:
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
      - copy:
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
      - drop:
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
      - drop:
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
      - transpose: {}
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert list(df.columns) == ['Characters']
    
def test_round_one_input():
    """
    Test round with one input and output. decimals default is 0
    """
    data = pd.DataFrame({
        'col1': [3.13],
        'col2': [1.16],
        'col3': [2.5555],
        'col4': [3.15]
    })
    recipe = """
    wrangles:
      - round:
          input: col1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['col1'][0] == 3
    
def test_round_multi_input():
    """
    Test multiple inputs and outputs
    """
    data = pd.DataFrame({
        'col1': [3.13],
        'col2': [1.16],
        'col3': [2.5555],
        'col4': [3.15]
    })
    recipe = """
    wrangles:
      - round:
          input:
            - col1
            - col2
            - col3
          output:
            - out1
            - out2
            - out3
          decimals: 1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df[['out1', 'out2', 'out3']].values.tolist()[0] == [3.1, 1.2, 2.6]
    
def test_reindex():
    """
    Testing Pandas reindex function
    """
    index = ['Firefox', 'Chrome', 'Safari', 'IE10', 'Konqueror']
    data = pd.DataFrame({'http_status': [200, 200, 404, 404, 301],
                  'response_time': [0.04, 0.02, 0.07, 0.08, 1.0]},
                  index=index)
    
    rec = """
    wrangles:
      - reindex:
          index:
            - Safari
            - Iceweasel
            - Comodo Dragon
            - IE10
    """
    df = wrangles.recipe.run(recipe=rec, dataframe=data)
    assert df.index.to_list() == ['Safari', 'Iceweasel', 'Comodo Dragon', 'IE10']