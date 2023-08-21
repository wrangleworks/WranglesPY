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
    response = _requests.get(
        f'{_config.api_host}/model/metadata',
        params = {'id': id},
        headers = {'Authorization': f'Bearer {_auth.get_access_token()}'}
    )
    if response.ok:
        return response.json()
    elif response.status_code in [401, 403]:
        raise RuntimeError(f'Access denied to model {id}')
    else:
        raise RuntimeError(f'Something went wrong trying to access model {id}')


def model_content(id: str) -> list:
    """
    Get the training data for a model

    :param id: Model ID
    :return: Model data with Settings, Columns and Data as a 2D array
    """
    response = _requests.get(
        f'{_config.api_host}/model/content',
        params = {'model_id': id},
        headers = {'Authorization': f'Bearer {_auth.get_access_token()}'}
    )
    if response.ok:
        return response.json()
    elif response.status_code in [401, 403]:
        raise RuntimeError(f'Access denied to model {id}')
    else:
        raise RuntimeError(f'Something went wrong trying to access model {id}')