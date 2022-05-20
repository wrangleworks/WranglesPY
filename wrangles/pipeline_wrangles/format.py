"""
Functions to re-format data
"""
import pandas as _pd
from .. import format as _format


def price_breaks(df: _pd.DataFrame, input: list, categoryLabel: str, valueLabel: str) -> _pd.DataFrame:
    """
    Rearrange price breaks
    """
    df = _pd.concat([df, _format.price_breaks(df[input], categoryLabel, valueLabel)], axis=1)
    return df


def remove_duplicates(df: _pd.DataFrame, input: str, output: str) -> _pd.DataFrame:
    output_list = []
    for row in df[input].values.tolist():
        if isinstance(row, list):
            output_list.append(list(dict.fromkeys(row)))
        else:
            output_list.append(row)
    df[output] = output_list
    return df