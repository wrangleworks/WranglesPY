from . import config as _config
from . import data as _data
from . import batching as _batching
from typing import Union

def standardize(input: Union[str, list], model_id: str) -> list:
    """
    Extract entities using a custom model.

    :param input: A string or list of strings to search for information.
    :param model_id: The model to be used to search for information.
    :return: A list of entities found.
    """
    if isinstance(input, str): 
        json_data = [input]
    elif isinstance(input, list):
        json_data = input
    else:
        raise TypeError('Invalid input data provided. The input must be either a string or a list of strings.')

    url = f'{_config.api_host}/wrangles/standardize'
    params = {'responseFormat': 'array', 'model_id': model_id}
    model_properties = _data.model(model_id)
    batch_size = model_properties['batch_size'] or 10000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]
    
    return results

