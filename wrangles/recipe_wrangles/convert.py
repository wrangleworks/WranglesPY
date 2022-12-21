"""
Functions to convert data formats and representations
"""
import pandas as _pd
import json as _json
from typing import Union as _Union


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
    if isinstance(input, str):
        input = [input]
        output = [output]

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
    if isinstance(input, str):
        input = [input]
        output = [output]
        
    # If the datatype is datetime
    if data_type == 'datetime':
        temp = _pd.to_datetime(df[input].stack(), **kwargs).unstack()
        df[output] = temp

    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            df[output_column] = df[input_column].astype(data_type)

    return df


def to_json(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Convert an object to a JSON representation.
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type: string
        description: Name of the input column.
      output:
        type: string
        description: Name of the output column. If omitted, the input column will be overwritten
    """
    # Set output column as input if not provided
    if output is None: output = input
    
    # If a string provided, convert to list
    if isinstance(input, str):
        input = [input]
        output = [output]
        
    # Loop through and apply for all columns
    for input_columns, output_column in zip(input, output):
        df[output_column] = [_json.dumps(row) for row in df[input_columns].values.tolist()]
        
    return df

    
def from_json(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Convert a JSON representation into an object
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type: string
        description: Name of the input column.
      output:
        type: string
        description: Name of the output column. If omitted, the input column will be overwritten
    """
    # Set output column as input if not provided
    if output is None: output = input
    
    # If a string provided, convert to list
    if isinstance(input, str):
        input = [input]
        output = [output]
        
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = [_json.loads(x) for x in df[input_column]]
    
    return df
