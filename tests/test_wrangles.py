import pytest
import wrangles
import pandas as pd
from wrangles.train import train
import os


# Classify
def test_classify():
    result = wrangles.classify('cheese', 'a62c7480-500e-480c')
    assert result.split(' || ')[0] == 'Dairy'

def test_classify_list():
    result = wrangles.classify(['cheese'], 'a62c7480-500e-480c')
    assert result[0].split(' || ')[0] == 'Dairy'
  
##  Classify Raise Errors
# Invalid input data provided
def test_classify_error_1():
    with pytest.raises(TypeError) as info:
        raise wrangles.classify({'ball bearing'}, 'a62c7480-500e-480c')
    assert info.typename == 'TypeError' and info.value.args[0] == 'Invalid input data provided. The input must be either a string or a list of strings.'
    
# Incorrect or missing values in model_id. format is XXXXXXXX-XXXX-XXXX'
def test_classify_error_2():
    with pytest.raises(ValueError) as info:
        raise wrangles.classify('ball bearing', 'a62c7480-500e-480')
    assert info.typename == 'ValueError' and info.value.args[0] == 'Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX'

# Wrong Model id on wrong function name
def test_classify_error_3():
    with pytest.raises(ValueError) as info:
        raise wrangles.classify('ball bearing', 'fce592c9-26f5-4fd7')
    assert info.typename == 'ValueError' and info.value.args[0] == f'Using extract model_id fce592c9-26f5-4fd7 in a classify function.'

# Data
def test_user_models():
    result = wrangles.data.user.models('extract')
    assert len(result) > 0

def test_user_models_extract():
    result = wrangles.data.user.models('extract')
    assert result[0]['purpose'] == 'extract'

def test_user_models_classify():
    result = wrangles.data.user.models('classify')
    assert result[0]['purpose'] == 'classify'


# Extract
def test_address():
    result = wrangles.extract.address('1100 Congress Ave, Austin, TX 78701, USA', 'streets')
    assert result[0] == '1100 Congress Ave'

def test_address_list():
    result = wrangles.extract.address(['1100 Congress Ave, Austin, TX 78701, USA'], 'streets')
    assert result[0][0] == '1100 Congress Ave'

def test_attributes():
    result = wrangles.extract.attributes('something 15V something')
    assert result['voltage'][0] == '15V'

def test_attributes_list():
    result = wrangles.extract.attributes(['something 15V something'])
    assert result[0]['voltage'][0] == '15V'

def test_codes():
    result = wrangles.extract.codes('something ABC123ZZ something')
    assert result[0] == 'ABC123ZZ'

def test_codes_list():
    result = wrangles.extract.codes(['something ABC123ZZ something'])
    assert result[0][0] == 'ABC123ZZ'

def test_custom():
    result = wrangles.extract.custom('test skf test', 'fce592c9-26f5-4fd7')
    assert result[0] == 'SKF'

def test_custom_list():
    result = wrangles.extract.custom(['test skf test'], 'fce592c9-26f5-4fd7')
    assert result[0][0] == 'SKF'

def test_custom_first_element():
    result = wrangles.extract.custom('test skf test timken', 'fce592c9-26f5-4fd7', first_element=True)
    assert result == 'SKF' or result == 'TIMKEN'

def test_custom_first_element_list():
    result = wrangles.extract.custom(['test skf test timken', 'test timken test skf'], 'fce592c9-26f5-4fd7', first_element=True)
    assert result == ['SKF', 'SKF']

def test_properties():
    result = wrangles.extract.properties('something yellow something')
    assert result['Colours'][0] == 'Yellow'

def test_properties_list():
    result = wrangles.extract.properties(['something yellow something'])
    assert result[0]['Colours'][0] == 'Yellow'
    
##  Extract Raise Errors
# Invalid input data provided
def test_extract_error_1():
    with pytest.raises(TypeError) as info:
        raise wrangles.extract.custom({'ball bearing'}, 'a62c7480-500e-480c')
    assert info.typename == 'TypeError' and info.value.args[0] == 'Invalid input data provided. The input must be either a string or a list of strings.'
    
