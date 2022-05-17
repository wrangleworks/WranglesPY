"""
Functions to create new columns
"""
import pandas as _pd
import uuid as _uuid
import numpy as _np
from typing import Union as _Union


def column(df: _pd.DataFrame, output: _Union[str, list], parameters: dict = {}) -> _pd.DataFrame:
    """
    Create a column with a user defined value. Defaults to None (empty).

    :param df: Input Dataframe
    :param output: New column to be created
    """
    # If a string provided, convert to list
    if isinstance(output, str): output = [output]

    # Loop through and create uuid for all requested columns
    for output_column in output:
        df[output_column] = parameters.get('value', None)

    return df


def guid(df: _pd.DataFrame, output: _Union[str, list]) -> _pd.DataFrame:
    """
    Create a column with a GUID
    """
    return uuid(df, output)


def index(df: _pd.DataFrame, output: _Union[str, list], parameters: dict = {}) -> _pd.DataFrame:
    """
    Create a new incremental index.
    """
    # Get start number if provided, default 1
    start = parameters.get('start', 1)

    # If a string provided, convert to list
    if isinstance(output, str): output = [output]

    # Loop through and create incremental index
    for output_column in output:
        df[output_column] = _np.arange(start, len(df) + start)

    return df


def uuid(df: _pd.DataFrame, output: _Union[str, list]) -> _pd.DataFrame:
    """
    Create a column with a UUID
    """
    # If a string provided, convert to list
    if isinstance(output, str): output = [output]

    # Loop through and create uuid for all requested columns
    for output_column in output:
        df[output_column] = [_uuid.uuid4() for _ in range(len(df.index))]

    return df