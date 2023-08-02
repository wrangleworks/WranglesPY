import wrangles
import pandas as pd
import re as _re
from fractions import Fraction as _Fraction
import pytest


#
# CASE
#
def test_case_default():
    """
    Default value -> no case specified
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Data1'] == 'a string'

def test_case_list():
    """
    Input is a list
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input:
            - Data1
            - Data2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Data1'] == 'a string' and df.iloc[0]['Data2'] == 'another string'


def test_case_output():
    """
    Specifying output column
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          output: Column
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Column'] == 'a string'

def test_case_list_to_list():
    """
    Output and input are a multi columns
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input:
            - Data1
            - Data2
          output:
            - Column1
            - Column2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Column1'] == 'a string' and df.iloc[0]['Column2'] == 'another string'

# Test error when a list is input with only one output given
def test_case_multi_input_single_output():
    """
    Input is a list of columns and output is a single column
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input:
            - Data1
            - Data2
          output: Column1
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'The lists for input and output must be the same length.'

# Test error when a single input with list of outputs is given
def test_case_single_input_multi_output():
    """
    Input is a list of columns and output is a single column
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          output:
            - Column1
            - Column2
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'The lists for input and output must be the same length.'

def test_case_lower():
    """
    Test converting to lower case
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          case: lower
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Data1'] == 'a string'

def test_case_upper():
    """
    Test converting to upper case
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          case: upper
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Data1'] == 'A STRING'
    
def test_case_title():
    """
    Test converting to title case
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          case: title
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Data1'] == 'A String'

def test_case_sentence():
    """
    Test converting to sentence case
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          case: sentence
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Data1'] == 'A string'

def test_case_where():
    """
    Test converting to title case using where
    """
    data = pd.DataFrame({
    'Col1': ['ball bearing', 'roller bearing', 'needle bearing'],
    'number': [25, 31, 22]
    })
    recipe = """
    wrangles:
      - convert.case:
          input: Col1
          case: title
          where: number > 22
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Col1'] == 'Ball Bearing' and df.iloc[2]['Col1'] == ""

#
# Data Type
#
def test_data_type_str():
    """
    Test converting to string data type
    """
    data = pd.DataFrame([[1, "2"]], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.data_type:
          input: Data1
          data_type: str
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert isinstance(df.iloc[0]['Data1'], str)

# List of inputs to a list of outputs
def test_data_list_to_list():
    """
    Test using a list of outputs and a list of inputs
    """
    data = pd.DataFrame([[1, "2"]], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.data_type:
          input: 
            - Data1
            - Data2
          output:
            - out1
            - out2
          data_type: str
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert isinstance(df.iloc[0]['out1'], str) and isinstance(df.iloc[0]['out2'], str) 
    
# List of inputs to a single output
def test_data_multi_input_single_output():
    """
    Test error when list of inputs given with a single output
    """
    data = pd.DataFrame([[1, "2"]], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.data_type:
          input: 
            - Data1
            - Data2
          output: out1
          data_type: str
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'The lists for input and output must be the same length.'
    
# Single input to a list of outputs
def test_data_single_input_multi_output():
    """
    Test error when single input given with list of outputs
    """
    data = pd.DataFrame([[1, "2"]], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.data_type:
          input: Data1
          output: 
            - out1
            - out2
          data_type: str
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'The lists for input and output must be the same length.'

def test_data_where():
    """
    Test convert.data_type using where
    """
    data = pd.DataFrame({
    'number': [25, 31, 22]
    })
    recipe = """
    wrangles:
      - convert.data_type:
          input: number
          output: number string
          data_type: str
          where: number > 25
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['number string'] == "" and df.iloc[1]['number string'] == '31'

