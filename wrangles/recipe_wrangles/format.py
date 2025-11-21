"""
Functions to re-format data
"""
from typing import Union as _Union
import pandas as _pd
from .. import format as _format
from ..utils import safe_str_transform as _safe_str_transform


def dates(df: _pd.DataFrame, input: _Union[str, int, list], format: str, output: _Union[str, list] = None) -> _pd.DataFrame:
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
          - integer
          - array
        description: Name of the input column
      output:
        type:
          - string
          - array
        description: Name of the output column
      format:
        type:
          - string
        description: String pattern to format date
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # If the input and output are not the same type
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        # convert the column to timestamp type and format date
        df[output_column] = _pd.to_datetime(df[input_column]).dt.strftime(format)
    
    return df
    
    
def pad(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    pad_length: int,
    side: str,
    char: str,
    output: _Union[str, list] =  None,
    skip_empty: bool = False
) -> _pd.DataFrame:
    """
    type: object
    description: Pad a string to a fixed length
    additionalProperties: false
    required:
      - input
      - pad_length
      - side
      - char
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the input column
      output:
        type:
          - string
          - array
        description: Name of the output column
      pad_length:
        type:
          - number
        description: Length for the output
      side:
        type:
          - string
        description:  Side from which to fill resulting string
      char:
        type:
          - string
        description: The character to pad the input with
      skip_empty:
        type: boolean
        description: If true, skip padding for empty or whitespace-only values
        default: (Optional) false
  """
    char = str(char)
    # If the output is not specified, overwrite input columns in place
    if output is None: output = input
    
    # If the input is a string
    if isinstance(input, str): input = [input]
    if isinstance(output, str): output = [output]

    # If the input and output are not the same type
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
  
    for input_column, output_column in zip(input, output):
      if skip_empty:  
        # Create a mask for non-empty values  
        mask = df[input_column].astype(str).str.strip() != ''  

        # Initialize output column with input values  
        df[output_column] = df[input_column].astype(str)  
        
        # Only pad non-empty values  
        df.loc[mask, output_column] = df.loc[mask, input_column].astype(str).str.pad(pad_length, side, char)  
      else:  
        df[output_column] = df[input_column].astype(str).str.pad(pad_length, side, char)
    
    return df


def prefix(
        df: _pd.DataFrame,
        input: _Union[str, int, list],
        value: _Union[str, int, float],
        output: _Union[str, list] = None,
        skip_empty: bool = False) -> _pd.DataFrame:
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
          - integer
          - array
        description: Name of the input column
      value:
        type:
          - string
          - number
        description: Prefix value to add
      output:
        type:
          - string
          - array
        description: (Optional) Name of the output column
      skip_empty:
        type: boolean
        desription: Whether to skip empty values
        default: (Optional) false
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # If the input and output are not the same type
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        if skip_empty:
          df[output_column] = df[input_column].apply(lambda x: value + x if x else x)
        else:  
          df[output_column] = str(value) + df[input_column].astype(str)

    return df


def remove_duplicates(df: _pd.DataFrame, input: _Union[str, int, list], output: _Union[str, list] = None, ignore_case: bool = False) -> _pd.DataFrame:
    """
    type: object
    description: Remove duplicates from a list. Preserves input order.
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type: 
          - string
          - integer
          - array
        description: Name of the input column
      output:
        type: 
          - string
          - array
        description: Name of the output column
      ignore_case:
        type: boolean
        description: Ignore case when removing duplicates
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # If the input and output are not the same type
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] =  _format.remove_duplicates(df[input_column].values.tolist(), ignore_case)

    return df


def significant_figures(df: _pd.DataFrame, input: _Union[str, int, list], significant_figures: int = 3, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Format a value to a specific number of significant figures
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the input column
      output:
        type:
          - string
          - array
        description: Name of the output column
      significant_figures:
        type:
          - integer
        description: Number of significant figures to format to. Default is 3.
    """
    if output is None: output = input
    
    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    # Loop through all requested columns and apply sig figs
    for input_column, output_column in zip(input, output):
        df[output_column] = _format.significant_figures(df[input_column].to_list(), significant_figures)
        
    return df


def suffix(
        df: _pd.DataFrame,
        input: _Union[str, int, list],
        value: _Union[str, int, float, list],
        output: str = None,
        skip_empty: bool = False
  ) -> _pd.DataFrame:
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
            - integer
            - array
          description: Name of the input column
        value:
          type:
            - string
            - number
          description: Suffix value to add
        output:
          type:
            - string
            - array
          description: (Optional) Name of the output column
        skip_empty:
          type: boolean
          description: Whether to skip empty values
          default: (Optional) false
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # If the input and output are not the same type
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        if skip_empty:
          df[output_column] = df[input_column].apply(lambda x: x + value if x else x)
        else:  
          df[output_column] = df[input_column].astype(str) + str(value)
  
    return df


def trim(df: _pd.DataFrame, input: _Union[str, int, list], output: _Union[str, list] = None) -> _pd.DataFrame:
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
          - integer
          - array
        description: Name of the input column
      output:
        type:
          - string
          - array
        description: Name of the output column
    """
    if output is None: output = input

    # If a single input, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    warnings = {
        "invalid_data": {
            "logged": False,
            "message": 'Found invalid values when using format.trim. Non-string values will be skipped.'
        }
    }

    # Loop through all requested columns
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].apply(lambda x: _safe_str_transform(x, "strip", warnings))

    return df
    

# Undocumented
def price_breaks(df: _pd.DataFrame, input: list, categoryLabel: str, valueLabel: str) -> _pd.DataFrame: # pragma: no cover
    """
    Rearrange price breaks
    """
    df = _pd.concat([df, _format.price_breaks(df[input], categoryLabel, valueLabel)], axis=1)
    return df
