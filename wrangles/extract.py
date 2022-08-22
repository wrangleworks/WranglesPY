"""
Functions to extract information from unstructured text.
"""

from . import config as _config
from . import data as _data
from . import batching as _batching
from typing import Union as _Union

from .format import tokenize


def address(input: _Union[str, list], dataType: str) -> list:
    """
    Extract geographical information from unstructured text such as streets, cities or countries.
    Requires WrangleWorks Account.

    e.g. '1100 Congress Ave, Austin, TX 78701, United States' -> '1100 Congress Ave'

    :param input: A string or list of strings with addresses to search for information.
    :param dataType: The type of information to return. 'streets', 'cities', 'regions' or 'countries'
    :return: A list of any results found.
    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    url = f'{_config.api_host}/wrangles/extract/address'
    params = {'responseFormat':'array', 'dataType':dataType }
    batch_size = 10000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]
    
    return results

    
def attributes(input: _Union[str, list], responseContent: str = 'span', type: str = None, desiredUnit: str = None, bound: str = 'mid') -> _Union[dict, list]:
    """
    Extract numeric attributes from unstructured text such as lengths or voltages.
    Requires WrangleWorks Account.

    >>> wrangles.extract.attributes('tape 25m')
    {'length': ['25m']}

    :param input: Input string or list of strings to be searched for attributes
    :param responseContent: (Optional, default Span) 'span' or 'object'. If span, returns original text, if object returns an object of value and dimension.
    :param type: (Optional) Specify which types of attributes to find. If omitted, a dict of all attributes types is returned
    :param bound: (Optional, default mid). When returning an object, if the input is a range. e.g. 10-20mm, set the value to return. min, mid or max.
    """
    # Check that attribute_type is correct
    attributes_type_list = ["angle","area","current","force","length","power","pressure","electric potential","volume","mass"]
    if type not in attributes_type_list: raise ValueError(f'"{type}" is not a valid attribute_type value. Be sure to use lowercase')
    
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    url = f'{_config.api_host}/wrangles/extract/attributes'
    params = {'responseFormat':'array', 'responseContent': responseContent}
    if type: params['attributeType'] = type
    if desiredUnit: params['desiredUnit'] = desiredUnit
    
    if bound in ['min', 'mid', 'max']:
        params['bound'] = bound
    else:
        raise ValueError('Invalid boundary setting. min, mid or max permitted.')
    
    batch_size = 1000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)
    
    if isinstance(input, str): results = results[0]

    return results


def codes(input: _Union[str, list]) -> list:
    """
    Extract alphanumeric codes from unstructured text.
    Requires WrangleWorks Account.

    e.g. 'Something ABC123ZZ something' -> 'ABC123ZZ'

    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    url = f'{_config.api_host}/wrangles/extract/codes'
    params = {'responseFormat': 'array'}
    batch_size = 10000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]
    
    return results


def custom(input: _Union[str, list], model_id: str) -> list:
    """
    Extract entities using a custom model.
    Requires WrangleWorks Account and Subscription.

    :param input: A string or list of strings to searched for information.
    :param model_id: The model to be used to search for information.
    :return: A list of entities found.
    """
    if isinstance(input, str): 
        json_data = [input]
    elif isinstance(input, list):
        json_data = input
    else:
        raise TypeError('Invalid input data provided. The input must be either a string or a list of strings.')
        
    # If the Model Id is not appropriate, raise error (Only for Recipes)
    if isinstance(model_id, dict):
        raise ValueError('Incorrect model_id type.\nIf using Recipe, may be missing "${ }" around value')
        
    # Checking to see if GUID format is correct
    if [len(x) for x in model_id.split('-')] != [8, 4, 4]:
        raise ValueError('Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX')

    url = f'{_config.api_host}/wrangles/extract/custom'
    params = {'responseFormat': 'array', 'model_id': model_id}
    model_properties = _data.model(model_id)
    # If model_id format is correct but no mode_id exists
    if model_properties.get('message', None) == 'error': raise ValueError('Incorrect model_id.\nmodel_id may be wrong or does not exists')
    batch_size = model_properties['batch_size'] or 10000
    
    # Using model_id in wrong function
    purpose = model_properties['purpose']
    if purpose != 'extract':
        raise ValueError(f'Using {purpose} model_id in an extract function.')
    
    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]
    
    return results


def geography(input: _Union[str, list], dataType: str) -> list:
    """
    Extract geographical information from unstructured text such as streets, cities or countries.
    Requires WrangleWorks Account.

    e.g. '1100 Congress Ave, Austin, TX 78701, United States' -> '1100 Congress Ave'

    :param input: A string or list of strings with addresses to search for information.
    :param dataType: The type of information to return. 'streets', 'cities', 'regions' or 'countries'
    :return: A list of any results found.
    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    url = f'{_config.api_host}/wrangles/extract/geography'
    params = {'responseFormat': 'array', 'dataType': dataType}
    batch_size = 10000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]
    
    return results


def html(input: _Union[str, list], dataType: str) -> list:
    """
    Extract specific html elements from strings containing html.
    Requires WrangleWorks Account.

    :param input: A string or list of strings with addresses to search for information.
    :param dataType: The type of information to return. 'text' or 'links'
    :return: A list of any results found.
    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    url = f'{_config.api_host}/wrangles/extract/html'
    params = {'responseFormat': 'array', 'dataType': dataType}
    batch_size = 10000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]
    
    return results

    
def properties(input: _Union[str, list], type: str = None, return_data_type: str = 'list') -> _Union[dict, list]:
    """
    Extract categorical properties from unstructured text such as colours or materials.
    Requires WrangleWorks Account.

    >>> wrangles.extract.properties('The Green Mile')
    {'Colours': ['Green']}

    :param input: A string or list of strings to be searched for properties
    :param type: (Optional) The specific type of property to search for. If omitted an objected with all results will be returned.
    :return: A single or list with the extracted properties. Each extracted property may be a dict or list depending on settings.
    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    url = f'{_config.api_host}/wrangles/extract/properties'
    params = {'responseFormat':'array'}
    if type is not None: params['dataType'] = type
    batch_size = 10000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]
    
    if return_data_type == 'string': results = [', '.join(x) if x != [] else '' for x in results]
    
    return results



# SUPER MARIO
def remove_words(input, to_remove, tokenize_to_remove, ignore_case):
    """
    Remove all the elements that occur in one list from another.
    
    :param input: both input and to_remove can be a string or a list or multiple lists. Lowered for precision
    :param output: a string of remaining words
    """
    
    # Tokenize to_remove values
    if tokenize_to_remove == True:
        to_remove = [tokenize(to_remove[x]) for x in range(len(to_remove))]
            
    # If Input is a string
    if isinstance(input[0], str):
        input = [x.split() for x in input]
    
    if ignore_case == True:
        """
        Takes inputs and converts to lower
        """
    
        results = []
        for item in range(len(input)):
            temp = []
            to_remove_lower = [item.lower() for sublist in to_remove[item] for item in sublist]
            input_lower = [x.lower() for x  in input[item]]
            temp = filter(None, [x.title() for x in input_lower if x not in to_remove_lower])
            results.append(' '.join(temp))
            
    else:
        """
        Takes inputs as is (raw)
        """
        results = []
        for item in range(len(input)):
            temp = []
            to_remove_lower = [item for sublist in to_remove[item] for item in sublist]
            input_lower = [x for x  in input[item]]
            temp = filter(None, [x for x in input_lower if x not in to_remove_lower])
            results.append(' '.join(temp))

    return results
    
    