# Incorrect or missing values in model_id. format is XXXXXXXX-XXXX-XXXX'
def test_extract_error_2():
    with pytest.raises(ValueError) as info:
        raise wrangles.extract.custom('ball bearing', 'fce592c9-26f5-4fd')
    assert info.typename == 'ValueError' and info.value.args[0] == 'Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX'

# Wrong Model id on wrong function name
def test_extract_error_3():
    with pytest.raises(ValueError) as info:
        raise wrangles.extract.custom('ball bearing', 'a62c7480-500e-480c')
    assert info.typename == 'ValueError' and info.value.args[0] == f'Using classify model_id a62c7480-500e-480c in an extract function.'

def test_extract_html_str():
    result = wrangles.extract.html('<a href="https://www.wrangleworks.com/">Wrangle Works!</a>', dataType='text')
    assert result == 'Wrangle Works!'
# Translate
def test_translate():
    result = wrangles.translate('My name is Chris', 'DE')
    assert result == 'Mein Name ist Chris.'

def test_translate_list():
    result = wrangles.translate(['My name is Chris'], 'DE')
    assert result[0] == 'Mein Name ist Chris.'
    
# Invalid input type (dict)
def test_translate_typeError():
    with pytest.raises(TypeError) as info:
        raise wrangles.translate({'No Funciona'}, 'ES')
    assert info.typename == 'TypeError' and info.value.args[0] == 'Invalid input data provided. The input must be either a string or a list of strings.'
    
def test_translate_list_lower_case():
    result = wrangles.translate(['PRUEBA UNO'], 'EN-GB', case= 'lower')
    assert result[0] == 'test one'
    
def test_translate_list_upper_case():
    result = wrangles.translate(['prueba dos'], 'EN-GB', case= 'upper')
    assert result[0] == 'TEST TWO'

def test_translate_list_title_case():
    result = wrangles.translate(['PRueBa TrEs'], 'EN-GB', case= 'title')
    assert result[0] == 'Test Three'    

# Standardize

# Str as input
def test_standardize_1():
    result = wrangles.standardize('ASAP', '6ca4ab44-8c66-40e8')
    assert result == 'As Soon As Possible'
    
# invalid input
def test_standardize_2():
    with pytest.raises(TypeError) as info:
        raise wrangles.standardize({'ASAP'}, '6ca4ab44-8c66-40e8')
    assert info.typename == 'TypeError' and info.value.args[0] == 'Invalid input data provided. The input must be either a string or a list of strings.'

# Headers not included ['Find', 'Replace']
def test_standardize_train_2():
    data = [
        ['Rice', 'Arroz'],
        ['Wheat']
    ]
    config = {
        'training_data': data,
        'name': 'test_standardize',
        'model_id': '1234567890',
    }
    with pytest.raises(ValueError) as info:
        raise train.standardize(**config)
    assert info.typename == 'ValueError' and info.value.args[0][:31] == 'Training_data list must contain'
    
def test_standardize_train_3():
    data = {'Rice': 'Arroz'}
    config = {
        'training_data': data,
        'name': 'test_standardize',
        'model_id': '1234567890',
    }
    with pytest.raises(ValueError) as info:
        raise train.standardize(**config)
    assert info.typename == 'ValueError' and info.value.args[0] == 'A list is expected for training_data'


#
# Train Wrangles
#

class temp_classify():
    status_code = 202
    content = b'{"access_token":"abc"}'
    
# input of lists of lists
# ValueError, input does not contain Category 
def test_classify_train_1():
    data = [
        ['Rice', 'Grain'],
        ['Wheat', '']
    ]
    config = {
        'training_data': data,
        'name': 'test_classify',
        'model_id': '1234567890',
    }
    with pytest.raises(ValueError) as info:
        raise train.classify(**config)
    assert info.typename == 'ValueError' and info.value.args[0][:31] == "Training_data list must contain"

