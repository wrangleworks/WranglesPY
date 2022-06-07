import wrangles
import pandas as pd


#
# Classify
#
df_classify = pd.DataFrame({
    'Col1': ['Ball Bearing']
})
# Input is one column
def test_classify():
    recipe = """
    wrangles:
        - classify:
            input: Col1
            output: Class
            model_id: c77839db-237a-476b
    """
    # Using IESA Commodity Wrangle
    df = wrangles.pipeline.run(recipe, dataframe=df_classify)
    assert df.iloc[0]['Class'] == 'Ball Bearing'
    
# Input is mulit column
df_classify_milti_input = pd.DataFrame({
    'Col1': ['Ball Bearing'],
    'Col2': ['Bearing']
})
def test_classify_milti_input():
    recipe = """
    wrangles:
        - classify:
            input:
              - Col1
              - Col2
            output:
              - Output 1
              - Output 2
            model_id: c77839db-237a-476b
    """
    # Using IESA Commodity Wrangle
    df = wrangles.pipeline.run(recipe, dataframe=df_classify_milti_input)
    assert df.iloc[0]['Output 1'] == 'Ball Bearing'
    
#
# Filter
#
df_filter = pd.DataFrame({
    'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
    'Color': ['red','green', 'orange', 'red']
})

def test_filter():
    recipe = """
    wrangles:
        - filter:
            input: Color
            equal:
              - red
    """
    # Using IESA Commodity Wrangle
    df = wrangles.pipeline.run(recipe, dataframe=df_filter)
    assert df.iloc[1]['Fruit'] == 'Strawberry'
    
#
# Log
#
    
#
# Remove Words
#

# Input is a string
df_remove_words_str_input = pd.DataFrame({
    'Description': ['Steel Blue Bottle'],
    'Materials': [['Steel']],
    'Colours': [['Blue']]
})
def test_remove_words_str_input():
    recipe = """
    wrangles:
        - remove_words:
            input: Description
            to_remove:
                - Materials
                - Colours
            output: Product
    """
    # Using IESA Commodity
    df = wrangles.pipeline.run(recipe, dataframe=df_remove_words_str_input)
    assert df.iloc[0]['Product'] == 'Bottle'
    
# Input is a List
df_remove_words_list_input = pd.DataFrame({
    'Description': [['Steel', 'Blue', 'Bottle']],
    'Materials': [['Steel']],
    'Colours': [['Blue']]
})
def test_remove_words_list_input():
    recipe = """
    wrangles:
        - remove_words:
            input: Description
            to_remove:
                - Materials
                - Colours
            output: Product
    """
    # Using IESA Commodity
    df = wrangles.pipeline.run(recipe, dataframe=df_remove_words_list_input)
    assert df.iloc[0]['Product'] == 'Bottle'
    
#
# Rename
#
df_rename = pd.DataFrame({
    'Manufacturer Name': ['Delos'],
    'Part Number': ['CH465517080'],
})
# Multi Column
def test_rename():
    recipe = """
    wrangles:
        - rename:
            Manufacturer Name: Company
            Part Number: MPN
    """
    # Using IESA Commodity
    df = wrangles.pipeline.run(recipe, dataframe=df_rename)
    assert df.iloc[0]['MPN'] == 'CH465517080'

# One column using input and output
def test_rename_one_col():
    recipe = """
    wrangles:
        - rename:
            input: Manufacturer Name
            output: Company
            
    """
    # Using IESA Commodity
    df = wrangles.pipeline.run(recipe, dataframe=df_rename)
    assert df.iloc[0]['Company'] == 'Delos'

#
# Standardize
#
df_standardize = pd.DataFrame({
    'Abbrev': ['ASAP', 'ETA'],
})

def test_standardize():
    recipe = """
    wrangles:
        - standardize:
            input: Abbrev
            output: Abbreviations
            model_id: 6ca4ab44-8c66-40e8
    """
    # Using IESA Commodity
    df = wrangles.pipeline.run(recipe, dataframe=df_standardize)
    assert df.iloc[0]['Abbreviations'] == 'As Soon As Possible'
    
#
# Tokenize List
#
df_tokenize_list = pd.DataFrame({
    'Materials': [['Stainless Steel', 'Oak Wood']],
})

def test_tokenize_list():
    recipe = """
    wrangles:
        - tokenize_list:
            input: Materials
            output: Tokenize
    """
    # Using IESA Commodity
    df = wrangles.pipeline.run(recipe, dataframe=df_tokenize_list)
    assert df.iloc[0]['Tokenize'][2] == 'Oak'
    
#
# Translate
#
df_translate = pd.DataFrame({
    'Español': ['¡Hola Mundo!'],
})

def test_translate():
    recipe = """
    wrangles:
        - translate:
            input: Español
            output: English
            source_language: ES
            target_language: EN-GB
    """
    # Using IESA Commodity
    df = wrangles.pipeline.run(recipe, dataframe=df_translate)
    assert df.iloc[0]['English'] == 'Hello World!'