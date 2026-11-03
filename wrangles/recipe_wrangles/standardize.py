"""Dataframe wrappers for standardization wrangles."""

import json as _json
import logging as _logging
import re as _re
from typing import Union as _Union

import numpy as _np
import pandas as _pd
import yaml as _yaml

from ..standardize import clean as _clean
from ._serialization import _YAMLLoader, _YAMLDumper, _normalize_default_list


def _is_missing(value) -> bool:
    """Return whether a scalar value should be skipped during concatenation."""
    try:
        result = _pd.isna(value)
    except (TypeError, ValueError):
        return False

    # pandas returns an array for list-like cells; those are values, not a
    # scalar missing marker.
    if hasattr(result, '__len__'):
        return False
    return bool(result)


def _concatenate_row(values, separator: str) -> str:
    """Join non-missing row values as text."""
    return separator.join(
        str(value)
        for value in values
        if (
            not _is_missing(value)
            and (not isinstance(value, str) or value != '')
        )
    )


def clean(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, int, list] = None,
    fix_encoding: bool = True,
    unescape_html: _Union[str, bool] = 'auto',
    normalization: str = 'NFC',
    fix_character_width: bool = True,
    uncurl_quotes: bool = True,
    remove_control_chars: bool = True,
    collapse_whitespace: bool = True,
    preserve_line_breaks: bool = False,
    trim: bool = True,
    separator: str = ' ',
    unescape_unicode: bool = False,
    latex_to_text: bool = False,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Repair common encoding, Unicode, HTML character reference, control character, and whitespace problems locally.
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name or list of input columns.
      output:
        type:
          - string
          - integer
          - array
        description: Name or list of output columns. Defaults to overwriting input.
      fix_encoding:
        type: boolean
        default: true
        description: Repair mojibake and other reversible encoding errors.
      unescape_html:
        anyOf:
          - type: boolean
          - type: string
            enum:
              - auto
        default: auto
        description: Decode HTML character references. Auto avoids decoding text that appears to contain HTML markup.
      normalization:
        type:
          - string
          - "null"
        enum:
          - NFC
          - NFKC
          - NFD
          - NFKD
          - null
        default: NFC
        description: Unicode normalization form.
      fix_character_width:
        type: boolean
        default: true
        description: Normalize fullwidth and halfwidth characters.
      uncurl_quotes:
        type: boolean
        default: true
        description: Replace typographic quotes with straight quotes.
      remove_control_chars:
        type: boolean
        default: true
        description: Remove C0 and C1 control characters.
      collapse_whitespace:
        type: boolean
        default: true
        description: Collapse runs of Unicode whitespace.
      preserve_line_breaks:
        type: boolean
        default: false
        description: Preserve line breaks while collapsing other whitespace.
      trim:
        type: boolean
        default: true
        description: Remove leading and trailing whitespace.
      unescape_unicode:
        type: boolean
        default: false
        description: Decode literal printable Unicode escapes in prose, preserving code and Markdown link destinations.
      latex_to_text:
        type: boolean
        default: false
        description: Convert supported inline LaTeX units, symbols and numeric fractions to readable text. Preserve numeric dollar amounts, ranges and explicit price qualifiers; remove extra dollar signs from other supported inline math. Preserve unsupported formulas. Set collapse_whitespace and trim to false to retain Markdown layout.
      separator:
        type: string
        default: " "
        description: Text used to join multiple input columns into one output.
    """
    if output is None:
        output = input

    if not isinstance(input, list):
        input = [input]
    if not isinstance(output, list):
        output = [output]

    if not isinstance(separator, str):
        raise TypeError('separator must be a string.')

    clean_options = {
        'fix_encoding': fix_encoding,
        'unescape_html': unescape_html,
        'normalization': normalization,
        'fix_character_width': fix_character_width,
        'uncurl_quotes': uncurl_quotes,
        'remove_control_chars': remove_control_chars,
        'collapse_whitespace': collapse_whitespace,
        'preserve_line_breaks': preserve_line_breaks,
        'trim': trim,
        'unescape_unicode': unescape_unicode,
        'latex_to_text': latex_to_text,
        **kwargs
    }

    if len(input) > 1 and len(output) == 1:
        combined = [
            _concatenate_row(values, separator)
            for values in df[input].itertuples(index=False, name=None)
        ]
        df[output[0]] = _clean(combined, **clean_options)
        return df

    if len(input) != len(output):
        raise ValueError(
            'standardize.clean must output to a single column or the same '
            'number of columns as input.'
        )

    warned_for_non_strings = False
    source_values = [df[input_column].tolist() for input_column in input]
    for values, output_column in zip(source_values, output):
        if not warned_for_non_strings and any(
            not isinstance(value, str)
            for value in values
        ):
            _logging.warning(
                ': standardize.clean preserved non-string values in mapped input columns.'
            )
            warned_for_non_strings = True

        df[output_column] = _clean(values, **clean_options)

    return df


def from_json(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, list] = None,
    default = None,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Convert a JSON representation into an object.
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the input column.
      output:
        type:
          - string
          - array
        description: Name of the output column. If omitted, the input column will be overwritten
      default:
        type: ["string","array","object","number","boolean","null"]
        description: >-
            Value to return if the row is empty or fails to be parsed as JSON.
            If input is a list, default may also be a list - either a single
            value to apply to all columns, or one value per input column.
    """
    # Set output column as input if not provided
    if output is None: output = input

    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    defaults = _normalize_default_list(default, input, 'convert.from_json')

    # Loop through and apply for all columns
    for input_column, output_column, col_default in zip(input, output, defaults):
        def _load_with_fallback(value, _col_default=col_default):
            try:
                return _json.loads(value, **kwargs)
            except:
                if _col_default is not None:
                    return _col_default
                else:
                    raise ValueError(
                        "Unable to load all rows as JSON. " +
                        "Set a default to set a value if the row is empty or fails to parse."
                    )

        df[output_column] = [
            _load_with_fallback(x)
            for x in df[input_column]
        ]

    return df


