"""
Functions to extract information from unstructured text.
"""

from . import config as _config
from . import data as _data
from . import batching as _batching
from typing import Union as _Union


def address(input: _Union[str, list], dataType: str) -> list:
    """
    Extract geographical information from unstructured text such as streets, cities or countries.

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

    
def attributes(input: _Union[str, list], responseContent: str = 'span', type: str = None) -> _Union[dict, list]:
    """
    Extract numeric attributes from unstructured text such as lengths or voltages.

    >>> wrangles.extract.attributes('tape 25m')
    {'length': ['25m']}

    :param input: Input string or list of strings to be searched for attributes
    :param responseContent: (Optional, default Span) 'span' or 'object'. If span, returns original text, if object returns an object of value and dimension.
    :param type: (Optional) Specify which types of attributes to find. If omitted, a dict of all attributes types is returned
    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    url = f'{_config.api_host}/wrangles/extract/attributes'
    params = {'responseFormat':'array', 'responseContent': responseContent}
    if type is not None: params['attributeType'] = type

    batch_size = 1000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)
    
    if isinstance(input, str): results = results[0]

    return results


def codes(input: _Union[str, list]) -> list:
    """
    Extract alphanumeric codes from unstructured text.

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

    url = f'{_config.api_host}/wrangles/extract/custom'
    params = {'responseFormat': 'array', 'model_id': model_id}
    model_properties = _data.model(model_id)
    batch_size = model_properties['batch_size'] or 10000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]
    
    return results


def geography(input: _Union[str, list], dataType: str) -> list:
    """
    Extract geographical information from unstructured text such as streets, cities or countries.

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


def properties(input: _Union[str, list], type: str = None) -> _Union[dict, list]:
    """
    Extract categorical properties from unstructured text such as colours or materials.

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
    
    return results



# SUPER MARIO
from boltons.setutils import IndexedSet
def diff(input):
    """
    input is going to be list of lists, where each list contains tokens
    diff subtracts the tokens in 2nd list from the first using set ops
    All inputs are "lowered" before difference operation
    """
    results = []
    for row in input:
        # target = row[0].lower()
        target = [x.lower() for x in row[0]]
        # remove = row[1].lower()
        remove = [x.lower() for x in row[1]]
        result = list(IndexedSet(target).difference(remove))
        results.append([x.lower() for x in result])
    
    return results