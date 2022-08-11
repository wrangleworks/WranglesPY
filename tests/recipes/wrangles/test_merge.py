import wrangles
import pandas as pd
import pytest

#
# Coalesce
#
def test_coalesce_1():
    data = pd.DataFrame({
        'Col1': ['A', '', ''],
        'Col2': ['', 'B', ''],
        'Col3': ['', '', 'C']
    })
    recipe = """
    wrangles:
      - merge.coalesce:
          input: 
            - Col1
            - Col2
            - Col3
          output: Output Col
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Output Col'].values.tolist() == ['A', 'B', 'C']

#
# Concatenate
#
# One column concat
def test_concatenate_1():
    data = pd.DataFrame({
        'Col1': [['A', 'B', 'C']]
    })
    recipe = """
    wrangles:
      - merge.concatenate:
          input: Col1
          output: Join List
          char: ' '
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Join List'] == 'A B C'
    
# Multi column concat
def test_concatenate_2():
    data = pd.DataFrame({
        'Col1': ['A'],
        'Col2': ['B'],
        'Col3': ['C']
    })
    recipe = """
    wrangles:
        - merge.concatenate:
            input: 
                - Col1
                - Col2
                - Col3
            output: Join Col
            char: ', '
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Join Col'] == 'A, B, C'

# Wrong input type
def test_concatenate_3():
    data = pd.DataFrame({
        'Col1': ['A'],
        'Col2': ['B'],
        'Col3': ['C']
    })
    recipe = """
    wrangles:
        - merge.concatenate:
            input: 
                Col1 : Col2
            output: Join Col
            char: ', '
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Unexpected data type for merge.concatenate / input'

#
# Lists
#
# Joining lists together
def test_lists_1():
    data = pd.DataFrame({
        'Col1': [['A', 'B']],
        'Col2': [['D', 'E']]
    })
    recipe = """
    wrangles:
        - merge.lists:
            input: 
                - Col1
                - Col2
            output: Combined Col
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Combined Col'] == ['A', 'B', 'D', 'E']


#
# to_list
#

def test_to_lists_1():
    data = pd.DataFrame({
        'Col1': ['A'],
        'Col2': ['B'],
        'Col3': ['C']
    })
    recipe = """
    wrangles:
        - merge.to_list:
            input: 
                - Col1
                - Col2
                - Col3
            output: Combined Col
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Combined Col'] == ['A', 'B', 'C']
    

#
# To Dict
#
def test_to_dict_1():
    data = pd.DataFrame({
    'Col1':[{'A'}],
    'Col2':[{'B'}]
})
    recipe = """
    wrangles:
        - merge.to_dict:
            input: 
                - Col1
                - Col2
            output: Dict Col
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Dict Col'] == {'Col1': {'A'}, 'Col2': {'B'}}

# input is a wildcard
def test_to_dict_2():
    data = pd.DataFrame({
    'Col1':[{'A'}],
    'Col2':[{'B'}]
})
    recipe = """
    wrangles:
        - merge.to_dict:
            input: Col*
            output: Dict Col
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Dict Col'] == {'Col1': {'A'}, 'Col2': {'B'}}

#
# Key Value Pairs
#
def test_key_value_pairs_1():
    data = pd.DataFrame({
    'Letter': ['A', 'B', 'C'],
    'Number': [1, 2, 3],
    })
    recipe = """
    wrangles:
        - merge.key_value_pairs:
            input:
              Letter: Number
            output: Pairs
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[2]['Pairs'] == {'C': 3}

# Using a Wildcard
def test_key_value_pairs_2():
    data = pd.DataFrame({
    'key 1': ['A', 'B', 'C'],
    'key 2': ['One', 'Two', 'three'],
    'value 1': ['a', 'b', 'c'],
    'value 2': ['First', 'Second', 'Third']
    })
    recipe = """
    wrangles:
        - merge.key_value_pairs:
            input:
              key*: value*
            output: Object
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[2]['Object'] == {'C': 'c', 'three': 'Third'}

