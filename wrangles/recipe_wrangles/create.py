"""
Functions to create new columns
"""
import pandas as _pd
import uuid as _uuid
import numpy as _np
from typing import Union as _Union
import math as _math
from ..connectors.test import _generate_cell_values


def column(df: _pd.DataFrame, output: _Union[str, list], value = None) -> _pd.DataFrame:
    """
    type: object
    description: Create column(s) with a user defined value. Defaults to None (empty).
    additionalProperties: false
    required:
      - output
    properties:
      output:
        type:
          - string
          - array
        description: Name or list of names of new columns
      value:
        type: string
        description: (Optional) Value to add in the new column(s). If omitted, defaults to None.
    """
    # Get list of existing columns
    existing_column = df.columns
    
    # Get number of rows in df
    rows = len(df)
    # Get number of columns created
    cols_created = len(output)
    # If a string provided, convert to list
    if isinstance(output, str):
      if output in existing_column:
        raise ValueError(f'"{output}" column already exists in dataFrame.')
      output = [output]
    
    # Allow for user to enter either a list and/or a string in output and value and not error
    if isinstance(value, list) and cols_created == 1:
        value = [value[0] for _ in range(cols_created)]
    elif isinstance(value, str):
        value = [value for _ in range(cols_created)]
    elif value == None:
        value = ['' for _ in range(cols_created)]
        
    # Check if the list of outputs exist in dataFrame
    check_list = [x for x in output if x in existing_column]
    if len(check_list) > 0:
      raise ValueError(f'{check_list} column(s) already exists in the dataFrame') 
    
    for output_column, values_list in zip(output, value):
        # Data to generate
        data = _pd.DataFrame(_generate_cell_values(values_list, rows), columns=[output_column])
        # Merging existing dataframe with values created
        df = _pd.concat([df, data], axis=1)

    return df


def guid(df: _pd.DataFrame, output: _Union[str, list]) -> _pd.DataFrame:
    """
    type: object
    description: Create column(s) with a GUID.
    additionalProperties: false
    required:
      - output
    properties:
      output:
        type:
          - string
          - array
        description: Name or list of names of new columns
    """
    return uuid(df, output)


def index(df: _pd.DataFrame, output: _Union[str, list], start: int = 1, step: int = 1) -> _pd.DataFrame:
    """
    type: object
    description: Create column(s) with an incremental index.
    additionalProperties: false
    required:
      - output
    properties:
      output:
        type:
          - string
          - array
        description: Name or list of names of new columns
      start:
        type: integer
        description: (Optional; default 1) Starting number for the index
      step:
        type: integer
        description: (Optional; default 1) Step between successive rows
    """
    # If a string provided, convert to list
    if isinstance(output, str): output = [output]

    # Loop through and create incremental index
    for output_column in output:
        df[output_column] = _np.arange(start, len(df) * step + start, step=step)

    return df


def uuid(df: _pd.DataFrame, output: _Union[str, list]) -> _pd.DataFrame:
    """
    type: object
    description: Create column(s) with a UUID.
    additionalProperties: false
    required:
      - output
    properties:
      output:
        type:
          - string
          - array
        description: Name or list of names of new columns
    """
    # If a string provided, convert to list
    if isinstance(output, str): output = [output]

    # Loop through and create uuid for all requested columns
    for output_column in output:
        df[output_column] = [_uuid.uuid4() for _ in range(len(df.index))]

    return df
    
    
def bins(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list], bins: _Union[int, list], labels: _Union[str, list] = None, **kwargs):
    """
    type: object
    description: Creates a column that segment and sort data values into bins
    additionalProperties: false
    required:
      - input
      - output
      - bins
    properties:
      input:
        type:
          - array
        description: Name of input column
      output:
        type:
          - array
        description: Name of new column
      bins:
        type:
          - integer
          - array
        description: Defines the number of equal-width bins in the range
      labels:
        type:
          - string
          - array
        description: Labels for the returned bins
    """
    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    for in_col, out_col in zip(input, output):
      # Dealing with positive infinity. At end of bins list
      if isinstance(bins, list):
          if bins[-1] == '+':
              bins[-1] = _math.inf
          
          # Dealing with negative infinity. At start of bins list
          if bins[0] == '-':
              bins[0] = -_math.inf
      
      df[out_col] = _pd.cut(
          x=df[in_col],
          bins=bins,
          labels=labels,
          **kwargs
      )
    
    return df
