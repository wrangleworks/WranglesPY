"""
Functions to convert data formats and representations
"""
import json as _json
from typing import Union as _Union
import re as _re
import pandas as _pd
from fractions import Fraction as _Fraction
import yaml as _yaml


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
            fractions = fractions = _re.finditer(r'\b(\d+[\s-])?\d+/\d+\b', item)
            replacement_list = []
            for match in fractions:
                fraction_str = match.group()
                                
                # Get only the fraction part with or without whole number
                fraction = _Fraction(_re.findall(r'\d+\/\d+', fraction_str)[0])
                decimal = round(float(fraction), decimals)
                
                # try to see if there is a whole number
                if _re.findall(r'(\d+[\s-])', fraction_str):
                    # remove the "-" from the whole number
                    whole_number = _re.findall(r'(\d+[\s-])', fraction_str)[0].strip()
                    whole_number = _re.sub(r'-', "", whole_number)
                    whole_number = int(whole_number)
                    decimal = whole_number + decimal
                
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
        **kwargs
        ) -> _pd.DataFrame:
    """
    type: object
    description: Convert a JSON representation into an object
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
        df[output_column] = [_json.loads(x, **kwargs) for x in df[input_column]]
    
    return df


def to_json(
        df: _pd.DataFrame, 
        input: _Union[str, list], 
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
            _json.dumps(row, ensure_ascii=ensure_ascii, **kwargs) 
            for row in df[input_columns].values.tolist()
            ]
        
    return df


def from_yaml(
    df: _pd.DataFrame, 
    input: _Union[str, list], 
    output: _Union[str, list] = None,
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
          - array
        description: Name of the input column.
      output:
        type:
          - string
          - array
        description: >-
          Name of the output column.
          If omitted, the input column will be overwritten
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
        df[output_column] = [
            _yaml.safe_load(x, **kwargs)
            for x in df[input_column]
        ]
    
    return df


def to_yaml(
    df: _pd.DataFrame, 
    input: _Union[str, list], 
    output: _Union[str, list] = None, 
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
          If sort_keys is true (default: True),
          then the output of dictionaries will be sorted by key.
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
            _yaml.dump(row, **kwargs) 
            for row in df[input_columns].values.tolist()
        ]
        
    return df
