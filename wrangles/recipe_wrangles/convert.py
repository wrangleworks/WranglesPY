"""
Functions to convert data formats and representations
"""
import ast as _ast
import copy as _copy
import json as _json
import math as _math
from typing import Union as _Union
import re as _re
import numpy as _np
import pandas as _pd
import logging as _logging
import yaml as _yaml
from ..utils import safe_str_transform as _safe_str_transform
import wrangles as _wrangles
from .standardize import _SENTENCE_CASE_RE, case, data_type, fraction_to_decimal
try:
    from yaml import CSafeLoader as _YAMLLoader, CSafeDumper as _YAMLDumper
except ImportError:
    from yaml import SafeLoader as _YAMLLoader, SafeDumper as _YAMLDumper

_DEFAULT_NOT_SET = object()


class _ObjectYAMLLoader(_YAMLLoader):
    """
    Safe YAML loader with JSON-like scalar resolution.

    Preserve YAML-only numeric forms, "yes", "on", and ISO dates as text.
    Their implicit conversions are surprising when YAML is being used as a
    tolerant parser for JSON-like data.
    """


_ObjectYAMLLoader.yaml_implicit_resolvers = {
    key: [
        (tag, regexp)
        for tag, regexp in resolvers
        if tag not in (
            "tag:yaml.org,2002:bool",
            "tag:yaml.org,2002:float",
            "tag:yaml.org,2002:int",
            "tag:yaml.org,2002:timestamp",
        )
    ]
    for key, resolvers in _YAMLLoader.yaml_implicit_resolvers.items()
}
_ObjectYAMLLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    _re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)
_ObjectYAMLLoader.add_implicit_resolver(
    "tag:yaml.org,2002:int",
    _re.compile(r"^-?(?:0|[1-9][0-9]*)$"),
    list("-0123456789"),
)
_ObjectYAMLLoader.add_implicit_resolver(
    "tag:yaml.org,2002:float",
    _re.compile(
        r"^-?(?:(?:0|[1-9][0-9]*)\.[0-9]+(?:[eE][-+]?[0-9]+)?|"
        r"(?:0|[1-9][0-9]*)[eE][-+]?[0-9]+)$"
    ),
    list("-0123456789"),
)



def _normalize_default_list(default, input: list, func_name: str) -> list:
    """
    Normalize a default value/list into a per-column list of defaults.

    A scalar (or a single-element list) is broadcast to all columns.
    A list with the same length as input is used as-is, one default per column.
    An empty list (`[]`) is treated as the default value itself, not a per-column list.
    """
    if isinstance(default, list) and len(default) > 0:
        if len(default) == 1:
            return [default[0]] * len(input)
        elif len(default) != len(input):
            raise ValueError(
                f'The list of default values must be a single value or the same length as input/output for {func_name}'
            )
        else:
            return default
    else:
        return [default] * len(input)


def _normalize_expected_list(expected, input: list) -> list:
    """
    Normalize expected object types into one value per input column.
    """
    if isinstance(expected, list):
        if len(expected) == 1:
            expected_values = expected * len(input)
        elif len(expected) != len(input):
            raise ValueError(
                "The list of expected types must be a single value or the "
                "same length as input/output for convert.parse"
            )
        else:
            expected_values = expected
    else:
        expected_values = [expected] * len(input)

    allowed = {"any", "dictionary", "list", "scalar"}
    if any(str(value).lower() not in allowed for value in expected_values):
        raise ValueError(
            "expected must be one of: any, dictionary, list, scalar"
        )
    return expected_values