class temp_extract():
    status_code = 202
    content = b'{"access_token":"abc"}'
        
# input of lists of lists
# ValueError, input contains None for Variant (Optional) 
def test_extract_train_1():
    data = [
        ['Television', 'TV'],
        ['Computer']
    ]
    config = {
        'training_data': data,
        'name': 'test_extract'
    }
    with pytest.raises(ValueError) as info:
        raise train.extract(**config)
    assert info.typename == 'ValueError' and info.value.args[0][:31] == "Training_data list must contain"

# format
def test_sig_figs():
    """
    Test sigfigs calling as a python function
    """
    vals = [
        '13.45644 ft',
        'length: 34453.3323ft',
        '34.234234',
        'nothing here',
        13.4565,
        134234,
        ''
    ]
    res = wrangles.format.significant_figures(vals, 3)
    assert res == ['13.5 ft', 'length: 34500ft', '34.2', 'nothing here', 13.5, 134000, '']

### Lookup
def test_lookup_single_value_no_columns():
    """
    Test lookup with a single value and no columns specified
    """
    result = wrangles.lookup("a", "fe730444-1bda-4fcd")
    assert result == {"Value": 1}

def test_lookup_list_value_no_columns():
    """
    Test lookup with list of values and no columns specified
    """
    result = wrangles.lookup(["a"], "fe730444-1bda-4fcd")
    assert result == [{"Value": 1}]

def test_lookup_single_value_single_column():
    """
    Test lookup with a single input value and a single result column
    """
    result = wrangles.lookup("a", "fe730444-1bda-4fcd", "Value")
    assert result == 1

def test_lookup_single_value_list_column():
    """
    Test lookup with a single input value and a list of result columns
    """
    result = wrangles.lookup("a", "fe730444-1bda-4fcd", ["Value"])
    assert result == [1]

def test_lookup_list_value_single_column():
    """
    Test lookup with a list of input values and a single result column
    """
    result = wrangles.lookup(["a"], "fe730444-1bda-4fcd", "Value")
    assert result == [1]

def test_lookup_list_value_list_column():
    """
    Test lookup with a list of input values and a list of result columns
    """
    result = wrangles.lookup(["a"], "fe730444-1bda-4fcd", ["Value"])
    assert result == [[1]]

def test_embedding_single():
    """
    Test generating an embedding from a single value
    """
    result = wrangles.openai.embeddings(
        "test string",
        api_key=os.environ["OPENAI_API_KEY"],
        model="text-embedding-3-small"
    )
    assert len(result) == 1536
    assert [round(float(x), 3) for x in result[:3]] == [0.007, -0.045, 0.025]

def test_embedding_list():
    """
    Test generating embeddings for a list
    """
    result = wrangles.openai.embeddings(
        ["test string", "test string 2"],
        api_key=os.environ["OPENAI_API_KEY"],
        model="text-embedding-3-small"
    )
    assert len(result) == 2
    assert len(result[0]) == 1536
    assert [round(float(x), 3) for x in result[0][:3]] == [0.007, -0.045, 0.025]

def test_extract_ai_model_id():
    """
    Test using python api for extract.ai
    using a pre-created model_id
    """
    results = wrangles.extract.ai(
        "yellow square",
        model_id="0e81f1ad-c0a3-42b4",
        api_key=os.environ['OPENAI_API_KEY']
    )

    assert (
        'Colors' in results and
        'Shapes' in results and
        isinstance(results['Colors'], list)
    )

def test_extract_ai_model_id_list():
    """
    Test using python api for extract.ai
    using a pre-created model_id with a list
    """
    results = wrangles.extract.ai(
        ["yellow square", "red circle"],
        model_id="0e81f1ad-c0a3-42b4",
        api_key=os.environ['OPENAI_API_KEY']
    )

    assert (
        isinstance(results, list) and
        'Colors' in results[0] and
        'Shapes' in results[1] and
        isinstance(results[1]['Colors'], list)
    )

