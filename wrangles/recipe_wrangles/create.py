"""
Functions to create new columns
"""
import pandas as _pd
import uuid as _uuid
import numpy as _np
from typing import Union as _Union


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
    description: Create column(s) with a GUID
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
    description: Create column(s) with a UUID
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