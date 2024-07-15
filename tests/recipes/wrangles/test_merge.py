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

def test_coalesce_empty_dataframe():
    """
    Test coalesce using an empty dataframe
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - merge.coalesce:
              input: 
                - Col1
                - Col2
                - Col3
              output: Output Col
        """,
        dataframe=pd.DataFrame({
            'Col1': [],
            'Col2': [],
            'Col3': []
        })
    )
    assert len(df) == 0 and "Output Col" in df.columns

def test_coalesce_where_empty():
    """
    Test coalesce using where and an empty dataframe
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                Col1: ['a', 'b', 'c', 'd', 'e']
                Col2: ['f', 'g', 'h', 'i', 'j']
                Col3: ['k', 'l', 'm', 'n', 'o']
        wrangles:
          - merge.coalesce:
              input: 
                - Col1
                - Col2
                - Col3
              output: Output Col
              where: 1 = 2
        """
    )
    # All values should be empty
    assert all(x=="" for x in df['Output Col'].values.tolist())

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

def test_concatenate_integer():
    """
    Test that a non-string doesn't
    break the concatenation
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header1: ["a", 1]
        wrangles:
          - merge.concatenate:
              input: header1
              output: result
              char: ''
        """
    )
    assert df["result"][0] == 'a1'

def test_concatenate_skip_empty_true():
    """
    Test skipping empty values as true
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header1: a
                header2: ""
                header3: b
        wrangles:
          - merge.concatenate:
              input:
                - header1
                - header2
                - header3
              output: result
              char: '-'
              skip_empty: true
        """
    )
    assert df["result"][0] == 'a-b'

def test_concatenate_skip_empty_false():
    """
    Test skipping empty values set as false
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header1: a
                header2: ""
                header3: b
        wrangles:
          - merge.concatenate:
              input:
                - header1
                - header2
                - header3
              output: result
              char: '-'
              skip_empty: false
        """
    )
    assert df["result"][0] == 'a--b'

def test_concatenate_skip_empty_default():
    """
    Test skipping empty values not provided
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header1: a
                header2: ""
                header3: b
        wrangles:
          - merge.concatenate:
              input:
                - header1
                - header2
                - header3
              output: result
              char: '-'
        """
    )
    assert df["result"][0] == 'a--b'

def test_concatenate_empty_dataframe():
    """
    Test concatenate using an empty dataframe
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - merge.concatenate:
              input: 
                - Col1
                - Col2
                - Col3
              output: Join Col
              char: ', '
        """,
        dataframe=pd.DataFrame({
            'Col1': [],
            'Col2': [],
            'Col3': []
        })
    )
    assert len(df) == 0 and "Join Col" in df.columns

def test_concatenate_where_empty():
    """
    Test concatenate using where and an empty dataframe
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                Col1: ['a', 'b', 'c', 'd', 'e']
                Col2: ['f', 'g', 'h', 'i', 'j']
                Col3: ['k', 'l', 'm', 'n', 'o']
        wrangles:
          - merge.concatenate:
              input: 
                - Col1
                - Col2
                - Col3
              output: Join Col
              char: ', '
              where: 1 = 2
        """
    )
    # All values should be empty
    assert all(x=="" for x in df['Join Col'].values.tolist())

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

def test_lists_empty_dataframe():
    """
    Test merge.lists using an empty dataframe
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - merge.lists:
              input: 
                - Col1
                - Col2
              output: Combined Col
        """,
        dataframe=pd.DataFrame({
            'Col1': [],
            'Col2': []
        })
    )
    assert len(df) == 0 and "Combined Col" in df.columns

def test_lists_where_empty():
    """
    Test merge.lists using where and an empty dataframe
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                Col1: [['a', 'b']]
                Col2: [['c', 'd']]
        wrangles:
          - merge.lists:
              input: 
                - Col1
                - Col2
              output: Combined Col
              where: 1 = 2
        """
    )
    # All values should be empty
    assert all(x=="" for x in df['Combined Col'].values.tolist())

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

def test_to_lists_empty_dataframe():
    """
    Test merge.to_list using an empty dataframe
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - merge.to_list:
              input: 
                - Col1
                - Col2
                - Col3
              output: Combined Col
        """,
        dataframe=pd.DataFrame({
            'Col1': [],
            'Col2': [],
            'Col3': []
        })
    )
    assert len(df) == 0 and "Combined Col" in df.columns

def test_to_lists_where_empty():
    """
    Test merge.to_list using where and an empty dataframe
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                Col1: ['a', 'b', 'c', 'd', 'e']
                Col2: ['f', 'g', 'h', 'i', 'j']
                Col3: ['k', 'l', 'm', 'n', 'o']
        wrangles:
          - merge.to_list:
              input: 
                - Col1
                - Col2
                - Col3
              output: Combined Col
              where: 1 = 2
        """
    )
    # All values should be empty
    assert all(x=="" for x in df['Combined Col'].values.tolist())

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

def test_to_dict_empty_dataframe():
    """
    Test merge.to_dict using an empty dataframe
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - merge.to_dict:
              input: 
                - Col1
                - Col2
              output: Dict Col
        """,
        dataframe=pd.DataFrame({
            'Col1': [],
            'Col2': []
        })
    )
    assert len(df) == 0 and "Dict Col" in df.columns

def test_to_dict_where_empty():
    """
    Test merge.to_dict using where and an empty dataframe
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                Col1: ['a', 'b', 'c', 'd', 'e']
                Col2: ['f', 'g', 'h', 'i', 'j']
        wrangles:
          - merge.to_dict:
              input: 
                - Col1
                - Col2
              output: Dict Col
              where: 1 = 2
        """
    )
    # All values should be empty
    assert all(x=="" for x in df['Dict Col'].values.tolist())

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

def test_empty_dataframe():
    """
    Test merge.key_value_pairs using an empty dataframe
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - merge.key_value_pairs:
              input:
                key1: value1
              output: output
        """,
        dataframe=pd.DataFrame({
            'key1': [],
            'value1': []
        })
    )
    assert len(df) == 0 and "output" in df.columns

def test_key_value_pairs_where_empty():
    """
    Test merge.key_value_pairs using where and an empty dataframe
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                key1: ['a', 'b', 'c', 'd', 'e']
                value1: ['f', 'g', 'h', 'i', 'j']
        wrangles:
          - merge.key_value_pairs:
              input:
                key1: value1
              output: output
              where: 1 = 2
        """
    )
    # All values should be empty
    assert all(x=="" for x in df['output'].values.tolist())
    
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

def test_merge_dictionaries_empty_dataframe():
    """
    Tests merge.dictionaries using an empty dataframe
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - merge.dictionaries:
              input: 
                - d1
                - d2
              output: output
        """,
        dataframe=pd.DataFrame({
            'd1': [],
            'd2': []
        })
    )
    assert len(df) == 0 and "output" in df.columns

def test_merge_dictionaries_where_empty():
    """
    Tests merge.dictionaries using where and an empty dataframe
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                d1: [{'a': 1}]
                d2: [{'a': 2}]
        wrangles:
          - merge.dictionaries:
              input: 
                - d1
                - d2
              output: output
              where: 1 = 2
        """
    )
    # All values should be empty
    assert all(x=="" for x in df['output'].values.tolist())