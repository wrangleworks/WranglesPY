import pytest
import wrangles
import pandas as pd
import os
import requests


# Testing Auth
from wrangles.auth import get_access_token

class temp_response():
    status_code = 401

# get_access_token using invalid credentials error
def test_get_access_token_error1(mocker):
    m = mocker.patch("wrangles.auth._refresh_access_token")
    m.return_value = temp_response
    with pytest.raises(RuntimeError) as info:
        raise get_access_token()
    assert type(info.value).__name__ == 'RuntimeError' and info.value.args[0] == 'Invalid login details provided'
    
# get_access_token using Unexpected error
class temp_unexpected_error():
    status_code = 500

def test_get_access_token_error2(mocker):
    m = mocker.patch("wrangles.auth._refresh_access_token")
    m.return_value = temp_unexpected_error
    m2 = mocker.patch("wrangles.auth.get_access_token")
    m2.return_value = 'None'
    with pytest.raises(RuntimeError) as info:
        raise get_access_token()
    assert type(info.value).__name__ == 'RuntimeError' and info.value.args[0] == 'Unexpected error when authenticating'
    
# Testing Batching
from wrangles.batching import batch_api_calls

# Getting Status code errors - 500 Internal server Error
headers = {'Authorization': f'Bearer 3141'}
class temp_response_batch_calls():
    status_code = 500
    reason = 'Internal Server Error.'
    text = 'An internal error has occured.'
    

# Get user config
def test_user_config_credentials():
    from wrangles.config import authenticate
    user = os.getenv('WRANGLES_USER','...')
    password = os.getenv('WRANGLES_PASSWORD', '...')
    assert authenticate(user, password) == None


def test_refresh_token_error():
    """
    Check error is raised when invalid refresh token is used.
    """
    wrangles.auth.refresh_token = "should fail"

    with pytest.raises(RuntimeError, match="Error refreshing"):
        wrangles.extract.codes('test ABC123ZZ')

    wrangles.auth.refresh_token = None

def test_refresh_token():
    """
    Check refresh token works correctly.
    """
    wrangles.auth.refresh_token = requests.post(
        f"{wrangles.config.keycloak.host}/auth/realms/{wrangles.config.keycloak.realm}/protocol/openid-connect/token",
        headers=headers,
        data={
            "grant_type": "password",
            "username": wrangles.config.api_user,
            "password": wrangles.config.api_password,
            "client_id": wrangles.config.keycloak.client_id
        }
    ).json()['refresh_token']
    assert wrangles.extract.codes('test ABC123ZZ') == ["ABC123ZZ"]
    wrangles.auth.refresh_token = None
