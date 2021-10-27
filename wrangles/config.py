"""
Configuration Settings
"""
import os


api_host = 'https://clbqu0wyx6.execute-api.us-east-2.amazonaws.com'
api_user = os.environ.get('WRANGLES_USER')
api_password = os.environ.get('WRANGLES_PASSWORD')

def authenticate(user, password):
    """
    Provide login details to authenticate with Wrangles API.
    """
    global api_user, api_password
    api_user = user
    api_password = password


class keycloak():
    """
    Settings for keycloak server
    """
    host = 'https://sso.wrangle.works'
    realm = 'wrwx'
    client_id = 'services'