"""
Functions to run extraction wrangles
"""
import pandas as _pd
from typing import Union as _Union
from .. import extract as _extract


def address(df: _pd.DataFrame, input: str, output: str) -> _pd.DataFrame:
    """
    """
    df[output] = _extract.address(df[input].astype(str).tolist())
    return df


def attributes(df: _pd.DataFrame, input: str, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    """
    df[output] = _extract.attributes(df[input].astype(str).tolist(), **parameters)
    return df


def codes(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list]) -> _pd.DataFrame:
    """
    
    """
    if isinstance(input, str):
        df[output] = _extract.codes(df[input].astype(str).tolist())
    elif isinstance(input, list):
        # If a list of inputs is provided, ensure the list of outputs is the same length
        if len(input) != len(output):
            raise ValueError('If providing a list of inputs, a corresponding list of outputs must also be provided.')
        for input_column, output_column in zip(input, output):
            df[output_column] = _extract.codes(df[input_column].astype(str).tolist())

    return df


def custom(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list], parameters: dict = {}) -> _pd.DataFrame:
    """
    
    """
    if isinstance(input, str):
        df[output] = _extract.custom(df[input].astype(str).tolist(), **parameters)
    elif isinstance(input, list):
        # If a list of inputs is provided, ensure the list of outputs is the same length
        if len(input) != len(output):
            raise ValueError('If providing a list of inputs, a corresponding list of outputs must also be provided.')
        for input_column, output_column in zip(input, output):
            df[output_column] = _extract.custom(df[input_column].astype(str).tolist(), **parameters)
            
    return df


def properties(df: _pd.DataFrame, input: str, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    """
    df[output] = _extract.properties(df[input].astype(str).tolist(), **parameters)
    return df