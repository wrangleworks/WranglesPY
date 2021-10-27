"""
Functions to classify information.
"""

import requests as _requests
from . import config as _config
from . import auth as _auth
from typing import Union


def classify(input: Union[str, list[str]], model_id: str) -> Union[str, list]:
    """
    Predict which category an input belongs to.

    :param input: A string or list of strings to be classified.
    :param model_id: The model to be used to predict the class.
    :return: A string or list of prediction corresponding to the input.
    """
    if isinstance(input, str): 
        json_data = [input]
    elif isinstance(input, list):
        json_data = input
    else:
        raise TypeError('Invalid input data provided. The input must be either a string or a list of strings.')

    response = _requests.post(f'{_config.api_host}/classify', params={'responseFormat':'array', 'model_id': model_id}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=json_data)
    results = response.json()

    if isinstance(input, str): results = results[0]

    return results