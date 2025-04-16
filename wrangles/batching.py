"""
Code to batch API calls for large volumes of data that
are unable to be processed in a single request
"""

import requests as _requests
from . import auth as _auth
import pandas as _pd


def batch_api_calls(
    url,
    params,
    input_list,
    batch_size,
    input_columns=None
):
    """
    Batch API calls into multiple of set batch size

    :param url: URL to send the request to
    :param params: Parameters to be sent with the request
    :param input_list: List of inputs to be sent in batches
    :param batch_size: Size of each batch
    :param input_columns: Optional columns to be sent with the request
    """
    if input_list == []:
        # If input list is empty, shortcut and 
        # immediately return an empty list
        return []

    results = None
    for i in range(0, len(input_list), batch_size):
        retries = 1

        while retries > 0:
            try:
                response = _requests.post(
                    url,
                    params=params,
                    headers={
                        'Authorization': f'Bearer {_auth.get_access_token()}'
                    },
                    json=(
                        input_list[i:i + batch_size] if input_columns is None
                        else {"columns": input_columns, "data": input_list[i:i + batch_size]}
                    )
                )

            except Exception as e:
                if retries > 0:
                    retries -= 1
                    continue
                raise ValueError(f"API call failed: {e}")

            # Checking status code
            if not response.ok:
                if retries > 0 and str(response.status_code)[0] not in ['4']:
                    retries -= 1
                    continue
                else:
                    raise ValueError(f"Status Code: {response.status_code} - {response.reason}. {response.text} \n")
            
            try:
                response_data = response.json()
                break
            except:
                if retries > 0:
                    retries -= 1
                    continue
                raise ValueError(f"Failed to parse JSON response: {response.text}")

        if isinstance(response_data, list):
            if results is None:
                results = []

            results += response_data

        elif isinstance(response_data, dict):
            if results is None:
                results = {"data": [], "columns": []}

            if "data" not in response_data or "columns" not in response_data:
                raise ValueError("API Response did not return an expected format.")
            
            if results['columns'] == []:
                results["columns"] = response_data["columns"]
                results["data"] += response_data["data"]
            elif results["columns"] == response_data["columns"]:
                results["data"] += response_data["data"]
            else:
                # Use pandas to align the columns
                _pd.concat(
                    [
                        _pd.DataFrame(
                            results["data"],
                            columns=results["columns"]
                        ),
                        _pd.DataFrame(
                            response_data["data"],
                            columns=response_data["columns"]
                        )
                    ]
                ).to_dict(orient="tight")
        else:
            raise ValueError("API Response did not return an expected format.")

    return results
