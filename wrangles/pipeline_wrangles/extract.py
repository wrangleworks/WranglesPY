"""
Functions to run extraction wrangles
"""
import pandas as _pd
from typing import Union as _Union
from .. import extract as _extract
from .. import format as _format


def address(df: _pd.DataFrame, input: str, output: str) -> _pd.DataFrame:
    """
    type: object
    description: Extract parts of addresses
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: string
        description: Name of the input column.
      output:
        type: string
        description: Name of the output column.
    """
    df[output] = _extract.address(df[input].astype(str).tolist())
    return df


def attributes(df: _pd.DataFrame, input: str, output: str, responseContent: str = 'span', attribute_type: str = None) -> _pd.DataFrame:
    """
    type: object
    description: Extract numeric attributes from the input such as weights or lengths
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: string
        description: Name of the input column.
      output:
        type: string
        description: Name of the output column.
      attribute_type:
        type: string
        description: Request only a specific type of attribute
      responseContent:
        type: string
        description: span - returns the text found. object - returns an object with the value and unit
        enum:
          - span
          - object
    """
    df[output] = _extract.attributes(df[input].astype(str).tolist(), responseContent, attribute_type)
    return df


def codes(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list]) -> _pd.DataFrame:
    """
    type: object
    description: Extract alphanumeric codes from the input
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type:
          - string
          - array
        description: Name or list of input columns.
      output:
        type:
          - string
          - array
        description: Name or list of output columns
    """
    if isinstance(input, str):
        df[output] = _extract.codes(df[input].astype(str).tolist())
    elif isinstance(input, list):
        # If a list of inputs is provided, ensure the list of outputs is the same length
        if len(input) != len(output):
            if isinstance(output, str):
                df[output] = _extract.codes(_format.concatenate(df[input].astype(str).values.tolist(), ' aaaaaaa '))
            else:
                raise ValueError('If providing a list of inputs, a corresponding list of outputs must also be provided.')
        else:
            for input_column, output_column in zip(input, output):
                df[output_column] = _extract.codes(df[input_column].astype(str).tolist())

    return df


def custom(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list], model_id: str) -> _pd.DataFrame:
    """
    type: object
    description: Extract data from the input using a DIY or bespoke extraction wrangle
    additionalProperties: false
    required:
      - input
      - output
      - model_id
    properties:
      input:
        type:
          - string
          - array
        description: Name or list of input columns.
      output:
        type:
          - string
          - array
        description: Name or list of output columns
      model_id:
        type: string
        description: The ID of the wrangle to use
    """
    if isinstance(input, str):
        df[output] = _extract.custom(df[input].astype(str).tolist(), model_id=model_id)
    elif isinstance(input, list):
        # If a list of inputs is provided, ensure the list of outputs is the same length
        if len(input) != len(output):
            if isinstance(output, str):
                df[output] = _extract.custom(_format.concatenate(df[input].astype(str).values.tolist(), ' '), model_id=model_id)
            else:
                raise ValueError('If providing a list of inputs, a corresponding list of outputs must also be provided.')
        else:
            for input_column, output_column in zip(input, output):
                df[output_column] = _extract.custom(df[input_column].astype(str).tolist(), model_id=model_id)
            
    return df


def properties(df: _pd.DataFrame, input: str, output: str, property_type: str = None) -> _pd.DataFrame:
    """
    type: object
    description: Extract text properties from the input
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: string
        description: Name of the input column
      output:
        type: string
        description: Name of the output columns
      property_type:
        type: string
        description: The specific type of properties to extract
    """
    df[output] = _extract.properties(df[input].astype(str).tolist(), type=property_type)
    return df
    
    
# SUPER MARIO
def diff(df: _pd.DataFrame, input: str, output: str) -> _pd.DataFrame:
    """
    type: object
    description: Remove all the elements that occur in one list from another
    additionalProperties: false
    required:
      - input1
      - input2
      - output
    properties:
      input1:
        type: string
        description: Name of list to remove items from
      input2:
        type: string
        description: Name of the list that contains elements to subtract
      output:
        type: string
        description: Name of the output columns
    """
    df[output] = _extract.diff(df[input].values.tolist())
    return df