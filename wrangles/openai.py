import base64 as _base64
import yaml as _yaml
import json as _json
import copy as _copy
import concurrent.futures as _futures
from itertools import chain as _chain
import logging as _logging
import requests as _requests
import numpy as _np
import time as _time
import warnings as _warnings
try:
    from yaml import CSafeDumper as _YAMLDumper
except ImportError:
    from yaml import SafeDumper as _YAMLDumper

SUPPORTED_PROVIDERS = ["openai", "jina"]
JINA_TASKS = {"retrieval.query", "retrieval.passage", "text-matching", "classification", "separation"}
DEFAULT_EMBEDDING_URLS = {
    "openai": "https://api.openai.com/v1/embeddings",
    "jina":   "https://api.jina.ai/v1/embeddings",
}


def chatGPT(
    data: any,
    api_key: str,
    settings: dict,
    url: str = "https://api.openai.com/v1/chat/completions",
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
    if isinstance(data, (dict, list)):
        content = _yaml.dump(
            data,
            indent=2,
            sort_keys=False,
            allow_unicode=True,
            Dumper=_YAMLDumper,
            width=1000
        )
    else:
        content = str(data)

    settings_local = _copy.deepcopy(settings)
    settings_local["messages"].append(
        {
            "role": "user",
            "content": f"\n---Data:\n---\n{content}"
        }
    )

    if not isinstance(retries, int) or retries < 0:
        raise ValueError("Retries must be a positive integer")

    _logging.debug(f": Calling OpenAI ChatGPT :: timeout :: {timeout}, retries :: {retries}")

    response = None
    backoff_time = 1
    retry_count = 0
    while (retries + 1):
        try:
            response = _requests.post(
                url = url,
                headers = {
                    "Authorization": f"Bearer {api_key}"
                },
                json = settings_local,
                timeout=timeout
            )
        except _requests.exceptions.ReadTimeout:
            if retries == 0:
                if settings_local.get("tools", []):
                    return {
                        param: "Timed Out"
                        for param in 
                        settings_local.get("tools", [])[0]["function"]["parameters"]["required"]
                    }
                else:
                    return "Timed Out"
        except Exception as e:
            if retries == 0:
                if settings_local.get("tools", []):
                    return {
                        param: e
                        for param in 
                        settings_local.get("tools", [])[0]["function"]["parameters"]["required"]
                    }
                else:
                    return e

        if response and response.ok:
            break
        else:
            try:
                error_message = response.json().get('error').get('message')
            except:
                error_message = ""
            # Raise errors for fatal errors rather than continuing
            if error_message:
                if "Invalid schema" in error_message:
                    raise ValueError("The schema submitted for output is not valid.")
                if "Incorrect API key" in error_message:
                    raise ValueError("API Key provided is missing or invalid.")
 
        retries -= 1
        retry_count += 1
        if retries >= 0:
            _logging.warning(f": Retrying OpenAI request :: attempt :: {retry_count}")
            _time.sleep(backoff_time)
            backoff_time *= 2

    if response and response.ok:
        try:
            return _json.loads(
                response.json()['choices'][0]['message']['tool_calls'][0]['function']['arguments']
            )
        except:
            pass

    # Attempt to get a useful error message
    try:
        error_message = response.json()['error']['message']
    except:
        error_message = "Failed"

    _logging.error(f": OpenAI API error :: {error_message}")

    # Return error for each requested column
    return {
        param: error_message
        for param in 
        settings_local.get("tools", [])[0]["function"]["parameters"]["required"]
    }

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
    url: str,
    retries: int = 0,
    request_params: dict = None,
    precision: str = "float32",
    provider: str = "openai"
):
    """
    Get embeddings

    :param input_list: List of strings to generate embeddings for
    :param api_key: API key for the provider
    :param model: Specific model to use
    :param url: The endpoint to send requests to. The expected request/response format is determined by provider.
    :param retries: Number of times to retry. This will exponentially backoff.
    :param request_params: Additional request parameters to pass to the backend.
    :param precision: The precision of the embeddings. Default is float32.
    :param provider: The embedding provider to use. Default is openai.
    """
    if request_params is None:
        request_params = {}

    input_values = [str(val) if val != "" else " " for val in input_list]

    _OPENAI_ONLY_PARAMS = {"encoding_format"}
    if provider == "jina":
        request_body = {
            "model": model,
            "input": input_values,
            **{k: v for k, v in request_params.items() if k not in _OPENAI_ONLY_PARAMS}
        }
    else:
        request_body = {
            "model": model,
            "encoding_format": "base64",
            "input": input_values,
            **request_params
        }
    _logging.debug(f": Computing embeddings :: model :: {model}, record_count :: {len(input_list)}")

    response = None
    backoff_time = 1
    while (retries + 1):
        try:
            response = _requests.post(
                url=url,
                headers={
                    "Authorization": f"Bearer {api_key}"
                },
                json=request_body,
                timeout=30
            )
        except Exception:
            pass

        if response and response.ok:
            break
        else:
            if response is not None and response.status_code == 401:
                raise ValueError("API Key provided is missing or invalid.")
            try:
                error_message = response.json().get('error').get('message')
            except Exception:
                error_message = ""
            # Raise errors for fatal errors rather than continuing
            if error_message:
                if "Incorrect API key" in error_message:
                    raise ValueError("API Key provided is missing or invalid.")

        retries -= 1
        _time.sleep(backoff_time)
        backoff_time *= 2

    if response and response.ok:
        if provider == "jina":
            try:
                return [
                    _np.array(row['embedding'], dtype=_np.float32).astype(
                        getattr(_np, precision), copy=False
                    )
                    for row in response.json()['data']
                ]
            except (KeyError, TypeError) as e:
                raise RuntimeError(f"Unexpected Jina response schema: {e}")
        else:
            return [
                _np.frombuffer(
                    _base64.b64decode(row['embedding']),
                    dtype=_np.float32
                ).astype(getattr(_np, precision), copy=False)
                for row in response.json()['data']
            ]
    else:
        try:
            error_msg = response.json().get('error').get('message')
        except Exception:
            error_msg = 'Unknown error'
        raise RuntimeError(
            f"Failed to get embeddings: {error_msg}. Consider raising the number of retries."
        )

