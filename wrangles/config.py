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


class models():
    """
    Default OpenAI model names used by AI-powered wrangles.
    Centralized here so models can be updated in one place
    (e.g. when a model is deprecated) and so usage/cost can
    be tracked per function via distinct model strings.
    """
    extract_ai = 'gpt-5.4-mini'
    generate_ai = 'gpt-5-mini'
    embeddings = 'text-embedding-3-small'

    class testing():
        """
        Models used by the test suite, kept separate from the
        production defaults above so test runs can be tracked
        separately in OpenAI usage/cost data.
        """
        extract_ai = 'gpt-5.4-mini'
        generate_ai = 'gpt-5-mini'
        embeddings = 'text-embedding-3-small'


# When using where, these Wrangles
# overwrite the output rather than
# trying to merge the contents
# back to the original dataframe 
where_overwrite_output = [
    'pandas.transpose',
    'transpose',
    'filter',
    'sql',
    'select.group_by',
    'select.sample',
    'select.columns',
    'select.head',
    'pandas.head',
    'select.tail',
    'pandas.tail',
    'sort'
]

# Wrangles that don't work with where
where_not_implemented = [
    'drop',
    'rename',
    'reindex'
]

# Recipe names that use forbidden python keywords
reserved_word_replacements = {
    "try": "Try"
}