def _is_missing_object_value(value) -> bool:
    """
    Return whether a scalar value represents a missing cell.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if _pd.api.types.is_scalar(value):
        try:
            return bool(_pd.isna(value))
        except (TypeError, ValueError):
            return False
    return False


def _normalize_json_compatible(value, active_ids=None):
    """
    Normalize and validate a JSON-compatible Python object tree.
    """
    if active_ids is None:
        active_ids = set()

    if isinstance(value, _np.ndarray):
        value = value.tolist()
    elif isinstance(value, _np.generic):
        value = value.item()

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not _math.isfinite(value):
            raise ValueError("Non-finite numbers are not supported")
        return value

    if isinstance(value, (list, dict)):
        value_id = id(value)
        if value_id in active_ids:
            raise ValueError("Recursive objects are not supported")
        active_ids.add(value_id)
        try:
            if isinstance(value, list):
                return [
                    _normalize_json_compatible(item, active_ids)
                    for item in value
                ]

            if not all(isinstance(key, str) for key in value):
                raise TypeError("Dictionary keys must be strings")
            return {
                key: _normalize_json_compatible(item, active_ids)
                for key, item in value.items()
            }
        finally:
            active_ids.remove(value_id)

    raise TypeError(
        f"Values of type {type(value).__name__} are not supported"
    )


def _parse_object_text_once(value: str):
    """
    Parse one layer of JSON, Python literal, or safe JSON-like YAML.
    """
    try:
        return _json.loads(value)
    except (_json.JSONDecodeError, TypeError):
        pass

    try:
        return _ast.literal_eval(value)
    except (ValueError, SyntaxError):
        pass

    try:
        # Scan before loading: CSafeLoader does not use Python compose_node
        # overrides, and expanding aliases during normalization can be costly.
        for token in _yaml.scan(value, Loader=_ObjectYAMLLoader):
            if isinstance(token, (_yaml.tokens.AnchorToken, _yaml.tokens.AliasToken)):
                raise ValueError("YAML anchors and aliases are not supported")
            if isinstance(token, _yaml.tokens.TagToken):
                raise ValueError("Explicit YAML tags are not supported")
        return _yaml.load(value, Loader=_ObjectYAMLLoader)
    except _yaml.YAMLError as error:
        raise ValueError("Value is not valid JSON, Python, or YAML") from error


def _looks_like_object_text(value: str) -> bool:
    """
    Return whether a parsed string appears to contain another object layer.
    """
    value = value.strip()
    return (
        (
            len(value) >= 2
            and (
                (value[0] == "{" and value[-1] == "}")
                or (value[0] == "[" and value[-1] == "]")
            )
        )
        or bool(_re.search(r"(^|\n)\s*[^:\n]+:\s+", value))
        or bool(_re.search(r"(^|\n)\s*-\s+", value))
    )


def _matches_expected_object_type(value, expected: str) -> bool:
    """
    Validate a parsed value against the requested result category.
    """
    expected = str(expected).lower()
    if expected == "any":
        return True
    if expected == "dictionary":
        return isinstance(value, dict)
    if expected == "list":
        return isinstance(value, list)
    if expected == "scalar":
        return not isinstance(value, (dict, list))
    raise ValueError(
        "expected must be one of: any, dictionary, list, scalar"
    )


def parse(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, list] = None,
    default=_DEFAULT_NOT_SET,
    expected: _Union[str, list] = "any",
) -> _pd.DataFrame:
    """
    type: object
    description: >-
      Parse JSON, Python, YAML, or human-readable JSON-like structures into
      JSON-compatible Python values. YAML-only numeric forms such as 00123
      and 12:34 remain strings. YAML anchors, aliases, and explicit tags
      are not supported. Parsed values retain their Python types, preserving
      integer precision in mixed columns. Excessively nested inputs use the
      configured default or raise a contextual ValueError.
    additionalProperties: false
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
        description: >-
          Name or list of output columns. If omitted, the input columns
          will be overwritten.
      default:
        type: ["string","array","object","number","boolean","null"]
        description: >-
          Value to return for missing, invalid, or type-mismatched rows.
          If input is a list, default may be a single value applied to every
          column or a list containing one value per input column.
          Defaults must be JSON-compatible; NumPy values are normalized and
          mutable defaults are copied independently for each row.
      expected:
        description: >-
          Required result category. Use any, dictionary, list, or scalar.
          A list may provide one category per input column.
        default: any
        oneOf:
          - type: string
            enum: [any, dictionary, list, scalar]
          - type: array
            items:
              type: string
              enum: [any, dictionary, list, scalar]
    """
    if output is None:
        output = input

    if not isinstance(input, list):
        input = [input]
    if not isinstance(output, list):
        output = [output]

    if len(input) != len(output):
        raise ValueError(
            "The lists for input and output must be the same length."
        )

    defaults = _normalize_default_list(
        default,
        input,
        "convert.parse",
    )
    expected_types = _normalize_expected_list(expected, input)

    for input_column, output_column, col_default, col_expected in zip(
        input,
        output,
        defaults,
        expected_types,
    ):
        if col_default is not _DEFAULT_NOT_SET:
            try:
                col_default = _normalize_json_compatible(col_default)
            except (TypeError, ValueError, RecursionError) as error:
                raise ValueError(
                    f"Invalid default for column '{input_column}' "
                    f"in convert.parse: {error}"
                ) from error

        def _convert_value(value):
            if _is_missing_object_value(value):
                if col_default is _DEFAULT_NOT_SET:
                    return None
                return _copy.deepcopy(col_default)

            try:
                if isinstance(value, str):
                    result = _parse_object_text_once(value.strip())
                    if (
                        isinstance(result, str)
                        and _looks_like_object_text(result)
                    ):
                        result = _parse_object_text_once(result.strip())
                else:
                    result = value

                result = _normalize_json_compatible(result)
                if not _matches_expected_object_type(result, col_expected):
                    raise TypeError(
                        f"Result is not a valid {col_expected}"
                    )
                return result
            except (TypeError, ValueError, RecursionError) as error:
                if col_default is not _DEFAULT_NOT_SET:
                    return _copy.deepcopy(col_default)
                try:
                    value_repr = repr(value)
                except RecursionError:
                    value_repr = "<value too deeply nested to display>"
                raise ValueError(
                    f"Unable to convert value in column '{input_column}' "
                    f"to a {col_expected} object: {value_repr}. "
                    "Set a default to replace invalid rows."
                ) from error

        # Inferred numeric dtypes can round integers when mixed with floats
        # or missing values. Preserve each parsed value and the source index.
        df[output_column] = _pd.Series(
            [_convert_value(value) for value in df[input_column]],
            index=df.index,
            dtype=object,
        )

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