def embeddings(
    input_list,
    api_key,
    model: str = "text-embedding-3-small",
    batch_size: int = 100,
    threads: int = 10,
    retries: int = 0,
    url: str = DEFAULT_EMBEDDING_URLS["openai"],
    precision: str = "float32",
    provider: str = None,
    task: str = None,
    **kwargs
) -> list:
    """
    Generate embeddings for a list of strings.

    >>> wrangles.openai.embeddings(
    >>>  ["sentence 1", "sentence 2"],
    >>>  api_key="...",
    >>> )

    :param input_list: A list of strings to generate embeddings for.
    :param api_key: API Key for the provider.
    :param model: (Optional) The model to use for generating embeddings.
    :param batch_size: (Optional, default 100) The number of rows to submit per individual request.
    :param threads: (Optional, default 10) The number of requests to submit in parallel. \
          Each request contains the number of rows set as batch_size.
    :param retries: The number of times to retry. This will exponentially \
          backoff to assist with rate limiting
    :param url: The endpoint to send requests to. Defaults to the standard endpoint for \
          the resolved provider. Setting a Jina URL without an explicit provider will \
          automatically use Jina's request/response format.
    :param precision: The precision of the embeddings. Default is float32.
    :param provider: Controls the request/response format (openai or jina). Inferred from \
          url when omitted (jina.ai → jina, otherwise openai). Setting provider also sets the \
          default url for that provider — you only need one of the two for standard endpoints. \
          Pass both only when using a custom endpoint with a non-default provider's API format.
    :param task: (Optional, Jina only) The task type for the embedding model. \
          Valid values: retrieval.query, retrieval.passage, text-matching, classification, separation.
    :return: A list of embeddings corresponding to the input
    """
    # Infer provider from URL when not explicitly set
    if provider is None:
        if "jina.ai" in url:
            provider = "jina"
        else:
            provider = "openai"

    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Provider must be one of {SUPPORTED_PROVIDERS}. Got '{provider}'")

    # If URL is still the OpenAI default but a different provider is set, switch to that provider's URL
    if url == DEFAULT_EMBEDDING_URLS["openai"] and provider != "openai":
        url = DEFAULT_EMBEDDING_URLS.get(provider, url)

    if precision not in ["float32", "float16"]:
        raise ValueError(f"Precision must be either float32 or float16. Got {precision}")

    if task is not None:
        if provider != "jina":
            _warnings.warn(
                f"task parameter is only supported for the Jina provider and will be ignored for provider='{provider}'.",
                UserWarning,
                stacklevel=2
            )
        elif task not in JINA_TASKS:
            raise ValueError(f"task must be one of {sorted(JINA_TASKS)}. Got '{task}'")

    if provider == "jina" and task is not None:
        kwargs = {**kwargs, "task": task}

    # Ensure input is treated as a list
    # and store the original type to
    # mirror the output as later
    user_input_was_list = True
    if not isinstance(input_list, list):
        user_input_was_list = False
        input_list = [input_list]

    with _futures.ThreadPoolExecutor(max_workers=threads) as executor:
        batches = list(_divide_batches(input_list, batch_size))
        results = list(executor.map(
            _embedding_thread,
            batches,
            [api_key] * len(batches),
            [model] * len(batches),
            [url] * len(batches),
            [retries] * len(batches),
            [kwargs] * len(batches),
            [precision] * len(batches),
            [provider] * len(batches)
        ))

    results = list(_chain.from_iterable(results))

    # If user provided a list, return as list
    # else return the embeddings
    if user_input_was_list:
        return results
    else:
        return results[0]
