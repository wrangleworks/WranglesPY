"""
Tests for passthrough pandas capabilities
"""
import wrangles
import pandas as pd
import pytest

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

def test_pandas_head_where():
    """
    Test using pandas head function using where
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - pandas.head:
              parameters:
                n: 2
              where: header > 2
        """,
        dataframe=pd.DataFrame(
            {'header': [1, 2, 3, 4, 5]}
        )
    )
    assert df.iloc[0]['header'] == 3 and len(df) == 2

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

def test_pandas_tail_where():
    """
    Test using pandas tail function using where
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - pandas.tail:
              parameters:
                n: 2
              where: header < 4
        """,
        dataframe=pd.DataFrame(
            {'header': [1, 2, 3, 4, 5]}
        )
    )
    assert df.iloc[0]['header'] == 2 and len(df) == 2

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

def test_pandas_input_output_where():
    """
    Test a function that has an input and output using where
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
          where: numbers > 3
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['round_num'].iloc[0] == 3.14 and df.iloc[1]['round_num'] == ''

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

def test_pd_copy_where():
    """
    Test copy using where
    """
    data = pd.DataFrame({
        'col': ['SuperMario', 'Luigi', 'Bowser'],
        'numbers': [4, 2, 8]
    })
    recipe = """
    wrangles:
      - copy:
          input: col
          output: col-copy
          where: numbers > 3
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['col-copy'] == 'SuperMario' and df.iloc[1]['col-copy'] == ''

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
    
def test_round_where():
    """
    Test round using where
    """
    data = pd.DataFrame({
        'col': [3.13, 1.16, 2.5555, 3.15]
    })
    recipe = """
    wrangles:
      - round:
          input: col
          output: rounded
          where: col > 2.5
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['rounded'] == 3.0 and df.iloc[1]['rounded'] == ''
    
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


def test_explode():
    """
    Test explode basic function
    """
    df = wrangles.recipe.run(
        recipe="""
        wrangles:
          - explode:
              input:
                - C
        """,
        dataframe=pd.DataFrame({
            'A': [[0, 1, 2], 'foo', [], [3, 4]],
            'B': 1,
            'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
        })
    )
    assert df['C'].tolist() == ['a', 'b', 'c', 'NAN', '', 'd', 'e']
    

def test_explode_string():
    """
    Test explode with input as a string
    """
    df = wrangles.recipe.run(
        recipe="""
        wrangles:
          - explode:
              input: A
        """,
        dataframe=pd.DataFrame({
            'A': [[0, 1, 2], 'foo', [], [3, 4]],
            'B': 1,
            'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
        })
    )
    assert df['A'].tolist() == [0, 1, 2, 'foo', '', 3, 4]

def test_explode_nothing_to_explode():
    """
    Test explode where there's nothing to change
    """
    df = wrangles.recipe.run(
        recipe="""
        wrangles:
          - explode:
              input: B
        """,
        dataframe=pd.DataFrame({
            'A': [[0, 1, 2], 'foo', [], [3, 4]],
            'B': 1,
            'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
        })
    )
    assert df['A'].tolist() == [[0, 1, 2], 'foo', [], [3, 4]]

def test_explode_multiple_columns():
    """
    Test explode with multiple columns
    """
    df = wrangles.recipe.run(
        recipe="""
        wrangles:
          - explode:
              input:
                - A
                - C
        """,
        dataframe=pd.DataFrame({
            'A': [[0, 1, 2], 'foo', [], [3, 4]],
            'B': 1,
            'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
        })
    )
    assert len(df['A']) == 7
    
def test_explode_non_existent_col():
    """
    Test explode function with a col that does not exists in df
    """
    with pytest.raises(KeyError) as info:
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - explode:
                input:
                  - AA
            """,
            dataframe=pd.DataFrame({
                'A': [[0, 1, 2], 'foo', [], [3, 4]],
                'B': 1,
                'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
            })
        )
    assert info.typename == 'KeyError'

def test_explode_multiple_columns_wildcard():
    """
    Test explode multiple columns defined
    using a wildcard
    """
    df = wrangles.recipe.run(
        recipe="""
        wrangles:
          - explode:
              input: A*
        """,
        dataframe=pd.DataFrame({
            'A1': [[0, 1, 2], 'foo', [], [3, 4]],
            'B': 1,
            'A2': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
        })
    )
    assert (
        df['A1'].tolist() == [0, 1, 2, 'foo', '', 3, 4] and
        df['A2'].tolist() == ['a', 'b', 'c', 'NAN', '', 'd', 'e']
    )

