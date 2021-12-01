"""
Configuration Settings
"""
import os


api_host = 'https://api.wrangle.works'
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