"""
Functions to extract information from unstructured text.
"""
import re as _re
import logging as _logging
from typing import Union as _Union
import concurrent.futures as _futures
import json as _json
import time as _time
from . import config as _config
from . import data as _data
from . import batching as _batching
from .format import flatten_lists as _flatten_lists
from . import openai as _openai
from . import openai_responses as _openai_responses
from . import ai_config as _ai_config
from . import ai_definition as _ai_definition

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
    messages: list = None,
    url: str = None,
    strict: bool = None,
    reasoning: dict = None,
    verbosity: str = None,
    provider: str = None,
    protocol: str = None,
    deadline: float = None,
    store: bool = None,
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
    :param api_key: API Key
    :param output: (Optional) This can be a string prompting the output, a JSON schema definition \
        of the output requested or a dict of JSON schema definitions.
    :param model_id: (Optional) An extract.ai model ID containing a saved definition. Use this or output. \
        If both are provided, output that precedence over the definition from the model_id.
    :param model: (Optional) The model to use for the extraction.
    :param threads: (Optional) Number of threads to use for parallel processing.
    :param timeout: (Optional) Timeout in seconds for each API call.
    :param retries: (Optional) Number of retries to attempt on failure.
    :param messages: (Optional) Overall prompts to pass additional instructions.
    :param url: (Optional) Override the configured endpoint.
    :param strict: (Optional) Enable structured output strict mode. Dynamic object schemas \
        automatically use non-strict mode and are validated locally.
    :param reasoning: (Optional) Responses API reasoning options. Defaults to {"effort": "none"} \
        for models that support reasoning.
    :param verbosity: (Optional) Responses API text verbosity. Defaults to "low" \
        for models that support low verbosity.
    :param provider: (Optional) AI provider. Currently only "openai" is supported.
    :param protocol: (Optional) API protocol: "responses" or legacy "chat_completions".
    :param deadline: (Optional) Total seconds allowed for this extract.ai call, including retries.
    :param store: (Optional) Whether OpenAI may store Responses. Defaults to False.

    :return: A scalar or list of extracted information.
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

    if not isinstance(strict, bool):
        raise ValueError("strict must be true or false.")
    if not isinstance(store, bool):
        raise ValueError("store must be true or false.")
    if verbosity is not None and verbosity not in {"low", "medium", "high"}:
        raise ValueError("verbosity must be 'low', 'medium', or 'high'.")
    if reasoning is not None and not isinstance(reasoning, dict):
        raise ValueError("reasoning must be an object such as {'effort': 'none'}.")
    _validate_ai_runtime_settings(threads, timeout, retries, deadline)

    if messages is None:
        messages = []

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
        messages=messages,
        strict=strict,
        saved_model_content=saved_model_content,
        source=f"saved model {model_id}" if model_id else "recipe/Python output",
    )
    output = compiled.output
    model = compiled.model
    strict = compiled.strict
    output_generic_key = compiled.output_generic_key
    _key_to_original = compiled.key_to_original
    _needs_remap = compiled.needs_remap
    root_schema = compiled.root_schema

    messages = [
        {
            "role": "user",
            "content": message
        }
        for message in compiled.messages
    ]

    if protocol == "responses":
        field_guidance = []
        for field, schema_node in output.items():
            examples = schema_node.get("examples")
            if examples:
                field_guidance.append(
                    f"- {field}: examples are {_json.dumps(examples, default=str)}"
                )

        schema = _openai_responses.sanitize_schema(
            root_schema,
            strict=strict,
        )
        instructions = str(
            policy.get("prompt", {}).get("instructions", "")
        ).strip()
        if not instructions:
            raise ValueError("extract.ai prompt instructions are missing from the AI configuration.")
        if field_guidance:
            instructions += "\n\nUse these field examples as style guidance, not values to copy:\n"
            instructions += "\n".join(field_guidance)
        if messages:
            instructions += "\n\nAdditional instructions:\n" + "\n".join(
                str(message.get("content", ""))
                for message in messages
            )

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
            "prompt_cache_key": _openai_responses.prompt_cache_key(
                "extract.ai",
                model,
                schema,
            ),
            "store": store,
            **_openai_responses.sanitize_request_params(kwargs),
        }
        if reasoning is not None:
            if _openai_responses.supports_reasoning(model):
                payload["reasoning"] = reasoning
            else:
                _LOG.warning(
                    "Ignoring 'reasoning' parameter: not supported by model '%s'",
                    model,
                )
        elif _openai_responses.supports_reasoning(model):
            payload["reasoning"] = policy.get("reasoning", {"effort": "none"})
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

        deadline_at = _time.monotonic() + deadline
        with _futures.ThreadPoolExecutor(max_workers=threads) as executor:
            results = list(executor.map(
                _openai_responses.call_structured,
                input,
                [api_key] * len(input),
                [payload] * len(input),
                [url] * len(input),
                [timeout] * len(input),
                [retries] * len(input),
                [list(output.keys())] * len(input),
                [deadline_at] * len(input),
            ))

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

    messages = [
        {
            "role": "system",
            "content": " ".join([
                "You are an expert data analyst.",
                "Your job is to extract and standardize information as provided by the user.",
                "The data may be provided as a single value or as YAML syntax with keys and values."
            ])
        },
        {
            "role": "system",
            "content": " ".join([
                "Use the function parse_output to return the data to be submitted.",
                "Only use the functions you have been provided with.",
            ])
        },
    ] + messages
    
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

    deadline_at = _time.monotonic() + deadline
    with _futures.ThreadPoolExecutor(max_workers=threads) as executor:
        results = list(executor.map(
            _openai.chatGPT,
            input, 
            [api_key] * len(input),
            [settings] * len(input),
            [url] * len(input),
            [timeout] * len(input),
            [retries] * len(input),
            [deadline_at] * len(input),
        ))

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

    """
    if isinstance(input, str): 
        json_data = [input]
    else:
        json_data = input

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
    sort: str = 'training_order',
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
            results = [
                row[0]
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
        
        if use_labels and first_element:
            results = [{k:v[0] for (k, v) in zip(objs.keys(), objs.values())} for objs in results]
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
    include_brackets: bool = False
    ) -> list:
    """
    Extract values in brackets, [], {}, (), <>
    
    :param input: Input string to search for brackets
    :param find: Types of brackets to find (e.g., 'round', 'square', 'curly', 'angled'). Default is all types.
    :param include_brackets: Whether to include brackets in the results
    :return: List of extracted values
    """
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
            results.append(', '.join(re))
        else:
            results.append(', '.join(re))
        
    return results
