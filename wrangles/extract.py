"""
Functions to extract information from unstructured text.
"""
import re as _re
from typing import Union as _Union
from . import config as _config
from . import data as _data
from . import batching as _batching
from .format import tokenize, flatten_lists


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

    
def attributes(
    input: _Union[str, list],
    responseContent: str = 'span',
    type: str = None,
    desiredUnit: str = None,
    bound: str = 'mid',
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
    
    if isinstance(input, str): results = results[0]

    return results


def codes(
    input: _Union[str, list],
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
        **kwargs
    }
    model_properties = _data.model(model_id)
    # If model_id format is correct but no mode_id exists
    if model_properties.get('message', None) == 'error': raise ValueError('Incorrect model_id.\nmodel_id may be wrong or does not exists')
    batch_size = model_properties['batch_size'] or 10000
    
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
        _remove = flatten_lists(_remove)
        
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


def brackets(input: str) -> list:
    """
    Extract values in brackets, [], {}
    
    :param input: Name of the input column
    :param output: Name of the output column
    """
    results = []
    for item in input:
        re = _re.findall(r'\[.*?\]|{.*?}|\(.*?\)|<.*?>', item)
        re = [_re.sub(r'\[|\]|{|}|\(|\)|<|>', '', re[x]) for x in range(len(re))]
        
        results.append(', '.join(re))
        
    return results
