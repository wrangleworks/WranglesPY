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


    
    
def reindex(
        df: _pd.DataFrame,
        labels: list= None,
        index: list = None,
        columns: list = None,
        axis: _Union[str, int] = None,
        **kwargs
        ) -> _pd.DataFrame:
    """
    type: object
    description: Changes the row labels and column labels of a DataFrame.
    additionalProperties: false
    properties:
      labels:
        type: array
        description: New labels / index to conform the axis specified by ‘axis’ to.
      index:
        type: array
        description: New labels for the index. Preferably an Index object to avoid duplicating data.
      columns:
        type: array
        description: New labels for the columns. Preferably an Index object to avoid duplicating data.
      axis:
        type:
          - number
          - string
        description: Axis to target. Can be either the axis name (‘index’, ‘columns’) or number (0, 1).  
    """
    
    df = df.reindex(labels=labels, index=index, columns=columns, axis=axis, **kwargs)
    
    return df
    
