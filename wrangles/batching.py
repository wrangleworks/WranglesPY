"""
Code to batch API calls for large volumes of data that
are unable to be processed in a single request
"""
import time as _time
import requests as _requests
from . import auth as _auth


def batch_api_calls(url, params, input_list, batch_size):
    """
    Batch API calls into multiple of set batch size
    """
    if input_list == []:
        # If input list is empty, shortcut and 
        # immediately return an empty list
        return []

    results = None
    for i in range(0, len(input_list), batch_size):
        retries = 1
        backoff_time = 1
        while retries > 0:
            try:
                # Attempt to make the API call
                response = _requests.post(
                    url,
                    params=params,
                    headers={'Authorization': f'Bearer {_auth.get_access_token()}'},
                    json=input_list[i:i + batch_size],
                    timeout=29
                )
            except Exception as e:
                response = None
                # If we've exhausted retries, raise the error
                if (retries-1) <= 0:
                    raise e

            if response is not None and not str(response.status_code).startswith('5'):
                break

            # If we get a 5xx error, wait and retry
            _time.sleep(backoff_time)
            retries -= 1
            backoff_time *= 2
        
        # If we totally failed to get a valid response
        if response is None:
            raise ValueError("No response from API.")

        # If we get a 4xx error, notify the user
        if not response.ok:
            raise ValueError(f"Status Code: {response.status_code} - {response.reason}. {response.text} \n")
        
        if isinstance(response.json(), list):
            if results is None:
                results = []
            results += response.json()
        elif isinstance(response.json(), dict):
            if results is None:
                results = {}
            results["data"] = results.get("data", []) + response.json()["data"]
            results["columns"] = response.json()["columns"]
        else:
            raise ValueError(f"API Response did not return an expected format.")

    return results