#
# JSON
#
def test_to_json_array():
    """
    Test converting to a list to a JSON array
    """
    data = pd.DataFrame([['val1', 'val2']], columns=['header1', 'header2'])
    recipe = """
    wrangles:
        - merge.to_list:
            input:
              - header1
              - header2
            output: headers
        - convert.to_json:
            input: headers
            output: headers_json
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['headers_json'] == '["val1", "val2"]'

# Test converting to json using a list of input and output columns
def test_to_json_array_list_to_list():
    """
    Test converting to a list to a JSON array with a list of input and output columns
    """
    data = pd.DataFrame([[["val1", "val2"], ["val3", "val4"]]], columns=['header1', 'header2'])
    recipe = """
    wrangles:
        - convert.to_json:
            input: 
              - header1
              - header2
            output: 
              - out1
              - out2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == '["val1", "val2"]' and df.iloc[0]['out2'] == '["val3", "val4"]'
    
# Test error when using a list of input columns and a single output column
def test_to_json_array_list_to_single_output():
    """
    Test converting to a list to a JSON array with a list of input columns and a single output column
    """
    data = pd.DataFrame([[["val1", "val2"], ["val3", "val4"]]], columns=['header1', 'header2'])
    recipe = """
    wrangles:
        - convert.to_json:
            input: 
              - header1
              - header2
            output: out1
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'The lists for input and output must be the same length.'
    
# Test error when using a single input column and a list of output columns
def test_to_json_array_single_input_to_multi_output():
    """
    Test converting to a list to a JSON array with a single input and a list of output columns
    """
    data = pd.DataFrame([[["val1", "val2"], ["val3", "val4"]]], columns=['header1', 'header2'])
    recipe = """
    wrangles:
        - convert.to_json:
            input: header1
            output: 
              - out1
              - out2
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'The lists for input and output must be the same length.'

def test_to_json_array_where():
    """
    Test converting to a list to a JSON array using where
    """
    data = pd.DataFrame({
        'header1': ['val1', 'val2', 'val3'],
        'header2': ['val4', 'val5', 'val6'],
        'numbers': [2, 7, 4]
    })
    recipe = """
    wrangles:
        - merge.to_list:
            input:
              - header1
              - header2
            output: headers
        - convert.to_json:
            input: headers
            output: headers_json
            where: numbers > 6
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['headers_json'] == "" and df.iloc[1]['headers_json'] == '["val2", "val5"]'

# Test convert.to_json using indent
def test_to_json_array_indent():
    """
    Test converting to a list to a JSON array using indent
    """
    data = pd.DataFrame([['val1', 'val2']], columns=['header1', 'header2'])
    recipe = """
    wrangles:
        - merge.to_list:
            input:
              - header1
              - header2
            output: headers
        - convert.to_json:
            input: headers
            output: headers_json
            indent: 4
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['headers_json'] == '[\n    "val1",\n    "val2"\n]'
    
# Test convert.to_json using sort_keys
def test_to_json_array_sort_keys():
    """
    Test converting to a list to a JSON array using sort_keys
    """
    data = pd.DataFrame([['val3', 'val1', 'val2']], columns=['header3', 'header1', 'header2'])
    recipe = """
    wrangles:
        - merge.to_dict:
            input:
              - header3
              - header1
              - header2
            output: headers
        - convert.to_json:
            input: headers
            output: headers_json
            sort_keys: True
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['headers_json'] == '{"header1": "val1", "header2": "val2", "header3": "val3"}'

def test_from_json_array():
    """
    Test converting to a JSON array to a list
    """
    data = pd.DataFrame([['["val1", "val2"]']], columns=['header1'])
    recipe = """
    wrangles:
        - convert.from_json:
            input: header1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert isinstance(df.iloc[0]['header1'], list)

# test converting from json with a list to a list
def test_from_json_array_list_to_list():
    """
    Test converting to a JSON array to a list using a list of inputs and outputs
    """
    data = pd.DataFrame([['["val1", "val2"]', '["val3", "val4"]']], columns=['header1', 'header2'])
    recipe = """
    wrangles:
        - convert.from_json:
            input: 
              - header1
              - header2
            output:
              - out1
              - out2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert isinstance(df.iloc[0]['out1'], list) and isinstance(df.iloc[0]['out2'], list)
    
# test error with a list to a single output
def test_from_json_array_list_to_single_output():
    """
    Test error with a list of inputs and a single output
    """
    data = pd.DataFrame([['["val1", "val2"]', '["val3", "val4"]']], columns=['header1', 'header2'])
    recipe = """
    wrangles:
        - convert.from_json:
            input: 
              - header1
              - header2
            output: out1
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'The lists for input and output must be the same length.'
    
