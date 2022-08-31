import wrangles
import pandas as pd


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
    recipe = """
    wrangles:
        - split.text:
            input: col1
            output: out1
            char:
              - '@'
              - '&'
              - '\$'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == ['Wrangles', 'are', 'very', 'cool']
    
# Multiple character split using wildcard (*)
def test_split_text_5():
    data = pd.DataFrame({
    'col1': ['Wrangles@are&very$cool']
    })
    recipe = """
    wrangles:
        - split.text:
            input: col1
            output: out*
            char:
              - '@'
              - '&'
              - '\$'
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
def test_split_dictionary_1():
    data = pd.DataFrame({
    'col1': [{'Col1': 'A', 'Col2': 'B', 'Col3': 'C'}]
    })
    recipe = """
    wrangles:
      - split.dictionary:
          input: col1
    """

    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Col2'] == 'B'
    
    
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
    