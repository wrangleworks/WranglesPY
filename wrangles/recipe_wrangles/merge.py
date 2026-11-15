"""
Functions to merge data from one or more columns into a single column
"""
from typing import Union as _Union
import fnmatch as _fnmatch

import logging as _logging
import pandas as _pd
from .. import format as _format
import numpy as _np
from .._data_contracts import (
    data_contract as _data_contract,
    text_matrix as _text_matrix,
    is_empty_scalar as _is_empty_scalar,
    is_missing_scalar as _is_missing_scalar,
    normalize_missing_values as _normalize_missing_values,
    assign_result as _assign_result,
)


def coalesce(
    df: _pd.DataFrame,
    input: list,
    output: str = None
) -> _pd.DataFrame:
    """
    type: object
    description: Take the first non-empty value from a series of columns or lists.
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - array
          - string
          - integer
        description: List of input columns or a single column containing lists
      output:
        type: string
        description: Name of the output columns. This is required if multiple input columns are provided.
    """
    # NOTE: cleaner implementations that I've found implemented directly in pandas do not work with empty strings
    # If a better solution found, replace but ensure it works with all falsy values in python

    # Ensure input is a list
    if not isinstance(input, list): input = [input]

    _logging.debug(f": Coalescing values :: input :: {input}")
    if len(input) == 1:
        if output is None:
            output = input[0]
        
        df[output] = _format.coalesce(
            [
                x if isinstance(x, list) else [x]
                for x in df[input[0]].fillna('')
            ]
        )
    else:
        if output is None:
            raise ValueError('An output column must be provided if coalescing multiple input columns')

        if df.empty:
            df[output] = _pd.Series(dtype=object)
            return df

        arr = df[input].fillna('').to_numpy(dtype=object)  # object array (n_rows, n_cols)
        n_rows = len(arr)
        m = len(input)

        # Fast C-level check: find first column per row where value != ''
        # This handles the common case of true empty strings efficiently
        mask = arr != ''
        idx = _np.argmax(mask, axis=1)
        has_any = mask.any(axis=1)
        result = arr[_np.arange(n_rows), idx].copy()
        result[~has_any] = ''

        # NOTE: arr != '' treats whitespace-only strings ('  ') as non-empty and
        # non-string falsy values (0, False) as non-empty. Handle those edge cases.
        # Strip only the n selected values (not all n*m) to find which need fallback.
        # Fast path: assume all values are strings (typical case). If non-string
        # values are present, fall back to a safe per-element strip.
        try:
            stripped_result = _np.frompyfunc(str.strip, 1, 1)(result)
        except (TypeError, AttributeError):
            def _safe_strip(x):
                try:
                    return x.strip()
                except AttributeError:
                    return x  # non-strings can't be whitespace-only
            stripped_result = _np.frompyfunc(_safe_strip, 1, 1)(result)
        needs_fallback = _np.where(has_any & (stripped_result == ''))[0]
        for i in needs_fallback:
            for j in range(int(idx[i]) + 1, m):
                val = arr[i, j]
                if isinstance(val, str):
                    val = val.strip()
                    if val:
                        result[i] = val
                        break
                else:
                    result[i] = val
                    break
            else:
                result[i] = ''

        df[output] = result.tolist()

    return df


@_data_contract(family='text_consumer', missing='stringify', non_text='stringify', notes='Multiple columns use text; a single column delegates native scalar/list handling.')
def concatenate(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: str,
    char: str = ',',
    skip_empty: bool = False
) -> _pd.DataFrame:
    """
    type: object
    description: Concatenate a list of columns or a list within a single column.
    additionalProperties: false
    required:
      - input
      - output
      - char
    properties:
      input:
        type: 
          - array
          - string
          - integer
        description: Either a single column name or list of columns
      output:
        type: string
        description: Name of the output column
      char:
        type: string
        description: (Optional) Character to add between successive values
      skip_empty:
        type: boolean
        desription: Whether to skip empty values
        default: false
    """
    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    _logging.debug(f": Concatenating columns :: input :: {input}, char :: {char}")
    if len(input) == 1:
        df[output[0]] = _format.concatenate(df[input[0]].values, char, skip_empty)
    else:
        df[output[0]] = _format.concatenate(_text_matrix(df[input], missing='stringify'), char, skip_empty)

    return df


def dictionaries(df: _pd.DataFrame, input: list, output: str, skip_empty: bool = False) -> _pd.DataFrame:
    """
    type: object
    description: Take dictionaries in multiple columns and merge them to a single dictionary.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: array
        description: list of input columns
      output:
        type: string
        description: Name of the output column
      skip_empty:
        type: boolean
        description: Whether to skip empty dictionaries when merging 
        default: false
    """

    _logging.debug(f": Merging dictionary columns :: input :: {input}")
    rows = df[input].values.tolist()  
      
    if skip_empty:  
        # Filter empty values during merge  
        output_list = [  
            {  
                key: value   
                for pair in row   
                for key, value in pair.items()   
                if value is not None and (not isinstance(value, str) or value.strip())  
            }  
            for row in rows  
        ]  
    else:  
        output_list = [  
            {key: value for pair in row for key, value in pair.items()}  
            for row in rows  
        ]  
      
    df[output] = output_list  

    return df

