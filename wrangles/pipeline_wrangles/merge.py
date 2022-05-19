"""
Functions to merge data from one or more columns into a single column
"""
import pandas as _pd
from .. import format as _format
from typing import Union as _Union


def coalesce(df: _pd.DataFrame, input: list, output: str) -> _pd.DataFrame:
    """
    Return the first non-empty value from a list of columns

    :param input: List of input columns
    :param output: Column to output the results to
    """
    # NOTE: cleaner implementations that I've found implemented directly in pandas do not work with empty strings
    # If a better solution found, replace but ensure it works with all falsy values in python
    df[output] = _format.coalesce(df[input].fillna('').values.tolist())
    return df


def concatenate(df: _pd.DataFrame, input: _Union[str, list], output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    If input is a list of columns, concatenate multiple columns into one as a delimited string.

    If input is a single column, concatenate a list contained within that column into a delimited string.
    
    :param input: Either a single column name or list of columns
    :param output: Column to output the results to
    :return: Updated Dateframe
    """
    if isinstance(input, str):
        df[output] = _format.join_list(df[input].tolist(), parameters.get('char',','))
    elif isinstance(input, list):
        df[output] = _format.concatenate(df[input].astype(str).values.tolist(), parameters.get('char',','))
    else:
        raise ValueError('Unexpected data type for merge.concatenate / input')
    return df


def lists(df: _pd.DataFrame, input: list, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    Take multiple columns of lists and merge to a single output list

    >>> [a,b,c], [d,e,f]  ->  [a,b,c,d,e,f]

    :param input: List of input columns
    :param output: Column to output the results to
    :return: Updated Dataframe
    """
    remove_duplicates = parameters.get('remove_duplicates', False)

    output_list = []
    for row in df[input].values.tolist():
        output_row = []
        for col in row:
            if not isinstance(col, list): col = [str(col)]
            output_row += col
        # Use dict.fromkeys over set to preserve input order
        if remove_duplicates: output_row = list(dict.fromkeys(output_row))
        output_list.append(output_row)
    df[output] = output_list
    return df


def to_list(df: _pd.DataFrame, input: list, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    Take multiple columns and merge them to a list

    >>> Col1, Col2, Col3 -> [Col1, Col2, Col3]

    :param input: List of input columns
    :param output: Column to output the results to
    :return: Updated Dataframe
    """
    include_empty = parameters.get('include_empty', False)

    output_list = []
    for row in df[input].values.tolist():
        output_row = []
        for col in row:
            if col or include_empty: output_row.append(col)
        output_list.append(output_row)
    df[output] = output_list
    return df
    

def to_dict(df: _pd.DataFrame, input: list, output: str, parameters: dict = {}) -> _pd.DataFrame:
    """
    Take multiple columns and merge them to a dictionary (aka object) using the column headers as keys

    >>> Header1,Header2,Header3  ->  {'Header1':'Value1', 'Header2':'Value2', 'Header3':'Value3'}
    >>> Value1,Value2,Value3

    :param input: List of input columns
    :param output: Column to output the results to
    :return: Updated Dataframe
    """
    include_empty = parameters.get('include_empty', False)

    output_list = []
    column_headers = df[input].columns
    for row in df[input].values.tolist():
        output_dict = {}
        for col, header in zip(row, column_headers):
            if col or include_empty: output_dict[header] = col
        output_list.append(output_dict)
    df[output] = output_list
    return df