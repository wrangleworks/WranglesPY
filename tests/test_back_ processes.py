import pytest
import wrangles
import pandas as pd
import os


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
    assert info.typename == 'RuntimeError' and info.value.args[0] == 'Invalid login details provided'
    
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
    assert info.typename == 'RuntimeError' and info.value.args[0] == 'Unexpected error when authenticating'
    
# Testing Batching
from wrangles.batching import batch_api_calls

# Getting Status code errors - 500 Internal server Error
headers = {'Authorization': f'Bearer 3141'}
class temp_response_batch_calls():
    status_code = 500
    reason = 'Internal Server Error.'
    text = 'An internal error has occured.'
    
def test_batch_api_calls_errors(mocker):
    m = mocker.patch("wrangles.auth.get_access_token")
    m.return_value = headers
    m2 = mocker.patch("requests.post")
    m2.return_value = temp_response_batch_calls
    config = {
        "url": "supermario@google.com",
        "params": "extract",
        "input_list": ['A1'],
        "batch_size": 10_000
    }
    with pytest.raises(ValueError) as info:
        raise batch_api_calls(**config)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Status Code: 500 - Internal Server Error.. An internal error has occured. \n'
    

# Get user config
def test_user_config_credentials():
    from wrangles.config import authenticate
    user = os.getenv('WRANGLES_USER','...')
    password = os.getenv('WRANGLES_PASSWORD', '...')
    assert authenticate(user, password) == None
