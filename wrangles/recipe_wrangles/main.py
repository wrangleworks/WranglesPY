"""
Standalone functions

These will be called directly, without belonging to a parent module
"""
from ..classify import classify as _classify
from ..standardize import standardize as _standardize
from ..translate import translate as _translate
from .. import extract as _extract
from .. import recipe as _recipe

import numexpr as _ne
import pandas as _pd
from typing import Union as _Union
import sqlite3 as _sqlite3
import os
import requests


def classify(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list], model_id: str) -> _pd.DataFrame:
    """
    type: object
    description: Run classify wrangles on the specified columns. Requires WrangleWorks Account and Subscription.
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


def filter(df: _pd.DataFrame, input: str,
          equal: _Union[str, list] = None,
          is_in: _Union[str, list] = None,
          not_in: _Union[str, list] = None,
          greater_than: _Union[int, float] = None,
          greater_than_equal_to: _Union[int, float] = None,
          less_than: _Union[int, float] = None,
          less_than_equal_to: _Union[int, float] = None,
          between: list = None,
          contains: str = None,
          does_not_contain: str = None,
          not_null: bool = None,
          **kwargs,
          ) -> _pd.DataFrame:
    """
    type: object
    description: Filter the dataframe based on the contents.
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type: string
        description: Name of the column to filter on
      equal:
        type:
          - string
          - array
        description: Value or list of values to filter to
      is_in:
        type:
          - string
          - array
        description: Value or list of values to filter to
      not_in:
        type:
          - string
          - array
        description: Value or list of values to filter to
      greater_than:
        type:
          - integer
          - number
        description: Value or list of values to filter to
      greater_than_equal:
        type:
          - integer
          - number
        description: Value or list of values to filter to
      lower_than:
        type:
          - integer
          - number
        description: Value or list of values to filter to
      lower_than_equal:
        type:
          - integer
          - number
        description: Value or list of values to filter to
      in_between:
        type:
          - array
        description: Value or list of values to filter to
      
    """
    # check that only one variable is selected
    none_list = [equal, is_in, not_in, greater_than, greater_than_equal_to, less_than, less_than_equal_to, between, contains, does_not_contain, not_null]
    variables_count = [x for x in none_list if x != None]
    if len(variables_count) > 1: raise ValueError("Only one filter at a time can be used.")
    
    if equal != None:
        if isinstance(equal, str) or isinstance(equal, bool): equal = [equal]
        df = df.loc[df[input].isin(equal)]
    elif is_in != None:
        if isinstance(is_in, str): is_in = [is_in]
        df = df[df[input].isin(is_in)]
    elif not_in != None:
        if isinstance(not_in, str): not_in = [not_in]
        df = df[~df[input].isin(not_in)]
    elif greater_than != None:
        df = df[df[input] > greater_than]
    elif greater_than_equal_to != None:
        df = df[df[input] >= greater_than_equal_to]
    elif less_than != None:
        df = df[df[input] < less_than]
    elif less_than_equal_to != None:
        df = df[df[input] <= less_than_equal_to]
    elif between != None:
        if len(between) != 2: raise ValueError('Can only use "between" with two values')
        df = df[df[input].between(between[0], between[1], **kwargs)]
    elif contains != None:
        df = df[df[input].str.contains(contains, **kwargs)]
    elif does_not_contain != None:
        df = df[~df[input].str.contains(does_not_contain, **kwargs)]
    elif not_null != None:
        if not_null == True:
            df = df[df[input].notnull()]
        else:
            df = df[df[input].isnull()]
     
    return df


def log(df: _pd.DataFrame, columns: list = None):
    """
    type: object
    description: Log the current status of the dataframe.
    additionalProperties: false
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


def rename(df: _pd.DataFrame, input: _Union[str, list] = None, output: _Union[str, list] = None, **kwargs) -> _pd.DataFrame:
    """
    type: object
    description: Rename a column or list of columns.
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
    description: Standardize data using a DIY or bespoke standardization wrangle. Requires WrangleWorks Account and Subscription.
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
    description: Translate the input to a different language. Requires WrangleWorks Account and DeepL API Key (A free account for up to 500,000 characters per month is available).
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


def remove_words(df: _pd.DataFrame, input: str, to_remove: str, output: str, tokenize_to_remove: bool = False) -> _pd.DataFrame:
    """
    type: object
    description: Remove all the elements that occur in one list from another.
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
      output:
        type: boolean
        description: tokenize all to_remove inputs
    """
    df[output] = _extract.remove_words(df[input].values.tolist(), df[to_remove].values.tolist(), tokenize_to_remove)
    return df


def sql(df: _pd.DataFrame, command: str) -> _pd.DataFrame:
    """
    type: object
    description: Apply a SQL command to the current dataframe. Only SELECT statements are supported - the result will be the output.
    additionalProperties: false
    required:
      - command
    properties:
      command:
        type: string
        description: SQL Command. The table is called df. For specific SQL syntax, this uses the SQLite dialect.
    """
    if command.strip().split()[0].upper() != 'SELECT':
      raise ValueError('Only SELECT statements are supported for sql wrangles')

    # Create an in-memory db with the contents of the current dataframe
    db = _sqlite3.connect(':memory:')
    df.to_sql('df', db, if_exists='replace', index = False, method='multi', chunksize=1000)

    # Execute the user's query against the database and return the results
    df = _pd.read_sql(command, db)
    db.close()
    return df


def math(df: _pd.DataFrame, input: str, output: str) -> _pd.DataFrame:
    """
    type: object
    description: Apply a mathematical calculation.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: string
        description: The mathematical expression using column names. e.g. column1 * column2 + column3
      output:
        type: string
        description: The column to output the results to
    """
    df[output] = _ne.evaluate(input, df.to_dict(orient='list'))
    return df


def maths(df: _pd.DataFrame, input: str, output: str) -> _pd.DataFrame:
    """
    type: object
    description: Apply a mathematical calculation.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: string
        description: The mathematical expression using column names. e.g. column1 * column2 + column3
      output:
        type: string
        description: The column to output the results to
    """
    df[output] = _ne.evaluate(input, df.to_dict(orient='list'))
    return df
    

def recipe(df: _pd.DataFrame, name, variables = {}, output_columns = None):
    """
    type: object
    description: Run a recipe as a Wrangle. Recipe-ception,
    additionalProperties: false
    required:
      - name
    properties:
      name:
        type: string
        description: file name of the recipe
      variables:
        type: object
        description: A dictionary of variables to pass to the recipe
    """
    original_df = df.copy() # copy of the original df
    
    # Running recipe wrangle
    df_temp = _recipe.run(name, variables=variables, dataframe=df)
    
    # colum output logic
    if output_columns is None:
        df = df_temp
    else:
        df = original_df.merge(df_temp[output_columns], how='left', left_index=True, right_index=True)
        print()
        
    return df
    