import pytest
import wrangles
import pandas as pd
import logging

#
# Classify
#
def test_classify():
    """
    Test classify on a single input
    """
    df = wrangles.recipe.run(
        """
        wrangles:
            - classify:
                input: Col1
                output: Class
                model_id: c77839db-237a-476b
        """,
        dataframe = pd.DataFrame({
            'Col1': ['Ball Bearing']
        })
    )
    assert df.iloc[0]['Class'] == 'Ball Bearing'

def test_classify_2():
    """
    Multiple column input and output
    """
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
    assert (
        info.typename == 'ValueError' and
        "The lists for" in info.value.args[0]
    )

def test_classify_extract_model_id():
    """
    Test error message when passing an extract model id into a classify wrangle
    """
    data = pd.DataFrame({
    'Col1': ['Ball Bearing'],
    'Col2': ['Ball Bearing']
    })
    recipe = """
    wrangles:
        - classify:
            input: 
              - Col1
            output: 
              - Class
            model_id: 1eddb7e8-1b2b-4a52
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        'Using extract model_id 1eddb7e8-1b2b-4a52 in a classify function.' in info.value.args[0]
    )

def test_classify_invalid_model():
    """
    # Incorrect model_id missing "${ }" around value
    """
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
    assert (
        info.typename == 'ValueError' and
        'Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX' in info.value.args[0]
    )
    
def test_classify_invalid_variable_syntax():
    """
    # Not using ${} in recipe when using a model-id
    """
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
    assert (
        info.typename == 'ValueError' and
        'Incorrect model_id type.\nIf using Recipe, may be missing "${ }" around value' in info.value.args[0]
    )

def test_classify_where():
    """
    Test classify using where
    """
    data = pd.DataFrame({
    'Col1': ['Ball Bearing', 'Roller Bearing'],
    'Col2': ['Ball Bearing', 'Needle Bearing'],
    'number': [25, 31]
    })
    recipe = """
    wrangles:
        - classify:
            input: 
              - Col1
              - Col2
            output: 
              - Class1
              - Class2
            model_id: c77839db-237a-476b
            where: number > 25
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Class1'] == "" and df.iloc[1]['Class1'] == 'Roller Bearing'
    
#
# Filter
#

# Equal
def test_filter_equal():
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

# Equal
def test_filter_not_equal():
    data = pd.DataFrame({
        'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
        'Color': ['red','green', 'orange', 'red']
    })
    recipe = """
    wrangles:
        - filter:
            input: Color
            not_equal: red
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['Fruit'] == 'Orange'

# Is_in
def test_filter_in():
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
def test_filter_not_in():
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
def test_filter_greater_than():
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
def test_filter_greater_than_equal_to():
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
def test_filter_less_than():
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
def test_filter_less_than_equal_to():
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
def test_filter_between():
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
def test_filter_between_error():
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
    assert (
        info.typename == 'ValueError' and
        'Can only use "between" with two values' in info.value.args[0]
    )

# Contains
def test_filter_contains():
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
def test_filter_not_contains():
    data = pd.DataFrame({
        'Random': ['Apples', 'Applications', 'App', 'nothing here'],
        'Number': [13, 26, 52, 52]
    })
    recipe = """
    wrangles:
        - filter:
            input: Random
            not_contains: App
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 1
    
# is_null
def test_filter_is_null_true():
    data = pd.DataFrame({
        'Random': ['Apples', 'None', 'App', None],
    })
    recipe = """
    wrangles:
        - filter:
            input: Random
            is_null: False
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 3
    
# not_null, False
def test_filter_is_null_false():
    data = pd.DataFrame({
        'Random': ['Apples', 'None', 'App', None],
    })
    recipe = """
    wrangles:
        - filter:
            input: Random
            is_null: True
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 1

def test_filter_multiple():
    data = pd.DataFrame({
        'Random': ['Apples', 'None', 'App', None],
    })
    recipe = """
    wrangles:
        - filter:
            input: Random
            contains: App
            not_contains: les
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 1

def test_filter_where():
    data = pd.DataFrame({
        'Random': ['Apples', 'None', 'App', None],
    })
    recipe = """
    wrangles:
        - filter:
            where: Random = 'Apples'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 1

