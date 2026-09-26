import base64 as _base64
import yaml as _yaml
import json as _json
import copy as _copy
import concurrent.futures as _futures
from itertools import chain as _chain
import logging as _logging
import requests as _requests
import numpy as _np
import warnings as _warnings
from . import openai_responses as _openai_responses
from . import ai_config as _ai_config
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
_RETRYABLE_TRANSPORT_ERRORS = (
    _requests.exceptions.Timeout,
    _requests.exceptions.ConnectionError,
    _requests.exceptions.ChunkedEncodingError,
    _requests.exceptions.ContentDecodingError,
)


def format_input_data(data: any) -> str:
    """Serialize row input exactly as Chat Completions will receive it."""
    if isinstance(data, (dict, list)):
        return _yaml.dump(
            data,
            indent=2,
            sort_keys=False,
            allow_unicode=True,
            Dumper=_YAMLDumper,
            width=1000,
        )
    return str(data)


def _chatGPT(data, api_key, settings, url, timeout, retries):
    """Send Chat Completions using transport settings resolved by the caller."""
    content = format_input_data(data)

    settings_local = _copy.deepcopy(settings)
    settings_local["messages"].append(
        {
            "role": "user",
            "content": f"\n---Data:\n---\n{content}"
        }
    )

    if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0:
        raise ValueError("Retries must be a non-negative integer")

    _logging.debug(f": Calling OpenAI ChatGPT :: timeout :: {timeout}, retries :: {retries}")
    response = None
    backoff_time = 1
    for attempt in range(retries + 1):
        response = None
        try:
            response = _requests.post(
                url = url,
                headers = {
                    "Authorization": f"Bearer {api_key}"
                },
                json = settings_local,
                timeout=timeout
            )
        except Exception as e:
            if attempt == retries or not isinstance(e, _RETRYABLE_TRANSPORT_ERRORS):
                error = "Timed Out" if isinstance(e, _requests.exceptions.Timeout) else e
                if settings_local.get("tools", []):
                    return {
                        param: error
                        for param in 
                        settings_local.get("tools", [])[0]["function"]["parameters"]["required"]
                    }
                else:
                    return error

        if response is not None and response.ok:
            break
        else:
            error_message = ""
            try:
                error_message = response.json().get('error').get('message')
            except:
                pass
            # Raise errors for fatal errors rather than continuing
            if error_message:
                if "Invalid schema" in error_message:
                    raise ValueError("The schema submitted for output is not valid.")
                if "Incorrect API key" in error_message:
                    raise ValueError("API Key provided is missing or invalid.")
            context = _openai_responses._response_context(
                response,
                endpoint="chat_completions",
                model=settings_local.get("model"),
            ) if response is not None else {}
            _openai_responses._raise_for_fatal_error(context)
            if attempt == retries or (response is not None and not _openai_responses._should_retry(context)):
                if response is not None:
                    _openai_responses._log_api_error(context, final=True)
                break
            if response is not None:
                _openai_responses._log_api_error(context, final=False)
 
        if attempt < retries:
            _logging.warning(f": Retrying OpenAI request :: attempt :: {attempt + 1}")
            if response is not None and not response.ok:
                _openai_responses._sleep_for_retry(
                    context,
                    backoff_time,
                )
            else:
                _openai_responses._sleep_for_retry(
                    {},
                    backoff_time,
                )
            backoff_time *= 2

    if response is not None and response.ok:
        try:
            result = _json.loads(
                response.json()['choices'][0]['message']['tool_calls'][0]['function']['arguments']
            )
            return result
        except:
            pass

    # Attempt to get a useful error message
    try:
        error_message = _openai_responses._error_message(
            _openai_responses._response_context(
                response,
                endpoint="chat_completions",
                model=settings_local.get("model"),
            )
        )
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
    retries: int,
    request_params: dict,
    precision: str,
    provider: str,
    timeout: float,
):
    """
    Get embeddings

    :param input_list: List of strings to generate embeddings for
    :param api_key: API key for the provider
    :param model: Specific model to use
    :param url: The endpoint to send requests to. The expected request/response format is determined by provider.
    :param retries: Number of times to retry. This will exponentially backoff.
    :param request_params: Additional request parameters to pass to the backend.
    :param precision: The resolved precision of the embeddings.
    :param provider: The resolved embedding provider.
    :param timeout: Resolved per-attempt request timeout in seconds.
    """
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
    transport_error = None
    backoff_time = 1
    for attempt in range(retries + 1):
        response = None
        transport_error = None
        try:
            response = _requests.post(
                url=url,
                headers={"Authorization": f"Bearer {api_key}"},
                json=request_body,
                timeout=timeout,
            )
        except _requests.exceptions.RequestException as exc:
            transport_error = exc

        if response is not None and response.ok:
            break

        context = _openai_responses._response_context(
            response, endpoint="embeddings", model=model, attempt=attempt + 1,
        )
        if transport_error is not None:
            context["message"] = f"{type(transport_error).__name__}: {transport_error}"
        if response is not None and (
            response.status_code == 401 or "Incorrect API key" in context.get("message", "")
        ):
            raise ValueError("API Key provided is missing or invalid.")
        if provider == "openai":
            _openai_responses._raise_for_fatal_error(context)

        retryable = (
            isinstance(transport_error, _RETRYABLE_TRANSPORT_ERRORS)
            or _openai_responses._should_retry(context)
        )
        final = attempt == retries or not retryable
        _openai_responses._log_api_error(context, final=final)
        if final:
            break
        _openai_responses._sleep_for_retry(context, backoff_time)
        backoff_time *= 2

    if response is not None and response.ok:
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
        return [
            _np.frombuffer(
                _base64.b64decode(row['embedding']),
                dtype=_np.float32
            ).astype(getattr(_np, precision), copy=False)
            for row in response.json()['data']
        ]
    else:
        error_msg = _openai_responses._error_message(context)
        raise RuntimeError(
            f"Failed to get embeddings after {attempt + 1} attempt(s): {error_msg}"
        ) from transport_error


