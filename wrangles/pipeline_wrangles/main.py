"""
Standalone functions

These will be called directly, without belonging to a parent module
"""
from ..classify import classify as _classify
from .. import format as _format
from .. import match as _match
from ..standardize import standardize as _standardize
from ..translate import translate as _translate
from .. import extract as _extract

import pandas as _pd
from typing import Union as _Union


def classify(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list], model_id: str) -> _pd.DataFrame:
    """
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
    if isinstance(input, str):
        df[output] = _classify(df[input].astype(str).tolist(), model_id)
    elif isinstance(input, list):
        # If a list of inputs is provided, ensure the list of outputs is the same length
        if len(input) != len(output):
            raise ValueError('If providing a list of inputs, a corresponding list of outputs must also be provided.')
        for input_column, output_column in zip(input, output):
            df[output_column] = _classify(df[input_column].astype(str).tolist(), model_id)
        
    return df


def filter(df: _pd.DataFrame, input: str, equal: _Union[str, list]) -> _pd.DataFrame:
    """
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
    if isinstance(equal, str): equal = [equal]
    df = df.loc[df[input].isin(equal)]
    return df


def log(df: _pd.DataFrame, columns: list = None):
    """
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
    if columns is not None:
        print(df[columns])
    else:
        print(df)

    return df


def match(df: _pd.DataFrame, input: list) -> _pd.DataFrame:
    """
    """
    df = _pd.concat([df, _match.run(df[input])], axis=1)
    return df


def rename(df: _pd.DataFrame, input: _Union[str, list] = None, output: _Union[str, list] = None, **kwargs) -> _pd.DataFrame:
    """
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


def standardize(df: _pd.DataFrame, input: _Union[str, list], model_id: _Union[str, list], output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Standardize data using a DIY or bespoke standardization wrangle
    additionalProperties: false
    required:
      - input
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
        type:
          - string
          - array
        description: The ID of the wrangle to use
    """
    # If user hasn't specified an output column, overwrite the input
    if output is None: output = input

    # If user provides a single string, convert all the arguments to lists for consistency
    if isinstance(input, str): input = [input]
    if isinstance(output, str): output = [output]
    if isinstance(model_id, str): model_id = [model_id]

    for model in model_id:
      for input_column, output_column in zip(input, output):
        df[output_column] = _standardize(df[input_column].astype(str).tolist(), model)

    return df


def translate(df: _pd.DataFrame, input: str, output: str, target_language: str, source_language: str = 'AUTO', case: str = None) -> _pd.DataFrame:
    """
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
    df[output] = _translate(df[input].astype(str).tolist(), target_language, source_language, case)
    return df



# SUPER MARIO
def remove_words(df: _pd.DataFrame, input: str, to_remove: str, output: str) -> _pd.DataFrame:
    """
    type: object
    description: Remove all the elements that occur in one list from another
    additionalProperties: false
    required:
      - input
      - to_remove
      - output
    properties:
      input:
        type: 
          - string
          - array
        description: Name of column to remove words from
      to_remove:
        type: array
        description: Column or list of columns with a list of words to be removed
      output:
        type: string
        description: Name of the output columns
    """
    df[output] = _extract.remove_words(df[input].values.tolist(), df[to_remove].values.tolist())
    return df