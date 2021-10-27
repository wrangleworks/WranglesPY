"""
Functions for interacting with Keycloak Server
"""
import requests
from datetime import datetime, timedelta
from . import config


_access_token = None
_access_token_expiry = datetime.now()


def _refresh_access_token():
    """
    Call openid-connect/token route to get a refreshed access token and return the response.
    :returns: JSON keycloak access token
    """
    if config.api_user == None or config.api_password == None: raise RuntimeError('User or password not provided')

    url = f"{config.keycloak.host}/auth/realms/{config.keycloak.realm}/protocol/openid-connect/token"
    payload = f"grant_type=password&username={config.api_user}&password={config.api_password}&client_id={config.keycloak.client_id}"
    headers = { 'Content-Type': 'application/x-www-form-urlencoded' }

    response = requests.post(url, headers=headers, data=payload)

    return response


def get_access_token():
    """
    Check access token and refresh if necessary.
    :returns: None
    """
    global _access_token, _access_token_expiry

    if _access_token == None or _access_token_expiry < datetime.now():
        response = _refresh_access_token()
        if response.status_code == 200:
            _access_token = response.json()['access_token']
        elif response.status_code == 401:
            raise RuntimeError('Invalid login details provided')
        else:
            raise RuntimeError('Unexpected error when authenticating')

        _access_token_expiry = datetime.now() + timedelta(0, response.json()['expires_in'])

    return _access_token