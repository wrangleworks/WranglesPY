"""
Functions to select data from within columns
"""
from .. import select as _select
import pandas as _pd


_schema = {}


def list_element(df: _pd.DataFrame, input: str, output: str, element: int = 0) -> _pd.DataFrame:
    """
    Select a numbered element of a list (zero indexed)
    """
    df[output] = _select.list_element(df[input].tolist(), element)
    return df

_schema['list_element'] = """
type: object
description: Select a numbered element of a list (zero indexed)
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


def dictionary_element(df: _pd.DataFrame, input: str, output: str, element: str) -> _pd.DataFrame:
    """
    Select a named element of a dictionary
    """
    df[output] = _select.dict_element(df[input].tolist(), element)
    return df

_schema['dictionary_element'] = """
type: object
description: Select a named element of a dictionary
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


def highest_confidence(df: _pd.DataFrame, input: list, output: str) -> _pd.DataFrame:
    """
    Select the option with the highest confidence from multiple columns. Inputs are expected to be of the form [<<value>>, <<confidence_score>>]
    """
    df[output] = _select.highest_confidence(df[input].values.tolist())
    return df

_schema['highest_confidence'] = """
type: object
description: Select the option with the highest confidence from multiple columns. Inputs are expected to be of the form [<<value>>, <<confidence_score>>]
additionalProperties: false
required:
  - input
  - output
properties:
  input:
    type: array
    description: List of the input columns to select from
  output:
    type: string
    description: Name of the output column
"""


def threshold(df: _pd.DataFrame, input: list, output: str, threshold: float) -> _pd.DataFrame:
    """
    Select the first option if it exceeds a given threshold, else the second option

    The first option must be of the form [<<value>>, <<confidence_score>>]
    """
    df[output] = _select.confidence_threshold(df[input[0]].tolist(), df[input[1]].tolist(), threshold)
    return df

_schema['threshold'] = """
type: object
description: Select the first option if it exceeds a given threshold, else the second option
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