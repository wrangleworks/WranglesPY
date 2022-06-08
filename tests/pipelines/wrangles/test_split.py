import wrangles
import pandas as pd


#
# Split From Text
#

# Text Split - text to a list separated by char
def test_split_from_text_1():
    data = pd.DataFrame({
    'Col1': ['Hello, Wrangles!']
    })
    recipe = """
    wrangles:
        - split.from_text:
            input: Col1
            output: Col2
            char: ', '
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Col2'] == ['Hello', 'Wrangles!']
    
# using a wild card - text to columns
def test_split_from_text_2():
    data = pd.DataFrame({
    'Col': ['Hello, Wrangles!']
    })
    recipe = """
    wrangles:
        - split.from_text:
            input: Col
            output: Col*
            char: ', '
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Col2'] == 'Wrangles!'
    
# Multiple named columns as outputs - text to columns
def test_split_from_text_3():
    data = pd.DataFrame({
    'Col': ['Hello Wrangles! Other']
    })
    recipe = """
    wrangles:
      - split.from_text:
          input: Col
          output:
            - Col 1
            - Col 2
            - Col 3
          char: ' '
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Col 2'] == 'Wrangles!'
    
#
# Re Split
#
def test_re_split_1():
    data = pd.DataFrame({
    'col1': ['Wrangles@are&very$cool']
    })
    recipe = """
    wrangles:
        - split.re_from_text:
            input: col1
            output: out1
            char:
              - '@'
              - '&'
              - '\$'
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == ['Wrangles', 'are', 'very', 'cool']
    
#
# Split from List
#
# Using Wild Card
def test_split_from_list_1():
    data = pd.DataFrame({
    'Col': [['Hello', 'Wrangles!']]
    })
    recipe = """
    wrangles:
        - split.from_list:
            input: Col
            output: Col*
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Col2'] == 'Wrangles!'
    
# Multiple column named outputs
def test_split_from_list_2():
    data = pd.DataFrame({
    'col1': [['Hello', 'Wrangles!']]
    })
    recipe = """
    wrangles:
      - split.from_list:
          input: col1
          output:
            - out1
            - out2
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['out2'] == 'Wrangles!'
    
    
#
# Split from Dict
#
def test_split_from_dict_1():
    data = pd.DataFrame({
    'col1': [{'Col1': 'A', 'Col2': 'B', 'Col3': 'C'}]
    })
    recipe = """
    wrangles:
      - split.from_dict:
          input: col1
    """

    df = wrangles.pipeline.run(recipe, dataframe=data)
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
    df = wrangles.pipeline.run(recipe, dataframe=data)
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
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'][1] == 'Steel'
    