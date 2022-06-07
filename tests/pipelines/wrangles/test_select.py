import wrangles
import pandas as pd

#
# Dictionary Element
#
df_test_dictionary_element = pd.DataFrame({
    'Prop': [{'colours': ['red', 'white', 'blue'], 'shapes': 'round', 'materials': 'tungsten'}]
})
def test_dictionary_element():
    recipe = """
    wrangles:
        
        - select.dictionary_element:
            input: Prop
            output: Shapes
            element: shapes
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_dictionary_element)
    assert df.iloc[0]['Shapes'] == 'round'
    
#
# List Element
#
df_test_list_element = pd.DataFrame({
    'Col1': [['A', 'B', 'C']]
})
def test_list_element():
    recipe = """
    wrangles:
        
        - select.list_element:
            input: Col1
            output: Second Element
            element: 1
    """

    df = wrangles.pipeline.run(recipe, dataframe=df_test_list_element)
    assert df.iloc[0]['Second Element'] == 'B'
    
#
# Highest confidence
#
df_highest_confidence = pd.DataFrame({
    'Col1': [['A', .79]],
    'Col2': [['B', .80]],
    'Col3': [['C', .99]]
})

def test_highest_confidence():
    recipe = """
    wrangles:
        - select.highest_confidence:
            input:
                - Col1
                - Col2
                - Col3
            output: Winner
    """

    df = wrangles.pipeline.run(recipe, dataframe=df_highest_confidence)
    assert df.iloc[0]['Winner'] == ['C', 0.99]
    
#
# Threshold
#


df_threshold = pd.DataFrame({
    'Col1': [['A', .60]],
    'Col2': [['B', .79]]
})

def test_threshold():
    recipe = """
    wrangles:
        - select.threshold:
            input:
                - Col1
                - Col2
            output: Top Words
            threshold: .77
    """

    df = wrangles.pipeline.run(recipe, dataframe=df_threshold)
    assert df.iloc[0]['Top Words'] == 'B'
    
# Noun (Token) return empty
df_threshold_None = pd.DataFrame({
    'Col1': [None],
    'Col2': ['B || .90']
})

def test_threshold_str():
    recipe = """
    wrangles:
        - select.threshold:
            input:
                - Col1
                - Col2
            output: Top Words
            threshold: .77
    """

    df = wrangles.pipeline.run(recipe, dataframe=df_threshold_None)
    print(df.iloc[0]['Top Words'] == 'B || .90')
    
