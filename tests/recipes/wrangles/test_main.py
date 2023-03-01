import pytest
import wrangles
import pandas as pd
import io
import sys
import logging

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
    assert info.typename == 'ValueError' and info.value.args[0] == 'Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX'
    
# Not using ${} in recipe when using a model-id
def test_classify_5():
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
            model_id: {noWord}
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Incorrect model_id type.\nIf using Recipe, may be missing "${ }" around value'
    
#
# Filter
#

# Equal
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
    
# Is_in
def test_filter_2():
    data = pd.DataFrame({
    'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
    'Color': ['red','green', 'orange', 'red']
    })
    recipe = """
    wrangles:
        - filter:
            input: Color
            is_in:
              - red
              - green
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['Fruit'] == 'Apple'
    
# Not_in
def test_filter_3():
    data = pd.DataFrame({
    'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
    'Color': ['red','green', 'orange', 'red']
    })
    recipe = """
    wrangles:
        - filter:
            input: Color
            not_in:
              - red
              - green
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Fruit'] == 'Orange'
    
# Greater_than
def test_filter_4():
    data = pd.DataFrame({
    'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
    'Number': [13, 26, 13, 26]
    })
    recipe = """
    wrangles:
        - filter:
            input: Number
            greater_than: 14
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Fruit'] == 'Apple'

# Greater_than or equal to
def test_filter_5():
    data = pd.DataFrame({
    'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
    'Number': [13, 26, 13, 26]
    })
    recipe = """
    wrangles:
        - filter:
            input: Number
            greater_than_equal_to: 13
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 4
    
# Less than
def test_filter_6():
    data = pd.DataFrame({
    'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
    'Number': [13, 26, 13, 26]
    })
    recipe = """
    wrangles:
        - filter:
            input: Number
            less_than: 26
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 2
    
# Less than or equal to
def test_filter_6_less_than():
    data = pd.DataFrame({
    'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
    'Number': [13, 26, 13, 26]
    })
    recipe = """
    wrangles:
        - filter:
            input: Number
            less_than_equal_to: 25
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 2
    
# Between
def test_filter_7():
    data = pd.DataFrame({
    'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
    'Number': [13, 26, 52, 52]
    })
    recipe = """
    wrangles:
        - filter:
            input: Number
            between:
              - 14
              - 50
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Fruit'] == 'Apple'
    
# Between, more than two values error
def test_filter_8():
    data = pd.DataFrame({
    'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
    'Number': [13, 26, 52, 52]
    })
    recipe = """
    wrangles:
        - filter:
            input: Number
            between:
              - 14
              - 50
              - 133
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Can only use "between" with two values'

# Contains
def test_filter_9():
    data = pd.DataFrame({
    'Random': ['Apples', 'Random', 'App', 'nothing here'],
    'Number': [13, 26, 52, 52]
    })
    recipe = """
    wrangles:
        - filter:
            input: Random
            contains: 'App'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 2
    
# Does not contain
def test_filter_10():
    data = pd.DataFrame({
    'Random': ['Apples', 'Applications', 'App', 'nothing here'],
    'Number': [13, 26, 52, 52]
    })
    recipe = """
    wrangles:
        - filter:
            input: Random
            does_not_contain: 'App'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 1
    
# not_null
def test_filter_11():
    data = pd.DataFrame({
    'Random': ['Apples', None, 'App', None],
    })
    recipe = """
    wrangles:
        - filter:
            input: Random
            not_null: True
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 2
    
# not_null, False
def test_filter_12():
    data = pd.DataFrame({
    'Random': ['Apples', 'None', 'App', None],
    })
    recipe = """
    wrangles:
        - filter:
            input: Random
            not_null: False
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 1

#
# Log
#

LOGGER = logging.getLogger(__name__)

# Specify log columns
def test_log_1(caplog):
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
    wrangles.recipe.run(recipe, dataframe=data)
    assert caplog.messages[-1] == ': Dataframe ::\n\n           Col1\n0  Ball Bearing\n'
    
    
# no log columns specified
def test_log_2(caplog):
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
    assert caplog.messages[-1] == ': Dataframe ::\n\n           Col1     Col2      Output 1 Output 2\n0  Ball Bearing  Bearing  Ball Bearing  Bearing\n'

# Test one column with wildcard
def test_log_3(caplog):
    data = pd.DataFrame({
        'Col': ['Hello, Wrangle, Works'],
    })
    recipe = """
    wrangles:
      - split.text:
          input: Col
          output: Col*
          char: ', '

      - log:
          columns:
            - Col*
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert caplog.messages[-1] == ': Dataframe ::\n\n                     Col   Col1     Col2   Col3\n0  Hello, Wrangle, Works  Hello  Wrangle  Works\n'

# Test column with escape character
def test_log_4(caplog):
    data = pd.DataFrame({
        'Col': ['Hello'],
        'Col*': ['WrangleWorks!'],
    })
    recipe = """
    wrangles:
      - log:
          columns:
            - Col\*
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert caplog.messages[-1] == ': Dataframe ::\n\n            Col*\n0  WrangleWorks!\n'



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
    
# if the input is multiple columns (a list)
def test_remove_words_3():
    data = pd.DataFrame({
    'Description': [['Steel', 'Blue', 'Bottle']],
    'Description2': [['Steel', 'Blue', 'Bottle']],
    'Materials': [['Steel']],
    'Colours': [['Blue']]
    })
    recipe = """
    wrangles:
        - remove_words:
            input:
              - Description
              - Description2
            to_remove:
                - Materials
                - Colours
            output:
              - Product1
              - Product2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Product2'] == 'Bottle'

# if the input and output are not the same type
def test_remove_words_4():
    data = pd.DataFrame({
    'Description': [['Steel', 'Blue', 'Bottle']],
    'Description2': [['Steel', 'Blue', 'Bottle']],
    'Materials': [['Steel']],
    'Colours': [['Blue']]
    })
    recipe = """
    wrangles:
        - remove_words:
            input:
              - Description
              - Description2
            to_remove:
                - Materials
                - Colours
            output: Product1
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == "If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided."

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
def test_standardize_4():
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