@_data_contract(family='structured', output='structured', notes='Normalize missing values, preserve keys; skip_empty adds whitespace text.')
def key_value_pairs(df: _pd.DataFrame, input: dict, output: str, skip_empty: bool = False) -> _pd.DataFrame:
    """
    type: object
    description: Create a dictionary from keys and values in paired columns e.g. COLUMN_NAME_1, COLUMN_VALUE_1, COLUMN_NAME_2, COLUMN_VALUE_2 ...
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: object
        description: Matched pairs of key and value columns
      output:
        type: string
        description: Name of the output column
      skip_empty:
        type: boolean
        description: Whether to skip empty keys or values when creating the dictionary
        default: false
    """
    _logging.debug(f": Creating key-value pairs :: input :: {input}")
    pairs = {}

    # If user has used wildcards, expand out
    for key, val in input.items():
        if '*' in key and '*' in val:
            key_columns = _fnmatch.filter(df.columns, key)
            val_columns = _fnmatch.filter(df.columns, val)
            for key_col, val_col in zip(key_columns, val_columns):
                pairs[key_col] = val_col
        else:
            pairs[key] = val

    # Preserve native values; scalar-null normalization is separate from text.
    results = [
        {
            row[key]: _normalize_missing_values(row[val])
            for key, val in pairs.items()
            if not skip_empty or (
                not _is_empty_scalar(row[key], whitespace=True)
                and not _is_empty_scalar(row[val], whitespace=True)
            )
        }
        for row in df.to_dict('records')
    ]
    _assign_result(df, output, results, output_kind='structured')

    return df


def lists(df: _pd.DataFrame, input: list, output: str, remove_duplicates: bool = False, ignore_case: bool = False, include_empty: bool = True) -> _pd.DataFrame:
    """
    type: object
    description: Take lists in multiple columns and merge them to a single list.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: array
        description: List of input columns
      output:
        type: string
        description: Name of the output column
      remove_duplicates:
        type: boolean
        description: Whether to remove duplicates from the created list
      ignore_case:
        type: boolean
        description: Ignore case when removing duplicates
      include_empty:
        type: boolean
        description: Whether to include empty values in the created list
    """
    _logging.debug(f": Merging list columns :: input :: {input}")
    output_list = []
    for row in df[input].values.tolist():
        output_row = []
        for col in row:
            if not isinstance(col, list): 
                col = [str(col)]
            # Filter empty values if include_empty is False
            if include_empty:
                output_row += col
            else:
                output_row += [item for item in col if item]
        # Remove duplicates, regardless of case
        if remove_duplicates and ignore_case:
            seen = set()
            output_row = [x for x in output_row if x.lower() not in seen and not seen.add(x.lower())]

        # Use dict.fromkeys over set to preserve input order
        elif remove_duplicates and not ignore_case:
            output_row = list(dict.fromkeys(output_row))

        output_list.append(output_row)
    df[output] = output_list
    return df


@_data_contract(family='structured', output='structured', notes='Legacy include_empty zero filtering; booleans/nulls survive.')
def to_dict(df: _pd.DataFrame, input: list, output: str, include_empty: bool = False) -> _pd.DataFrame:
    """
    type: object
    description: Take multiple columns and merge them to a dictionary (aka object) using the column headers as keys.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type:
          - array
          - string
          - integer
        description: List of input columns
      output:
        type: string
        description: Name of the output column
      include_empty:
        type: boolean
        description: Whether to include empty columns in the created dictionary
    """
    _logging.debug(f": Converting columns to dict :: output :: {output}")
    output_list = []
    selected = df[input]
    for row in selected.itertuples(index=False, name=None):
        output_dict = {}
        for header, value in zip(selected.columns, row):
            # Retain the legacy include_empty contract for zero/empty cells.
            # Actual booleans and nulls always survive; literal marker strings
            # remain text instead of being reinterpreted after a round trip.
            if (
                isinstance(value, (bool, _np.bool_))
                or _is_missing_scalar(value)
                or include_empty
                or bool(value)
            ):
                output_dict[header] = _normalize_missing_values(value)
        output_list.append(output_dict)
    _assign_result(df, output, output_list, output_kind='structured')

    return df


def to_list(df: _pd.DataFrame, input: list, output: str, include_empty: bool = False) -> _pd.DataFrame:
    """
    type: object
    description: Take multiple columns and merge them to a list.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type:
          - array
          - string
          - integer
        description: List of input columns
      output:
        type: string
        description: Name of the output column
      include_empty:
        type: boolean
        description: Whether to include empty columns in the created list
    """
    _logging.debug(f": Converting columns to list :: output :: {output}")
    output_list = []
    for row in df[input].values.tolist():
        output_row = []
        for col in row:
            if col or include_empty: output_row.append(col)
        output_list.append(output_row)
    df[output] = output_list
    return df
