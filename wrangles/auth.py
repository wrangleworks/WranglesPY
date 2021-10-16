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
    url = f"{config.keycloak.host}/auth/realms/{config.keycloak.realm}/protocol/openid-connect/token"
    payload = f"grant_type=password&username={config.api_user}&password={config.api_password}&client_id={config.keycloak.client.id}"
    headers = { 'Content-Type': 'application/x-www-form-urlencoded' }

    response = requests.post(url, headers=headers, data=payload)

    return response.json()


def get_access_token():
    """
    Check access token and refresh if necessary.
    :returns: None
    """
    global _access_token, _access_token_expiry

    if _access_token == None or _access_token_expiry < datetime.now():
        response = _refresh_access_token()
        _access_token = response['access_token']
        _access_token_expiry = datetime.now() + timedelta(0, response['expires_in'])

    return _access_token