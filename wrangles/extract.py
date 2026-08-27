"""
Functions to extract information from unstructured text.
"""
import re as _re
import logging as _logging
from typing import Union as _Union
import time as _time
from . import config as _config
from . import data as _data
from . import batching as _batching
from .format import flatten_lists as _flatten_lists
from . import openai as _openai
from . import openai_responses as _openai_responses
from . import ai_config as _ai_config
from . import ai_definition as _ai_definition
from . import ai_cache as _ai_cache

_LOG = _logging.getLogger(__name__)


def _normalize_ai_protocol(protocol: str) -> str:
    protocol = str(protocol or "").strip().lower().replace("-", "_")
    aliases = {
        "responses_api": "responses",
        "chat": "chat_completions",
        "chat_completion": "chat_completions",
    }
    protocol = aliases.get(protocol, protocol)
    if protocol not in {"responses", "chat_completions"}:
        raise ValueError(
            "protocol must be 'responses' or 'chat_completions'. "
            f"Received {protocol!r}."
        )
    return protocol


def _validate_ai_runtime_settings(
    threads: int,
    timeout: float,
    retries: int,
    deadline: float,
) -> None:
    if not isinstance(threads, int) or isinstance(threads, bool) or threads < 1:
        raise ValueError("threads must be a positive integer.")
    if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0:
        raise ValueError("retries must be a non-negative integer.")
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("timeout must be a positive number of seconds.")
    if not isinstance(deadline, (int, float)) or isinstance(deadline, bool) or deadline <= 0:
        raise ValueError("deadline must be a positive number of seconds.")


def _cacheable_ai_result(result) -> bool:
    """Do not retain transport, validation, or deadline failures."""
    if not isinstance(result, dict) or not result:
        return False
    error_prefixes = (
        "deadline exceeded",
        "failed",
        "invalid structured response",
        "openai api error",
        "timed out",
    )
    for value in result.values():
        if isinstance(value, BaseException):
            return False
        if isinstance(value, str) and value.strip().lower().startswith(error_prefixes):
            return False
    return True


def _enable_responses_web_search(payload: dict) -> None:
    """Add native web search without replacing expert Responses settings."""
    tools = payload.setdefault("tools", [])
    if not isinstance(tools, list):
        raise ValueError("OpenAI Responses 'tools' must be an array.")
    if not any(
        isinstance(tool, dict)
        and tool.get("type") in {"web_search", "web_search_preview"}
        for tool in tools
    ):
        tools.append({"type": "web_search"})

    included = payload.setdefault("include", [])
    if not isinstance(included, list):
        raise ValueError("OpenAI Responses 'include' must be an array.")
    source_include = "web_search_call.action.sources"
    if source_include not in included:
        included.append(source_include)

    payload.setdefault("tool_choice", "auto")


