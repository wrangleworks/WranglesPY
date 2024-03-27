import wrangles
import pandas as pd
import pytest

#
# Split From Text
#

# Text Split - text to a list separated by char
def test_split_text_1():
    data = pd.DataFrame({
    'Col1': ['Hello, Wrangles!']
    })
    recipe = """
    wrangles:
        - split.text:
            input: Col1
            output: Col2
            char: ', '
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Col2'] == ['Hello', 'Wrangles!']
    
# using a wild card - text to columns
def test_split_text_2():
    data = pd.DataFrame({
    'Col': ['Hello, Wrangles!']
    })
    recipe = """
    wrangles:
        - split.text:
            input: Col
            output: Col*
            char: ', '
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Col2'] == 'Wrangles!'
    
# Multiple named columns as outputs - text to columns
def test_split_text_3():
    data = pd.DataFrame({
    'Col': ['Hello Wrangles! Other']
    })
    recipe = """
    wrangles:
      - split.text:
          input: Col
          output:
            - Col 1
            - Col 2
            - Col 3
          char: ' '
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Col 2'] == 'Wrangles!'
    
# Multiple character split
def test_split_text_4():
    data = pd.DataFrame({
    'col1': ['Wrangles@are&very$cool']
    })
    recipe = r"""
      wrangles:
        - split.text:
            input: col1
            output: out1
            char: 'regex: @|&|\$'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == ['Wrangles', 'are', 'very', 'cool']
    
# Multiple character split using wildcard (*)
def test_split_text_5():
    data = pd.DataFrame({
    'col1': ['Wrangles@are&very$cool']
    })
    recipe = r"""
      wrangles:
        - split.text:
            input: col1
            output: out*
            char: 'regex: @|&|\$'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out4'] == 'cool'
    
# Select element from the output list
def test_split_text_6():
    data = pd.DataFrame({
    'col1': ['Wrangles are very cool']
    })
    recipe = """
    wrangles:
        - split.text:
            input: col1
            output: Out
            char: ' '
            element: 0
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Out'] == 'Wrangles'

# Select element from the output list, index error
# Number of index greater than Out list size
def test_split_text_7():
    data = pd.DataFrame({
    'col1': ['Wrangles are very cool']
    })
    recipe = """
    wrangles:
        - split.text:
            input: col1
            output: Out
            char: ' '
            element: 100
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Out'] == ''
    
# Select element from the output list, using list slice
def test_split_text_8():
    data = pd.DataFrame({
    'col1': ['Wrangles are very cool']
    })
    recipe = """
    wrangles:
        - split.text:
            input: col1
            output: Out
            char: ' '
            element: '0:3'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Out'] == ['Wrangles', 'are', 'very']  
    
    
# If more columns than number of splits
def test_split_text_9():
    data = pd.DataFrame({
    'col1': ['Wrangles are very cool']
    })
    recipe = """
    wrangles:
        - split.text:
            input: col1
            output: 
              - Out1
              - Out2
              - Out3
              - Out4
              - Out5
            char: ' '
            pad: True
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Out5'].iloc[0] == ''
    
def test_split_text_more_splits_than_output():
    """
    Test split.text with more splits than output columns
    """
    data = pd.DataFrame({
    'col1': ['Wrangles are very cool, I tell you whut!']
    })
    recipe = """
    wrangles:
        - split.text:
            input: col1
            output: 
              - Out1
              - Out2
              - Out3
            char: ' '
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert list(df.columns) == ['col1', 'Out1', 'Out2', 'Out3'] and df['Out3'].iloc[0] == 'very'

def test_split_text_uneven_lengths():
    """
    Test split.text with uneven split/output lengths
    """
    data = pd.DataFrame({
    'col1': ['Wrangles, are, very, cool', 'There, is, a, wrangle, for, that']
    })
    recipe = """
    wrangles:
        - split.text:
            input: col1
            output: output*
            char: ', '
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['output6'].iloc[0] == '' and df['output6'].iloc[1] == 'that'

def test_split_text_where():
    """
    Test split.text using where
    """
    data = pd.DataFrame({
        'Col1': ['Hello, Wrangles!', 'Hello, World!', 'Hola, Mundo!'],
        'numbers': [4, 5, 6]
    })
    recipe = """
    wrangles:
        - split.text:
            input: Col1
            output: output
            char: ', '
            where: numbers > 4
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[2]['output'] == ['Hola', 'Mundo!'] and df.iloc[0]['output'] == ''

def test_split_text_string():
    """
    Test a string passed into the element parameter
    """
    data = pd.DataFrame({
        'col1': ['Wrangles are very cool']
    })
    recipe="""
    wrangles:
      - split.text:
          input: col1
          output: Out
          char: ' '
          element: '1'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Out'].iloc[0] == 'are'

def test_split_text_slice_start():
    """
    Test a string slice passed into the element parameter
    """
    data = pd.DataFrame({
        'col1': ['Wrangles are very cool and super fun to work with']
    })
    recipe="""
    wrangles:
      - split.text:
          input: col1
          output: Out
          char: ' '
          element: ':3'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Out'].iloc[0] == ['Wrangles', 'are','very']

def test_split_text_slice_end():
    """
    Test a string slice passed into the element parameter
    """
    data = pd.DataFrame({
        'col1': ['Wrangles are very cool and super fun to work with']
    })
    recipe="""
    wrangles:
      - split.text:
          input: col1
          output: Out
          char: ' '
          element: '3:'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Out'].iloc[0] == ['cool', 'and', 'super', 'fun', 'to', 'work', 'with']

#
# Split from List
#
# Using Wild Card
def test_split_list_1():
    data = pd.DataFrame({
    'Col': [['Hello', 'Wrangles!']]
    })
    recipe = """
    wrangles:
        - split.list:
            input: Col
            output: Col*
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Col2'] == 'Wrangles!'
    