def to_json(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, list] = None,
    ensure_ascii: bool = False,
    **kwargs
) -> _pd.DataFrame:
    r"""
    type: object
    description: Convert an object to a JSON representation.
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the input column.
      output:
        type:
          - string
          - array
        description: Name of the output column. If omitted, the input column will be overwritten
      indent:
        type:
          - string
          - integer
        description: >-
          If indent is a non-negative integer or string, then JSON array elements and object members will be pretty-printed
          with that indent level. An indent level of 0, negative, or "" will only insert newlines. None (the default) selects the most
          compact representation. Using a positive integer indent indents that many spaces per level. If indent is a string (such as '\t'),
          that string is used to indent each level.
      sort_keys:
        type: boolean
        description: If sort_keys is true (defaults to False), then the output of dictionaries will be sorted by key.
      ensure_ascii:
        type: boolean
        description: If true, non-ASCII characters will be escaped. Default is false
    """
    def handle_unusual_datatypes(o):
        if isinstance(o, _np.ndarray):
            return o.tolist()
        if isinstance(o, (_np.integer, _np.floating)):
            return o.item()
        else:
            return o.__str__()

    # Set output column as input if not provided
    if output is None: output = input

    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) == len(output):
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            def wrap_scalar(val):
                if _pd.api.types.is_scalar(val):
                    return [val]
                return val
            df[output_column] = [
            _json.dumps(
                wrap_scalar(row),
                ensure_ascii=ensure_ascii,
                default=handle_unusual_datatypes,
                **kwargs
            )
            for row in df[input_column].values
            ]
    elif len(input) > 1 and len(output) == 1:
        df[output] = [
            _json.dumps(
                row,
                ensure_ascii=ensure_ascii,
                default=handle_unusual_datatypes,
                **kwargs
            )
            for row in df[input].to_dict(orient="records")
        ]
    else:
        raise ValueError('The lists for input and output must be the same length.')

    return df


