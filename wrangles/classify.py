"""
Functions to classify information.
"""

from . import config as _config
from . import data as _data
from . import batching as _batching
from typing import Union


def classify(input: Union[str, list], model_id: str) -> Union[str, list]:
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
    
    # If the Model Id is not appropriate, raise error (Maybe more specific?)
    if isinstance(model_id, dict) or len(model_id.split('-')) != 3:
        raise ValueError('Incorrect model_id. May be missing "${ }" around value')
        
    # Checking to see if GUID format is correct
    if [len(x) for x in model_id.split('-')] != [8, 4, 4]:
        raise ValueError('Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX')
       
    url = f'{_config.api_host}/wrangles/classify'
    params = {'responseFormat': 'array', 'model_id': model_id}
    model_properties = _data.model(model_id)
    batch_size = model_properties['batch_size'] or 5000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]

    return results