# Multiple column named outputs
def test_split_list_2():
    data = pd.DataFrame({
    'col1': [['Hello', 'Wrangles!']]
    })
    recipe = """
    wrangles:
      - split.list:
          input: col1
          output:
            - out1
            - out2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out2'] == 'Wrangles!'
    
#
# Split from Dict
#
def test_split_dictionary():
    """
    Test splitting a dictionary
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - split.dictionary:
              input: col1
        """, 
        dataframe=pd.DataFrame({
            'col1': [{'Col1': 'A', 'Col2': 'B', 'Col3': 'C'}]
        })
    )
    assert df['Col2'][0] == 'B'
    
def test_split_dictionary_json():
    """
    Test splitting a dictionary that is 
    actually a JSON string
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - split.dictionary:
              input: col1
        """,
        dataframe=pd.DataFrame({
            'col1': ['{"Col1": "A", "Col2": "B", "Col3": "C"}']
        })
    )
    assert df['Col2'][0] == 'B'

def test_split_dictionary_where():
    """
    Test split.dictionary using where
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - split.dictionary:
              input: col1
              where: numbers > 3
        """,
        dataframe=pd.DataFrame({
            'col1': [
                {'Col1': 'A', 'Col2': 'B', 'Col3': 'C'},
                {'Col1': 'D', 'Col2': 'E', 'Col3': 'F'},
                {'Col1': 'G', 'Col2': 'H', 'Col3': 'I'}
            ],
            'numbers': [3, 4, 5]
        })
    )
    assert df['Col2'][1] == 'E' and df['Col2'][0] == ''

def test_split_dictionary_default():
    """
    Test splitting a dictionary with default values
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - split.dictionary:
              input: col1
              default:
                Col2: X
                Col4: D
        """, 
        dataframe=pd.DataFrame({
            'col1': [{'Col1': 'A', 'Col2': 'B', 'Col3': 'C'}]
        })
    )
    assert (
        df['Col2'][0] == 'B' and 
        df['Col4'][0] == 'D'
    )

def test_split_dictionary_multiple():
    """
    Test splitting a list of dictionaries
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - split.dictionary:
              input: 
                - col1
                - col2
        """, 
        dataframe=pd.DataFrame({
            'col1': [{'Col1': 'A', 'Col2': 'B', 'Col3': 'C'}],
            'col2': [{'Col4': 'D', 'Col5': 'E', 'Col6': 'F'}]
        })
    )
    assert (
        df['Col2'][0] == 'B' and 
        df['Col4'][0] == 'D'
    )

def test_split_dictionary_multiple_duplicates():
    """
    Test splitting a list of dictionaries with duplicate keys
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - split.dictionary:
              input: 
                - col1
                - col2
        """, 
        dataframe=pd.DataFrame({
            'col1': [{'Col1': 'A', 'Col2': 'B', 'Col3': 'C'}],
            'col2': [{'Col3': 'D', 'Col4': 'E', 'Col5': 'F'}]
        })
    )
    assert (
        df['Col3'][0] == 'D'
    )

#
# Tokenize List
#
# input is a list
def test_tokenize_1():
    data = pd.DataFrame({
    'col1': [['Stainless Steel', 'Oak Wood']],
    })
    recipe = """
    wrangles:
      - split.tokenize:
          input: col1
          output: out1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'][2] == 'Oak'
    
# Input is a str
def test_tokenize_2():
    data = pd.DataFrame({
        'col1': ['Stainless Steel']
    })
    recipe = """
    wrangles:
      - split.tokenize:
          input: col1
          output: out1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'][1] == 'Steel'
    
# If the input is multiple columns (a list)
def test_tokenize_3():
    data = pd.DataFrame({
        'col1': ['Iron Man'],
        'col2': ['Spider Man'],
    })
    recipe = """
    wrangles:
      - split.tokenize:
          input:
            - col1
            - col2
          output:
            - out1
            - out2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'][1] == 'Man'
    
# if the input and output are not the same
# If the input is multiple columns (a list)
def test_tokenize_4():
    data = pd.DataFrame({
        'col1': ['Iron Man'],
        'col2': ['Spider Man'],
    })
    recipe = """
    wrangles:
      - split.tokenize:
          input:
            - col1
            - col2
          output: out1
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        "The list of inputs and outputs must be the same length for split.tokenize" in info.value.args[0]
    )

def test_tokenize_where():
    """
    Test split.tokenize using where
    """
    data = pd.DataFrame({
        'col1': [['Stainless Steel', 'Oak Wood'], ['Titanium', 'Cedar Wood'], ['Aluminum', 'Teak Wood']],
        'numbers': [2, 3, 4]
    })
    recipe = """
    wrangles:
      - split.tokenize:
          input: col1
          output: out1
          where: numbers >= 3
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['out1'][0] == 'Titanium' and df.iloc[0]['out1'] == ''

def test_split_text_inclusive():
    """
    Tests split.text with inclusive set to True
    """
    data = pd.DataFrame({
    'col1': ['80ga 90ga 100ga']
    })
    recipe = """
    wrangles:
        - split.text:
            input: col1
            output: out1
            char: 'ga'
            inclusive: True
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['out1'].iloc[0] == ['80', 'ga', ' 90', 'ga', ' 100', 'ga', '']

def test_split_text_regex():
    """
    Tests split.text using regex
    """
    data = pd.DataFrame({
    'col1': ['Hello, Wrangles!']
    })
    recipe = """
    wrangles:
        - split.text:
            input: col1
            output: out1
            char: 'regex: (,|!)'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['out1'].iloc[0][1] == ',' and len(df['out1'].iloc[0]) == 5
