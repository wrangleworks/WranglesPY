import pytest
import os
from wrangles.auth import _refresh_access_token

# Testing Auth



def test_get_access_token_invalid_user():
    """
    Test that an invalid user raises an appropriate error
    """
    with pytest.raises(RuntimeError, match="Invalid login"):
        raise _refresh_access_token("user", "doesnotexist")

def test_get_access_token_invalid_password():
    """
    Test that an invalid password raises an appropriate error
    """
    with pytest.raises(RuntimeError, match="Invalid login"):
        raise _refresh_access_token("wrwx", "notthecorrectpassword")

# Get user config
def test_user_config_credentials():
    from wrangles.config import authenticate
    user = os.getenv('WRANGLES_USER','...')
    password = os.getenv('WRANGLES_PASSWORD', '...')
    assert authenticate(user, password) == None
