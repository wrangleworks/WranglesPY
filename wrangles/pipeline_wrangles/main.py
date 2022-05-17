"""
Standalone functions

These will be called directly, without belonging to a parent module
"""
from .. import classify as _classify
from .. import format as _format
from .. import match as _match
from ..standardize import standardize as _standardize
from .. import translate as _translate

import pandas as _pd
from typing import Union as _Union


def classify(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list], parameters: dict = {}) -> _pd.DataFrame:
    """
    Run classify wrangles on the specified columns

    :return: Update Dateframe
    """
    if isinstance(input, str):
        df[output] = _classify(df[input].astype(str).tolist(), **parameters)
    elif isinstance(input, list):
        # If a list of inputs is provided, ensure the list of outputs is the same length
        if len(input) != len(output):
            raise ValueError('If providing a list of inputs, a corresponding list of outputs must also be provided.')
        for input_column, output_column in zip(input, output):
            df[output_column] = _classify(df[input_column].astype(str).tolist(), **parameters)
        
    return df


def rename(df: _pd.DataFrame, input: _Union[str, list] = None, output: _Union[str, list] = None, **kwargs) -> _pd.DataFrame:
    """
    Rename a column or list of columns

    :return: Update Dateframe
    """
    # If short form of paired names is provided, use that
    if input is None:
        rename_dict = kwargs
    else:
        # Otherwise create a dict from input and output columns
        if isinstance(input, str):
            input = [input]
            output = [output]
        rename_dict = dict(zip(input, output))

    return df.rename(columns=rename_dict)


def standardize(df: _pd.DataFrame, input: str, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    Run a standardize wrangle

    :return: Update Dateframe
    """
    df[output] = _standardize(df[input].astype(str).tolist(), **parameters)
    return df


def translate(df: _pd.DataFrame, input: str, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    Translate the input

    :return: Update Dateframe
    """
    df[output] = _translate(df[input].astype(str).tolist(), **parameters)
    return df


def join(df: _pd.DataFrame, input: str, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    Join a list to a string e.g. ['ele1', 'ele2', 'ele3'] -> 'ele1,ele2,ele3'
    """
    df[output] = _format.join_list(df[input].tolist(), parameters['char'])
    return df

def concatenate(df: _pd.DataFrame, input: str, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    Concatenate multiple columns into one

    :return: Update Dateframe
    """
    df[output] = _format.concatenate(df[input].astype(str).values.tolist(), parameters['char'])
    return df

def split(df: _pd.DataFrame, input: str, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    Split to a string to multiple columns

    :return: Update Dateframe
    """
    df[output] = _format.split(df[input].astype(str).tolist(), parameters['char'])
    return df

def expand(df: _pd.DataFrame, input: str, output: str) -> _pd.DataFrame:
    """
    Expand an object to multiple columns

    :return: Update Dateframe
    """
    df[output] = [x for x in df[input].tolist()]
    return df


def match(df: _pd.DataFrame, input: list) -> _pd.DataFrame:
    """
    """
    df = _pd.concat([df, _match.run(df[input])], axis=1)
    return df