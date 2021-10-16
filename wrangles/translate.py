"""
Functions to translate text
"""

import requests
from . import config as _config
from . import auth
from typing import Union

def translate(input: Union[str, list], target_language: str) -> list:
    """
    Translate text

    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    response = requests.post(f'{_config.api_host}/wrangles/translate', params={'responseFormat':'array', 'targetLanguage': target_language}, headers={'Authorization': f'Bearer {auth.get_access_token()}'}, json=json_data)
    results = response.json()

    if isinstance(input, str): results = results[0]

    return results