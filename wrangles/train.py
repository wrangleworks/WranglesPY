"""
Train new models
"""

import requests as _requests
from . import config as _config
from . import auth as _auth

class train():
    """
    Train new models
    """

    def classify(training_data: list, name: str):
        """
        Train a classification model. This can predict the category of a text input.
        
        :param training_data: paired list of examples and labels.
        :param name: The name of the new model.
        """
        # Validate input here
        response = _requests.post(f'{_config.api_host}/data/user/model/train', params={'type':'classify', 'name': name}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=training_data)
        return response

    def extract(training_data: list, name: str):
        """
        Train an extraction model. This can extract custom entities from the input.
        
        :param training_data: paired list of entities to find and optional standard representation of that entitiy.
        :param name: The name of the new model.
        """
        # Validate input here
        response = _requests.post(f'{_config.api_host}/data/user/model/train', params={'type':'extract', 'name': name}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=training_data)
        return response