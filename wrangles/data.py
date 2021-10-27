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
        response = _requests.get(f'{_config.api_host}/data/user/models', params=params, headers={'Authorization': f'Bearer {_auth.get_access_token()}'})
        results = response.json()
        return results