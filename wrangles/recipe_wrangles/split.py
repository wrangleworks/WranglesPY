"""
Split a single column to multiple columns
"""
# Rename List to _list to be able to use function name list without clashing
from typing import Union as _Union, List as _list
import pandas as _pd
from .. import format as _format
import json as _json
import itertools as _itertools


def dictionary(
    df: _pd.DataFrame,
    input: _Union[str, _list],
    output: _Union[str, _list] = None,
    default: dict = {}
) -> _pd.DataFrame:
    """
    type: object
    description: |-
      Split one or more dictionaries into columns.
      The dictionary keys will be returned as the new column headers.
      If the dictionaries contain overlapping values, the last value will be returned.
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type: 
          - string
          - array
        description: |-
          Name or lists of the column(s) containing dictionaries to be split.
          If providing multiple dictionaries and the dictionaries
          contain overlapping values, the last value will be returned.
      output:
        type: 
          - string
          - array
        description: |-
          (Optional) Subset of keys to extract from the dictionary.
          If not provided, all keys will be returned.
          Columns can be renamed with the following syntax:
          output:
            - key1: new_column_name1
            - key2: new_column_name2
      default:
        type: object
        description: >-
          Provide a set of default headings and values
          if they are not found within the input
    """ 
    # Ensure input is passed as a list
    if not isinstance(input, _list):
        input = [input]

    def _parse_dict_or_json(val):
        if isinstance(val, dict):
            return val.items()
        elif isinstance(val, str) and val.startswith('{') and val.endswith('}'):
            try:
                return _json.loads(val).items()
            except:
                pass
        raise ValueError(f'{val} is not a valid Dictionary') from None
        

    # Generate new columns for each key in the dictionary
    df_temp = _pd.DataFrame([
        dict(_itertools.chain.from_iterable(_parse_dict_or_json(d) for d in ([default] + row.tolist())))
        for row in df[input].values
    ])

    # If user has defined how they'd like the output columns
    if output is not None:
        # Ensure output is a list
        if not isinstance(output, _list):
            output = [output]
        
        # Rename the columns if any dictionary are provided
        rename_dict = dict(
            _itertools.chain.from_iterable(
                [x.items() for x in output if isinstance(x, dict)]
            )
        )
        if rename_dict:
            df_temp = df_temp.rename(columns=rename_dict)

        # Get the output names from either the unmodified
        # strings or the renamed dictionary values
        output = [
            v for item in output
            for v in (item.values() if isinstance(item, dict) else [item])
        ]
        df_temp = df_temp[output]

    df[df_temp.columns] = df_temp.values

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
    output: _Union[str, _list],
    char: str = ',',
    pad: bool = False,
    element: _Union[int, str] = None,
    inclusive: bool = False
) -> _pd.DataFrame:
    """
    type: object
    description: Split a string to multiple columns or a list.
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
        description: Name of the output column
      char:
        type: string
        description: (Optional) Set the character(s) to split on. Default comma (,)
      pad:
        type: boolean
        description: (Optional) If outputting to a list, choose whether to pad to a consistent length. Default False
      element:
        type: 
          - integer
          - string
        description: (Optional) Select a specific element or range after splitting
      inclusive:
        type: boolean
        description: (Optional) Include the split character in the output. Default False
    """
    # If output is a list, then pad to a consistent length
    if isinstance(output, str) and '*' in output or isinstance(output, _list):
        pad = True

    results = _format.split(df[input].astype(str).tolist(), char, output, pad, inclusive)

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
        
    # Specific element of the output list
    if isinstance(element, int):
        element_list = []
        for x in df[output]:
            try:
                element_list.append(x[element])
            except(IndexError):
                element_list.append('')
        df[output] = element_list
        
    elif isinstance(element, str):
        slice_values = [int(x) for x in element.split(':')]
        df[output] = df[output].apply(lambda x: x[slice_values[0]:slice_values[1]])
        
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