def from_yaml(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, list] = None,
    default = None,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Convert a YAML representation into an object
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the input column.
      output:
        type:
          - string
          - array
        description: >-
          Name of the output column.
          If omitted, the input column will be overwritten
      default:
        type: ["string","array","object","number","boolean","null"]
        description: >-
          Value to return if the row is empty or fails to be parsed as YAML.
          If input is a list, default may also be a list - either a single
          value to apply to all columns, or one value per input column.
    """
    # Set output column as input if not provided
    if output is None: output = input

    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    defaults = _normalize_default_list(default, input, 'convert.from_yaml')

    # Loop through and apply for all columns
    for input_column, output_column, col_default in zip(input, output, defaults):
        def _load_with_fallback(value, _col_default=col_default):
            try:
                result = _yaml.load(value, Loader=_YAMLLoader, **kwargs)
                # Only fall back to the default if the row was empty (parses to None).
                # A falsy-but-valid result (e.g. [], {}, '', False, 0) must be preserved
                # as-is rather than being overwritten by the default.
                return _col_default if result is None else result
            except:
                if _col_default is not None:
                    return _col_default
                else:
                    raise ValueError(
                        "Unable to load all rows as YAML. " +
                        "Set a default to set a value if the row is empty or fails to parse."
                    )

        df[output_column] = [
            _load_with_fallback(x)
            for x in df[input_column]
        ]

    return df


def to_yaml(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, list] = None,
    sort_keys: bool = False,
    allow_unicode: bool = True,
    **kwargs
) -> _pd.DataFrame:
    r"""
    type: object
    description: Convert an object to a YAML representation.
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the input column.
      output:
        type:
          - string
          - array
        description: >-
          Name of the output column.
          If omitted, the input column will be overwritten
      indent:
        type: integer
        description: >-
          Specify the number of spaces for indentation to
          specify nested elements
      sort_keys:
        type: boolean
        description: >-
          If sort_keys is true (default: False),
          then the output of dictionaries will be sorted by key.
    """
    # Set output column as input if not provided
    if output is None: output = input

    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) == len(output):
        # Loop through and apply for all columns
        for input_columns, output_column in zip(input, output):
            df[output_column] = [
                _yaml.dump(
                    row,
                    sort_keys=sort_keys,
                    allow_unicode=allow_unicode,
                    Dumper=_YAMLDumper,
                    **kwargs
                )
                for row in df[input_columns].values
            ]
    elif len(input) > 1 and len(output) == 1:
        # User specified multiple inputs but only one output
        # Merge the inputs into a single dictionary before converting
        df[output] = [
            _yaml.dump(
                row,
                sort_keys=sort_keys,
                allow_unicode=allow_unicode,
                Dumper=_YAMLDumper,
                **kwargs
            )
            for row in df[input].to_dict(orient="records")
        ]
    else:
        raise ValueError('The lists for input and output must be the same length.')

    return df


def custom(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    model_id: _Union[str, list],
    output: _Union[str, list] = None,
    case_sensitive: bool = False,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Standardize data using a DIY or bespoke standardization wrangle. Requires WrangleWorks Account and Subscription.
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name or list of input columns.
      output:
        type:
          - string
          - array
        description: Name or list of output columns
      model_id:
        type:
          - string
          - array
        description: The ID of the wrangle to use (do not include 'find' and 'replace')
      case_sensitive:
        type: boolean
        description: Allows the wrangle to be case sensitive if set to True, default is False.
    """
    # Import lazily to avoid a package initialization cycle. Delegating keeps
    # the existing recipe implementation as the single compatibility path.
    from .main import standardize as _legacy_standardize

    return _legacy_standardize(
        df=df,
        input=input,
        model_id=model_id,
        output=output,
        case_sensitive=case_sensitive,
        **kwargs
    )


def replace(df: _pd.DataFrame, input: _Union[str, int, list], find: str, replace: str, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Quick find and replace for simple values. Can use regex if 'input' in params and isinstance(params['input'], list):in the find field.
    additionalProperties: false
    required:
      - input
      - find
      - replace
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name or list of input column
      output:
        type:
          - string
          - array
        description: Name or list of output column
      find:
        type: string
        description: Pattern to find using regex
      replace:
        type: string
        description: Value to replace the pattern found
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    def custom_replacement(x, find, replace, row):
        if isinstance(x, (dict, list, bool)):  # Check if the input is an object
            # Raise warning
            if not getattr(custom_replacement, "_warning_logged", False):
                _logging.warning(
                    f"Found invalid values at row {row} when using replace. Dict, list and bool values will be skipped."
                )
                custom_replacement._warning_logged = True  # mark as logged
            return x  # Return the object as-is without modification

        try:
            return _re.sub(str(find), str(replace), str(x))  # Apply the regex substitution
        except:
            return x

    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = df.apply(lambda row: custom_replacement(row[input_column], find, replace, row=row.name), axis=1)

    return df
