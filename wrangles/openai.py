import base64 as _base64
import yaml as _yaml
import json as _json
import copy as _copy
import concurrent.futures as _futures
from itertools import chain as _chain
import requests as _requests
import numpy as _np
import time as _time

def chatGPT(
    data: any,
    api_key: str,
    settings: dict,
    timeout: int = None,
    retries: int = 0,
):
    """
    Submit a request to openAI chatGPT.

    :param data: Dict with the data for that row
    :param api_key: OpenAI API Key
    :param settings: Custom model settings
    :param timeout: Time limit to apply to the request
    :param retries: Number of times to retry if the request fails
    """
    if len(data) == 1:
        content = list(data.values())[0]
    else:
        content = _yaml.dump(data, indent=2)

    settings_local = _copy.deepcopy(settings)
    settings_local["messages"].append(
        {
            "role": "user",
            "content": f"\n---Data:\n---\n{content}"
        }
    )

    if not isinstance(retries, int) or retries < 0:
        raise ValueError("Retries must be a positive integer")
    
    response = None
    backoff_time = 5
    while (retries + 1):
        try:
            response = _requests.post(
                url = "https://api.openai.com/v1/chat/completions",
                headers = {
                    "Authorization": f"Bearer {api_key}"
                },
                json = settings_local,
                timeout=timeout
            )
        except _requests.exceptions.ReadTimeout:
            if retries == 0:
                if settings_local.get("functions", []):
                    return {
                        param: "Timed Out"
                        for param in 
                        settings_local.get("functions", [])[0]["parameters"]["required"]
                    }
                else:
                    return "Timed Out"
        except Exception as e:
            if retries == 0:
                if settings_local.get("functions", []):
                    return {
                        param: e
                        for param in 
                        settings_local.get("functions", [])[0]["parameters"]["required"]
                    }
                else:
                    return e

        if response and response.ok:
            break
 
        retries -=1
        _time.sleep(backoff_time)
        backoff_time *= 2

    if response.ok:
        try:
            function_call = response.json()['choices'][0]['message']['function_call']
            return _json.loads(function_call['arguments'])
        except:
            try:
                return response.json()['choices']
            except:
                return response.text
    else:
        try:
            return response.json()['error']['message']
        except:
            return 'Failed'

def _divide_batches(l, n):
    """
    Yield successive n-sized
    batches from l.
    """
    for i in range(0, len(l), n): 
        yield l[i:i + n]

def _embedding_thread(
    input_list: list,
    api_key: str,
    model: str,
    retries: int = 0
):
    """
    Get embeddings 

    :param input_list: List of strings to generate embeddings for
    :param api_key: API key for the provider
    :param model: Specific model to use
    :param retries: Number of times to retry. This will exponentially backoff.
    """
    response = None

    while (retries + 1):
        response = _requests.post(
            url="https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": model,
                "encoding_format": "base64",
                "input": [
                    str(val) if val != "" else " " 
                    for val in input_list
                ]
            }
        )

        if response and response.ok:
            break

        retries -=1


    if response and response.ok:
        return [
            _np.frombuffer(
                _base64.b64decode(row['embedding']),
                dtype=_np.float32
            )
            for row in response.json()['data']
        ]
    else:
        return ['Error' for _ in input_list]

def embeddings(
    input_list,
    api_key,
    model: str = "text-embedding-ada-002",
    batch_size: int = 100,
    threads: int = 10,
    retries: int = 0
) -> list:
    """
    Generate embeddings for a list of strings.

    >>> wrangles.openai.embeddings(
    >>>  ["sentence 1", "sentence 2"],
    >>>  api_key="...",
    >>> )
    
    :param input_list: A list of strings to generate embeddings for.
    :param api_key: OpenAI API Key.
    :param model: (Optional) The model to use for generating embeddings.
    :param batch_size: (Optional, default 100) The number of rows to submit per individual request.
    :param threads: (Optional, default 10) The number of requests to submit in parallel. \
          Each request contains the number of rows set as batch_size.
    :param retries: The number of times to retry. This will exponentially \
          backoff to assist with rate limiting
    :return: A list of embeddings corresponding to the input
    """
    with _futures.ThreadPoolExecutor(max_workers=threads) as executor:
        batches = list(_divide_batches(input_list, batch_size))
        results = list(executor.map(
            _embedding_thread,
            batches,
            [api_key] * len(batches),
            [model] * len(batches),
            [retries] * len(batches)
        ))

    results = list(_chain.from_iterable(results))

    return results
