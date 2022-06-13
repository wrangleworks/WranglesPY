import wrangles
import pandas as pd
import pytest

#
# Dictionary Element
#
def test_dictionary_element_1():
    data = pd.DataFrame({
    'Prop': [{'colours': ['red', 'white', 'blue'], 'shapes': 'round', 'materials': 'tungsten'}]
    })
    recipe = """
    wrangles:
      - select.dictionary_element:
          input: Prop
          output: Shapes
          element: shapes
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Shapes'] == 'round'
    
#
# List Element
#
def test_list_element_1():
    data = pd.DataFrame({
    'Col1': [['A', 'B', 'C']]
    })
    recipe = """
    wrangles:
      - select.list_element:
          input: Col1
          output: Second Element
          element: 1
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Second Element'] == 'B'
    
# Empty values
def test_list_element_2():
    data = pd.DataFrame({
    'Col1': [['A One', '', 'C']],
    })
    recipe = """
    wrangles:
      - select.list_element:
          input: Col1
          output: Second Element
          element: 1
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Second Element'] == ''
    
# Out of Index values
def test_list_element_3():
    data = pd.DataFrame({
    'Col1': [['A One']],
    })
    recipe = """
    wrangles:
      - select.list_element:
          input: Col1
          output: Second Element
          element: 5
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Second Element'] == ''
    
#
# Highest confidence
#
def test_highest_confidence_1():
    data = pd.DataFrame({
    'Col1': [['A', .79]],
    'Col2': [['B', .80]],
    'Col3': [['C', .99]]
    })
    recipe = """
    wrangles:
      - select.highest_confidence:
          input:
            - Col1
            - Col2
            - Col3
          output: Winner
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Winner'] == ['C', 0.99]
    
#
# Threshold
#
def test_threshold_1():
    data = pd.DataFrame({
    'Col1': [['A', .60]],
    'Col2': [['B', .79]]
    })
    recipe = """
    wrangles:
      - select.threshold:
          input:
            - Col1
            - Col2
          output: Top Words
          threshold: .77
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Top Words'] == 'B'
    
# Noun (Token) return empty aka None
def test_threshold_2():
    data = pd.DataFrame({
    'Col1': [None],
    'Col2': ['B || .90']
    })
    recipe = """
    wrangles:
        - select.threshold:
            input:
                - Col1
                - Col2
            output: Top Words
            threshold: .77
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Top Words'] == 'B || .90'
    
# Noun (Token) return empty aka None and cell 2 is a list
def test_threshold_3():
    data = pd.DataFrame({
    'Col1': [None],
    'Col2': [['B || .90']]
    })
    recipe = """
    wrangles:
        - select.threshold:
            input:
                - Col1
                - Col2
            output: Top Words
            threshold: .77
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Top Words'] == 'B || .90'
    
# Cell_1[0] is above the threshold
def test_threshold_4():
    data = pd.DataFrame({
    'Col1': [['A', .90]],
    'Col2': [['B', .79]]
    })
    recipe = """
    wrangles:
      - select.threshold:
          input:
            - Col1
            - Col2
          output: Top Words
          threshold: .77
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Top Words'] == 'A'
    
def test_threshold_5():
    data = pd.DataFrame({
    'Col1': ['A || .50'],
    'Col2': ['B || .90']
    })
    recipe = """
    wrangles:
        - select.threshold:
            input:
                - Col1
                - Col2
            output: Top Words
            threshold: .77
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Top Words'] == 'B || .90'
    
#    
# Left
#
# Multi Columns input and output
def test_left_1():
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.left:
            input:
                - Col1
                - Col2
            output:
                - Out1
                - Out2
            length: 5
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Out1'] == 'One T'
    
# Input is none
def test_left_2():
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.left:
            input: Col1
            length: 5
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Col1'] == 'One T'
    
#
# Right
#
# Multi column
def test_right_1():
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.right:
            input:
                - Col1
                - Col2
            output:
                - Out1
                - Out2
            length: 4
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Out1'] == 'Four'
    
# Input is none
def test_right_2():
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.right:
            input: Col1
            length: 4
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Col1'] == 'Four'
    
    
#
# Substring
#

# Multi column input
def test_substring_1():
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.substring:
            input:
                - Col1
                - Col2
            output:
                - Out1
                - Out2
            start: 4
            length: 4
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Out1'] == ' Two'
    
# Input is none
def test_substring_2():
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.substring:
            input: Col1
            start: 4
            length: 4
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Col1'] == ' Two'