def embeddings(
    input_list,
    api_key,
    model: str = None,
    batch_size: int = None,
    threads: int = None,
    retries: int = None,
    url: str = None,
    precision: str = None,
    provider: str = None,
    task: str = None,
    timeout: float = None,
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
    :param model: (Optional) The model to use for generating embeddings. Defaults to the \
          configured embeddings model for the resolved provider. Jina requires an explicit \
          model unless a Jina embeddings default is configured.
    :param batch_size: (Optional) Rows per request; defaults to the AI configuration.
    :param threads: (Optional) Concurrent requests; defaults to the AI configuration. \
          Each request contains the number of rows set as batch_size.
    :param retries: Additional attempts after transient HTTP or transport failures.
          Defaults to the AI configuration. Uses exponential backoff and Retry-After; permanent errors fail immediately.
    :param url: The endpoint to send requests to. Defaults to the standard endpoint for \
          the resolved provider. Setting a Jina URL without an explicit provider will \
          automatically use Jina's request/response format.
    :param precision: The precision of the embeddings. Defaults to the AI configuration.
    :param provider: Controls the request/response format (openai or jina). Inferred from \
          an explicit url when omitted (jina.ai → jina, otherwise openai), or the AI \
          configuration when neither is supplied. Setting provider also sets the \
          default url for that provider — you only need one of the two for standard endpoints. \
          Pass both only when using a custom endpoint with a non-default provider's API format.
    :param task: (Optional, Jina only) The task type for the embedding model. \
          Defaults and allowed values come from the selected model's AI configuration. \
          Jina v5 supports retrieval.query, retrieval.passage, text-matching, \
          classification, and clustering. Legacy models without a configured task \
          enum retain retrieval.query, retrieval.passage, text-matching, \
          classification, and separation.
    :param timeout: Per-attempt request timeout in seconds. Defaults to the AI configuration.
    :return: A list of embeddings corresponding to the input
    """
    # Explicit URLs retain their existing provider inference, including compatible proxies.
    if provider is None and url is not None:
        provider = "jina" if "jina.ai" in url else "openai"
    if provider is not None and provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Provider must be one of {SUPPORTED_PROVIDERS}. Got '{provider}'")

    policy = _ai_config.resolve("embeddings", model=model, provider=provider)
    provider = policy["provider"]
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Provider must be one of {SUPPORTED_PROVIDERS}. Got '{provider}'")
    if policy["protocol"] != "embeddings":
        raise ValueError("Embedding requests require the 'embeddings' protocol.")
    model = policy["model"]
    _ai_config.warn_if_deprecated(model, provider)
    batch_size = policy["batch_size"] if batch_size is None else batch_size
    threads = policy["default_concurrency"] if threads is None else threads
    retries = policy["retries"] if retries is None else retries
    precision = policy["precision"] if precision is None else precision
    timeout = policy["request_timeout_seconds"] if timeout is None else timeout
    task = policy.get("task") if task is None else task
    request_keys = (
        ("dimensions", "normalized", "truncate", "late_chunking")
        if provider == "jina" else ("dimensions", "user")
    )
    kwargs = {**{key: policy[key] for key in request_keys if key in policy}, **kwargs}
    if url is None or (url == DEFAULT_EMBEDDING_URLS["openai"] and provider != "openai"):
        url = policy.get("endpoints", {}).get("embeddings")
    if not url:
        raise ValueError(f"No endpoint is configured for embeddings provider {provider!r}.")

    if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0:
        raise ValueError("retries must be a non-negative integer.")
    if (
        not isinstance(timeout, (int, float)) or isinstance(timeout, bool)
        or not _np.isfinite(timeout) or timeout <= 0
    ):
        raise ValueError("timeout must be a positive finite number of seconds.")

    if precision not in ["float32", "float16"]:
        raise ValueError(f"Precision must be either float32 or float16. Got {precision}")

    if task is not None:
        if provider != "jina":
            _warnings.warn(
                f"task parameter is only supported for the Jina provider and will be ignored for provider='{provider}'.",
                UserWarning,
                stacklevel=2
            )
        else:
            supported_tasks = _ai_config.model_supported_values(model, provider).get("task", sorted(JINA_TASKS))
            if task not in supported_tasks:
                raise ValueError(f"task must be one of {supported_tasks} for model '{model}'. Got '{task}'")

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
            [provider] * len(batches),
            [timeout] * len(batches),
        ))

    results = list(_chain.from_iterable(results))

    # If user provided a list, return as list
    # else return the embeddings
    if user_input_was_list:
        return results
    else:
        return results[0]
