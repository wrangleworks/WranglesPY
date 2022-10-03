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
import re as _re


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
        description: Value or list of values to filter, equal to parameter values
      is_in:
        type:
          - string
          - array
        description: Value or list of values to filter that are in parameter values
      not_in:
        type:
          - string
          - array
        description: Value or list of values to filter that are not in parameter values
      greater_than:
        type:
          - integer
          - number
        description: Value or list of values to filter that are greater than parameter values
      greater_than_equal:
        type:
          - integer
          - number
        description: Value or list of values to filter that are greater than or equal to parameter values
      lower_than:
        type:
          - integer
          - number
        description: Value or list of values to filter that are lower than parameter values
      lower_than_equal:
        type:
          - integer
          - number
        description: Value or list of values to filter that are lower than or equal to parameter values
      in_between:
        type:
          - array
        description: Value or list of values to filter that are in between two parameter values
      
    """
    # check that only one variable is selected
    none_list = [equal, is_in, not_in, greater_than, greater_than_equal_to, less_than, less_than_equal_to, between, contains, does_not_contain, not_null]
    variables_count = [x for x in none_list if x != None]
    if len(variables_count) > 1: raise ValueError("Only one filter at a time can be used.")
    
    if equal != None:
        if isinstance(equal, str) or isinstance(equal, bool): equal = [equal] # pragma: no cover 
        df = df.loc[df[input].isin(equal)]
    elif is_in != None:
        if isinstance(is_in, str): is_in = [is_in] # pragma: no cover 
        df = df[df[input].isin(is_in)]
    elif not_in != None:
        if isinstance(not_in, str): not_in = [not_in] # pragma: no cover 
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

        # Get the wildcards
        wildcard_check = [x for x in columns if '*' in x]

        
        columns_to_print = []
        temp_cols = []
        # Check if there are any asterisks in columns to print
        if len(wildcard_check):
            for iter in wildcard_check:
                
                # Do nothing if the user enters an escape character
                if '\\' in iter:
                    column = iter.replace('\\', '')
                    columns_to_print.append(column)
                # Add all columns names with similar name
                else:
                    column = iter.replace('*', '')
                    re_pattern = r"^\b{}(\s)?(\d+)?\b$".format(column)
                    list_re = [_re.search(re_pattern, x) for x in df.columns]
                    temp_cols.extend([x.string for x in list_re if x != None])


        # Remove columns that have "*" as they are handled above
        no_wildcard = [x for x in columns if '*' not in x]
        columns_to_print.extend(no_wildcard)
        columns_to_print.extend(temp_cols)

        print(df[columns_to_print])
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
    # For checking if columns exist
    df_cols = list(df.columns)
    
    # If short form of paired names is provided, use that
    if input is None:
        # Check that column name exists
        rename_cols = list(kwargs.keys())
        for x in rename_cols:
            
            if x not in df_cols: raise ValueError(f'Rename column "{x}" not found.')
        
        rename_dict = kwargs
    else:
        # Otherwise create a dict from input and output columns
        
        # Check column exists
        if input not in df_cols: raise ValueError(f'Rename column "{input}" not found.')
        
        if isinstance(input, str):
            input = [input]
            output = [output]
        rename_dict = dict(zip(input, output))

    return df.rename(columns=rename_dict)


def standardize(df: _pd.DataFrame, input: _Union[str, list], model_id: _Union[str, list] = None, output: _Union[str, list] = None, find: str = None, replace: str = None) -> _pd.DataFrame:
    """
    type: object
    description: Standardize data using a DIY or bespoke standardization wrangle. Requires WrangleWorks Account and Subscription.
    additionalProperties: false
    required:
      - input
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
        description: The ID of the wrangle to use (do not include 'find' and 'replace')
      find:
        type:
          - string
        description: Pattern to find using regex (do not include model_id)
      replace:
        type:
          - string
        description: Value to replace the pattern found (do not include model_id)
    """
    # If user hasn't specified an output column, overwrite the input
    if output is None: output = input
      
    if model_id is not None and [find, replace] == [None, None]:

      # If user provides a single string, convert all the arguments to lists for consistency
      if isinstance(input, str): input = [input]
      if isinstance(output, str): output = [output]
      if isinstance(model_id, str): model_id = [model_id]

      for model in model_id:
        for input_column, output_column in zip(input, output):
          df[output_column] = _standardize(df[input_column].astype(str).tolist(), model)
    
    # Small on Demand Standardize if model ID is not provided
    elif model_id is None and find is not None and replace is not None:
      
        def mini_standardize(string):
            new_string = _re.sub(find, replace, string)
            return new_string
      
        df[output] = df[input].apply(lambda x: mini_standardize(x))
    
    else:
        raise ValueError("Standardize must have model_id or find and replace as parameters")

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

    # If the input is a string
    if isinstance(input, str) and isinstance(output, str):
        df[output] = _translate(df[input].astype(str).tolist(), target_language, source_language, case)
    
    # If the input is multiple columns (a list)
    elif isinstance(input, list) and isinstance(output, list):
        for in_col, out_col in zip(input, output):
            df[out_col] = _translate(df[in_col].astype(str).tolist(), target_language, source_language, case)
    
    # If the input and output are not the same type
    elif type(input) != type(output):
        raise ValueError('If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided.')

    return df


def remove_words(df: _pd.DataFrame, input: str, to_remove: str, output: str = None, tokenize_to_remove: bool = False, ignore_case: bool = True) -> _pd.DataFrame:
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
      tokenize_to_remove:
        type: boolean
        description: Tokenize all to_remove inputs
      ignore_case:
        type: boolean
        description: Ignore input and to_remove case
    """
    if output is None: output = input

    # If the input is a string
    if isinstance(input, str) and isinstance(output, str):
        df[output] = _extract.remove_words(df[input].values.tolist(), df[to_remove].values.tolist(), tokenize_to_remove, ignore_case)

    # If the input is multiple columns (a list)
    elif isinstance(input, list) and isinstance(output, list):
        for in_col, out_col in zip(input, output):
            df[out_col] = _extract.remove_words(df[in_col].values.tolist(), df[to_remove].values.tolist(), tokenize_to_remove, ignore_case)
    
    # If the input and output are not the same type
    elif type(input) != type(output):
        raise ValueError('If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided.')
    
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
        df = original_df.merge(df_temp[output_columns], how='left', left_index=True, right_index=True) # pragma no cover
        
    return df
    