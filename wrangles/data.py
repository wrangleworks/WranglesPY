"""
Functions for interacting with user and app data
"""
import requests as _requests
from . import config as _config
from . import auth as _auth


class user():
    """
    Get user data
    """

    def models(type: str = None) -> list:
        """
        Get a list of the user's models

        :param type: (Optional) Specify the type of models. 'classify' or 'extract'
        :returns: List of user's model, each a dict of properties.
        """
        params = {}
        if type: params['type'] = type
        response = _requests.get(f'{_config.api_host}/user/models', params=params, headers={'Authorization': f'Bearer {_auth.get_access_token()}'})
        results = response.json()
        return results


def model(id: str):
    """
    Get a model definition
    :param id: model ID
    :returns: Dict of model properties
    """
    params = {'id': id}
    response = _requests.get(f'{_config.api_host}/model/metadata', params=params, headers={'Authorization': f'Bearer {_auth.get_access_token()}'})
    results = response.json()
    return results


def model_data(id: str, purpose: str) -> list:
    """
    Get the training data for a model

    :param id: Model ID
    :param purpose: classify, extract, standardize
    :return: Model data as a list of lists
    """
    params = {'model_id': id, 'type': purpose}
    response = _requests.get(f'{_config.api_host}/model/content', params=params, headers={'Authorization': f'Bearer {_auth.get_access_token()}'})
    if response.status_code == 200:
        results = response.json()
    elif response.status_code == 400:
        raise RuntimeError('Not able to validate access, check wrangle to ensure accessibility')

    return results['Data']