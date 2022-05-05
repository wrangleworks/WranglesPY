"""
Functions to translate text
"""

from . import config as _config
from . import batching as _batching
from typing import Union


def translate(input: Union[str, list], target_language: str, source_language: str = 'AUTO') -> list:
    """
    Translate text

    :param input: A string or list of strings to be translated.
    :param target_language: A two letter code for the target language. For codes see: https://www.deepl.com/docs-api/translating-text/
    :param source_language: (Optional) A two letter code for the source language. Defaults to auto.
    """
    if isinstance(input, str): 
        json_data = [input]
    elif isinstance(input, list):
        json_data = input
    else:
        raise TypeError('Invalid input data provided. The input must be either a string or a list of strings.')

    url = f'{_config.api_host}/wrangles/translate'
    params = {'responseFormat':'array', 'targetLanguage': target_language, 'sourceLanguage': source_language}
    batch_size = 60

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]

    return results