def test_extract_ai_output_schema_keys():
    """
    Test using python api for extract.ai
    using an output definition with keys
    """
    results = wrangles.extract.ai(
        "yellow square",
        api_key=os.environ['OPENAI_API_KEY'],
        output={
            "Colors": {
                "type": "string",
                "description": "Any colors found in the input"
            }
        },
        retries=2
    )

    assert (
        'Colors' in results and
        isinstance(results['Colors'], str)
    )

def test_extract_ai_output_schema():
    """
    Test using python api for extract.ai
    using an output without keys
    """
    results = wrangles.extract.ai(
        "12 penguins",
        api_key=os.environ['OPENAI_API_KEY'],
        output={
            "type": "number",
            "description": "The number of penguins"
        },
        retries=2
    )

    assert results == 12

def test_extract_ai_output_string():
    """
    Test using python api for extract.ai
    using an output that is just a description
    """
    results = wrangles.extract.ai(
        "yellow square",
        api_key=os.environ['OPENAI_API_KEY'],
        output="The names of any colors found in the input",
        retries=2
    )

    assert "yellow" in results

def test_extract_ai_properties_list():
    """
    Test using a simplier syntax for properties without defining type etc.
    """
    result = wrangles.extract.ai(
        "12mm spanner",
        api_key=os.environ['OPENAI_API_KEY'],
        output={
            "type": "array",
            "description": "Any numeric values such as lengths or weights returned as an object with keys for unit and value",
            "items": {
                "type": "object",
                "properties": "unit,value"
            }
        },
        retries=2
    )
    assert isinstance(result, list) and 'unit' in result[0]

### Format Split Tests  
def test_format_split_skip_empty_true():  
    """  
    Test format.split with skip_empty=True  
    """  
    result = wrangles.format.split(['hello world  test', 'foo  bar'], skip_empty=True)  
    assert result == [['hello', 'world', 'test'], ['foo', 'bar']]  
  
def test_format_split_skip_empty_false():  
    """  
    Test format.split with skip_empty=False  
    """  
    result = wrangles.format.split(['hello world  test', 'foo  bar'], skip_empty=False)  
    assert result == [['hello', 'world', '', 'test'], ['foo', '', 'bar']]  
  
def test_format_split_skip_empty_default():  
    """  
    Test format.split with default skip_empty behavior (False)  
    """  
    result = wrangles.format.split(['hello world  test', 'foo  bar'])  
    assert result == [['hello', 'world', '', 'test'], ['foo', '', 'bar']]  
  
def test_format_split_skip_empty_with_regex():  
    """  
    Test format.split with skip_empty=True and regex pattern  
    """  
    result = wrangles.format.split(['hello,,world', 'foo,,bar'], split_char='regex:,', skip_empty=True)  
    assert result == [['hello', 'world'], ['foo', 'bar']]

### Format Concatenate Tests
def test_format_concatenate_basic():
    """
    Test format.concatenate with basic list
    """
    result = wrangles.format.concatenate([['hello', 'world'], ['foo', 'bar']], ' ')
    assert result == ['hello world', 'foo bar']

def test_format_concatenate_skip_empty_true():
    """
    Test format.concatenate with skip_empty=True
    """
    result = wrangles.format.concatenate([['hello', '', 'world'], ['foo', None, 'bar']], ' ', skip_empty=True)
    assert result == ['hello world', 'foo bar']

def test_format_concatenate_skip_empty_false():
    """
    Test format.concatenate with skip_empty=False
    """
    result = wrangles.format.concatenate([['hello', '', 'world'], ['foo', None, 'bar']], '-', skip_empty=False)
    assert result == ['hello--world', 'foo-None-bar']

def test_format_concatenate_different_separator():
    """
    Test format.concatenate with different separator
    """
    result = wrangles.format.concatenate([['a', 'b', 'c'], ['x', 'y', 'z']], ', ')
    assert result == ['a, b, c', 'x, y, z']