def address(
    input: _Union[str, list],
    dataType: str,
    **kwargs
) -> list:
    """
    Extract geographical information from unstructured text such as streets, cities or countries.
    Requires WrangleWorks Account.

    e.g. '1100 Congress Ave, Austin, TX 78701, United States' -> '1100 Congress Ave'

    :param input: A string or list of strings with addresses to search for information.
    :param dataType: The type of information to return. 'streets', 'cities', 'regions' or 'countries'
    :return: A list of any results found.
    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    _logging.info(f": Extracting address {dataType} from {len(json_data)} records")
    url = f'{_config.api_host}/wrangles/extract/address'
    params = {
        'responseFormat':'array',
        'dataType':dataType,
        **kwargs
    }
    batch_size = 10000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]
    
    return results


def ai(
    input,
    api_key: str,
    output: dict = None,
    model_id: str = None,
    model: str = None,
    threads: int = None,
    timeout: float = None,
    retries: int = None,
    messages: _Union[str, list] = None,
    examples: _Union[dict, list] = None,
    record_examples: _Union[dict, list] = None,
    url: str = None,
    strict: bool = None,
    reasoning: dict = None,
    verbosity: str = None,
    provider: str = None,
    protocol: str = None,
    deadline: float = None,
    store: bool = None,
    cache: bool = None,
    cache_ttl: float = None,
    web_search: bool = False,
    instructions: _Union[str, list] = None,
    **kwargs
) -> _Union[dict, list]:
    """
    >>> wrangles.extract.ai(
    >>>   "Yellow Submarine",
    >>>   api_key="...",
    >>>   output={
    >>>       "type": "string",
    >>>       "description": "The names of any colors in the input"
    >>>   }
    >>> )

    :param input: A single value or list of values to extract information from. If a list is provided, \
        each element will be analyzed individually and a list of equal length will be returned.
    :param api_key: OpenAI API key.
    :param output: (Optional) This can be a string prompting the output, a JSON schema definition \
        of the output requested or a dict of JSON schema definitions.
    :param model_id: (Optional) An extract.ai model ID containing a saved definition. Use this or output. \
        If both are provided, named output fields take precedence over matching saved fields.
    :param model: (Optional) The model to use for the extraction.
    :param threads: (Optional) Number of threads to use for parallel processing.
    :param timeout: (Optional) Timeout in seconds for each API call.
    :param retries: (Optional) Number of retries to attempt on failure.
    :param instructions: (Optional) Additional guidance applied to every input row. Use this for
        decision rules, evidence priorities, normalization requirements, or other behavior that
        applies to the complete extraction.
    :param messages: (Optional) Compatibility alias for instructions.
    :param examples: (Optional) Compatibility alias for record_examples.
    :param record_examples: (Optional) Whole-record examples containing input and output, with optional name and notes.
    :param url: (Optional) Override the configured endpoint.
    :param strict: (Optional) Enable structured output strict mode. Dynamic object schemas \
        automatically use non-strict mode and are validated locally.
    :param reasoning: (Optional) Responses API reasoning options. Defaults to {"effort": "none"} \
        for models that support disabling reasoning; otherwise omitted so the provider default applies.
    :param verbosity: (Optional) Responses API text verbosity. Defaults to "low" \
        for models that support low verbosity.
    :param provider: (Optional) AI provider. Currently only "openai" is supported.
    :param protocol: (Optional) API protocol: "responses" or legacy "chat_completions".
    :param deadline: (Optional) Total seconds allowed for this extract.ai call, including retries.
    :param store: (Optional) Whether OpenAI may store Responses. Defaults to False.
    :param cache: (Optional) Use the bounded warm-instance result cache. Defaults to True.
    :param cache_ttl: (Optional) Override the result-cache TTL in seconds for this call.
    :param web_search: (Optional) Enable native Responses web search. Each result then includes a
        web_search_sources list containing source titles and URLs. Defaults to False.
    :return: Extracted information. When web_search is true, returns a dictionary (or list of
        dictionaries) containing web_search_sources, including for single-field output.
    """
    policy = _ai_config.extract_ai()
    provider = str(provider or policy.get("provider", "openai")).strip().lower()
    if provider != "openai":
        raise ValueError(
            f"Unsupported extract.ai provider {provider!r}. Phase 1 supports only 'openai'."
        )

    if protocol is None:
        if url and "/chat/completions" in url:
            protocol = "chat_completions"
            _LOG.warning(
                "Inferred legacy protocol 'chat_completions' from url; "
                "set protocol explicitly while upgrading this definition."
            )
        else:
            protocol = policy.get("protocol", "responses")
    protocol = _normalize_ai_protocol(protocol)
    if not isinstance(web_search, bool):
        raise ValueError("web_search must be true or false.")
    if web_search and protocol != "responses":
        raise ValueError("web_search is supported only with protocol='responses'.")

    if url:
        if protocol == "responses" and "/chat/completions" in url:
            raise ValueError("A Chat Completions url cannot be used with protocol='responses'.")
        if protocol == "chat_completions" and "/responses" in url:
            raise ValueError("A Responses url cannot be used with protocol='chat_completions'.")
    else:
        url = policy.get("endpoints", {}).get(protocol)
    if not url:
        raise ValueError(f"No endpoint is configured for extract.ai protocol {protocol!r}.")

    model = model or policy.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string.")
    threads = threads if threads is not None else policy.get("max_concurrency", 20)
    timeout = timeout if timeout is not None else policy.get("request_timeout_seconds", 12)
    retries = retries if retries is not None else policy.get("retries", 0)
    strict = strict if strict is not None else policy.get("strict", True)
    deadline = deadline if deadline is not None else policy.get("total_deadline_seconds", 15)
    store = store if store is not None else policy.get("store", False)
    cache_policy = _ai_cache.resolve_policy(
        policy.get("cache", {}),
        enabled=cache,
        ttl_seconds=cache_ttl,
    )

    if not isinstance(strict, bool):
        raise ValueError("strict must be true or false.")
    if not isinstance(store, bool):
        raise ValueError("store must be true or false.")
    if verbosity is not None and verbosity not in {"low", "medium", "high"}:
        raise ValueError("verbosity must be 'low', 'medium', or 'high'.")
    if reasoning is not None and not isinstance(reasoning, dict):
        raise ValueError("reasoning must be an object such as {'effort': 'none'}.")
    _validate_ai_runtime_settings(threads, timeout, retries, deadline)

    if instructions not in (None, "") and messages not in (None, ""):
        raise ValueError("Use instructions or messages, not both.")
    if instructions in (None, ""):
        instructions = messages
    if record_examples not in (None, "") and examples not in (None, ""):
        raise ValueError("Use record_examples or examples, not both.")
    if record_examples in (None, ""):
        record_examples = examples

    # Ensure input is a list
    input_was_scalar = False
    if not isinstance(input, list):
        input_was_scalar = True
        input = [input]

    saved_model_content = (
        _data.model_content(model_id)
        if model_id is not None
        else None
    )
    compiled = _ai_definition.compile_definition(
        output,
        model=model,
        messages=instructions,
        examples=record_examples,
        strict=strict,
        saved_model_content=saved_model_content,
        source=f"saved model {model_id}" if model_id else "recipe/Python output",
    )
    output = compiled.output
    model = compiled.model
    saved_reasoning = compiled.reasoning
    strict = compiled.strict
    output_generic_key = compiled.output_generic_key
    _key_to_original = compiled.key_to_original
    _needs_remap = compiled.needs_remap
    root_schema = compiled.root_schema
    example_guidance = _ai_definition.render_example_guidance(compiled)
    if (
        web_search
        and _openai_responses.WEB_SEARCH_SOURCES_KEY in compiled.output
    ):
        raise ValueError(
            f"{_openai_responses.WEB_SEARCH_SOURCES_KEY!r} is reserved when "
            "web_search is enabled. Choose a different output field name."
        )

    messages = [
        {
            "role": "user",
            "content": message
        }
        for message in compiled.messages
    ]

    if protocol == "responses":
        schema = _openai_responses.sanitize_schema(
            root_schema,
            strict=strict,
        )
        instructions = str(
            policy.get("prompt", {}).get("instructions", "")
        ).strip()
        if not instructions:
            raise ValueError("extract.ai prompt instructions are missing from the AI configuration.")
        if example_guidance:
            instructions += "\n\nExamples:\n" + example_guidance
        if messages:
            instructions += "\n\nAdditional instructions:\n" + "\n".join(
                str(message.get("content", ""))
                for message in messages
            )
        if web_search:
            instructions += "\n\n" + " ".join([
                "Web search is enabled for this call.",
                "Information returned by the web search tool is authorized evidence in addition to DATA.",
                "Use web search only when it helps answer the requested fields, and return null when neither DATA nor web evidence supports a field.",
            ])

        payload = {
            "model": model,
            "instructions": instructions,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "extract_ai_response",
                    "schema": schema,
                    "strict": strict,
                },
            },
            "store": store,
            **_openai_responses.sanitize_request_params(kwargs),
        }
        if web_search:
            _enable_responses_web_search(payload)
        configured_reasoning = (
            reasoning
            if reasoning is not None
            else saved_reasoning or policy.get("reasoning", {"effort": "none"})
        )
        if _openai_responses.supports_reasoning(model):
            effort = configured_reasoning.get("effort")
            if _openai_responses.supports_reasoning_effort(model, effort):
                payload["reasoning"] = configured_reasoning
            else:
                _LOG.warning(
                    "Ignoring reasoning effort %r: not supported by model '%s'; "
                    "the provider's default reasoning effort will apply.",
                    effort,
                    model,
                )
        elif reasoning is not None or saved_reasoning is not None:
            _LOG.warning(
                "Ignoring 'reasoning' parameter: not supported by model '%s'",
                model,
            )
        if verbosity is not None:
            if _openai_responses.supports_low_verbosity(model):
                payload["text"]["verbosity"] = verbosity
            else:
                _LOG.warning(
                    "Ignoring 'verbosity' parameter: not supported by model '%s'",
                    model,
                )
        elif _openai_responses.supports_low_verbosity(model):
            payload["text"]["verbosity"] = policy.get("text", {}).get("verbosity", "low")

        payload["prompt_cache_key"] = _openai_responses.prompt_cache_key(
            "extract.ai",
            model,
            payload,
        )
        deadline_at = _time.monotonic() + deadline
        static_request = {
            "url": url,
            "payload": payload,
            "cache_ttl_seconds": cache_policy.ttl_seconds,
        }
        results = _ai_cache.execute_batch(
            input,
            key_for=lambda row: _ai_cache.make_key(
                namespace="extract.ai",
                provider=provider,
                protocol=protocol,
                tenant_secret=api_key,
                static_request=static_request,
                data=_openai_responses.format_input_data(row),
            ),
            compute=lambda row: _openai_responses.call_structured(
                row,
                api_key,
                payload,
                url,
                timeout,
                retries,
                list(output.keys()),
                deadline_at,
            ),
            cacheable=_cacheable_ai_result,
            max_workers=threads,
            policy=cache_policy,
            deadline_at=deadline_at,
        )

        if _needs_remap:
            results = [
                {_key_to_original.get(k, k): v for k, v in row.items()}
                if isinstance(row, dict) else row
                for row in results
            ]

        if input_was_scalar:
            if output_generic_key and not web_search:
                return results[0].get('output', 'Failed')
            else:
                return results[0]
        else:
            if output_generic_key and not web_search:
                return [x.get('output', 'Failed') for x in results]
            else:
                return results

    stable_messages = [
        {
            "role": "system",
            "content": " ".join([
                "You are an expert data analyst.",
                "Your job is to extract and standardize information as provided by the user.",
                "The data may be provided as a single value or as YAML syntax with keys and values.",
                "Return null when the data does not explicitly support a requested field.",
            ])
        },
        {
            "role": "system",
            "content": " ".join([
                "Use the function parse_output to return the data to be submitted.",
                "Only use the functions you have been provided with.",
            ])
        },
    ]
    if example_guidance:
        stable_messages.append({
            "role": "system",
            "content": "Examples:\n" + example_guidance,
        })
    messages = stable_messages + messages
    
    default_settings = {
        "gpt-4o-mini": {"temperature": 0.2},
        "gpt-4o": {"temperature": 0.2}
    }

    # Blend default settings into kwargs
    kwargs = {
        **default_settings.get(model, {}),
        **kwargs
    }

    settings = {
        "model": model,
        "messages": messages,
        "tools": [{
            "type": "function",
            "function": {
                "name": "parse_output",
                "description": "Submit the output corresponding to the extracted data in the form the user requires.",
                "parameters": root_schema,
                "strict": strict
            }
        }],
        "tool_choice": {"type": "function", "function": {"name": "parse_output"}},
        **kwargs
    }

    _logging.info(f": Extracting data using AI model :: model_id :: {model_id}, thread_count :: {threads}")
    deadline_at = _time.monotonic() + deadline
    static_request = {
        "url": url,
        "settings": settings,
        "cache_ttl_seconds": cache_policy.ttl_seconds,
    }
    results = _ai_cache.execute_batch(
        input,
        key_for=lambda row: _ai_cache.make_key(
            namespace="extract.ai",
            provider=provider,
            protocol=protocol,
            tenant_secret=api_key,
            static_request=static_request,
            data=_openai.format_input_data(row),
        ),
        compute=lambda row: _openai.chatGPT(
            row,
            api_key,
            settings,
            url,
            timeout,
            retries,
            deadline_at,
        ),
        cacheable=_cacheable_ai_result,
        max_workers=threads,
        policy=cache_policy,
        deadline_at=deadline_at,
    )

    if _needs_remap:
        results = [
            {_key_to_original.get(k, k): v for k, v in row.items()}
            if isinstance(row, dict) else row
            for row in results
        ]

    if input_was_scalar:
        if output_generic_key:
            return results[0].get('output', 'Failed')
        else:
            return results[0]
    else:
        if output_generic_key:
            return [x.get('output', 'Failed') for x in results]
        else:
            return results

def attributes(
    input: _Union[str, list],
    responseContent: str = 'span',
    type: str = None,
    desiredUnit: str = None,
    bound: str = 'mid',
    first_element: bool = False,
    **kwargs
) -> _Union[dict, list]:
    """
    Extract numeric attributes from unstructured text such as lengths or voltages.
    Requires WrangleWorks Account.

    >>> wrangles.extract.attributes('tape 25m')
    {'length': ['25m']}

    :param input: Input string or list of strings to be searched for attributes
    :param responseContent: (Optional, default Span) 'span' or 'object'. If span, returns original text, if object returns an object of value and dimension.
    :param type: (Optional) Specify which types of attributes to find. If omitted, a dict of all attributes types is returned
    :param bound: (Optional, default mid). When returning an object, if the input is a range. e.g. 10-20mm, set the value to return. min, mid or max.
    """
    
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    _logging.info(f": Extracting attributes from {len(json_data)} records")
    url = f'{_config.api_host}/wrangles/extract/attributes'
    params = {
        'responseFormat':'array',
        'responseContent': responseContent,
        **kwargs
    }
    if type: params['attributeType'] = type
    if desiredUnit: params['desiredUnit'] = desiredUnit
    
    if bound in ['min', 'mid', 'max']:
        params['bound'] = bound
    else:
        raise ValueError('Invalid boundary setting. min, mid or max permitted.')
    
    batch_size = 1000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if first_element and type:
        results = [x[0] if len(x) >= 1 else "" for x in results]

    if first_element and not type:
        raise TypeError('first_element must be used with a specified attribute_type')
    
    if isinstance(input, str): results = results[0]

    return results


def codes(
    input: _Union[str, list],
    first_element: bool = False,
    **kwargs
) -> list:
    """
    Extract alphanumeric codes from unstructured text.
    Requires WrangleWorks Account.

    e.g. 'Something ABC123ZZ something' -> 'ABC123ZZ'

    :param input: A string or list of strings to search for codes.
    :param first_element: Get the first element from results.
    :param min_length: Minimum length of allowed results.
    :param max_length: Maximum length of allowed results.
    :param strategy: Controls filtering of likely false positives such as measurements.
        'lenient' skips this filter, while 'balanced' and 'strict' currently apply
        the same filter. Default is 'balanced'. Unless min_length is provided,
        minimum lengths default to 3 for lenient, 4 for balanced, and 5 for strict.
    :param sort_order: Default is input order. Also allows 'longest' or 'shortest'.
    :param disallowed_patterns: A pattern or JSON array of regex patterns to not include in the found codes.
    :param include_multi_part_tokens: Whether to include multi-part tokens that have a space. Default True.
    :param extract_raw: Whether to return tokens with their adjacent non-whitespace characters
        included, rather than the cleaned token. Default False.
    :return: A list of codes found.
    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    _logging.info(f": Extracting codes from {len(json_data)} records")
    url = f'{_config.api_host}/wrangles/extract/codes'
    params = {'responseFormat': 'array', **kwargs}
    batch_size = 10000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if first_element:
        results = [x[0] if len(x) >= 1 else "" for x in results]

    if isinstance(input, str): results = results[0]
    
    return results


