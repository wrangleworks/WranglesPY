from typing import Union as _Union
import logging as _logging
import re as _re
import unicodedata as _unicodedata
from ftfy import fix_text as _fix_text
from . import config as _config
from . import data as _data
from . import batching as _batching


def standardize(
    input: _Union[str, list],
    model_id: str,
    case_sensitive: bool = False,
    **kwargs
) -> list:
    """
    Standardize text - Standardize Wrangles can replace words with alternatives,
    in addition to using regex patterns for more complex replacements.
    Requires WrangleWorks Account and Subscription.

    :param input: A string or list of strings to be standardized.
    :param model_id: The model to be used.
    :param case_sensitive: Allows setting the model to be case sensitive
    :return: A string or list with the updated text.
    """
    if isinstance(input, str): 
        json_data = [input]
    elif isinstance(input, list):
        json_data = input
    else:
        raise TypeError('Invalid input data provided. The input must be either a string or a list of strings.')
        
    # If the Model Id is not appropriate, raise error (Maybe more specific?)
    if isinstance(model_id, dict) or len(model_id.split('-')) != 3:
        raise ValueError('Incorrect model_id. May be missing "${ }" around value')
        
    # Checking to see if GUID format is correct
    if [len(x) for x in model_id.split('-')] != [8, 4, 4]:
        raise ValueError('Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX')

    url = f'{_config.api_host}/wrangles/standardize'
    params = {
        'responseFormat': 'array',
        'model_id': model_id,
        'caseSensitive': case_sensitive,
        **kwargs
    }
    model_properties = _data.model(model_id)
    # If model_id format is correct but no mode_id exists
    if model_properties.get('message', None) == 'error': raise ValueError('Incorrect model_id.\nmodel_id may be wrong or does not exists')
    batch_size = model_properties['batch_size'] or 10000
    
    # Using model_id in wrong function
    purpose = model_properties['purpose']
    if purpose != 'standardize':
        raise ValueError(f'Using {purpose} model_id {model_id} in a standardize function.')

    _logging.info(f": Standardizing {len(json_data)} records :: model_id :: {model_id}, case_sensitive :: {case_sensitive}")
    results = _batching.batch_api_calls(url, params, json_data, batch_size)

    if isinstance(input, str): results = results[0]
    
    return results


def clean(
    input: _Union[str, list],
    fix_encoding: bool = True,
    unescape_html: _Union[str, bool] = 'auto',
    normalization: str = 'NFC',
    fix_character_width: bool = True,
    uncurl_quotes: bool = True,
    remove_control_chars: bool = True,
    collapse_whitespace: bool = True,
    preserve_line_breaks: bool = False,
    trim: bool = True,
    **kwargs
) -> _Union[str, list]:
    """
    Repair common Unicode and encoding problems, then normalize whitespace.

    Strings are cleaned directly. Lists retain their length and order, and
    non-string list elements are returned unchanged so dataframe wrappers can
    preserve mixed-type cells.

    :param input: A string or list of values to clean.
    :param fix_encoding: Repair mojibake and other reversible encoding errors.
    :param unescape_html: Decode HTML character references. ``'auto'`` avoids
        decoding references in text that appears to contain HTML markup.
    :param normalization: Unicode normalization form, such as NFC or NFKC.
    :param fix_character_width: Normalize fullwidth and halfwidth characters.
    :param uncurl_quotes: Replace typographic quotes with straight quotes.
    :param remove_control_chars: Remove C0 and C1 control characters.
    :param collapse_whitespace: Collapse runs of Unicode whitespace.
    :param preserve_line_breaks: Preserve line breaks while collapsing other
        whitespace.
    :param trim: Remove leading and trailing whitespace.
    :param kwargs: Additional options forwarded to ``ftfy.fix_text``.
    :return: A cleaned string or shape-preserving list.
    """
    if isinstance(input, str):
        values = [input]
        scalar_input = True
    elif isinstance(input, list):
        values = input
        scalar_input = False
    else:
        raise TypeError(
            'Invalid input data provided. The input must be either a string or a list.'
        )

    results = []
    for value in values:
        if not isinstance(value, str):
            results.append(value)
            continue

        cleaned = _fix_text(
            value,
            fix_encoding=fix_encoding,
            unescape_html=unescape_html,
            normalization=normalization,
            fix_character_width=fix_character_width,
            uncurl_quotes=uncurl_quotes,
            remove_control_chars=remove_control_chars,
            **kwargs
        )

        if remove_control_chars:
            cleaned = ''.join(
                char
                for char in cleaned
                if char in '\t\r\n' or _unicodedata.category(char) != 'Cc'
            )

        if collapse_whitespace:
            if preserve_line_breaks:
                cleaned = _re.sub(r'[^\S\r\n]+', ' ', cleaned)
                cleaned = _re.sub(r' *(\r\n|\r|\n) *', r'\1', cleaned)
            else:
                cleaned = _re.sub(r'\s+', ' ', cleaned)

        if trim:
            cleaned = cleaned.strip()

        results.append(cleaned)

    return results[0] if scalar_input else results


def custom(
    input: _Union[str, list],
    model_id: str,
    case_sensitive: bool = False,
    **kwargs
) -> _Union[str, list]:
    """
    Explicit name for the model-backed standardization wrangle.

    This delegates to :func:`standardize` so existing Python callers and the
    new ``standardize.custom`` entry point share exactly the same behavior.

    :param input: A string or list of strings to be standardized.
    :param model_id: The model to be used.
    :param case_sensitive: Allows setting the model to be case sensitive.
    :return: A string or list with the updated text.
    """
    return standardize(
        input=input,
        model_id=model_id,
        case_sensitive=case_sensitive,
        **kwargs
    )


# ``standardize`` remains callable for backwards compatibility while also
# acting as the namespace used by dotted core calls.
standardize.clean = clean
standardize.custom = custom
