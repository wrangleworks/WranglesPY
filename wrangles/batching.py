"""
Code to batch API calls for large volumes of data that
are unable to be processed in a single request
"""

import requests as _requests
from urllib3.util import Retry as _Retry
from . import auth as _auth


def batch_api_calls(url, params, input_list, batch_size):
    """
    Batch API calls into multiple of set batch size
    """
    if input_list == []:
        # If input list is empty, shortcut and 
        # immediately return an empty list
        return []

    session = _requests.Session()
    session.mount(
        'https://',
        _requests.adapters.HTTPAdapter(
            max_retries=_Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[500, 501, 502, 503, 504],
                allowed_methods={'GET', 'PUT', 'POST', 'PATCH', 'OPTIONS'},
            )
        )
    )

    results = None
    try:
        for i in range(0, len(input_list), batch_size):
            headers = {'Authorization': f'Bearer {_auth.get_access_token()}'}
            response = session.post(url, params=params, headers=headers, json=input_list[i:i + batch_size])
            
            # Checking status code
            if str(response.status_code)[0] != '2':
                raise ValueError(f"Status Code: {response.status_code} - {response.reason}. {response.text} \n")
            
            response_json = response.json()

            if isinstance(response_json, list):
                if results is None:
                    results = []
                results += response_json
            elif isinstance(response_json, dict):
                if "data" not in response_json or "columns" not in response_json:
                    raise ValueError(f"API Response did not return an expected format.")

                if results is None:
                    results = {}

                results["data"] = results.get("data", []) + response_json["data"]
                results["columns"] = response_json["columns"]
            else:
                raise ValueError(f"API Response did not return an expected format.")
    finally:
        session.close()

    return results