def custom(
    input: _Union[str, list],
    model_id: str,
    first_element: bool = False,
    use_labels: bool = False,
    case_sensitive: bool = False,
    extract_raw: bool = False,
    use_spellcheck: bool = False,
    include_empty_labels: bool = True,
    sort: str = 'training_order',
    output_format: str = 'dict',
    **kwargs
) -> list:
    """
    Extract entities using a custom model.
    Requires WrangleWorks Account and Subscription.

    :param input: A string or list of strings to searched for information.
    :param model_id: The model to be used to search for information.
    :return: A list of entities found.
    """
    if isinstance(input, str): 
        json_data = [input]
    elif isinstance(input, list):
        json_data = input
    else:
        raise TypeError('Invalid input data provided. The input must be either a string or a list of strings.')
        
    # If the Model Id is not appropriate, raise error (Only for Recipes)
    if isinstance(model_id, dict):
        raise ValueError('Incorrect model_id type.\nIf using Recipe, may be missing "${ }" around value')
    
    # Checking to see if GUID format is correct
    if [len(x) for x in model_id.split('-')] != [8, 4, 4]:
        raise ValueError('Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX')

    url = f'{_config.api_host}/wrangles/extract/custom'
    params = {
        'responseFormat': 'array',
        'model_id': model_id,
        'use_labels': use_labels,
        'caseSensitive': case_sensitive,
        'extract_raw': extract_raw,
        'use_spellcheck': use_spellcheck,
        'sort': sort,
        **kwargs
    }

    model_properties = _data.model(model_id)
    model_content = _data.model_content(model_id)

    model_labels = set()
    for item in model_content['Data']:  
        if len(item) >= 2: 
            if ':' in item[1]: 
                label = item[1].split(':')[0]  # Second column typically contains the label/type  
                model_labels.add(label.strip())
    
    # If model_id format is correct but no mode_id exists
    if model_properties.get('message', None) == 'error':
        raise ValueError('Incorrect model_id.\nmodel_id may be wrong or does not exists')

    # Set appropriate batch_size
    if 'ai' in (model_properties.get('variant', '') or ''):
        batch_size = 20
    else:
        batch_size = 10000
    batch_size = model_properties['batch_size'] or batch_size
    
    # Using model_id in wrong function
    purpose = model_properties['purpose']
    if purpose != 'extract':
        raise ValueError(f'Using {purpose} model_id {model_id} in an extract function.')
    
    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(results, dict) and "data" in results and "columns" in results:
        if len(results["columns"]) == 1:
            # For a single output column, the service returns the matches
            # as a ", " joined string rather than an array. Convert this
            # back into a list of matches to preserve the expected output type.
            def _entities_to_list(value):
                if isinstance(value, list):
                    return value
                if value in (None, ""):
                    return []
                return [item.strip() for item in value.split(",")]

            if use_labels:
                results = [
                    {results["columns"][0]: _entities_to_list(row[0])}
                    for row in results["data"]
                ]
            else:
                results = [
                    _entities_to_list(row[0])
                    for row in results["data"]
                ]
        else:
            results = [
                {results["columns"][i]: row[i] for i in range(len(row))}
                for row in results["data"]
            ]
    if isinstance(results, list):
        if first_element and not use_labels:
            results = [x[0] if len(x) >= 1 else "" for x in results]
        
        if use_labels:
            if include_empty_labels:
                # Ensure every label has a key, create empty keys if missing.
                # Use both labels discovered from results and labels defined in the model.
                all_labels = {}
                for label in sorted(model_labels, key=lambda x: x.lower()):
                    all_labels.setdefault(label.lower(), label)
                for objs in results:
                    for label in objs:
                        all_labels.setdefault(str(label).lower(), label)

                for objs in results:
                    # Normalize existing keys to lower-case while preserving original keys
                    existing = {str(k).lower(): k for k in objs.keys()}
                    for normalized_label, label in all_labels.items():
                        if normalized_label not in existing:
                            objs[label] = []
            if first_element:
                results = [{k: v[0] if isinstance(v, list) and v else "" for k, v in objs.items()} for objs in results]
    else:
        raise ValueError(f'API Response did not return an expected format for model {model_id}')


    if isinstance(input, str): results = results[0]
    
    return results


