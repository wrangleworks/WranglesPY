"""
Standalone functions

These will be called directly, without belonging to a parent module
"""
from ..classify import classify as _classify
from .. import format as _format
from .. import match as _match
from ..standardize import standardize as _standardize
from ..translate import translate as _translate

import pandas as _pd
from typing import Union as _Union


_schema = {}


def classify(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list], model_id: str) -> _pd.DataFrame:
    """
    Run classify wrangles on the specified columns

    :return: Updated Dateframe
    """
    if isinstance(input, str):
        df[output] = _classify(df[input].astype(str).tolist(), model_id)
    elif isinstance(input, list):
        # If a list of inputs is provided, ensure the list of outputs is the same length
        if len(input) != len(output):
            raise ValueError('If providing a list of inputs, a corresponding list of outputs must also be provided.')
        for input_column, output_column in zip(input, output):
            df[output_column] = _classify(df[input_column].astype(str).tolist(), model_id)
        
    return df

_schema['classify'] = """
type: object
description: Run classify wrangles on the specified columns
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
    description: Name of the input column.
  output:
    type:
      - string
      - array
    description: Name of the output column.
  model_id:
    type: string
    description: ID of the classification model to be used
"""


def rename(df: _pd.DataFrame, input: _Union[str, list] = None, output: _Union[str, list] = None, **kwargs) -> _pd.DataFrame:
    """
    Rename a column or list of columns

    :return: Updated Dateframe
    """
    # If short form of paired names is provided, use that
    if input is None:
        rename_dict = kwargs
    else:
        # Otherwise create a dict from input and output columns
        if isinstance(input, str):
            input = [input]
            output = [output]
        rename_dict = dict(zip(input, output))

    return df.rename(columns=rename_dict)

_schema['rename'] = """
type: object
description: Rename a column or list of columns
properties:
  input:
    type:
      - array
      - string
    description: Name or list of input columns.
  output:
    type:
      - array
      - string
    description: Name or list of output columns.
"""


def standardize(df: _pd.DataFrame, input: str, output: str, model_id: str) -> _pd.DataFrame:
    """
    Run a standardize wrangle

    :return: Updated Dateframe
    """
    df[output] = _standardize(df[input].astype(str).tolist(), model_id)
    return df

_schema['standardize'] = """
type: object
description: Standardize data using a DIY or bespoke standardization wrangle
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


def translate(df: _pd.DataFrame, input: str, output: str, target_language: str, source_language: str = 'AUTO', case: str = None) -> _pd.DataFrame:
    """
    Translate the input

    :return: Updated Dateframe
    """
    df[output] = _translate(df[input].astype(str).tolist(), target_language, source_language, case)
    return df

_schema['translate'] = """
type: object
description: Translate the input to a different language
additionalProperties: false
required:
  - input
  - output
  - target_language
properties:
  input:
    type: string
    description: Name of the column to translate
  output:
    type: string
    description: Name of the output column
  target_language:
    type: string
    description: Code of the language to translate to
  source_language:
    type: string
    description: Code of the language to translate from. If omitted, automatically detects the input language
"""


def expand(df: _pd.DataFrame, input: str, output: str) -> _pd.DataFrame:
    """
    Expand an object to multiple columns

    :return: Updated Dateframe
    """
    df[output] = [x for x in df[input].tolist()]
    return df


def match(df: _pd.DataFrame, input: list) -> _pd.DataFrame:
    """
    """
    df = _pd.concat([df, _match.run(df[input])], axis=1)
    return df
    

def filter(df: _pd.DataFrame, input: str, equal: _Union[str, list]) -> _pd.DataFrame:
    if isinstance(equal, str): equal = [equal]
    df = df.loc[df[input].isin(equal)]
    return df

_schema['filter'] = """
type: object
description: Filter the dataframe based on the contents
additionalProperties: false
required:
  - input
  - equal
properties:
  input:
    type: string
    description: Name of the column to filter on
  equal:
    type:
      - string
      - array
    description: Value or list of values to filter to
"""

def log(df: _pd.DataFrame, columns: list = None):
  """
  Log the current status of the dataframe
  """
  if columns is not None:
    print(df[columns])
  else:
    print(df)

  return df

_schema['log'] = """
type: object
description: Log the current status of the dataframe
additionalProperties: false
required:
  - columns
properties:
  columns:
    type: array
    description: (Optional, default all columns) List of specific columns to log.
""" 


#  SUPER MARIO
def extend_list(df: _pd.DataFrame, input: list, output: str) -> _pd.DataFrame:
    """
    Convert a lists of lists into one list (flatten a list)
    """
    df[output] = _format.extend_list(df[input].values.tolist())
    return df

def tokenize_list_space(df: _pd.DataFrame, input: str, output: str) -> _pd.DataFrame:
    """
    """
    df[output] = _format.tokenize_list_space(df[input].values.tolist())
    return df