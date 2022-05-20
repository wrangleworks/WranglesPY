"""
Functions to convert data formats and representations
"""
import pandas as _pd
import json as _json
from typing import Union as _Union


def case(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list] = None, case: str = 'lower') -> _pd.DataFrame:
    """
    Change the case of the input.

    ```
    wrangles:
      - convert.case:
          input: column
          output: new column            # Optional
          case: lower                   # Optional
    ```
    :param df: Input Dataframe.
    :param input: Input column or list of columns to be operated on.
    :param output: (Optional) Output column or list of columns to save results to. Default - input columns will be replaced.
    :param case: (Optional) Desired case. upper, lower, title or sentence. Default - lower
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # Get the requested case, default lower
    desired_case = case.lower()

    # If a string provided, convert to list
    if isinstance(input, str):
        input = [input]
        output = [output]

    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        if desired_case == 'lower':
            df[output_column] = df[input_column].str.lower()
        elif desired_case == 'upper':
            df[output_column] = df[input_column].str.upper()
        elif desired_case == 'title':
            df[output_column] = df[input_column].str.title()
        elif desired_case == 'sentence':
            df[output_column] = df[input_column].str.capitalize()

    return df


def data_type(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list] = None, data_type: str = 'str') -> _pd.DataFrame:
    """
    Change the data type of the input.

    ```
    wrangles:
      - convert.data_type:
          input: column
          output: new column      # Optional
          data_type: str          # Optional
    ```
    :param df: Input Dataframe
    :param input: Input column or list of columns to be operated on
    :param output: (Optional) Output column or list of columns to save results to. Default - input columns will be replaced
    :param data_type: (Optional) Desired data type. Default str (string)
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if isinstance(input, str):
        input = [input]
        output = [output]

    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].astype(data_type)

    return df


def to_json(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    Convert an object to a JSON representation.

    ```
    wrangles:
      - convert.to_json:
          input: column
          output: new column       # Optional
    ```
    :param input: Name of the input column.
    :param output: (Optional) Name or list of output column(s). Default - input columns will be replaced
    """
    # Set output column as input if not provided
    if output is None: output = input

    df[output] = [_json.dumps(row) for row in df[input].values.tolist()]
    return df