def test_filter_where_params():
    """
    Test a parameterized where condition
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - filter:
              where: Random = ?
              where_params:
                - Apples
        """,
        dataframe= pd.DataFrame({
            'Random': ['Apples', 'None', 'App', None],
        })
    )
    assert len(df) == 1 and df['Random'][0] == 'Apples'

def test_filter_where_params_dict():
    """
    Test a parameterized where condition
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - filter:
              where: Random = :var
              where_params:
                var: Apples
        """,
        dataframe= pd.DataFrame({
            'Random': ['Apples', 'None', 'App', None],
        })
    )
    assert len(df) == 1 and df['Random'][0] == 'Apples'

def test_filter_where_or():
    data = pd.DataFrame({
        'Random': ['Apples', 'None', 'App', None],
    })
    recipe = """
    wrangles:
        - filter:
            where: |
              Random = 'Apples'
              OR Random = 'App'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 2

def test_filter_input_list():
    """
    Test using a list for input. All input columns must match the criteria
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - filter:
              input:
                - Column1
                - Column2
              contains: App
        """,
        dataframe = pd.DataFrame({
            'Column1': ['Apples', 'None', 'App', 'Other'],
            'Column2': ['Apples', 'Apples', 'Other', 'Other']
        })
    )
    assert len(df) == 1


#
# HUGGINGFACE
#
def test_huggingface():
    """
    Test a huggingface model
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: >
                  The tower is 324 metres (1,063 ft) tall, 
                  about the same height as an 81-storey building, 
                  and the tallest structure in Paris.
                  Its base is square, measuring 125 metres (410 ft) on each side. 
                  During its construction,
                  the Eiffel Tower surpassed the Washington Monument to 
                  become the tallest man-made structure in the world,
                  a title it held for 41 years until the Chrysler Building 
                  in New York City was finished in 1930.
                  It was the first structure to reach a height of 300 metres. 
                  Due to the addition of a broadcasting aerial at the top of the tower in 1957,
                  it is now taller than the Chrysler Building by 5.2 metres (17 ft). 
                  Excluding transmitters, the Eiffel Tower is the second tallest 
                  free-standing structure in France after the Millau Viaduct.

        wrangles:
          - huggingface:
              input: header
              output: summary
              api_token: ${HUGGINGFACE_TOKEN}
              model: facebook/bart-large-cnn

          - select.list_element:
              input: summary
              element: 0
    
          - select.dictionary_element:
              input: summary
              element: summary_text
        """
    )

    assert len(df['summary'][0]) / len(df['header'][0])  < 0.5

#
# Log
#
def test_log_columns(caplog):
    """
    Test log when specifying columns
    """
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

def test_log(caplog):
    """
    Test default log
    """
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
        - log: {}
    """
    wrangles.recipe.run(recipe, dataframe=data)
    assert caplog.messages[-1] == ': Dataframe ::\n\n           Col1     Col2      Output 1 Output 2\n0  Ball Bearing  Bearing  Ball Bearing  Bearing\n'

def test_log_wildcard(caplog):
    """
    Test one column with wildcard
    """
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
    wrangles.recipe.run(recipe, dataframe=data)
    assert caplog.messages[-1] == ': Dataframe ::\n\n                     Col   Col1     Col2   Col3\n0  Hello, Wrangle, Works  Hello  Wrangle  Works\n'

def test_log_escaped_wildcard(caplog):
    """
    Test escaping a wildcard when specifying columns.
    """
    data = pd.DataFrame({
        'Col': ['Hello'],
        'Col*': ['WrangleWorks!'],
    })
    recipe = r"""
    wrangles:
      - log:
          columns:
            - Col\*
    """
    wrangles.recipe.run(recipe, dataframe=data)
    assert caplog.messages[-1] == ': Dataframe ::\n\n            Col*\n0  WrangleWorks!\n'

def test_log_write():
    """
    Test using a connector as part of a log
    """
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header: value
            
        wrangles:
          - log:
              write:
                - file:
                    name: tests/temp/temp.csv
        """
    )
    df = wrangles.recipe.run(
        """
        read:
          - file:
              name: tests/temp/temp.csv
        """
    )
    assert len(df) == 5 and df['header'][0] == 'value'

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
    assert (
        info.typename == 'ValueError' and
        "The lists for" in info.value.args[0]
    )

# tokenize inputs
def test_remove_words_tokenize():
    data = pd.DataFrame({
        'col': ['Metal Carbon Water Tank'],
        'materials': ['Metal Carbon']
    })
    recipe = """
    wrangles:
      - remove_words:
          input: col
          to_remove:
            - materials
          output: Out
          tokenize_to_remove: True
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Out'].iloc[0] == 'Water Tank'

