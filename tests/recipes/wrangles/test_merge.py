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

def test_coalesce_where():
    """
    Test coalesce using where
    """
    data = pd.DataFrame({
        'Col1': ['A', '', ''],
        'Col2': ['', 'B', ''],
        'Col3': ['', '', 'C'],
        'numbers': [3, 4, 5]
    })
    recipe = """
    wrangles:
      - merge.coalesce:
          input: 
            - Col1
            - Col2
            - Col3
          output: Output Col
          where: numbers = 4
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['Output Col'] == 'B' and df.iloc[0]['Output Col'] ==''

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

def test_concatenate_where():
    """
    Test concatenate using where
    """
    data = pd.DataFrame({
        'Col1': ['A', 'E', 'H'],
        'Col2': ['B', 'F', 'I'],
        'Col3': ['C', 'G', 'J'],
        'numbers': [23, 44, 13]
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
            where: numbers !=13
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Join Col'] == 'A, B, C' and df.iloc[2]['Join Col'] == ''

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

def test_lists_where():
    """
    Test merge.lists using where
    """
    data = pd.DataFrame({
        'Col1': [['A', 'B'], ['C', 'D']],
        'Col2': [['D', 'E'], ['F', 'G']],
        'numbers': [0, 5]
    })
    recipe = """
    wrangles:
        - merge.lists:
            input: 
                - Col1
                - Col2
            output: Combined Col
            where: numbers > 0
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Combined Col'] == '' and df.iloc[1]['Combined Col'] == ['C', 'D', 'F', 'G']

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
    
def test_to_lists_where():
    """
    Test merge.to_list using where
    """
    data = pd.DataFrame({
        'Col1': ['A', 'D', 'G'],
        'Col2': ['B', 'E', 'H'],
        'Col3': ['C', 'F', 'I'],
        'numbers': [3, 6, 9]
    })
    recipe = """
    wrangles:
        - merge.to_list:
            input: 
                - Col1
                - Col2
                - Col3
            output: Combined Col
            where: numbers = 6
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Combined Col'] == '' and df.iloc[1]['Combined Col'] == ['D', 'E', 'F']

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

# if the row instance is a boolean type
def test_to_dict_3():
    data = pd.DataFrame({
        'Col1':[True],
        'Col2':[False],
        'Col3': [None],
    })
    recipe = """
    wrangles:
        - merge.to_dict:
            input: Col*
            output: Dict Col
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Dict Col'] == {'Col1': True, 'Col2': False, 'Col3': None}

def test_to_dict_where():
    """
    Test merge.to_dict using where
    """
    data = pd.DataFrame({
        'Col1':['A', 'C', 'E'],
        'Col2':['B', 'D', 'F'],
        'numbers': [43, 22, 65]
    })
    recipe = """
    wrangles:
        - merge.to_dict:
            input: 
                - Col1
                - Col2
            output: Dict Col
            where: numbers < 60
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Dict Col'] == {'Col1': 'A', 'Col2': 'B'} and df.iloc[2]['Dict Col'] == ''

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

def test_key_value_pairs_where():
    """
    Test merge.key_value_pairs using where
    """
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
            where: Number = 2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['Pairs'] == {'B': 2} and df.iloc[0]['Pairs'] == ''

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


# True or False in row Values
def test_key_value_pairs_3():
    data = pd.DataFrame({
    'key 1': ['A'],
    'key 2': [True],
    'value 1': ['a'],
    'value 2': [False]
    })
    recipe = """
    wrangles:
        - merge.key_value_pairs:
            input:
              key*: value*
            output: Object
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Object'] == {'A': 'a', True: False}
    
#
# Dictionaries
#

def test_merge_dicts_1():
    data = pd.DataFrame({
        'd1': [{'Hello': 'Fey'}],
        'd2': [{'Hello2': 'Lucy'}],
    })
    recipe = """
    wrangles:
      - merge.dictionaries:
          input:
            - d1
            - d2
          output: out
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out'] == {'Hello': 'Fey', 'Hello2': 'Lucy'}

def test_merge_dicts_where():
    """
    Tests merge.dictionaries using where
    """
    data = pd.DataFrame({
        'd1': [{'Hello': 'Fey'}, {'Hello': 'Moto'}, {'Hello': 'World'}],
        'd2': [{'Hola': 'Lucy'}, {'Hola': 'Hello'}, {'Hola': 'Nice to meet you'}],
        'numbers': [2, 55, 71]
    })
    recipe = """
    wrangles:
      - merge.dictionaries:
          input:
            - d1
            - d2
          output: out
          where: numbers > 2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['out'] == {'Hello': 'Moto', 'Hola': 'Hello'} and df.iloc[0]['out'] == ''