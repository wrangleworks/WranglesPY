"""Structural recipe operations for splitting and serializing data."""

import json as _json
from typing import Union as _Union

import numpy as _np
import pandas as _pd
import yaml as _yaml

from ._serialization import _YAMLLoader, _YAMLDumper, _normalize_default_list

from .split import dictionary as split_dictionary
from .split import list as split_list
from .split import text as split_text
from .split import tokenize


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