# Raw inputs, ignore case is False
def test_remove_words_case_sensitive():
    data = pd.DataFrame({
        'col': ['METAl CaRBon WateR TaNk'],
        'materials': ['meTAL CaRBon']
    })
    recipe = """
    wrangles:
      - remove_words:
          input: col
          to_remove:
            - materials
          output: Out
          tokenize_to_remove: True
          ignore_case: False
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Out'].iloc[0] == 'METAl WateR TaNk'

# tokenize inputs and ignore case
def test_remove_words_tokenize_case_sensitive():
    data = pd.DataFrame({
        'col': ['METAl CaRBon WateR TaNk'],
        'materials': ['meTAL carbOn']
    })
    recipe = """
    wrangles:
      - remove_words:
          input: col
          to_remove:
            - materials
          output: Out
          tokenize_to_remove: True
          ignore_case: True
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Out'].iloc[0] == 'Water Tank'

def test_remove_words_where():
    """
    Test remove_words using where
    """
    data = pd.DataFrame({
    'Description': [['Steel', 'Blue', 'Bottle'], ['Aluminum', 'Red', 'Can'], ['Rubber', 'Yellow', 'Tire']],
    'Description2': [['Steel', 'Blue', 'Bottle'], ['Titanium', 'Blue', 'Pipe'], ['Iron', 'Brown', 'Plate']],
    'Materials': [['Steel', 'Rubber', 'Aluminum', 'Titanium', 'Iron'], ['Steel', 'Rubber', 'Aluminum', 'Titanium', 'Iron'], ['Steel', 'Rubber', 'Aluminum', 'Titanium', 'Iron']],
    'Colours': [['Blue', 'Red', 'Yellow', 'Brown'], ['Blue', 'Red', 'Yellow', 'Brown'], ['Blue', 'Red', 'Yellow', 'Brown']],
    'numbers': [4, 3, 2]
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
            where: numbers >= 3
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Product1'] == 'Bottle' and df.iloc[1]['Product2'] == 'Pipe' and df.iloc[2]['Product1'] == ""

#
# Rename
#
def test_rename_dict():
    """
    Rename using a dictionary of columns
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - rename:
              Manufacturer Name: Company
              Part Number: MPN
        """,
        dataframe = pd.DataFrame({
            'Manufacturer Name': ['Delos'],
            'Part Number': ['CH465517080'],
        })
    )
    assert df.iloc[0]['MPN'] == 'CH465517080'

def test_rename_input_output():
    """
    Rename using a single input to a single output
    """
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

def test_rename_missing_output():
    """
    Check error if input is provided but not output
    """
    with pytest.raises(ValueError) as info:
        wrangles.recipe.run(
            """
            wrangles:
                - rename:
                    input: Manufacturer Name
            """,
            dataframe = pd.DataFrame({
                'Manufacturer Name': ['Delos'],
                'Part Number': ['CH465517080'],
            })
        )
    assert (
        info.typename == 'ValueError' and
        'If an input' in info.value.args[0]
    )

def test_rename_inconsistent_input_output():
    """
    Check error if the lists for input and output are not equal lengths
    """
    with pytest.raises(ValueError) as info:
        wrangles.recipe.run(
            """
            wrangles:
                - rename:
                    input: Manufacturer Name
                    output:
                      - Two
                      - Columns
            """,
            dataframe = pd.DataFrame({
                'Manufacturer Name': ['Delos'],
                'Part Number': ['CH465517080'],
            })
        )
    assert (
        info.typename == 'ValueError' and
        "The lists for" in info.value.args[0]
    )

def test_rename_invalid_input():
    """
    Check error if a column specified in input doesn't exist
    """
    with pytest.raises(KeyError) as info:
        wrangles.recipe.run(
            """
            wrangles:
                - rename:
                    input: doesn't exist
                    output: Column
            """,
            dataframe = pd.DataFrame({
                'Manufacturer Name': ['Delos'],
                'Part Number': ['CH465517080'],
            })
        )
    assert info.typename == 'KeyError'

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
    assert (
        info.typename == 'ValueError' and
        'Incorrect model_id. May be missing "${ }" around value' in info.value.args[0]
    )

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
    assert (
        info.typename == 'ValueError' and
        'Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX' in info.value.args[0]
    )

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
    assert (
        info.typename == 'ValueError' and
        'Using extract model_id 1eddb7e8-1b2b-4a52 in a standardize function.' in info.value.args[0]
    )
    
# Using classify model with standardize function
def test_standardize_5():
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
    assert (
        info.typename == 'ValueError' and
        'Using classify model_id f7958bd2-af22-43b1 in a standardize function.' in info.value.args[0]
    )

def test_standardize_where():
    """
    Test standardize function using a where clause
    """
    data = pd.DataFrame({
    'Product': ['Wrench', 'Hammer', 'Pliers'],
    'Price': [4.99, 9.99, 14.99]
    })
    recipe = """
    wrangles:
        - standardize:
            input: Product
            output: Product Standardized
            model_id: 6ca4ab44-8c66-40e8
            where: Price > 10
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Product Standardized'] == "" and df.iloc[2]['Product Standardized'] == 'Pliers'


# List of inputs to one output
def test_standardize_multi_input_single_output():
    """
    Test error using multiple input columns and only one output
    """
    data = pd.DataFrame({
    'Abbrev1': ['ASAP'],
    'Abbrev2': ['RSVP']
    })
    recipe = """
    wrangles:
        - standardize:
            input: 
              - Abbrev1
              - Abbrev2
            output: Abbreviations
            model_id: 6ca4ab44-8c66-40e8
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        'The lists for input and output must be the same length.' in info.value.args[0]
    )

