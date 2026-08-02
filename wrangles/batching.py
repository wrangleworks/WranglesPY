"""
Code to batch API calls for large volumes of data that
are unable to be processed in a single request
"""

import logging as _logging
from . import auth as _auth
from . import utils as _utils


def batch_api_calls(url, params, input_list, batch_size):
    """
    Batch API calls into multiple of set batch size
    """
    if input_list == []:
        # If input list is empty, shortcut and 
        # immediately return an empty list
        return []

    total_batches = (len(input_list) + batch_size - 1) // batch_size
    _logging.info(f": Starting batch API calls :: url :: {url}, batch_size :: {batch_size}, total_records :: {len(input_list)}")

    results = None
    for i in range(0, len(input_list), batch_size):
        batch_num = i // batch_size + 1
        _logging.debug(f": Processing batch {batch_num} of {total_batches}")
        headers = {'Authorization': f'Bearer {_auth.get_access_token()}'}
        response = _utils.request_retries(
                    request_type='POST',
                    url=url,
                    **{
                        'params': params,
                        'headers': headers,
                        'json': input_list[i:i + batch_size]
                    }
                )
        
        # Checking status code
        if str(response.status_code)[0] != '2':
            _logging.error(f": Batch API request failed :: status_code :: {response.status_code}, batch :: {batch_num}")
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

    return results
