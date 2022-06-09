import pytest
import wrangles
import pandas as pd


#
# Classify
#
# Input is one column
def test_classify_1():
    data = pd.DataFrame({
    'Col1': ['Ball Bearing']
    })
    recipe = """
    wrangles:
        - classify:
            input: Col1
            output: Class
            model_id: c77839db-237a-476b
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Class'] == 'Ball Bearing'
    
# Multiple column input and output
def test_classify_2():
    data = pd.DataFrame({
    'Col1': ['Ball Bearing'],
    'Col2': ['Bearing']
    })
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
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Output 1'] == 'Ball Bearing'
    
# Len input != len output
def test_classify_3():
    data = pd.DataFrame({
    'Col1': ['Ball Bearing'],
    'Col2': ['Ball Bearing']
    })
    recipe = """
    wrangles:
        - classify:
            input: 
              - Col1
              - Col2
            output: 
              - Class
            model_id: c77839db-237a-476b
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.pipeline.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'If providing a list of inputs, a corresponding list of outputs must also be provided.'
    
# Incorrect model_id missing "${ }" around value
def test_classify_4():
    data = pd.DataFrame({
    'Col1': ['Ball Bearing'],
    'Col2': ['Ball Bearing']
    })
    recipe = """
    wrangles:
        - classify:
            input: 
              - Col1
              - Col2
            output: 
              - Class
              - Class2
            model_id: noWord
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.pipeline.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Incorrect model_id. May be missing "${ }" around value'
    
#
# Filter
#
def test_filter_1():
    data = pd.DataFrame({
    'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
    'Color': ['red','green', 'orange', 'red']
    })
    recipe = """
    wrangles:
        - filter:
            input: Color
            equal:
              - red
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[1]['Fruit'] == 'Strawberry'
    
#
# Log
#
# Specify log columns
def test_log_1():
    data = pd.DataFrame({
    'Col1': ['Ball Bearing'],
    'Col2': ['Bearing']
    })
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
        - log:
            columns:
              - Col1
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Output 1'] == 'Ball Bearing'

# no log columns specified
def test_log_2():
    data = pd.DataFrame({
    'Col1': ['Ball Bearing'],
    'Col2': ['Bearing']
    })
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
        - log:
            columns:
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Output 1'] == 'Ball Bearing'

#
# Remove Words
#
# Input is a string
def test_remove_words_1():
    data = pd.DataFrame({
    'Description': ['Steel Blue Bottle'],
    'Materials': [['Steel']],
    'Colours': [['Blue']]
    })
    recipe = """
    wrangles:
        - remove_words:
            input: Description
            to_remove:
                - Materials
                - Colours
            output: Product
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Product'] == 'Bottle'
    
# Input is a List
def test_remove_words_2():
    data = pd.DataFrame({
    'Description': [['Steel', 'Blue', 'Bottle']],
    'Materials': [['Steel']],
    'Colours': [['Blue']]
    })
    recipe = """
    wrangles:
        - remove_words:
            input: Description
            to_remove:
                - Materials
                - Colours
            output: Product
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Product'] == 'Bottle'
    
#
# Rename
#
# Multi Column
def test_rename_1():
    data = pd.DataFrame({
    'Manufacturer Name': ['Delos'],
    'Part Number': ['CH465517080'],
    })
    recipe = """
    wrangles:
        - rename:
            Manufacturer Name: Company
            Part Number: MPN
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['MPN'] == 'CH465517080'

# One column using input and output
def test_rename_2():
    data = pd.DataFrame({
    'Manufacturer Name': ['Delos'],
    'Part Number': ['CH465517080'],
    })
    recipe = """
    wrangles:
        - rename:
            input: Manufacturer Name
            output: Company
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Company'] == 'Delos'

#
# Standardize
#
def test_standardize_1():
    data = pd.DataFrame({
    'Abbrev': ['ASAP', 'ETA'],
    })
    recipe = """
    wrangles:
        - standardize:
            input: Abbrev
            output: Abbreviations
            model_id: 6ca4ab44-8c66-40e8
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['Abbreviations'] == 'As Soon As Possible'
    

#
# Translate
#
def test_translate_1():
    data = pd.DataFrame({
    'Español': ['¡Hola Mundo!'],
    })
    recipe = """
    wrangles:
        - translate:
            input: Español
            output: English
            source_language: ES
            target_language: EN-GB
    """
    df = wrangles.pipeline.run(recipe, dataframe=data)
    assert df.iloc[0]['English'] == 'Hello World!'