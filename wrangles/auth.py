"""
Functions for interacting with Keycloak Server
"""
from datetime import datetime as _datetime, timedelta as _timedelta
import requests as _requests
from . import config as _config
import urllib.parse as _urlparse
import time as _time


_access_token = None
_access_token_expiry = _datetime.now()


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

    # Query token. Retry up to 3 times on unexpected failures.
    retries = 3
    backoff_time = 1
    while (retries > 0):
        try:
            response = _requests.post(url, headers=headers, data=payload, timeout=5)
        except Exception as e:
            response = None
            # If we've exhausted retries, raise the error
            if (retries-1) <= 0:
                raise e

        if response:
            if response.ok:
                break
            if response.status_code in [401, 403]:
                raise RuntimeError('Invalid login details provided')

        _time.sleep(backoff_time)
        retries -= 1
        backoff_time *= 2

    return response


def get_access_token():
    """
    Check access token and refresh if necessary.
    :returns: None
    """
    global _access_token, _access_token_expiry

    if _access_token == None or _access_token_expiry < _datetime.now():
        response = _refresh_access_token()
        if response and response.ok:
            _access_token = response.json()['access_token']
            _access_token_expiry = _datetime.now() + _timedelta(0, response.json()['expires_in'] - 30)
        else:
            raise RuntimeError('Unexpected error when authenticating')

    return _access_token