# List of inputs and outputs single model_id
def test_standardize_multi_io_single_model():
    """
    Test output using multiple input and output columns with a single model_id
    """
    data = pd.DataFrame({
    'Abbrev1': ['ASAP'],
    'Abbrev2': ['ETA']
    })
    recipe = """
    wrangles:
        - standardize:
            input: 
              - Abbrev1
              - Abbrev2
            output: 
              - Abbreviations1
              - Abbreviations2
            model_id: 6ca4ab44-8c66-40e8
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Abbreviations1'] == 'As Soon As Possible' and df.iloc[0]['Abbreviations2'] == 'Estimated Time of Arrival'

# List of inputs and outputs single model_id with where
def test_standardize_multi_io_single_model_where():
    """
    Test output using multiple input and output columns with a single model_id with a where filter
    """
    data = pd.DataFrame({
    'Abbrev1': ['FOMO', 'IDK', 'ASAP', 'ETA'],
    'Abbrev2': ['IDK', 'FOMO', 'ASAP', 'ETA']
    })
    recipe = """
    wrangles:
        - standardize:
            input: 
              - Abbrev1
              - Abbrev2
            output: 
              - Abbreviations1
              - Abbreviations2
            model_id: 6ca4ab44-8c66-40e8
            where: Abbrev1 LIKE Abbrev2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Abbreviations1'] == "" and df.iloc[2]['Abbreviations1'] == 'As Soon As Possible'

def test_replace():
    """
    Test replace
    """
    data = pd.DataFrame({
    'Abbrev': ['random ASAP random', 'random ETA random'],
    })
    recipe = """
    wrangles:
        - replace:
            input: Abbrev
            output: Abbreviations
            find: ETA
            replace: Estimated Time of Arrival
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['Abbreviations'] == 'random Estimated Time of Arrival random'

def test_replace_lists():
    """
    Test replace with a list for input and output
    """
    data = pd.DataFrame({
        'Abbrev1': ['random ETA random'],
        'Abbrev2': ['another ETA another']
    })
    recipe = """
    wrangles:
        - replace:
            input:
              - Abbrev1
              - Abbrev2
            output:
              - Abbreviations1
              - Abbreviations2
            find: ETA
            replace: Estimated Time of Arrival
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert (
        df.iloc[0]['Abbreviations1'] == 'random Estimated Time of Arrival random' and
        df.iloc[0]['Abbreviations2'] == 'another Estimated Time of Arrival another'
    )

