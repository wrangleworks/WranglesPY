"""
Split a single column to multiple columns
"""
# Rename List to _list to be able to use function name list without clashing
from typing import Union as _Union, List as _list
import pandas as _pd
from .. import format as _format
import json as _json


def dictionary(df: _pd.DataFrame, input: _Union[str, _list], default: dict = {}) -> _pd.DataFrame:
    """
    type: object
    description: Split a dictionary into columns. The dictionary keys will be used as the new column headers.
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type: 
          - string
          - array
        description: Name of the column(s) to be split
      default:
        type: object
        description: >-
          Provide a set of default headings and values
          if they are not found within the input
    """ 
    # storing data as df temp to prevent the original data to be changed
    df_temp = df[input]

    # Ensure input is passed as a list
    if not isinstance(input, _list):
        input = [input]

    df_dict = {}
    for i in range(len(input)):
        try:
            df_temp = [_json.loads('{}') if x == '' else _json.loads(x) for x in df[input[i]]]
        except:
            df_temp = [{} if x == None else x for x in df[input[i]]]
        if default:
            df_temp = [{**default, **x} for x in df[input[i]]]

        df_dict['df{0}'.format(i)] = _pd.json_normalize(df_temp, max_level=0).fillna('')
        df_dict['df{0}'.format(i)].set_index(df.index, inplace=True)  # Restore index to ensure rows match

    # Combine dataframes for output
    for data in df_dict:
        df[df_dict[data].columns] = df_dict[data]

    return df

    
def list(df: _pd.DataFrame, input: str, output: _Union[str, _list]) -> _pd.DataFrame:
    """
    type: object
    description: Split a list in a single column to multiple columns.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: string
        description: Name of the column to be split
      output:
        type:
          - string
          - array
        description: Name of column(s) for the results. If providing a single column, use a wildcard (*) to indicate a incrementing integer
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
        # Else they should have provided a list for all the output columns
        df[output] = results

    return df


def text(
    df: _pd.DataFrame,
    input: str,
    output: _Union[str, _list] = None,
    char: str = ',',
    pad: bool = None,
    element: _Union[int, str] = None,
    inclusive: bool = False
) -> _pd.DataFrame:
    """
    type: object
    description: Split a string to multiple columns or a list.
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type: string
        description: Name of the column to be split
      output:
        type:
          - string
          - array
        description: |-
          Name of the output column(s)
          If a single column is provided,
          the results will be returned as a list
          If multiple columns are listed,
          the results will be separated into the columns.
          If omitted, will overwrite the input.
      char:
        type: string
        description: |-
          Set the character(s) to split on.
          Default comma (,)
          Can also prefix with "regex:" to split on a pattern.
      pad:
        type: boolean
        description: >-
          Choose whether to pad to ensure a consistent length.
          Default true if outputting to columns, false for lists.
      element:
        type: 
          - integer
          - string
        description: >-
          Select a specific element or range after splitting
          using slicing syntax. e.g. 0, ":5", "5:", "2:8:2"
      inclusive:
        type: boolean
        description: >-
          If true, include the split character in the output.
          Default False
    """
    # Ensure only a single input column is specified
    if isinstance(input, _list):
        if len(input) != 1:
            raise ValueError("Only a single column is allowed for input.")
        else:
            input = input[0]

    # If user didn't provide an output, overwrite the input
    if output is None:
        output = input

    if pad is None:
        # If user has specified output columns either named
        # or using a wildcard, set pad = True
        if (
            (isinstance(output, str) and '*' in output)
            or isinstance(output, _list)
        ):
            pad = True
        else:
            pad = False

    results = _format.split(
        df[input].astype(str).values,
        output_length = len(output) if isinstance(output, _list) else None,
        split_char = char,
        pad = pad,
        inclusive = inclusive,
        element = element
    )

    if isinstance(output, str) and '*' in output:
        # If user has entered a wildcard in the output column name
        # then add results to that with an incrementing index for each column
        # column * -> column 1, column 2, column 3...
        output_headers = []
        for i in range(1, len(results[0]) + 1):
            output_headers.append(output.replace('*', str(i)))
        df[output_headers] = results

    else:
        # User has given a single column - return as a list within that column
        df[output] = results
        
    return df


def tokenize(df: _pd.DataFrame, input: _Union[str, _list], output: _Union[str, _list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Tokenize elements in a list into individual tokens.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type:
          - string
          - array
        description: list in column to split
      output:
        type: 
          - string
          - array
        description: Name of the output column
    """
    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, _list): input = [input]
    if not isinstance(output, _list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The list of inputs and outputs must be the same length for split.tokenize')
    
    for in_col, out_col in zip(input, output):
        df[out_col] = _format.tokenize(df[in_col].values.tolist())
            
    return df