def html(
    input: _Union[str, list],
    dataType: str,
    **kwargs
) -> list:
    """
    Extract specific html elements from strings containing html.
    Requires WrangleWorks Account.

    :param input: A string or list of strings with addresses to search for information.
    :param dataType: The type of information to return. 'text' or 'links'
    :return: A list of any results found.
    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    _logging.info(f": Extracting {dataType} from HTML")
    url = f'{_config.api_host}/wrangles/extract/html'
    params = {
        'responseFormat': 'array',
        'dataType': dataType,
        **kwargs
    }
    batch_size = 10000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]
    
    return results

    
def properties(
    input: _Union[str, list],
    type: str = None,
    return_data_type: str = 'list',
    first_element: bool = False,
    **kwargs
) -> _Union[dict, list]:
    """
    Extract categorical properties from unstructured text such as colours or materials.
    Requires WrangleWorks Account.

    >>> wrangles.extract.properties('The Green Mile')
    {'Colours': ['Green']}

    :param input: A string or list of strings to be searched for properties
    :param type: (Optional) The specific type of property to search for. If omitted an objected with all results will be returned.
    :param return_data_type: (Optional) The format to return the data, as a list or as a string.
    :return: A single or list with the extracted properties. Each extracted property may be a dict or list depending on settings.
    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

    _logging.info(f": Extracting properties from {len(json_data)} records")
    url = f'{_config.api_host}/wrangles/extract/properties'
    params = {'responseFormat':'array', **kwargs}
    if type is not None: params['dataType'] = type
    batch_size = 10000

    results = _batching.batch_api_calls(url, params, json_data, batch_size)
    
    if first_element and type:
        results = [x[0] if len(x) >= 1 else "" for x in results]

    if first_element and not type:
        raise TypeError('first_element must be used with a specified property_type')

    if isinstance(input, str): results = results[0]
    
    if return_data_type == 'string': results = [', '.join(x) if x != [] else '' for x in results]
    
    return results


