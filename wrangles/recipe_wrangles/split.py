"""
Split a single column to multiple columns
"""
import pandas as _pd
from .. import format as _format
from typing import Union as _Union
from typing import List as _list       # Rename List to _list to be able to use function name list without clashing


def text(df: _pd.DataFrame, input: str, output: _Union[str, list], char: str = ',', pad: bool = False, element: _Union[str, int] = None) -> _pd.DataFrame:
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
        type: 
          - string
          - array
        description: (Optional) Set the character(s) to split on. Default comma (,)
      pad:
        type: boolean
        description: (Optional) If outputting to a list, choose whether to pad to a consistent length. Default False
      element:
        type: 
          - integer
          - string
        description: (Optional) Select a specific element or range after splitting
    """
    # If char is a list -> split on multiple chars using regex
    if isinstance(char, _list) and '*' not in output:
      df[output] = _format.split_re(df[input].astype(str).tolist(), char, output)
      return df
      
    # Wildcard with multiple split and multiple char
    if isinstance(output, str) and '*' in output and isinstance(char, _list):
        # If user has entered a wildcard in the output column name
        # then add results to that with an incrementing index for each column
        # column * -> column 1, column 2, column 3...
        results = _format.split_re(df[input].astype(str).tolist(), char, output)
        output_headers = []
        for i in range(1, len(results[0]) + 1):
            output_headers.append(output.replace('*', str(i)))
        df[output_headers] = results
        return df
        
    # Wildcard with multiple splits 
    if isinstance(output, str) and '*' in output:
        # If user has entered a wildcard in the output column name
        # then add results to that with an incrementing index for each column
        # column * -> column 1, column 2, column 3...
        results = _format.split(df[input].astype(str).tolist(), char, output, pad=True)
        output_headers = []
        for i in range(1, len(results[0]) + 1):
            output_headers.append(output.replace('*', str(i)))
        df[output_headers] = results

    elif isinstance(output, str) and not pad:
        # User has given a single column - return as a list within that column
        df[output] = _format.split(df[input].astype(str).tolist(), char, output)

    elif isinstance(output, _list) or pad:
        df[output] = _format.split(df[input].astype(str).tolist(), char, output, pad=True)
        
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
    
    
def list(df: _pd.DataFrame, input: str, output: list) -> _pd.DataFrame:
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


def dictionary(df: _pd.DataFrame, input: str) -> _pd.DataFrame:
    """
    type: object
    description: Split a dictionary into columns. The dictionary keys will be used as the new column headers.
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type: string
        description: Name of the column to be split
    """
    exploded_df = _pd.json_normalize(df[input], max_level=1).fillna('')
    df[exploded_df.columns] = exploded_df
    return df


def tokenize(df: _pd.DataFrame, input: str, output: str = None) -> _pd.DataFrame:
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
        type: string
        description: Name of the output column
    """
    if output is None: output = input
    
    # If the input is a string
    if isinstance(input, str) and isinstance(output, str):
        df[output] = _format.tokenize(df[input].values.tolist())
    
    # If the input is multiple columns (a list)
    elif isinstance(input, _list) and isinstance(output, _list):
        for in_col, out_col in zip(input, output):
            df[out_col] = _format.tokenize(df[in_col].values.tolist())
    
    # If the input and output are not the same type
    elif type(input) != type(output):
        raise ValueError('If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided.')
            
    return df