# Mini Standardize
def test_standardize_5():
    data = pd.DataFrame({
    'Abbrev': ['random ASAP random', 'random ETA random'],
    })
    recipe = """
    wrangles:
        - standardize:
            input: Abbrev
            output: Abbreviations
            find: ETA
            replace: Estimated Time of Arrival
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['Abbreviations'] == 'random Estimated Time of Arrival random'
    
# Mini Standardize error with model id also included
def test_standardize_6():
    data = pd.DataFrame({
    'Abbrev': ['random ASAP random', 'random ETA random'],
    })
    recipe = """
    wrangles:
        - standardize:
            input: Abbrev
            output: Abbreviations
            find: ETA
            replace: Estimated Time of Arrival
            model_id: f7958bd2-af22-43b1
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Standardize must have model_id or find and replace as parameters'

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
    
# using full language names
def test_translate_2():
    data = pd.DataFrame({
    'Español': ['¡Hola Mundo!'],
    })
    recipe = """
    wrangles:
        - translate:
            input: Español
            output: English
            source_language: Spanish
            target_language: English
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['English'] == 'Hello World!'
    
# If the input is multiple columns (a list)
def test_translate_3():
    data = pd.DataFrame({
    'Español': ['¡Hola Mundo!'],
    'Español2': ['¡Hola Mundo Dos!'],
    })
    recipe = """
    wrangles:
        - translate:
            input:
              - Español
              - Español2
            output:
              - English
              - English2
            source_language: Spanish
            target_language: English
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['English2'] == 'Hello World Two!'
    
# if the input and output are not the same
def test_translate_4():
    data = pd.DataFrame({
    'Español': ['¡Hola Mundo!'],
    'Español2': ['¡Hola Mundo Dos!'],
    })
    recipe = """
    wrangles:
        - translate:
            input:
              - Español
              - Español2
            output: English
            source_language: Spanish
            target_language: English
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == "If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided."
    
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
    

#
# Maths
#

# Regular use
def test_maths_1():
    data = pd.DataFrame({
        'col1': [1, 1, 1],
        'col2': [2, 2, 2]
    })
    recipe = """
    wrangles:
      - maths:
          input: col1 + col2
          output: result
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['result'] == 3
    
# US spelling of maths
def test_math_1():
    data = pd.DataFrame({
        'col1': [1, 1, 1],
        'col2': [2, 2, 2]
    })
    recipe = """
    wrangles:
      - math:
          input: col1 + col2
          output: result
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['result'] == 3
    
#
# SQL
#

#regular use
def test_sql_1():
    data = pd.DataFrame({
        'header1': [1, 2, 3],
        'header2': ['a', 'b', 'c'],
        'header3': ['x', 'y', 'z'],
    })
    recipe = """
    wrangles:
      - sql:
          command: |
            SELECT header1, header2
            FROM df
            WHERE header1 >= 2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['header1'] == 2
    
# Using an incorrect sql statement
def test_sql_2():
    data = pd.DataFrame({
        'header1': [1, 2, 3],
        'header2': ['a', 'b', 'c'],
        'header3': ['x', 'y', 'z'],
    })
    recipe = """
    wrangles:
      - sql:
          command: |
            CREATE TABLE header1
            FROM df
            WHERE header1 >= 2
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Only SELECT statements are supported for sql wrangles'
    
# sql with objects in data
def test_sql_3():
    data = pd.DataFrame({
        'header1': [1, 2, 3],
        'header2': ['a', 'b', 'c'],
        'header3': ['x', 'y', {"Object": "z"}],
    })
    recipe = """
    wrangles:
      - sql:
          command: |
            SELECT *
            FROM df
            WHERE header1 >= 3
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['header3'] == {"Object": "z"}

#
# Recipe as a wrangle. Recipe-ception
#
def test_recipe_wrangle_1():
    data = pd.DataFrame({
        'col': ['Mario', 'Luigi']
    })
    recipe = """
    wrangles:
      - recipe:
          name: 'tests/samples/recipe_ception.wrgl.yaml'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['col'].iloc[0] == 'MARIO'
    
    
#
# Date Calculator
#

# add time (default)
def test_date_calc_1():
    data = pd.DataFrame({
        'date1': ['12/25/2022'],
    })
    recipe = """
    wrangles:
      - date_calculator:
          input: date1
          output: out1
          time_unit: days
          time_value: 6
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1']._date_repr == '2022-12-31'
    
# subtract time
def test_date_calc_2():
    data = pd.DataFrame({
        'date1': ['12/25/2022'],
    })
    recipe = """
    wrangles:
      - date_calculator:
          input: date1
          output: out1
          operation: subtract
          time_unit: days
          time_value: 1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1']._date_repr == '2022-12-24'
    
# Invalid operation
def test_date_calc_3():
    data = pd.DataFrame({
        'date1': ['12/25/2022'],
    })
    recipe = """
    wrangles:
      - date_calculator:
          input: date1
          output: out1
          operation: matrix-multiplication
          time_unit: days
          time_value: 6
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == '"matrix-multiplication" is not a valid operation. Available operations: "add", "subtract"'