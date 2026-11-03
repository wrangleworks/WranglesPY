"""
Functions to select data from within columns
"""
from typing import Union as _Union
import logging as _logging
import pandas as _pd
from .. import select as _select

# Structural selections retain their historical imports without duplicating code.
from .structure import (
    select_columns as columns,
    dictionary_elements as dictionary_element,
    element,
    group_by,
    head,
    list_elements as list_element,
    sample,
    tail,
)


def highest_confidence(df: _pd.DataFrame, input: list, output: _Union[str,list]) -> _pd.DataFrame:
    """
    type: object
    description: Select the option with the highest confidence from multiple columns. Inputs are expected to be of the form [<<value>>, <<confidence_score>>].
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: array
        description: List of the input columns to select from
      output:
        type:
          - array
          - string
        description: If two columns; the result and confidence. If one column; [result, confidence]
    """

    _logging.debug(f": Selecting highest confidence :: input :: {input}")
    if isinstance(output, list) and len(output) == 1:
        output = output[0]
    elif isinstance(output, list) and len(output) > 2:
        raise ValueError(f"Invalid Output: If output is a list, it can only contain 2 columns. Recieved: {output}")

    df[output] = _select.highest_confidence(df[input].values.tolist())
    
    return df


def left(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    length: int,
    output: _Union[str, list] = None
) -> _pd.DataFrame:
    """
    type: object
    description: >-
      Return characters from the left of text.
      Strings shorter than the length defined will be unaffected.
    additionalProperties: false
    required:
      - input
      - length
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the column(s) to edit
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
      length:
        type: integer
        description: >-
          Number of characters to include from the left.
          If negative, this will remove the specified
          number of characters from the left.
          May not equal 0.
    """
    # If user hasn't provided an output, replace input
    if output is None: output = input

    if df.empty:
        df[output] = None
        return df

    # If a string provided, convert to list
    if isinstance(input, str): input = [input]
    if isinstance(output, str): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # If length is a string like '1', convert to integer
    if isinstance(length, str) and length.isdigit():
        length = int(length)

    # Ensure length is an integer
    if not isinstance(length, int):
        raise TypeError('Length must be an integer')

    # Ensure length is not 0
    if length == 0:
        raise ValueError('Length may not equal 0')

    if length > 0:
        # Loop through and get characters from the left
        for input_column, output_column in zip(input, output):
            df[output_column] = df[input_column].str[:length]
    else:
        # Loop through and remove characters from the left
        for input_column, output_column in zip(input, output):
            df[output_column] = df[input_column].str[-1*length:]

    return df


def length(
  df: _pd.DataFrame,
  input: _Union[str, int, list],
  output: _Union[str, list] = None,
):
  """
  type: object
  description: >-
    Calculate the lengths of data in a column.
    The length depends on the data type
    e.g. text will be the length of the text,
    lists will be the number of elements in the list.
  required:
    - input
  properties:
    input:
      type:
        - string
        - integer
        - array
      description: Name of the input column(s).
    output:
      type:
        - string
        - array
      description: Name of the output column(s).
  """
  if not output: output = input
  if not isinstance(output, list): output = [output]
  if not isinstance(input, list): input = [input]

  for input_col, output_col in zip(input, output):
    df[output_col] = [len(item) for item in df[input_col].values]

  return df


def right(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    length: int,
    output: _Union[str, list] = None
) -> _pd.DataFrame:
    """
    type: object
    description: >-
      Return characters from the right of text.
      Strings shorter than the length defined will be unaffected.
    additionalProperties: false
    required:
      - input
      - length
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the column(s) to edit
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
      length:
        type: integer
        description: >-
          Number of characters to include from the right.
          If negative, this will remove the specified
          number of characters from the right.
          May not equal 0.
    """
    # If user hasn't provided an output, replace input
    if output is None: output = input

    if df.empty:
        df[output] = None
        return df

    # If a string provided, convert to list
    if isinstance(input, str): input = [input]
    if isinstance(output, str): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # If length is a string like '1', convert to integer
    if isinstance(length, str) and length.isdigit():
        length = int(length)

    # Ensure length is an integer
    if not isinstance(length, int):
        raise TypeError('Length must be an integer')

    # Ensure length is not 0
    if length == 0:
        raise ValueError('Length may not equal 0')
    
    if length > 0:
        # Loop through and get characters from the right
        for input_column, output_column in zip(input, output):
            df[output_column] = df[input_column].str[-length:]
    else:
        # Loop through and remove characters from the right
        for input_column, output_column in zip(input, output):
            df[output_column] = df[input_column].str[:length]

    return df


def substring(df: _pd.DataFrame, input: _Union[str, int, list], start: int = None, length: int = None, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Return characters from the middle of text.
    additionalProperties: false
    required:
      - input
      - start
      - length
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the column(s) to edit
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
      start:
        type: integer
        description: |
          The position of the first character to select.
          If ommited will start from the beginning and length must 
          be provided.
        minimum: 1
      length:
        type: integer
        description: |
          The length of the string to select. If ommited
          will select to the end of the string and start must be provided.
        minimum: 1
    """
    # If user hasn't provided an output, replace input
    if output is None: output = input

    if df.empty:
        df[output] = None
        return df

    # If a string provided, convert to list
    if isinstance(input, str): input = [input]
    if isinstance(output, str): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # Ensure start or length have been provided
    if start is None and length is None:
        raise ValueError('Either start or length must be provided.')
    
    # Set start and end parameters
    if start is None:
        start = 1
        start_param = None
    else:
        start_param = start - 1
    
    if length is None:
        end_param = None
    else:
        end_param = start + length - 1

    # Loop through and get the substring requested for all requested columns
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].str[start_param:end_param]

    return df


def threshold(df: _pd.DataFrame, input: list, output: str, threshold: float) -> _pd.DataFrame:
    """
    type: object
    description: Select the first option if it exceeds a given threshold, else the second option.
    additionalProperties: false
    required:
      - input
      - output
      - threshold
    properties:
      input:
        type: array
        description: List of the input columns to select from
      output:
        type: string
        description: Name of the output column
      threshold:
        type: number
        description: Threshold above which to choose the first option, otherwise the second
        minimum: 0
        maximum: 1
    """
    _logging.debug(f": Applying confidence threshold :: {threshold} on {input}")
    df[output] = _select.confidence_threshold(df[input[0]].tolist(), df[input[1]].tolist(), threshold)
    return df
