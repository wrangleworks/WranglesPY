"""
Functions to re-format data
"""
import pandas as _pd
from .. import format as _format


def price_breaks(df: _pd.DataFrame, input: list, categoryLabel: str, valueLabel: str) -> _pd.DataFrame: # pragma: no cover
    """
    Rearrange price breaks
    """
    df = _pd.concat([df, _format.price_breaks(df[input], categoryLabel, valueLabel)], axis=1)
    return df


def remove_duplicates(df: _pd.DataFrame, input: str, output: str = None) -> _pd.DataFrame:
    """
    type: object
    description: Remove duplicates from a list. Preserves input order.
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type: string
        description: Name of the input column
      output:
        type: string
        description: Name of the output column
    """
    # If user hasn't provided an output, overwrite input
    if output is None: output = input

    # If the input is a string
    if isinstance(input, str) and isinstance(output, str):
        df[output] = _format.remove_duplicates(df[input].values.tolist())
    
    # If the input is multiple columns (a list)
    elif isinstance(input, list) and isinstance(output, list):
        for in_col, out_col in zip(input, output):
            df[out_col] =  _format.remove_duplicates(df[in_col].values.tolist())

    # If the input and output are not the same type
    elif type(input) != type(output):
        raise ValueError('If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided.')

    return df


def trim(df: _pd.DataFrame, input: str, output: str = None) -> _pd.DataFrame:
    """
    type: object
    description: Remove excess whitespace at the start and end of text.
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - string
          - array
        description: Name of the input column
      output:
        type:
          - string
          - array
        description: Name of the output column
    """
    if output is None: output = input

    # If a string provided, convert to list
    if isinstance(output, str): output = [output]

    # Loop through and create uuid for all requested columns
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].str.strip()

    return df
    

def prefix(df: _pd.DataFrame, input: str, value: str, output: str = None) -> _pd.DataFrame:
    """
    type: object
    description: Add a prefix to a column
    additionalProperties: false
    required:
      - input
      - value
    properties:
      input:
        type:
          - string
          - array
        description: Name of the input column
      value:
        type:
          - string
        description: Prefix value to add
      output:
        type:
          - string
          - array
        description: (Optional) Name of the output column
    """
    # If the output is not specified
    if output is None: output = input

    # If the input is a string
    if isinstance(input, str) and isinstance(output, str):  
        df[output] = value + df[input].astype(str)
    
    # If the input is multiple columns (a list)
    elif isinstance(input, list) and isinstance(output, list):
        for in_col, out_col in zip(input, output):
            df[out_col] = value + df[in_col].astype(str)
    
    # If the input and output are not the same type
    elif type(input) != type(output):
        raise ValueError('If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided.')

    return df


def suffix(df: _pd.DataFrame, input: str, value: str, output: str = None) -> _pd.DataFrame:
    """
    type: object
    description: Add a suffix to a column
    additionalProperties: false
    required:
        - input
        - value
    properties:
        input:
          type:
            - string
            - array
          description: Name of the input column
        value:
          type: string
          description: Suffix value to add
        output:
          type:
            - string
            - array
          description: (Optional) Name of the output column
    """
    # If the output is not specified
    if output is None: output = input

    # If the input is a string
    if isinstance(input, str) and isinstance(output, str):
        df[output] = df[input].astype(str) + value

    # If the input is multiple columns (a list)
    elif isinstance(input, list) and isinstance(output, list):
        for in_col, out_col in zip(input, output):
            df[out_col] = df[in_col].astype(str) + value

    # If the input and output are not the same type
    elif type(input) != type(output):
        raise ValueError('If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided.')
  
    return df


def dates(df: _pd.DataFrame, input: str, format: str, output: str = None) -> _pd.DataFrame:
    """
    type: object
    description: Format a date
    additionalProperties: false
    required:
      - input
      - format
    properties:
      input:
        type:
          - string
        description: Name of the input column
      output:
        type:
          - string
        description: Name of the output column
      format:
        type:
          - string
        description: String pattern to format date
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input
    
    # convert the column to timestamp type and format date
    df[output] = _pd.to_datetime(df[input]).dt.strftime(format)
    
    return df
