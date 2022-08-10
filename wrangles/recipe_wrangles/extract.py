"""
Functions to run extraction wrangles
"""
import pandas as _pd
from typing import Union as _Union
from .. import extract as _extract
from .. import format as _format


def address(df: _pd.DataFrame, input: str, output: str, dataType: str) -> _pd.DataFrame:
    """
    type: object
    description: Extract parts of addresses. Requires WrangleWorks Account.
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
    df[output] = _extract.address(df[input].astype(str).tolist(), dataType)
    return df


def attributes(df: _pd.DataFrame, input: str, output: str, responseContent: str = 'span', attribute_type: str = None, desired_unit: str = None, bound: str = 'mid') -> _pd.DataFrame:
    """
    type: object
    description: Extract numeric attributes from the input such as weights or lengths. Requires WrangleWorks Account.
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
        enum:
          - angle
          - area
          - capacitance
          - charge
          - current
          - data transfer rate
          - electric potential
          - electrical conductance
          - electrical resistance
          - energy
          - force
          - frequency
          - inductance
          - instance frequency
          - length
          - mass
          - power
          - pressure
          - speed
          - temperature
          - time
          - volume
          - volumetric flow
      responseContent:
        type: string
        description: span - returns the text found. object - returns an object with the value and unit
        enum:
          - span
          - object
      bound:
        type: string
        description: When returning an object, if the input is a range (e.g. 10-20mm) set the value to return. min, mid or max. Default mid.
        enum:
          - min
          - mid
          - max
    """
    df[output] = _extract.attributes(df[input].astype(str).tolist(), responseContent, attribute_type, desired_unit, bound)
    return df


def codes(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list]) -> _pd.DataFrame:
    """
    type: object
    description: Extract alphanumeric codes from the input. Requires WrangleWorks Account.
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
    description: Extract data from the input using a DIY or bespoke extraction wrangle. Requires WrangleWorks Account and Subscription.
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


def html(df: _pd.DataFrame, input: _Union[str, list], data_type: str, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Extract elements from strings containing html. Requires WrangleWorks Account.
    additionalProperties: false
    required:
      - input
      - output
      - data_type
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
      data_type:
        type: string
        description: The type of data to extract
        enum:
          - text
          - links
    """
    if isinstance(input, str): input = [input]
    if output is None: output = input

    for input_column, output_column in zip(input, output):
        df[output_column] = _extract.html(df[input_column].astype(str).tolist(), dataType=data_type)
            
    return df


def properties(df: _pd.DataFrame, input: str, output: str, property_type: str = None) -> _pd.DataFrame:
    """
    type: object
    description: Extract text properties from the input. Requires WrangleWorks Account.
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
        enum:
          - Colours
          - Materials
          - Shapes
          - Standards
    """
    df[output] = _extract.properties(df[input].astype(str).tolist(), type=property_type)
    return df
    