"""
Functions to create new columns
"""
import pandas as _pd
import uuid as _uuid
import numpy as _np
from typing import Union as _Union
import math as _math


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
    # If a string provided, convert to list
    if isinstance(output, str): output = [output]

    # Loop through and create new columns
    for output_column in output:
        df[output_column] = value

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
        description: Namen of new column
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
    
    # Dealing with positive infinity. At end of bins list
    if isinstance(bins, list):
        if bins[-1] == '+':
            bins[-1] = _math.inf
        
        # Dealing with negative infinity. At start of bins list
        if bins[0] == '-':
            bins[0] = -_math.inf
    
    
    df[output] = _pd.cut(
        x=df[input],
        bins=bins,
        labels=labels,
        **kwargs
    )
    print(df[['IMAP_Value', 'Pricing']].head(10).to_markdown(index=False))
    
    return df
  