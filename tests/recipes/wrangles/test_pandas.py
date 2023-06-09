"""
Tests for passthrough pandas capabilities
"""
import wrangles
import pandas as pd

#
# PASSTHROUGH
#
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

#
# NATIVE RECIPE WRANGLES
#
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

def test_drop_one_column():
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
          columns: col2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert list(df.columns) == ['col']

def test_drop_multiple_columns():
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
          columns:
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

def test_round_specify_decimals():
    """
    Test round with one input and output. decimals default is 0
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                col1: 3.13
                col2: 1.16

        wrangles:
          - round:
              input:
                - col1
                - col2
              decimals: 1
        """
    )
    assert (
        df['col1'][0] == 3.1 and
        df['col2'][0] == 1.2
    )

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
    data = pd.DataFrame(
        {
            'http_status': [200, 200, 404, 404, 301],
            'response_time': [0.04, 0.02, 0.07, 0.08, 1.0]
        },
        index=['Firefox', 'Chrome', 'Safari', 'IE10', 'Konqueror']
    )
    
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