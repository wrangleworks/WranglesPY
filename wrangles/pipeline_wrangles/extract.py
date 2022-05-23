"""
Functions to run extraction wrangles
"""
import pandas as _pd
from typing import Union as _Union
from .. import extract as _extract
from .. import format as _format


_schema = {}


def address(df: _pd.DataFrame, input: str, output: str) -> _pd.DataFrame:
    """
    """
    df[output] = _extract.address(df[input].astype(str).tolist())
    return df

_schema['address'] = """
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


def attributes(df: _pd.DataFrame, input: str, output: str, responseContent: str = 'span', attribute_type: str = None) -> _pd.DataFrame:
    """

    :param df:
    :param input:
    :param output:
    :param responseContent:
    :param type:
    """
    df[output] = _extract.attributes(df[input].astype(str).tolist(), responseContent, attribute_type)
    return df

_schema['attributes'] = """
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
    description: span - returns the text found. object returns an object with the value and unit
"""


def codes(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list]) -> _pd.DataFrame:
    """
    

    :param df: Input Dataframe
    :param input: Name or list of names of input columns
    :param output: Name or list of names of output columns
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

_schema['codes'] = """
type: object
description: Extract alphanumeric codes from the input
additionalProperties: false
required:
  - input
  - output
properties:
  input:
    type: string
    description: Name or list of input columns.
  output:
    type: string
    description: Name or list of output columns
"""


def custom(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list], model_id: str) -> _pd.DataFrame:
    """
    
    :param df:
    :param input: Name or list of names of input columns
    :param output: Name or list of names of output columns
    :param model_id: ID of model to run
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

_schema['custom'] = """
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


def properties(df: _pd.DataFrame, input: str, output: str, property_type: str = None) -> _pd.DataFrame:
    """
    Run the extract - properties wrangle on the requested columns



    :param df: Input Dataframe
    :param input: 
    :param output: 
    :param type: (Optional) Request only a specific type of properties
    """
    df[output] = _extract.properties(df[input].astype(str).tolist(), type=property_type)
    return df

_schema['properties'] = """
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
    
    
# SUPER MARIO
def diff(df: _pd.DataFrame, input: str, output: str) -> _pd.DataFrame:
    """

    :param df:
    :param input:
    :param output:
    """
    df[output] = _extract.diff(df[input].values.tolist())
    return df