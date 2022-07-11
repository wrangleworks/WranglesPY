"""
Functions to translate text
"""

from . import config as _config
from . import batching as _batching
from typing import Union as _Union


def translate(input: _Union[str, list], target_language: str, source_language: str = 'AUTO', case: str = None) -> _Union[str, list]:
    """
    Translate text
    Requires WrangleWorks Account and DeepL API Key (A free account for up to 500,000 characters per month is available)

    :param input: A string or list of strings to be translated.
    :param target_language: A two letter code for the target language. For codes see: https://www.deepl.com/docs-api/translating-text/
    :param source_language: (Optional) A two letter code for the source language. Defaults to auto.
    :params case: (Optional) Allow changing the case of the input prior to translation. lower, upper or title
    :return: A translated string or list of strings corresponding to the input 
    """
    if isinstance(input, str): 
        json_data = [input]
    elif isinstance(input, list):
        json_data = input
    else:
        raise TypeError('Invalid input data provided. The input must be either a string or a list of strings.')

    if case == 'lower':
        json_data = [val.lower() for val in json_data]
    elif case == 'upper':
        json_data = [val.upper() for val in json_data]
    elif case == 'title':
        json_data = [val.title() for val in json_data]

    url = f'{_config.api_host}/wrangles/translate'
    params = {'responseFormat':'array', 'targetLanguage': target_language, 'sourceLanguage': source_language}
    batch_size = 60

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]

    return results