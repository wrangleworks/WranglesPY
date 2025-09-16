"""
Functions for interacting with Keycloak Server
"""
from datetime import datetime as _datetime, timedelta as _timedelta
from . import config as _config
import urllib.parse as _urlparse
import jwt as _jwt
from . import utils as _utils


_access_token = None
_access_token_expiry = _datetime.now()

refresh_token = None

def _refresh_access_token_from_refresh_token():
    """
    Call openid-connect/token route to get a refreshed access token using a refresh token and return the response.

    :param refresh_token: Keycloak refresh token
    :returns: JSON keycloak access token
    """
    if refresh_token is None:
        raise RuntimeError('Refresh token not provided')

    try:
        url = f"{_config.keycloak.host}/auth/realms/{_config.keycloak.realm}/protocol/openid-connect/token"
        data={
            "grant_type": "refresh_token",
            "client_id": _jwt.decode(refresh_token, options={"verify_signature": False})['azp'],
            "refresh_token": refresh_token,
        }

        response = _utils.backend_retries(request_type='POST', url=url, **{'data': data})

        response.raise_for_status()
    except:
        raise RuntimeError('Error refreshing access token using refresh token')

    return response

def _refresh_access_token():
    """
    Call openid-connect/token route to get a refreshed access token and return the response.
    :returns: JSON keycloak access token
    """
    if _config.api_user == None or _config.api_password == None: raise RuntimeError('User or password not provided')

    # Encode username and password
    username = _urlparse.quote(_config.api_user)
    password = _urlparse.quote(_config.api_password)

    url = f"{_config.keycloak.host}/auth/realms/{_config.keycloak.realm}/protocol/openid-connect/token"
    payload = f"grant_type=password&username={username}&password={password}&client_id={_config.keycloak.client_id}"
    headers = { 'Content-Type': 'application/x-www-form-urlencoded' }

    response = _utils.backend_retries(request_type='POST', url=url, **{'data': payload, 'headers': headers})

    return response


def get_access_token():
    """
    Check access token and refresh if necessary.
    :returns: None
    """
    global _access_token, _access_token_expiry

    if _access_token == None or _access_token_expiry < _datetime.now():
        # If refresh token is provided use it to get a new access token
        # Otherwise use username and password
        if refresh_token:
            response = _refresh_access_token_from_refresh_token()
        else:
            response = _refresh_access_token()

        if response.status_code == 200:
            _access_token = response.json()['access_token']
        elif response.status_code == 401:
            raise RuntimeError('Invalid login details provided')
        else:
            raise RuntimeError('Unexpected error when authenticating')

        _access_token_expiry = _datetime.now() + _timedelta(0, response.json()['expires_in'] - 30)

    return _access_token
