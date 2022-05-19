"""
Functions to convert data formats and representations
"""
import pandas as _pd
import json as _json


def case(df: _pd.DataFrame, input: str, output: str = None, parameters: dict = {}) -> _pd.DataFrame:
    """
    Change the case of the input

    ```
    wrangles:
      - convert.case:
          input: column
          output: new column
          parameters:
            case: lower
    ```

    :param df: Input Dataframe
    :param input: Input column or list of columns to be operated on
    :param output: (Optional) Output column or list of columns to save results to. If omitted, columns will be altered in place.
    :param parameters: Dict of settings - desired case
    :return: Update Dataframe
    """
    # TODO: enable list or string for input/output

    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # Get the requested case, default lower
    desired_case = parameters.get('case', 'lower').lower()

    if desired_case == 'lower':
        df[output] = df[input].str.lower()
    elif desired_case == 'upper':
        df[output] = df[input].str.upper()
    elif desired_case == 'title':
        df[output] = df[input].str.title()
    elif desired_case == 'sentence':
        df[output] = df[input].str.capitalize()

    return df


def data_type(df: _pd.DataFrame, input: str, output: str = None, parameters: dict = {}) -> _pd.DataFrame:
    """
    Change the data type of the input

    ```
    wrangles:
      - convert.data_type:
          input: column
          output: new column
          parameters:
            dataType: str
    ```
    :param df: Input Dataframe
    :param input: Input column or list of columns to be operated on
    :param output: (Optional) Output column or list of columns to save results to. If omitted, columns will be altered in place.
    :param parameters: Dict of settings - desired data type
    :return: Update Dataframe
    """
    # TODO: enable list or string for input/output

    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    df[output] = df[input].astype(parameters['dataType'])
    return df


def to_json(df: _pd.DataFrame, input: str, output: str = None) -> _pd.DataFrame:
    """
    Convert an object to a JSON representation

    :param input: Name of the input column.
    :param output: (Optional) Name of output column. If omitted, the input column will be replaced.
    """
    # Set output column as input if not provided
    if output is None: output = input

    output_list = []
    for row in df[input].values.tolist():
        output_list.append(_json.dumps(row))

    df[output] = output_list
    return df