### Format Coalesce Tests
def test_format_coalesce_basic():
    """
    Test format.coalesce returns first non-empty value
    """
    result = wrangles.format.coalesce([['', 'second', 'third'], ['', '', 'third']])
    assert result == ['second', 'third']

def test_format_coalesce_all_empty():
    """
    Test format.coalesce with all empty values
    """
    result = wrangles.format.coalesce([['', '', ''], [None, '', '']])
    assert result == ['', '']

def test_format_coalesce_first_value():
    """
    Test format.coalesce when first value is valid
    """
    result = wrangles.format.coalesce([['first', 'second', 'third'], ['alpha', 'beta', 'gamma']])
    assert result == ['first', 'alpha']

def test_format_coalesce_with_whitespace():
    """
    Test format.coalesce strips whitespace
    """
    result = wrangles.format.coalesce([['  ', 'second', 'third'], ['', 'beta', 'gamma']])
    assert result == ['second', 'beta']

### Format Remove Duplicates Tests
def test_format_remove_duplicates_list():
    """
    Test format.remove_duplicates with lists
    """
    result = wrangles.format.remove_duplicates([['apple', 'banana', 'apple', 'cherry'], ['x', 'y', 'x', 'z']])
    assert result == [['apple', 'banana', 'cherry'], ['x', 'y', 'z']]

def test_format_remove_duplicates_string():
    """
    Test format.remove_duplicates with strings
    """
    result = wrangles.format.remove_duplicates(['apple banana apple cherry', 'x y x z'])
    assert result == ['apple banana cherry', 'x y z']

def test_format_remove_duplicates_ignore_case_true():
    """
    Test format.remove_duplicates with ignore_case=True
    """
    result = wrangles.format.remove_duplicates([['Apple', 'banana', 'APPLE', 'Cherry'], ['X', 'y', 'x', 'Z']], ignore_case=True)
    assert result == [['Apple', 'banana', 'Cherry'], ['X', 'y', 'Z']]

def test_format_remove_duplicates_ignore_case_false():
    """
    Test format.remove_duplicates with ignore_case=False (case sensitive)
    """
    result = wrangles.format.remove_duplicates([['Apple', 'banana', 'APPLE', 'Cherry']], ignore_case=False)
    assert result == [['Apple', 'banana', 'APPLE', 'Cherry']]

def test_format_remove_duplicates_string_ignore_case():
    """
    Test format.remove_duplicates with strings and ignore_case=True
    """
    result = wrangles.format.remove_duplicates(['Apple banana APPLE cherry'], ignore_case=True)
    assert result == ['Apple banana cherry']

### Format Tokenize Tests
def test_format_tokenize_space():
    """
    Test format.tokenize with space method (default)
    """
    result = wrangles.format.tokenize(['hello world test', 'foo bar'])
    assert result == [['hello', 'world', 'test'], ['foo', 'bar']]

def test_format_tokenize_boundary():
    """
    Test format.tokenize with boundary method
    """
    result = wrangles.format.tokenize(["hello-world's test"], method='boundary')
    assert result == [['hello', '-', 'world', "'", 's', ' ', 'test']]

def test_format_tokenize_boundary_ignore_space():
    """
    Test format.tokenize with boundary_ignore_space method
    """
    result = wrangles.format.tokenize(["hello-world's test"], method='boundary_ignore_space')
    assert result == [['hello', '-', 'world', "'", 's', 'test']]

def test_format_tokenize_with_func():
    """
    Test format.tokenize with custom function
    """
    def custom_split(text):
        return text.split(',')
    result = wrangles.format.tokenize(['hello,world,test', 'foo,bar'], method=None, func=custom_split)
    assert result == [['hello', 'world', 'test'], ['foo', 'bar']]

def test_format_tokenize_list_input():
    """
    Test format.tokenize with list of lists
    """
    result = wrangles.format.tokenize([['hello world', 'foo bar']])
    assert result == [['hello', 'world', 'foo', 'bar']]

### Format Flatten Lists Tests
def test_format_flatten_lists_basic():
    """
    Test format.flatten_lists with nested lists
    """
    result = wrangles.format.flatten_lists([[1, 2], [3, 4]])
    assert result == [1, 2, 3, 4]

