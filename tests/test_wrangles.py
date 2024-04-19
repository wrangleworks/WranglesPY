import pytest
import wrangles
import pandas as pd
from wrangles.train import train


# Classify
def test_classify():
    result = wrangles.classify('ball bearing', '24ac9037-ecab-4030')
    assert result.split(' || ')[0] == 'Bearings'

def test_classify_list():
    result = wrangles.classify(['ball bearing'], '24ac9037-ecab-4030')
    assert result[0].split(' || ')[0] == 'Bearings'

def test_classify_large_list():
    input = ['ball bearing' for _ in range(25000)]
    results = wrangles.classify(input, '24ac9037-ecab-4030')
    assert len(results) == 25000 and results[0].split(' || ')[0] == 'Bearings'
  
##  Classify Raise Errors
# Invalid input data provided
def test_classify_error_1():
    with pytest.raises(TypeError) as info:
        raise wrangles.classify({'ball bearing'}, '24ac9037-ecab-4030')
    assert info.typename == 'TypeError' and info.value.args[0] == 'Invalid input data provided. The input must be either a string or a list of strings.'
    
# Incorrect or missing values in model_id. format is XXXXXXXX-XXXX-XXXX'
def test_classify_error_2():
    with pytest.raises(ValueError) as info:
        raise wrangles.classify('ball bearing', '24ac9037-ecab-403')
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

def test_custom_large_list():
    input = ['test skf test' for _ in range(25000)]
    results = wrangles.extract.custom(input, '4786921f-342f-4a0c')
    assert len(results) == 25000 and results[0][0] == 'SKF'

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
        raise wrangles.extract.custom({'ball bearing'}, 'fce592c9-26f5-4fd7')
    assert info.typename == 'TypeError' and info.value.args[0] == 'Invalid input data provided. The input must be either a string or a list of strings.'
    
# Incorrect or missing values in model_id. format is XXXXXXXX-XXXX-XXXX'
def test_extract_error_2():
    with pytest.raises(ValueError) as info:
        raise wrangles.extract.custom('ball bearing', 'fce592c9-26f5-4fd')
    assert info.typename == 'ValueError' and info.value.args[0] == 'Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX'

# Wrong Model id on wrong function name
def test_extract_error_3():
    with pytest.raises(ValueError) as info:
        raise wrangles.extract.custom('ball bearing', '24ac9037-ecab-4030')
    assert info.typename == 'ValueError' and info.value.args[0] == f'Using classify model_id 24ac9037-ecab-4030 in an extract function.'

def test_extract_html_str():
    result = wrangles.extract.html('<a href="https://www.wrangleworks.com/">Wrangle Works!</a>', dataType='text')
    assert result == 'Wrangle Works!'
# Translate
def test_translate():
    result = wrangles.translate('My name is Chris', 'DE')
    assert result == 'Mein Name ist Chris'

def test_translate_list():
    result = wrangles.translate(['My name is Chris'], 'DE')
    assert result[0] == 'Mein Name ist Chris'
    
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
    
# If input is a list, check to make sure that all sublists are length of 2
# Headers not included ['Find', 'Replace']
def test_standardize_train_1(mocker):
    data = [
        ['Rice', 'Arroz', ''],
        ['Wheat', 'Trigo', '']
    ]
    config = {
        'training_data': data,
        'name': 'test_standardize',
        'model_id': '1234567890',
    }
    m = mocker.patch("requests.post")
    m.return_value = temp_classify
    m2 = mocker.patch("wrangles.auth.get_access_token")
    m2.return_value = 'None'
    test = train.standardize(**config)
    assert test.status_code == 202
    
# If input is a list, check to make sure that all sublists are length of 2
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

# Input of lists of lists
# Headers not included ['Example', 'Category']
def test_classify_train_2(mocker):
    data = [
        ['Rice', 'Grain', ''],
        ['Wheat', 'Grain', '']
    ]
    config = {
        'training_data': data,
        'name': 'test_classify',
        'model_id': '1234567890',
    }
    m = mocker.patch("requests.post")
    m.return_value = temp_classify
    m2 = mocker.patch("wrangles.auth.get_access_token")
    m2.return_value = 'None'
    test = train.classify(**config)
    assert test.status_code == 202


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
    
# Input of lists of lists
# Headers not included ['Entity to Find', 'Variation (Optional)']
def test_extract_train_2(mocker):
    data = [
        ['Television', 'TV', ''],
        ['Computer', 'Comp', '']
    ]
    m = mocker.patch("requests.post")
    m.return_value = temp_extract
    m2 = mocker.patch("wrangles.auth.get_access_token")
    m2.return_value = 'None'
    config = {
        'training_data': data,
        'name': 'test_extract'
    }
    test = train.extract(**config)
    assert test.status_code == 202
    
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