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
    df = wrangles.recipe.run(recipe, dataframe=data)
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
    df = wrangles.recipe.run(recipe, dataframe=data)
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
        raise wrangles.recipe.run(recipe, dataframe=data)
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
        raise wrangles.recipe.run(recipe, dataframe=data)
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
    df = wrangles.recipe.run(recipe, dataframe=data)
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
    df = wrangles.recipe.run(recipe, dataframe=data)
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
    df = wrangles.recipe.run(recipe, dataframe=data)
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
    df = wrangles.recipe.run(recipe, dataframe=data)
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
    df = wrangles.recipe.run(recipe, dataframe=data)
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
    df = wrangles.recipe.run(recipe, dataframe=data)
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
    df = wrangles.recipe.run(recipe, dataframe=data)
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
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Abbreviations'] == 'As Soon As Possible'
    
# Missing ${ } in model_id
def test_standardize_2():
    data = pd.DataFrame({
    'Abbrev': ['ASAP'],
    })
    recipe = """
    wrangles:
        - standardize:
            input: Abbrev
            output: Abbreviations
            model_id: wrong_model
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Incorrect model_id. May be missing "${ }" around value'

# Missing a character in model_id format
def test_standardize_3():
    data = pd.DataFrame({
    'Abbrev': ['ASAP'],
    })
    recipe = """
    wrangles:
        - standardize:
            input: Abbrev
            output: Abbreviations
            model_id: 6c4ab44-8c66-40e8
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX'

# using an extract model with standardize function
def test_standardize_4():
    data = pd.DataFrame({
    'Abbrev': ['ASAP'],
    })
    recipe = """
    wrangles:
        - standardize:
            input: Abbrev
            output: Abbreviations
            model_id: 1eddb7e8-1b2b-4a52
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Using extract model_id in a standardize function.'
    
# Using classify model with standardize function
def test_steandardize_4():
    data = pd.DataFrame({
    'Abbrev': ['ASAP'],
    })
    recipe = """
    wrangles:
        - standardize:
            input: Abbrev
            output: Abbreviations
            model_id: f7958bd2-af22-43b1
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Using classify model_id in a standardize function.'
    

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
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['English'] == 'Hello World!'
    
#
# Custom Function
#

def my_function1(df, input, output):
    df[output] = df[input].apply(lambda x: x[::-1])
    return df
    
def test_custom_function():
    data = pd.DataFrame({'col1': ['Reverse Reverse']})
    recipe = """
    wrangles:
        - custom.my_function1:
            input: col1
            output: out1
    """
    df = wrangles.recipe.run(recipe, dataframe=data, functions=[my_function1])
    assert df.iloc[0]['out1'] == 'esreveR esreveR'
    
# using cell as args[0]
def my_function(cell):    
    return str(cell) + ' xyz'
def test_custom_function_cell():
    data = pd.DataFrame({'col1': ['Reverse Reverse']})
    recipe = """
    wrangles:
        - custom.my_function:
            input: col1
            output: out1
    """
    df = wrangles.recipe.run(recipe, dataframe=data, functions=[my_function])
    assert df.iloc[0]['out1'] == 'Reverse Reverse xyz'
    
# not mentioning output ->  using cell as args[0]
def my_function(cell):    
    return str(cell) + ' xyz'
def test_custom_function_cell_2():
    data = pd.DataFrame({'col1': ['Reverse Reverse']})
    recipe = """
    wrangles:
        - custom.my_function:
            input: col1
    """
    df = wrangles.recipe.run(recipe, dataframe=data, functions=[my_function])
    assert df.iloc[0]['col1'] == 'Reverse Reverse xyz'