def test_format_flatten_lists_deeply_nested():
    """
    Test format.flatten_lists with deeply nested lists
    """
    result = wrangles.format.flatten_lists([1, [2, [3, [4, 5]]]])
    assert result == [1, 2, 3, 4, 5]

def test_format_flatten_lists_mixed():
    """
    Test format.flatten_lists with mixed types
    """
    result = wrangles.format.flatten_lists([1, 'two', [3, ['four', 5]]])
    assert result == [1, 'two', 3, 'four', 5]

### Select Highest Confidence Tests
def test_select_highest_confidence_basic():
    """
    Test select.highest_confidence with basic input
    """
    result = wrangles.select.highest_confidence([[['option1', 0.7], ['option2', 0.9]]])
    assert result == [['option2', 0.9]]

def test_select_highest_confidence_string_input():
    """
    Test select.highest_confidence with string confidence values
    """
    result = wrangles.select.highest_confidence([[['option1', '0.7'], ['option2', '0.9']]])
    assert result == [['option2', 0.9]]

def test_select_highest_confidence_with_separator():
    """
    Test select.highest_confidence with separator format
    """
    result = wrangles.select.highest_confidence([['option1 || 0.7', 'option2 || 0.9']])
    assert result == [['option2', 0.9]]

### Select Confidence Threshold Tests
def test_select_confidence_threshold_above():
    """
    Test select.confidence_threshold when first option exceeds threshold
    """
    result = wrangles.select.confidence_threshold(['option1 || 0.9'], ['fallback'], 0.8)
    assert result == ['option1']

def test_select_confidence_threshold_below():
    """
    Test select.confidence_threshold when first option is below threshold
    """
    result = wrangles.select.confidence_threshold(['option1 || 0.7'], ['fallback'], 0.8)
    assert result == ['fallback']

def test_select_confidence_threshold_none_first():
    """
    Test select.confidence_threshold when first option is None
    """
    result = wrangles.select.confidence_threshold([None], ['fallback'], 0.5)
    assert result == ['fallback']

def test_select_confidence_threshold_list_fallback():
    """
    Test select.confidence_threshold with list as fallback
    """
    result = wrangles.select.confidence_threshold(['option1 || 0.7'], [['fallback', 0.6]], 0.8)
    assert result == ['fallback']

### Select List Element Tests
def test_select_list_element_single_index():
    """
    Test select.list_element with single index
    """
    result = wrangles.select.list_element([['a', 'b', 'c'], ['x', 'y', 'z']], 1)
    assert result == ['b', 'y']

def test_select_list_element_slice():
    """
    Test select.list_element with slice notation
    """
    result = wrangles.select.list_element([['a', 'b', 'c', 'd'], ['w', 'x', 'y', 'z']], '1:3')
    assert result == [['b', 'c'], ['x', 'y']]

def test_select_list_element_default():
    """
    Test select.list_element with index out of range and default value
    """
    result = wrangles.select.list_element([['a', 'b'], ['x', 'y']], 5, default='N/A')
    assert result == ['N/A', 'N/A']

def test_select_list_element_negative_index():
    """
    Test select.list_element with negative index
    """
    result = wrangles.select.list_element([['a', 'b', 'c'], ['x', 'y', 'z']], -1)
    assert result == ['c', 'z']

def test_select_list_element_json_string():
    """
    Test select.list_element with JSON string input
    """
    result = wrangles.select.list_element(['["a", "b", "c"]', '["x", "y", "z"]'], 1)
    assert result == ['b', 'y']

### Select Dict Element Tests
def test_select_dict_element_single_key():
    """
    Test select.dict_element with single key
    """
    result = wrangles.select.dict_element([{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}], 'name')
    assert result == ['Alice', 'Bob']

def test_select_dict_element_multiple_keys():
    """
    Test select.dict_element with multiple keys (list)
    """
    result = wrangles.select.dict_element([{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}], ['name', 'age'])
    assert result == [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}]

