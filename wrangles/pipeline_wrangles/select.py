"""
Functions to select data from within columns
"""
from .. import select as _select
import pandas as _pd


def list_element(df: _pd.DataFrame, input: str, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    Select a numbered element of a list (zero indexed)
    """
    df[output] = _select.list_element(df[input].tolist(), parameters.get('element', 0))
    return df


def dictionary_element(df: _pd.DataFrame, input: str, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    Select a named element of a dictionary
    """
    df[output] = _select.dict_element(df[input].tolist(), parameters['element'])
    return df


def highest_confidence(df: _pd.DataFrame, input: list, output: str) -> _pd.DataFrame:
    """
    Select the option with the highest confidence from multiple columns. Inputs are expected to be of the form [<<value>>, <<confidence_score>>]
    """
    df[output] = _select.highest_confidence(df[input].values.tolist())
    return df


def threshold(df: _pd.DataFrame, input: list, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    Select the first option if it exceeds a given threshold, else the second option

    The first option must be of the form [<<value>>, <<confidence_score>>]
    """
    df[output] = _select.confidence_threshold(df[input[0]].tolist(), df[input[1]].tolist(), parameters['threshold'])
    return df