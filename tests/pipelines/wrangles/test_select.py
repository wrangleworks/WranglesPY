import wrangles
import pandas as pd

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
    print(df.iloc[0]['Top Words'] == 'B || .90')
    