def test_explode_multiple_inconsistent():
    """
    Test explode multiple with columns
    but the columns are inconsistent lengths
    """
    with pytest.raises(ValueError) as info:
        wrangles.recipe.run(
            recipe="""
            wrangles:
            - explode:
                input:
                    - A
                    - C
            """,
            dataframe=pd.DataFrame({
                'A': [[0, 1, 2], 'foo', [], [3, 4]],
                'B': 1,
                'C': [['a', 'b'], 'NAN', [], ['d', 'e']]
            })
        )
    assert (
        info.typename == "ValueError" and 
        str(info.value) == "explode - columns must have matching element counts"
    )

def test_explode_reset_index_default():
    """
    Test explode with reset index as default
    """
    df = wrangles.recipe.run(
        recipe="""
        wrangles:
          - explode:
              input:
                - C
        """,
        dataframe=pd.DataFrame({
            'A': [[0, 1, 2], 'foo', [], [3, 4]],
            'B': 1,
            'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
        })
    )
    assert df.index.to_list() == [0, 0, 0, 1, 2, 3, 3]

def test_explode_reset_index_false():
    """
    Test explode with reset index as false
    """
    df = wrangles.recipe.run(
        recipe="""
        wrangles:
          - explode:
              input:
                - C
              reset_index: false
        """,
        dataframe=pd.DataFrame({
            'A': [[0, 1, 2], 'foo', [], [3, 4]],
            'B': 1,
            'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
        })
    )
    assert df.index.to_list() == [0, 0, 0, 1, 2, 3, 3]

def test_explode_reset_index_true():
    """
    Test explode with reset index as true
    """
    df = wrangles.recipe.run(
        recipe="""
        wrangles:
          - explode:
              input:
                - C
              reset_index: true
        """,
        dataframe=pd.DataFrame({
            'A': [[0, 1, 2], 'foo', [], [3, 4]],
            'B': 1,
            'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
        })
    )
    assert df.index.to_list() == [0, 1, 2, 3, 4, 5, 6]

def test_sort():
    """
    Test default sort
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 100
              values:
                column: <number(1.00-1000.00)>
        wrangles:
          - sort:
              by: column
        """
    )

    assert (
        df["column"][0] <= df["column"][1]
        and df["column"].tolist()[-2] <= df["column"].tolist()[-1]
    )

def test_sort_descending():
    """
    Test sort with a single column descending
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 100
              values:
                column: <number(1.00-1000.00)>
        wrangles:
          - sort:
              by: column
              ascending: false
        """
    )

    assert (
        df["column"][0] >= df["column"][1]
        and df["column"].tolist()[-2] >= df["column"].tolist()[-1]
    )

def test_lookup():
    """
    Test lookup function
    """
    data = pd.DataFrame({
        'Col1': ['One', 'Two', 'Three', 'Four'],
    })
    recipe = """
    wrangles:
      - lookup:
          input: Col1
          output: Col2
          reference:
            One: Eleven
            Two: Twelve
            Four: Fourteen
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Col2'] == 'Eleven' and df.iloc[1]['Col2'] == 'Twelve'

def test_lookup_multiple_inputs_outputs():
    """
    Test lookup function with multiple input and output columns
    """
    data = pd.DataFrame({
        'Col1': ['One', 'Two', 'Three', 'Four'],
        'Col2': ['Four', 'Three', 'Two', 'One']
    })
    recipe = """
    wrangles:
      - lookup:
          input: 
            - Col1
            - Col2
          output: 
            - Col3
            - Col4
          reference:
            One: Eleven
            Two: Twelve
            Four: Fourteen
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Col3'] == 'Eleven' and df.iloc[1]['Col4'] == ''

def test_lookup_multiple_outputs():
    """
    Test error when attempting to pass multiple output columns using one input
    """
    data = pd.DataFrame({
        'Col1': ['One', 'Two', 'Three', 'Four'],
        'Col2': ['Four', 'Three', 'Two', 'One']
    })
    recipe = """
    wrangles:
      - lookup:
          input: Col1
          output: 
            - Col3
            - Col4
          reference:
            One: Eleven
            Two: Twelve
            Four: Fourteen
    """
    with pytest.raises(ValueError) as info:
        wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == "ValueError" and 
        str(info.value) == "lookup - The input and output must be the same length."
    )

def test_lookup_no_output():
    """
    Test lookup function without an output
    """
    data = pd.DataFrame({
        'Col1': ['One', 'Two', 'Three', 'Four'],
        'Col2': ['Four', 'Three', 'Two', 'One']
    })
    recipe = """
    wrangles:
      - lookup:
          input: Col1
          reference:
            One: Eleven
            Two: Twelve
            Four: Fourteen
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Col1'] == 'Eleven'
    
def test_lookup_default():
    """
    Test lookup function using a default
    """
    data = pd.DataFrame({
        'Col1': ['One', 'Two', 'Three', 'Four']
    })
    recipe = """
    wrangles:
      - lookup:
          input: Col1
          output: Col2
          reference:
            One: Eleven
            Two: Twelve
            Four: Fourteen
          default: This is a default
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[2]['Col2'] == 'This is a default'