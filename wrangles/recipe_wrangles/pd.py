import pandas as _pd
from typing import Union as _Union


def copy(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list]) -> _pd.DataFrame:
    """
    type: object
    description: Make a copy of a column or a list of columns
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type:
          - string
          - array
        description: Name of the input columns or columns
      output:
        type:
          - string
          - array
        description: Name of the output columns or columns
    """
    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].copy()
        
    return df


def drop(df: _pd.DataFrame, column: _Union[str, list]) -> _pd.DataFrame:
    """
    type: object
    description: Drop (Delete) selected column(s)
    additionalProperties: true
    required:
      - column
    properties:
      column:
        type:
          - string
          - array
        description: Name of the column(s) to drop
    """
    # if a string provided, convert to list
    if not isinstance(column, list): column = [column]
    
    df = df.drop(columns=column)
    
    return df
    

def transpose(df: _pd.DataFrame) -> _pd.DataFrame:
    """
    type: object
    description: Drop (Delete) selected column(s)
    additionalProperties: true
    """
    df = df.transpose()
    
    return df

def round(df: _pd.DataFrame, input: _Union[str, list], decimals: int = 0, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Round column(s) to the specified decimals
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - string
          - array
        description: Name of the input column(s)
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
      decimals:
        type: number
        description: Number of decimal places to round column
    """
    
    if output is None: output = input
    
    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].round(decimals=decimals)
        
    return df


def map(df: _pd.DataFrame, arg, input: _Union[str, list], output: _Union[str, list] = None, na_action: str = None) -> _pd.DataFrame:
    """
    type: object
    description: Map values of Series according to an input mapping
    additionalProperties: false
    required:
      - arg
      - input
    properties:
      input:
        type:
          - string
          - array
        description: Name of the input column(s)
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
      arg:
        type:
          - object
        description: Mapping correspondence object
      na_action:
        type:
          - string
        description: Decide if values are passed to the mapping or ignored
        
    """
    
    if output is None: output = input
    
    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].map(arg=arg, na_action=na_action)
    
    return df
    
    
    