# SUPER MARIO
def remove_words(input: _Union[str, list], to_remove: list, tokenize_to_remove: bool, ignore_case: bool):
    """
    Remove all the elements that occur in one list from another.
    
    :param input: both input and to_remove can be a string or a list or multiple lists. Lowered for precision
    :param output: a string of remaining words
    :param tokenize_to_remove: (Optional) tokenize all of to_remove columns
    :pram ignore_case: (Optional) ignore the case of input and to_remove
    """
        
    # Deal with ignore_case
    if ignore_case == True:
        flags = _re.IGNORECASE
    else:
        flags = 0 # this is the default for _re.sub
    
    _logging.info(f": Removing words from {len(input)} records")
    results = []
    for _in, _remove in zip(input, to_remove):
        
        # Check if the input is a string or a list
        if isinstance(_in, list):
            # Make appropriate changes to the input to convert to a string
            _in = ' '.join(_in)
        
        # flatten the _remove lists if necessary
        _remove = _flatten_lists(_remove)
        
        #Custom word boundary that considers a space, the start of the string, or the end of the string as a boundary
        boundary = r'(?:\s|,|^|$)'
        
        text = _in
        for remove in _remove:
            # Convert to string since _re.escape only accepts strings
            remove = str(remove)
            
            # if Tokenize is true
            if tokenize_to_remove == True:
                # Tokenize                        
                token_remove = _re.split(r'\s|,', remove)
                for subtoken in token_remove:
                    subtoken = _re.escape(subtoken)  # escape the special characters just in case

                    # Use the custom word boundary in the regex pattern
                    pattern = r'{}{}{}'.format(boundary, subtoken, boundary)

                    # Use re.sub with the custom pattern, and remove extra spaces
                    text = _re.sub(pattern, ' ', text, flags=flags).strip()
                
            else:
                remove = _re.escape(remove) # escape the special characters just in case
                
                # Use the custom word boundary in the regex pattern
                pattern = r'{}{}{}'.format(boundary, remove, boundary)
                
                # Use re.sub with the custom pattern, and remove extra spaces
                text = _re.sub(pattern, ' ', text, flags=flags).strip()
                
            # remove any double spaces
            text = _re.sub(r'\s+', ' ', text)
        results.append(text)
    return results


