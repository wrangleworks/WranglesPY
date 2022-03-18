"""
Functions to extract information from unstructured text.
"""

import requests as _requests
from . import config as _config
from . import auth as _auth
from typing import Union


def address(input: Union[str, list], dataType: str) -> list:
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

    response = _requests.post(f'{_config.api_host}/wrangles/extract/address', params={'responseFormat':'array', 'dataType':dataType }, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=json_data)
    results = response.json()

    if isinstance(input, str): results = results[0]
    
    return results

    
def attributes(input: Union[str, list], responseContent: str = 'span') -> list:
    """
    Extract numeric attributes from unstructured text such as lengths or voltages.

    e.g. 'Mystery machine 220V' -> '220V'

    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    response = _requests.post(f'{_config.api_host}/wrangles/extract/attributes', params={'responseFormat':'array', 'responseContent': responseContent}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=json_data)
    results = response.json()
    
    if isinstance(input, str): results = results[0]

    return results


def codes(input: Union[str, list]) -> list:
    """
    Extract alphanumeric codes from unstructured text.

    e.g. 'Something ABC123ZZ something' -> 'ABC123ZZ'

    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    response = _requests.post(f'{_config.api_host}/wrangles/extract/codes', params={'responseFormat':'array'}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=json_data)
    results = response.json()

    if isinstance(input, str): results = results[0]
    
    return results


def custom(input: Union[str, list], model_id: str) -> list:
    """
    Extract entities using a custom model.

    :param input: A string or list of strings to search for information.
    :param model_id: The model to be used to search for information.
    :return: A list of entities found.
    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    response = _requests.post(f'{_config.api_host}/wrangles/extract/custom', params={'responseFormat':'array', 'model_id': model_id }, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=json_data)
    results = response.json()

    if isinstance(input, str): results = results[0]
    
    return results


def geography(input: Union[str, list], dataType: str) -> list:
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

    response = _requests.post(f'{_config.api_host}/wrangles/extract/geography', params={'responseFormat':'array', 'dataType':dataType }, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=json_data)
    results = response.json()

    if isinstance(input, str): results = results[0]
    
    return results


def properties(input: Union[str, list]) -> list:
    """
    Extract categorical properties from unstructured text such as colours or materials.

    e.g. 'The Green Mile' -> 'Green'

    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    response = _requests.post(f'{_config.api_host}/wrangles/extract/properties', params={'responseFormat':'array'}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=json_data)
    results = response.json()

    if isinstance(input, str): results = results[0]
    
    return results
