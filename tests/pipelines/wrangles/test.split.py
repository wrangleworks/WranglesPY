import wrangles
import pandas as pd


#
# Split From Text
#

test_split_from_text = pd.DataFrame({
    'Col1': ['Hello, Wrangles!']
})

# Text Split
def test_split_from_text_to_list():
    recipe = """
    wrangles:
        - split.from_text:
            input: Col1
            output: Col2
            char: ', '
    """

    df = wrangles.pipeline.run(recipe, dataframe=test_split_from_text)
    assert df.iloc[0]['Col2'] == ['Hello', 'Wrangles!']
    
# Text to Columns
def test_split_from_text_to_cols():
    recipe = """
    wrangles:
        - split.from_text:
            input: Col
            output: Col*
            char: ', '
    """

    df = wrangles.pipeline.run(recipe, dataframe=test_split_from_text)
    assert df.iloc[0]['Col2'] == 'Wrangles!'
    
#
# Split from List
#

test_split_from_list = pd.DataFrame({
    'Col': [['Hello', 'Wrangles!']]
})

# Using Wild Card
def test_split_from_list_wildcard():
    recipe = """
    wrangles:
        - split.from_list:
            input: Col
            output: Col*
    """

    df = wrangles.pipeline.run(recipe, dataframe=test_split_from_list)
    assert df.iloc[0]['Col2'] == 'Wrangles!'
    
# Using list of columns
def test_split_from_list_cols():
    recipe = """
    wrangles:
        - split.from_list:
            input: Col
            output:
                - Col1
                - Col2
    """

    df = wrangles.pipeline.run(recipe, dataframe=test_split_from_list)
    assert df.iloc[0]['Col2'] == 'Wrangles!'
    
#
# Split from Dict
#
df_test_split_from_dict = pd.DataFrame({
    'Col': [{'Col1': 'A', 'Col2': 'B', 'Col3': 'C'}]
})

def test_split_from_dict():
    recipe = """
    wrangles:
        - split.from_dict:
            input: Col
    """

    df = wrangles.pipeline.run(recipe, dataframe=df_test_split_from_dict)
    assert df.iloc[0]['Col2'] == 'B'