def brackets(
    input: str,
    find: list = _Union[str, list],
    include_brackets: bool = False,
    return_data_type: str = "string"
    ) -> list:
    """
    Extract values in brackets, [], {}, (), <>
    
    :param input: Input string to search for brackets
    :param find: Types of brackets to find (e.g., 'round', 'square', 'curly', 'angled'). Default is all types.
    :param include_brackets: Whether to include brackets in the results
    :return: List of extracted values
    """
    _logging.info(": Extracting text from brackets")
    results = []
    bracket_patterns = {
    'round': r'\(.*?\)',
    'square': r'\[.*?\]',
    'curly': r'\{.*?\}',
    'angled': r'<.*?>'
    }

    if isinstance(find, str): find = [find]

    if find != ['all']:
        patterns = [bracket_patterns[element] for element in find if element != 'all']
        pattern = '|'.join(patterns)
    else:
        # Default pattern matches all types of brackets if find is empty
        pattern = '|'.join(bracket_patterns.values())

    for item in input:
        # Finds all matches inside of brackets in item (list of strings)
        re = _re.findall(pattern, item)
    
        # Traverse list and remove all brackets if include_brackets is False
        if include_brackets is False:
            re = [_re.sub(r'\[|\]|{|}|\(|\)|<|>', '', re[x]) for x in range(len(re))]

        if return_data_type == "list":
            results.append(re)
        else:
            results.append(', '.join(re))
        
    return results
