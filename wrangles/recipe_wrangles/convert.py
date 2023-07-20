"""
Functions to convert data formats and representations
"""
import json as _json
from typing import Union as _Union
import re as _re
import pandas as _pd
from fractions import Fraction as _Fraction


def case(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list] = None, case: str = 'lower') -> _pd.DataFrame:
    """
    type: object
    description: Change the case of the input.
    additionalProperties: false
    required:
      - input
      - case
    properties:
      input:
        type:
          - string
          - array
        description: Name or list of input columns
      output:
        type:
          - string
          - array
        description: Name or list of output columns
      case:
        type: string
        description: The case to convert to. lower, upper, title or sentence
        enum:
          - lower
          - upper
          - title
          - sentence
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # Get the requested case, default lower
    desired_case = case.lower()

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        if desired_case == 'lower':
            df[output_column] = df[input_column].str.lower()
        elif desired_case == 'upper':
            df[output_column] = df[input_column].str.upper()
        elif desired_case == 'title':
            df[output_column] = df[input_column].str.title()
        elif desired_case == 'sentence':
            df[output_column] = df[input_column].str.capitalize()

    return df


def data_type(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list] = None, data_type: str = 'str', **kwargs) -> _pd.DataFrame:
    """
    type: object
    description: Change the data type of the input.
    additionalProperties: false
    required:
      - input
      - data_type
    properties:
      input:
        type: 
          - string
          - array
        description: Name or list of input columns
      output:
        type:
          - string
          - array
        description: Name or list of output columns
      data_type:
        type: string
        description: The new data type
        enum:
          - str
          - float
          - int
          - bool
          - datetime
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    # If the datatype is datetime
    if data_type == 'datetime':
        temp = _pd.to_datetime(df[input].stack(), **kwargs).unstack()
        df[output] = temp

    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            df[output_column] = df[input_column].astype(data_type)

    return df


def fraction_to_decimal(df: _pd.DataFrame, input: str, decimals: int = 4, output = None) -> _pd.DataFrame:
    """
    type: object
    description: Convert fractions to decimals
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - string
        description: Name of the input column
      output:
        type:
          - string
        description: Name of the output colum
      decimals:
        type:
          - number
        description: Number of decimals to round fraction
    """
    # Set the output column as input if not provided
    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    for in_col, out_col in zip(input, output):
      results = []
      for item in df[in_col].astype(str):
          fractions = fractions = _re.finditer(r'\b\d+/\d+\b', item)
          replacement_list = []
          for match in fractions:
              fraction_str = match.group()
              fraction = _Fraction(fraction_str)
              decimal = round(float(fraction), decimals)
              replacement_list.append((fraction_str, str(decimal)))
          for fraction, dec in replacement_list:
              item = item.replace(fraction, dec)
          
          
          results.append(item)
          
      df[out_col] = results
    
    return df


def from_json(
        df: _pd.DataFrame, 
        input: _Union[str, list], 
        output: _Union[str, list] = None,
        ) -> _pd.DataFrame:
    """
    type: object
    description: Convert a JSON representation into an object
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - string
          - array
        description: Name of the input column.
      output:
        type:
          - string
          - array
        description: Name of the output column. If omitted, the input column will be overwritten
    """
    # Set output column as input if not provided
    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
        
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = [_json.loads(x) for x in df[input_column]]
    
    return df


def to_json(
        df: _pd.DataFrame, 
        input: _Union[str, list], 
        output: _Union[str, list] = None, 
        skipkeys: bool = False,
        ensure_ascii: bool = True,
        check_circular: bool = True,
        allow_nan: bool = True,
        indent: _Union[str, int] = None,
        separators: str = None,
        sort_keys: bool = False #### cls and default skipped because they both use a custom function/class
        ) -> _pd.DataFrame:
    """
    type: object
    description: Convert an object to a JSON representation.
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - string
          - array
        description: Name of the input column.
      output:
        type:
          - string
          - array
        description: Name of the output column. If omitted, the input column will be overwritten
      skipkeys:
        type: boolean
        description: If skipkeys is true (default: False), then dict keys that are not of a basic type (str, int, float, bool, None) 
          will be skipped instead of raising a TypeError.
      ensure_ascii: 
        type: boolean
        description: If ensure_ascii is true (the default), the output is guaranteed to have all incoming non-ASCII characters escaped. 
          If ensure_ascii is false, these characters will be output as-is.
      check_circular:
        type: boolean
        description: If check_circular is false (default: True), then the circular reference check for container types will be skipped 
          and a circular reference will result in a RecursionError (or worse).
      allow_nan:
        type: boolean
        description: If allow_nan is false (default: True), then it will be a ValueError to serialize out of range float values 
          (nan, inf, -inf) in strict compliance of the JSON specification. If allow_nan is true, their JavaScript equivalents 
          (NaN, Infinity, -Infinity) will be used.
      indent:
        type:
          - string
          - integer
        description: If indent is a non-negative integer or string, then JSON array elements and object members will be pretty-printed 
          with that indent level. An indent level of 0, negative, or "" will only insert newlines. None (the default) selects the most 
          compact representation. Using a positive integer indent indents that many spaces per level. If indent is a string (such as '\t'), 
          that string is used to indent each level.
      separators:
        type: str
        description: If specified, separators should be an (item_separator, key_separator) tuple. The default is (', ', ': ') if indent 
          is None and (',', ': ') otherwise. To get the most compact JSON representation, you should specify (',', ':') to eliminate whitespace.
      sort_keys:
        type: boolean
        description: If sort_keys is true (default: False), then the output of dictionaries will be sorted by key.
    """
    # Set output column as input if not provided
    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
        
    # Loop through and apply for all columns
    for input_columns, output_column in zip(input, output):
        df[output_column] = [
            _json.dumps(row, skipkeys, ensure_ascii, check_circular, allow_nan, indent, separators, sort_keys) 
            for row in df[input_columns].values.tolist()
            ]
        
    return df
