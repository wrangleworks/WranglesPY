"""
Code to batch API calls for large volumes of data that
are unable to be processed in a single request
"""

import requests as _requests
from . import auth as _auth


def batch_api_calls(url, params, input_list, batch_size):
    """
    Batch API calls into multiple of set batch size
    """
    results = []
    for i in range(0, len(input_list), batch_size):
        headers = {'Authorization': f'Bearer {_auth.get_access_token()}'}
        response = _requests.post(url, params=params, headers=headers, json=input_list[i:i + batch_size])
        
        # Checking status code
        if str(response.status_code)[0] != '2':
            raise ValueError(f"Status Code: {response.status_code} - {response.reason}. \n")
        
        results = results + response.json()

    return results