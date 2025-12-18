"""
Configuration Settings
"""

import os as _os


api_host = "https://api.wrangle.works"
api_user = _os.environ.get("WRANGLES_USER")
api_password = _os.environ.get("WRANGLES_PASSWORD")


def authenticate(user, password):
    """
    Provide login details to authenticate with Wrangles API.
    """
    global api_user, api_password
    api_user = user
    api_password = password


class keycloak:
    """
    Settings for keycloak server
    """

    host = "https://sso.wrangle.works"
    realm = "wrwx"
    client_id = "services"


# When using where, these Wrangles
# overwrite the output rather than
# trying to merge the contents
# back to the original dataframe
where_overwrite_output = [
    "pandas.transpose",
    "transpose",
    "filter",
    "sql",
    "select.group_by",
    "select.sample",
    "select.columns",
    "select.head",
    "pandas.head",
    "select.tail",
    "pandas.tail",
    "sort",
]

# Wrangles that don't work with where
where_not_implemented = ["drop", "rename", "reindex"]

# Recipe names that use forbidden python keywords
reserved_word_replacements = {"try": "Try"}
