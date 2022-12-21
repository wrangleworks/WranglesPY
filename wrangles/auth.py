"""
Functions for interacting with Keycloak Server
"""
from datetime import datetime as _datetime, timedelta as _timedelta
import requests as _requests
from . import config as _config


_access_token = None
_access_token_expiry = _datetime.now()


def _refresh_access_token():
    """
    Call openid-connect/token route to get a refreshed access token and return the response.
    :returns: JSON keycloak access token
    """
    if _config.api_user == None or _config.api_password == None: raise RuntimeError('User or password not provided')

    url = f"{_config.keycloak.host}/auth/realms/{_config.keycloak.realm}/protocol/openid-connect/token"
    payload = f"grant_type=password&username={_config.api_user}&password={_config.api_password}&client_id={_config.keycloak.client_id}"
    headers = { 'Content-Type': 'application/x-www-form-urlencoded' }

    response = _requests.post(url, headers=headers, data=payload)

    return response


def get_access_token():
    """
    Check access token and refresh if necessary.
    :returns: None
    """
    global _access_token, _access_token_expiry

    if _access_token == None or _access_token_expiry < _datetime.now():
        response = _refresh_access_token()
        if response.status_code == 200:
            _access_token = response.json()['access_token']
        elif response.status_code == 401:
            raise RuntimeError('Invalid login details provided')
        else:
            raise RuntimeError('Unexpected error when authenticating')

        _access_token_expiry = _datetime.now() + _timedelta(0, response.json()['expires_in'] - 30)

    return _access_token
