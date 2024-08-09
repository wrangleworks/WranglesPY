"""
Functions to classify information.
"""
from typing import Union as _Union
from . import config as _config
from . import data as _data
from . import batching as _batching


def classify(
    input: _Union[str, list],
    model_id: str,
    **kwargs
) -> _Union[str, list]:
    """
    Predict which category an input belongs to.
    Requires WrangleWorks Account and Subscription.

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
    
    # If the Model Id is not appropriate, raise error (Only for Recipes)
    if isinstance(model_id, dict):
        raise ValueError('Incorrect model_id type.\nIf using Recipe, may be missing "${ }" around value')
        
    # Checking to see if GUID format is correct
    if [len(x) for x in model_id.split('-')] != [8, 4, 4]:
        raise ValueError('Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX')
       
    url = f'{_config.api_host}/wrangles/classify'
    params = {'responseFormat': 'array', 'model_id': model_id, **kwargs}
    model_properties = _data.model(model_id)
    # If model_id format is correct but no mode_id exists
    if model_properties.get('message', None) == 'error': raise ValueError('Incorrect model_id.\nmodel_id may be wrong or does not exists')
    batch_size = model_properties['batch_size'] or 5000
    
    
    # Using model_id in wrong function
    purpose = model_properties['purpose']
    if purpose != 'classify':
        raise ValueError(f'Using {purpose} model_id {model_id} in a classify function.')

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]

    return results
