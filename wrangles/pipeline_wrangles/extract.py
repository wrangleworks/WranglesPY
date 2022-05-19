"""
Functions to run extraction wrangles
"""
import pandas as _pd
from typing import Union as _Union
from .. import extract as _extract
from .. import format as _format


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
            if isinstance(output, str):
                df[output] = _extract.codes(_format.concatenate(df[input].astype(str).values.tolist(), ' aaaaaaa '))
            else:
                raise ValueError('If providing a list of inputs, a corresponding list of outputs must also be provided.')
        else:
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
            if isinstance(output, str):
                df[output] = _extract.custom(_format.concatenate(df[input].astype(str).values.tolist(), ' '), **parameters)
            else:
                raise ValueError('If providing a list of inputs, a corresponding list of outputs must also be provided.')
        else:
            for input_column, output_column in zip(input, output):
                df[output_column] = _extract.custom(df[input_column].astype(str).tolist(), **parameters)
            
    return df


def properties(df: _pd.DataFrame, input: str, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    """
    df[output] = _extract.properties(df[input].astype(str).tolist(), **parameters)
    return df
    
    
    
# SUPER MARIO
def diff(df: _pd.DataFrame, input: str, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    """
    df[output] = _extract.diff(df[input].values.tolist())
    return df