def test_replace_regex():
    """
    Test replace using a regex pattern
    """
    data = pd.DataFrame({
        'Abbrev': ['random 123 random'],
    })
    recipe = """
    wrangles:
        - replace:
            input: Abbrev
            output: Abbreviations
            find: "[0-9]+"
            replace: found
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Abbreviations'] == 'random found random'

def test_replace_where():
    """
    Test replace using where
    """
    data = pd.DataFrame({
    'Abbrev': ['random ASAP random', 'random ETA random'],
    'numbers': [1, 2]
    })
    recipe = """
    wrangles:
        - replace:
            input: Abbrev
            output: Abbreviations
            find: ETA
            replace: Estimated Time of Arrival
            where: numbers > 1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Abbreviations'] == "" and df.iloc[1]['Abbreviations'] == 'random Estimated Time of Arrival random'

def test_replace_inconsistent_input():
    """
    Check error when the lists for input and output are inconsistent
    """
    with pytest.raises(ValueError) as info:
        wrangles.recipe.run(
            """
            wrangles:
              - replace:
                  input:
                    - Abbrev1
                  output:
                    - Abbreviations1
                    - Abbreviations2
                  find: ETA
                  replace: Estimated Time of Arrival
            """,
            dataframe = pd.DataFrame({
                'Abbrev1': ['random ETA random'],
                'Abbrev2': ['another ETA another']
            })
        )
    assert (
        info.typename == 'ValueError' and
        'The lists for' in info.value.args[0]
    )

def test_replace_integer():
    """
    Test replace with integers
    """
    data = pd.DataFrame({
    'numbers': [555, 252, 355]
    })
    recipe = """
    wrangles:
        - replace:
            input: numbers
            output: replaced numbers
            find: 5
            replace: 2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['replaced numbers'] == '222'

def test_replace_integer_with_string():
    """
    Test replacing integers with strings
    """
    data = pd.DataFrame({
    'numbers': [555, 252, 355]
    })
    recipe = """
    wrangles:
        - replace:
            input: numbers
            output: replaced numbers
            find: 5
            replace: five
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['replaced numbers'] == 'fivefivefive'

def test_replace_string_with_integer():
    """
    Test replacing a string with an integer
    """
    data = pd.DataFrame({
    'numbers': ['five', 'fifty-five']
    })
    recipe = """
    wrangles:
        - replace:
            input: numbers
            output: replaced numbers
            find: five
            replace: 5
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['replaced numbers'] == 'fifty-5'

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
    assert (
        info.typename == 'ValueError' and
        "The lists for" in info.value.args[0]
    )
    
def test_translate_where():
    """
    Test translate using where
    """
    data = pd.DataFrame({
    'Español': ['¡Hola Mundo!', 'Me llamo es Johnny Numero Cinco'],
    'numbers': [3, 88]
    })
    recipe = """
    wrangles:
        - translate:
            input: Español
            output: English
            source_language: Spanish
            target_language: English
            where: numbers > 70
    """
    df =  wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['English'] == "" and df.iloc[1]['English'] == 'My name is Johnny Number Five'

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
    
def test_math_where():
    """
    Test math using where
    """
    data = pd.DataFrame({
        'col1': [5, 9, 12],
        'col2': [5, 3, 2]
    })
    recipe = """
    wrangles:
      - math:
          input: col1 + col2
          output: result
          where: col1 + col2 > 12
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['result'] == "" and df.iloc[2]['result'] == 14.0

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
    assert (
        info.typename == 'ValueError' and
        'Only SELECT statements are supported for sql wrangles' in info.value.args[0]
    )

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

def test_sql_params():
    """
    Test sql using params
    """
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
            WHERE header1 >= ($number)
          params: 
            number: 2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['header1'] == 2

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
def test_date_calc_1():
    """
    Add time (default)
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - date_calculator:
              input: date1
              output: out1
              time_unit: days
              time_value: 6
        """,
        dataframe = pd.DataFrame({
            'date1': ['12/25/2022'],
        })
    )
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

    assert (
        info.typename == 'ValueError' and
        '"matrix-multiplication" is not a valid operation. Available operations: "add", "subtract"' in info.value.args[0]
    )