# test error with a single input and a list of outputs
def test_from_json_array_single_input_to_multi_output():
    """
    Test error with a single input and a list of outputs
    """
    data = pd.DataFrame([['["val1", "val2"]', '["val3", "val4"]']], columns=['header1', 'header2'])
    recipe = """
    wrangles:
        - convert.from_json:
            input: header1
            output: 
              - out1
              - out2
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'The lists for input and output must be the same length.'

def test_from_json_array_where():
    """
    Test converting to a JSON array to a list using where
    """
    data = pd.DataFrame({
        'header1': ['["val1", "val2"]', '["val3", "val4"]'],
        'numbers': [5, 7]
    })
    recipe = """
    wrangles:
        - convert.from_json:
            input: header1
            where: numbers > 6
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['header1'] == "" and isinstance(df.iloc[1]['header1'], list)
    
#
# Convert to datetime
#

def test_convert_to_datetime():
    data = pd.DataFrame({
        'date': ['12/25/2050'],
    })
    recipe = """
    wrangles:
      - convert.data_type:
          input: date
          output: date_type
          data_type: datetime
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['date_type'].week == 51
    
def test_convert_to_datetime_where():
    """
    Test using convert to datetime using where
    """
    data = pd.DataFrame({
        'date': ['12/25/2050', '11/10/1987'],
        'numbers': [4, 2]
    })
    recipe = """
    wrangles:
      - convert.data_type:
          input: date
          output: date_type
          data_type: datetime
          where: numbers > 3
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['date_type'] == '0' and df.iloc[0]['date_type'].week == 51

#
# Fractions
#
def test_fraction_to_decimal():
    data = pd.DataFrame({
    'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
    })
    recipe = """
    wrangles:
      - convert.fraction_to_decimal:
          input: col1
          output: out1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == "The length is 0.5 wide 0.3333 high"

# Test converting fraction to decimal with a list of outputs and inputs
def test_fraction_to_decimal_list_to_list():
    """
    Test using a list of outputs and inputs
    """
    data = pd.DataFrame({
    'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
    'col2': ['The length is 3/4 wide 1/8 high', 'the panel is 1/3 inches', 'the diameter is 3/16 meters']
    })
    recipe = """
    wrangles:
      - convert.fraction_to_decimal:
          input: 
            - col1
            - col2
          output: 
            - out1
            - out2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == "The length is 0.5 wide 0.3333 high" and df.iloc[0]['out2'] == "The length is 0.75 wide 0.125 high"
    
# Test converting fraction to decimal with a list of inputs and a single output
def test_fraction_to_decimal_list_to_single_output():
    """
    Test using a list of inputs and a single output
    """
    data = pd.DataFrame({
    'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
    'col2': ['The length is 3/4 wide 1/8 high', 'the panel is 1/3 inches', 'the diameter is 3/16 meters']
    })
    recipe = """
    wrangles:
      - convert.fraction_to_decimal:
          input: 
            - col1
            - col2
          output: out1
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'The lists for input and output must be the same length.'

# Test converting fraction to decimal with a list of outputs and a single input
def test_fraction_to_decimal_single_input_multi_output():
    """
    Test using a single input and a list of outputs
    """
    data = pd.DataFrame({
    'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
    'col2': ['The length is 3/4 wide 1/8 high', 'the panel is 1/3 inches', 'the diameter is 3/16 meters']
    })
    recipe = """
    wrangles:
      - convert.fraction_to_decimal:
          input: col1
          output: 
            - out1
            - out2
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'The lists for input and output must be the same length.'

def test_fraction_to_decimal_where():
    """
    Test using fraction to decimal using where
    """
    data = pd.DataFrame({
    'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
    'numbers': [13, 12, 11]
    })
    recipe = """
    wrangles:
      - convert.fraction_to_decimal:
          input: col1
          output: out1
          where: numbers > 11
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[2]['out1'] == "" and df.iloc[0]['out1'] == "The length is 0.5 wide 0.3333 high"