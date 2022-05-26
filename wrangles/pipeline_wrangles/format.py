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


def trim(df: _pd.DataFrame, input: str, output: str = None) -> _pd.DataFrame:
    """
    type: object
    description: Remove excess whitespace at the start and end of text
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - array
          - string
        description: Name of the input column
      output:
        type:
          - array
          - string
        description: Name of the output column
    """
    if output is None: output = input

    # If a string provided, convert to list
    if isinstance(output, str): output = [output]

    # Loop through and create uuid for all requested columns
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].str.strip()

    return df