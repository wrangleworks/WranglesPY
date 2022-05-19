"""
Split a single column to multiple columns
"""
import pandas as _pd
from .. import format as _format
from typing import Union as _Union


def from_text(df: _pd.DataFrame, input: str, output: _Union[str, list], parameters: dict = {}) -> _pd.DataFrame:
    """
    Split a string to multiple columns or a list.

    For the output either a single column, a list of columns or a column name with a wildcard (*) may be entered.

    >>> "a,b,c"  ->  [a,b,c]  or a | b | c

    :param input: Name of column to be split.
    :param output: Name of column(s) for the results.
    :param parameters['char']: Defines the character to split on
    :return: Updated Dataframe
    """
    if isinstance(output, str) and '*' in output:
        # If user has entered a wildcard in the output column name
        # then add results to that with an incrementing index for each column
        # column * -> column 1, column 2, column 3...
        results = _format.split(df[input].astype(str).tolist(), parameters.get('char', ','), pad=True)
        output_headers = []
        for i in range(1, len(results[0]) + 1):
            output_headers.append(output.replace('*', str(i)))
        df[output_headers] = results

    elif isinstance(output, str) and not parameters.get('pad', False):
        # User has given a single column - return as a list within that column
        df[output] = _format.split(df[input].astype(str).tolist(), parameters.get('char', ','))

    elif isinstance(output, list) or parameters.get('pad', False):
        df[output] = _format.split(df[input].astype(str).tolist(), parameters.get('char', ','), pad=True)

    return df


def from_list(df: _pd.DataFrame, input: str, output: list) -> _pd.DataFrame:
    """
    Split a list in a single column to multiple columns

    For the output either a list of columns or a column name with a wildcard (*) may be entered.

    >>> [a,b,c]  ->  a | b | c

    :param input: Name of column to be split.
    :param output: Name of column(s) for the results.
    :return: Updated Dataframe
    """
    # Generate results and pad to a consistent length
    # as long as the max length
    max_len = max([len(x) for x in df[input].tolist()])
    results = [x + [''] * (max_len - len(x)) for x in df[input].tolist()]

    if isinstance(output, str) and '*' in output:
        # If user has provided a wildcard for the column name
        # then use that with an incrementing index
        output_headers = []
        for i in range(1, len(results[0]) + 1):
            output_headers.append(output.replace('*', str(i)))
        df[output_headers] = results

    else:
        # Else they should have provided a list for all the output fields
        df[output] = results

    return df


def from_dict(df: _pd.DataFrame, input: str) -> _pd.DataFrame:
    """
    Split a dictionary into columns. The dictionary keys will be used as the new column headers.

    >>>                                               Header1 | Header2
    >>> {'Header1':'Value1', 'Header2':'Value2'}  ->   Value1 |  Value2
    
    :param input: Input column name
    """
    exploded_df = _pd.json_normalize(df[input], max_level=1).fillna('')
    df[exploded_df.columns] = exploded_df
    return df