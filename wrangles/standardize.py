"""
Functions to standardize data
"""

from typing import Union as _Union
from . import config as _config
from . import data as _data
from . import batching as _batching
import warnings as _warnings


def attributes(
    input: _Union[str, list],
    type: str,
    desiredUnit: str = None,
    **kwargs
) -> list:
    """
    Standardize all attributes or a specific attribute type in a string.
    Requires WrangleWorks Account and Subscription.

    :param input: A string or list of strings to be standardized.
    :param type: (Optional) The attribute type to be standardized. Default is all.
    :param removeAttributes: (Optional) Remove attributes from the string. Default is False.
    """
    if isinstance(input, str):
        json_data = [input]
    else:
        json_data = input

    url = f'{_config.api_host}/wrangles/standardize/attributes'
    params = {
        'responseFormat': 'array',
        **kwargs
    }
    if type: params['attributeType'] = type
    if desiredUnit: params['desiredUnit'] = desiredUnit    

    batch_size = 1000
    results = _batching.batch_api_calls(url, params, json_data, batch_size)
    if isinstance(input, str): results = results[0]
    return results


def custom(
    input: _Union[str, list],
    model_id: str,
    case_sensitive: bool = False,
    **kwargs
) -> list:
    """
    Standardize text - Standardize Wrangles can replace words with alternatives, 
    in addition to using regex patterns for more complex replacements.
    Requires WrangleWorks Account and Subscription.

    :param input: A string or list of strings to be standardized.
    :param model_id: The model to be used.
    :param case_sensitive: Allows setting the model to be case sensitive
    :return: A string or list with the updated text.
    """
    if isinstance(input, str): 
        json_data = [input]
    elif isinstance(input, list):
        json_data = input
    else:
        raise TypeError('Invalid input data provided. The input must be either a string or a list of strings.')
        
    # If the Model Id is not appropriate, raise error (Maybe more specific?)
    if isinstance(model_id, dict) or len(model_id.split('-')) != 3:
        raise ValueError('Incorrect model_id. May be missing "${ }" around value')
        
    # Checking to see if GUID format is correct
    if [len(x) for x in model_id.split('-')] != [8, 4, 4]:
        raise ValueError('Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX')

    url = f'{_config.api_host}/wrangles/standardize'
    params = {
        'responseFormat': 'array',
        'model_id': model_id,
        'caseSensitive': case_sensitive,
        **kwargs
    }
    model_properties = _data.model(model_id)
    # If model_id format is correct but no mode_id exists
    if model_properties.get('message', None) == 'error': raise ValueError('Incorrect model_id.\nmodel_id may be wrong or does not exists')
    batch_size = model_properties['batch_size'] or 10000
    
    # Using model_id in wrong function
    purpose = model_properties['purpose']
    if purpose != 'standardize':
        raise ValueError(f'Using {purpose} model_id {model_id} in a standardize function.')

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]
    
    return results


####################################################################################################
# For legacy purposes, to be removed in future versions
####################################################################################################
def standardize(
    input: _Union[str, list],
    model_id: str,
    case_sensitive: bool = False,
    **kwargs
) -> list:
    """
    Deprecation Warning: if using using 'wrangles.standardize' use 'wrangles.standardize.custom' instead.
    """
    _warnings.warn(
        "'wrangles.standardize' is deprecated and slated for removal in a future version. Use 'wrangles.standardize.custom' instead.",
        DeprecationWarning
    )

    if isinstance(input, str): 
        json_data = [input]
    elif isinstance(input, list):
        json_data = input
    else:
        raise TypeError('Invalid input data provided. The input must be either a string or a list of strings.')
        
    # If the Model Id is not appropriate, raise error (Maybe more specific?)
    if isinstance(model_id, dict) or len(model_id.split('-')) != 3:
        raise ValueError('Incorrect model_id. May be missing "${ }" around value')
        
    # Checking to see if GUID format is correct
    if [len(x) for x in model_id.split('-')] != [8, 4, 4]:
        raise ValueError('Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX')

    url = f'{_config.api_host}/wrangles/standardize'
    params = {
        'responseFormat': 'array',
        'model_id': model_id,
        'caseSensitive': case_sensitive,
        **kwargs
    }
    model_properties = _data.model(model_id)
    # If model_id format is correct but no mode_id exists
    if model_properties.get('message', None) == 'error': raise ValueError('Incorrect model_id.\nmodel_id may be wrong or does not exists')
    batch_size = model_properties['batch_size'] or 10000
    
    # Using model_id in wrong function
    purpose = model_properties['purpose']
    if purpose != 'standardize':
        raise ValueError(f'Using {purpose} model_id {model_id} in a standardize function.')

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]
    
    return results