def test_date_calc_inconsistent_input():
    """
    Check error if input and output provided aren't consistent lengths
    """
    with pytest.raises(ValueError) as info:
        wrangles.recipe.run(
            """
            wrangles:
            - date_calculator:
                input:
                  - date1
                output:
                  - out1
                  - out2
                operation: subtract
                time_unit: days
                time_value: 1
            """,
            dataframe = pd.DataFrame({
                'date1': ['12/25/2022'],
            })
        )
    assert (
        info.typename == 'ValueError' and
        'The lists for' in info.value.args[0]
    )

# Test date_calculator using multiple input and output columns
def test_date_calc_multi_io():
    """
    Check output when ran with multiple input and output columns
    """
    recipe = """
    wrangles:
      - date_calculator:
          input:
            - date1
            - date2
          output:
            - out1
            - out2
          operation: subtract
          time_unit: days
          time_value: 5
    """
    data = pd.DataFrame({
                'date1': ['12/25/2022'],
                'date2': ['7/4/2023']
            })
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1']._date_repr == '2022-12-20' and df.iloc[0]['out2']._date_repr == '2023-06-29'

def test_date_calc_where():
    data = pd.DataFrame({
        'date1': ['12/25/2022', '12/31/2022'],
        'number': [6, 12]
    })
    recipe = """
    wrangles:
      - date_calculator:
          input: date1
          output: out1
          operation: subtract
          time_unit: days
          time_value: 1
          where: number > 6
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == '0' and df.iloc[1]['out1']._date_repr == '2022-12-30'

def test_copy():
    """
    Test copying a column
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 3
              values:
                col1: val1

        wrangles:
          - copy:
              input: col1
              output: col2
        """
    )
    assert list(df['col2'].values) == ['val1', 'val1', 'val1']

def test_copy_where():
    """
    Test copying a column
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - copy:
              input: col1
              output: col3
              where: col2 >= 2
        """,
        dataframe=pd.DataFrame({
            "col1": ["val1", "val1", "val1"],
            "col2": [1,2,3]
        })
    )
    assert list(df['col3'].values) == ['', 'val1', 'val1']

## Python
def test_python():
    """
    Test a simple python command
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: a
                header2: b
        wrangles:
          - python:
              command: header1 + " " + header2
              output: result
        """
    )
    assert df["result"][0] == "a b"

def test_python_list_comprehension():
    """
    Test a python list comprehension
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: '["a","b","c"]'
                header2: '["1","2","3"]'
        wrangles:
          - convert.from_json:
              input:
                - header1
                - header2
          - python:
              command: |
                [
                  x + " " + y
                  for x, y in zip(header1, header2)
                ]
              output: result
          - convert.to_json:
              input: result
        """
    )
    assert df["result"][0] == '["a 1", "b 2", "c 3"]'

def test_python_column_with_space():
    """
    Test a simple python command
    where a column name includes a space
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header 1: a
                header 2: b
        wrangles:
          - python:
              command: header_1 + " " + header_2
              output: result
        """
    )
    assert df["result"][0] == "a b"

def test_python_kwargs():
    """
    Test kwargs dict
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: a
                header2: b
        wrangles:
          - python:
              command: kwargs
              output: result
          - convert.to_json:
              input: result
        """
    )
    assert df["result"][0] == '{"header1": "a", "header2": "b"}'

def test_python_input():
    """
    Test using input to filter columns
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: a
                header2: b
                header3: c
        wrangles:
          - python:
              command: kwargs
              input:
                - header1
                - header2
              output: result
          - convert.to_json:
              input: result
        """
    )
    assert df["result"][0] == '{"header1": "a", "header2": "b"}'

def test_python_input_wildcard():
    """
    Test using input to filter columns with a wildcard
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: a
                header2: b
                not_this: c
        wrangles:
          - python:
              command: kwargs
              input: header*
              output: result
          - convert.to_json:
              input: result
        """
    )
    assert df["result"][0] == '{"header1": "a", "header2": "b"}'

def test_python_multiple_output():
    """
    Test providing multiple outputs
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: a
                header2: b
        wrangles:
          - python:
              command: kwargs.values()
              output:
                - result1
                - result2
        """
    )
    assert df["result1"][0] == "a" and df["result2"][0] == "b"
