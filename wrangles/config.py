"""
Configuration Settings
"""
import os as _os


api_host = 'https://api.wrangle.works'
api_user = _os.environ.get('WRANGLES_USER')
api_password = _os.environ.get('WRANGLES_PASSWORD')

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

# wrangles that don't work with where
no_where_list = [
    'pandas.transpose',
    'transpose',
    'filter',
    'rename',
    'sql',
    'drop',
    'split.list',
    'reindex',
    'select.group_by'
]