def test_select_dict_element_default():
    """
    Test select.dict_element with default value for missing key
    """
    result = wrangles.select.dict_element([{'name': 'Alice'}, {'name': 'Bob'}], 'age', default='Unknown')
    assert result == ['Unknown', 'Unknown']

def test_select_dict_element_json_string():
    """
    Test select.dict_element with JSON string input
    """
    result = wrangles.select.dict_element(['{"name": "Alice", "age": 30}', '{"name": "Bob", "age": 25}'], 'name')
    assert result == ['Alice', 'Bob']

def test_select_dict_element_single_dict():
    """
    Test select.dict_element with single dict (not a list)
    """
    result = wrangles.select.dict_element({'name': 'Alice', 'age': 30}, 'name')
    assert result == 'Alice'

def test_select_dict_element_renamed_keys():
    """
    Test select.dict_element with key renaming
    """
    result = wrangles.select.dict_element([{'old_name': 'Alice'}, {'old_name': 'Bob'}], [{'old_name': 'new_name'}])
    assert result == [{'new_name': 'Alice'}, {'new_name': 'Bob'}]

### Compare Contrast Tests
def test_compare_contrast_difference():
    """
    Test compare.contrast with difference type (default)
    Returns words from all strings that are NOT in the first string
    """
    result = wrangles.compare.contrast([['apple banana', 'apple date']])
    assert result == ['date']

def test_compare_contrast_intersection():
    """
    Test compare.contrast with intersection type
    """
    result = wrangles.compare.contrast([['apple banana cherry', 'apple date cherry']], type='intersection')
    assert result == ['apple cherry']

def test_compare_contrast_case_insensitive():
    """
    Test compare.contrast with case_sensitive=False
    """
    result = wrangles.compare.contrast([['Apple Banana', 'apple Date']], type='intersection', case_sensitive=False)
    assert result == ['Apple']

def test_compare_contrast_custom_separator():
    """
    Test compare.contrast with custom separator
    """
    result = wrangles.compare.contrast([['apple,banana', 'apple,date']], type='difference', char=',')
    assert result == ['date']

def test_compare_contrast_multiple_strings():
    """
    Test compare.contrast with more than two strings
    """
    result = wrangles.compare.contrast([['apple banana', 'apple cherry', 'apple date']], type='intersection')
    assert result == ['apple']

### Compare Overlap Tests
def test_compare_overlap_basic():
    """
    Test compare.overlap with basic matching
    """
    result = wrangles.compare.overlap([['hello', 'hallo']])
    assert result == ['h*llo']

def test_compare_overlap_exact_match():
    """
    Test compare.overlap with exact match
    """
    result = wrangles.compare.overlap([['test', 'test']])
    assert result == ['test']

def test_compare_overlap_with_ratio():
    """
    Test compare.overlap with include_ratio=True
    """
    result = wrangles.compare.overlap([['hello', 'hallo']], include_ratio=True)
    assert isinstance(result[0], list) and len(result[0]) == 2
    assert result[0][1] > 0 and result[0][1] < 1

def test_compare_overlap_empty_strings():
    """
    Test compare.overlap with empty strings
    """
    result = wrangles.compare.overlap([['', '']], all_empty='both empty')
    assert result == ['both empty']

def test_compare_overlap_case_insensitive():
    """
    Test compare.overlap with case_sensitive=False
    """
    result = wrangles.compare.overlap([['HELLO', 'hello']], case_sensitive=False)
    assert result == ['hello']

def test_compare_overlap_custom_non_match():
    """
    Test compare.overlap with custom non_match_char
    """
    result = wrangles.compare.overlap([['hello', 'hallo']], non_match_char='?')
    assert result == ['h?llo']

def test_compare_overlap_exact_match_custom():
    """
    Test compare.overlap with exact_match parameter
    """
    result = wrangles.compare.overlap([['test', 'test']], exact_match='MATCH')
    assert result == ['MATCH']