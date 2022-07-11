"""
Functions to select data from within columns
"""
from .. import select as _select
import pandas as _pd
from typing import Union as _Union


def list_element(df: _pd.DataFrame, input: str, output: str, element: int = 0) -> _pd.DataFrame:
    """
    type: object
    description: Select a numbered element of a list (zero indexed).
    additionalProperties: false
    required:
      - input
      - output
      - element
    properties:
      input:
        type: string
        description: Name of the input column
      output:
        type: string
        description: Name of the output column
      element:
        type: integer
        description: The numbered element of the list to select. Starts from zero
    """
    df[output] = _select.list_element(df[input].tolist(), element)
    return df


def dictionary_element(df: _pd.DataFrame, input: str, output: str, element: str) -> _pd.DataFrame:
    """
    type: object
    description: Select a named element of a dictionary.
    additionalProperties: false
    required:
      - input
      - output
      - element
    properties:
      input:
        type: string
        description: Name of the input column
      output:
        type: string
        description: Name of the output column
      element:
        type: string
        description: The key from the dictionary to select.
    """
    df[output] = _select.dict_element(df[input].tolist(), element)
    return df


def highest_confidence(df: _pd.DataFrame, input: list, output: str) -> _pd.DataFrame:
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
    df[output] = _select.highest_confidence(df[input].values.tolist())
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
    df[output] = _select.confidence_threshold(df[input[0]].tolist(), df[input[1]].tolist(), threshold)
    return df


def left(df: _pd.DataFrame, input: _Union[str, list], length: int, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Return characters from the left of text. Strings shorter than the length defined will be unaffected.
    additionalProperties: false
    required:
      - input
      - length
    properties:
      input:
        type:
          - string
          - array
        description: Name of the column(s) to edit
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
      length:
        type: integer
        description: Number of characters to include
        minimum: 1
    """
    # If user hasn't provided an output, replace input
    if output is None: output = input

    # If a string provided, convert to list
    if isinstance(input, str): input = [input]
    if isinstance(output, str): output = [output]

    # Loop through and get left characters of the length requested for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].str[:length]

    return df


def right(df: _pd.DataFrame, input: _Union[str, list], length: int, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Return characters from the right of text. Strings shorter than the length defined will be unaffected.
    additionalProperties: false
    required:
      - input
      - length
    properties:
      input:
        type:
          - string
          - array
        description: Name of the column(s) to edit
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
      length:
        type: integer
        description: Number of characters to include
        minimum: 1
    """
    # If user hasn't provided an output, replace input
    if output is None: output = input

    # If a string provided, convert to list
    if isinstance(input, str): input = [input]
    if isinstance(output, str): output = [output]

    # Loop through and get the right characters of the length requested for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].str[-length:]

    return df


def substring(df: _pd.DataFrame, input: _Union[str, list], start: int, length: int, output: _Union[str, list] = None) -> _pd.DataFrame:
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
          - array
        description: Name of the column(s) to edit
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
      start:
        type: integer
        description: The position of the first character to select
        minimum: 1
      length:
        type: integer
        description: The length of the string to select
        minimum: 1
    """
    # If user hasn't provided an output, replace input
    if output is None: output = input

    # If a string provided, convert to list
    if isinstance(input, str): input = [input]
    if isinstance(output, str): output = [output]

    # Loop through and get the substring requested for all requested columns
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].str[start-1:start+length-1]

    return df