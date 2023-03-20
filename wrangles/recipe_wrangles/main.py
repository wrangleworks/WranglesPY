"""
Standalone functions

These will be called directly, without belonging to a parent module
"""
import types as _types
from ..classify import classify as _classify
from ..standardize import standardize as _standardize
from ..translate import translate as _translate
from .. import extract as _extract
from .. import recipe as _recipe
from .convert import to_json as _to_json
from .convert import from_json as _from_json
import logging as _logging

import numexpr as _ne
import pandas as _pd
from typing import Union as _Union
import sqlite3 as _sqlite3
import re as _re
from jinja2 import Environment as _Environment, FileSystemLoader as _FileSystemLoader, BaseLoader as _BaseLoader
import wrangles as _wrangles
import yaml as _yaml


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


def filter(
          df: _pd.DataFrame,
          input: str = None,
          equal: _Union[str, list] = None,
          not_equal: _Union[str, list] = None,
          is_in: _Union[str, list] = None,
          not_in: _Union[str, list] = None,
          greater_than: _Union[int, float] = None,
          greater_than_equal_to: _Union[int, float] = None,
          less_than: _Union[int, float] = None,
          less_than_equal_to: _Union[int, float] = None,
          between: list = None,
          contains: str = None,
          not_contains: str = None,
          is_null: bool = None,
          where: str = None,
          **kwargs,
          ) -> _pd.DataFrame:
    """
    type: object
    description: |
      Filter the dataframe based on the contents.
      If multiple filters are specified, all must be correct.
      For complex filters, use the where parameter.
    additionalProperties: false
    properties:
      where:
        type: string
        description: Use a SQL WHERE clause to filter the data.
      input:
        type: string
        description: Name of the column to filter on
      equal:
        type:
          - string
          - array
        description: Select rows where the values equal a given value.
      not_equal:
        type:
          - string
          - array
        description: Select rows where the values do not equal a given value.
      is_in:
        type:
          - array
          - string
        description: Select rows where the values are in a given list.
      not_in:
        type:
          - array
          - string
        description: Select rows where the values are not in a given list.
      is_null:
        type: boolean
        description: If true, select all rows where the value is NULL. If false, where is not NULL.
      greater_than:
        type:
          - integer
          - number
        description: Select rows where the values are greater than a specified value. Does include the value itself.
      greater_than_equal_to:
        type:
          - integer
          - number
        description: Select rows where the values are greater than a specified value. Does include the value itself.
      less_than:
        type:
          - integer
          - number
        description: Select rows where the values are less than a specified value. Does not include the value itself.
      less_than_equal_to:
        type:
          - integer
          - number
        description: Select rows where the values are less than a specified value. Does include the value itself.
      between:
        type:
          - array
        description: Value or list of values to filter that are in between two parameter values
      contains:
        type: string
        description: Select rows where the input contains the value. Allows regular expressions.
      not_contains:
        type: string
        description: Select rows where the input does not contain the value. Allows regular expressions.
    """
    if where != None:
        df = sql(
            df,
            f"""
            SELECT *
            FROM df
            WHERE {where};
            """
        )

    if equal != None:
        if not isinstance(equal, list): equal = [equal] # pragma: no cover 
        df = df.loc[df[input].isin(equal)]

    if not_equal != None:
        if not isinstance(not_equal, list): not_equal = [not_equal] # pragma: no cover 
        df = df.loc[~df[input].isin(not_equal)]
    
    if is_in != None:
        if not isinstance(is_in, list): is_in = [is_in] # pragma: no cover 
        df = df[df[input].isin(is_in)]
    
    if not_in != None:
        if not isinstance(not_in, list): not_in = [not_in] # pragma: no cover 
        df = df[~df[input].isin(not_in)]
    
    if greater_than != None:
        df = df[df[input] > greater_than]
    
    if greater_than_equal_to != None:
        df = df[df[input] >= greater_than_equal_to]
    
    if less_than != None:
        df = df[df[input] < less_than]
    
    if less_than_equal_to != None:
        df = df[df[input] <= less_than_equal_to]
    
    if between != None:
        if len(between) != 2: raise ValueError('Can only use "between" with two values')
        df = df[df[input].between(between[0], between[1], **kwargs)]
    
    if contains != None:
        df = df[df[input].str.contains(contains, na=False, **kwargs)]
    
    if not_contains != None:
        df = df[~df[input].str.contains(not_contains, na=False, **kwargs)]
    
    if is_null == True:
        df = df[df[input].isnull()]
    
    if is_null == False:
        df = df[df[input].notnull()]
     
    return df


def log(df: _pd.DataFrame, columns: list = None, write: list = None):
    """
    type: object
    description: Log the current status of the dataframe.
    additionalProperties: false
    properties:
      columns:
        type: array
        description: (Optional, default all columns) List of specific columns to log.
      write:
        type: array
        description: (Optional) Allows for an intermediate output to a file/dataframe/database etc. 
        minItems: 1
        items: 
          '$ref: #/$defs/sources/read'
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

        df_tolog = df[columns_to_print]

    else:
        df_tolog = df

    _logging.info(msg=': Dataframe ::\n\n' + df_tolog.to_string() + '\n')

    if write is not None:
        write = _yaml.dump({'write': write})
        _wrangles.recipe.run(write, dataframe=df)

    return df


def rename(df: _pd.DataFrame, input: _Union[str, list] = None, output: _Union[str, list] = None, **kwargs) -> _pd.DataFrame:
    """
    type: object
    description: Rename a column or list of columns.
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
        type:
          - string
          - array
        description: Name of the column to translate
      output:
        type:
          - string
          - array
        description: Name of the output column
      target_language:
        type: string
        description: Code of the language to translate to
        enum:
          - Bulgarian
          - Chinese
          - Czech
          - Danish
          - Dutch
          - English (American)
          - English (British)
          - Estonian
          - Finnish
          - French
          - German
          - Greek
          - Hungarian
          - Italian
          - Japanese
          - Latvian
          - Lithuanian
          - Polish
          - Portuguese
          - Portuguese (Brazilian)
          - Romanian
          - Russian
          - Slovak
          - Slovenian
          - Spanish
          - Swedish
      source_language:
        type: string
        description: Code of the language to translate from. If omitted, automatically detects the input language
        enum:
          - Auto
          - Bulgarian
          - Chinese
          - Czech
          - Danish
          - Dutch
          - English
          - Estonian
          - Finnish
          - French
          - German
          - Greek
          - Hungarian
          - Italian
          - Japanese
          - Latvian
          - Lithuanian
          - Polish
          - Portuguese
          - Romanian
          - Russian
          - Slovak
          - Slovenian
          - Spanish
          - Swedish
    """
    
    # Convert Language to DeepL Code
    source_dict = [
        { 'key': 'AUTO', 'text': 'Auto'},
        { 'key': 'BG', 'text': 'Bulgarian' },
        { 'key': 'ZH', 'text': 'Chinese' },
        { 'key': 'CS', 'text': 'Czech' },
        { 'key': 'DA', 'text': 'Danish' },
        { 'key': 'NL', 'text': 'Dutch' },
        { 'key': 'EN', 'text': 'English' },
        { 'key': 'ET', 'text': 'Estonian' },
        { 'key': 'FI', 'text': 'Finnish' },
        { 'key': 'FR', 'text': 'French' },
        { 'key': 'DE', 'text': 'German' },
        { 'key': 'EL', 'text': 'Greek' },
        { 'key': 'HU', 'text': 'Hungarian' },
        { 'key': 'IT', 'text': 'Italian' },
        { 'key': 'JA', 'text': 'Japanese' },
        { 'key': 'LV', 'text': 'Latvian' },
        { 'key': 'LT', 'text': 'Lithuanian' },
        { 'key': 'PL', 'text': 'Polish' },
        { 'key': 'PT', 'text': 'Portuguese' },
        { 'key': 'RO', 'text': 'Romanian' },
        { 'key': 'RU', 'text': 'Russian' },
        { 'key': 'SK', 'text': 'Slovak' },
        { 'key': 'SL', 'text': 'Slovenian' },
        { 'key': 'ES', 'text': 'Spanish' },
        { 'key': 'SV', 'text': 'Swedish' },
    ]
    
    target_dict = [
        { 'key': 'BG', 'text': 'Bulgarian' },
        { 'key': 'ZH', 'text': 'Chinese' },
        { 'key': 'CS', 'text': 'Czech' },
        { 'key': 'DA', 'text': 'Danish' },
        { 'key': 'NL', 'text': 'Dutch' },
        { 'key': 'EN-US', 'text': 'English (American)' },
        { 'key': 'EN-GB', 'text': 'English (British)' },
        { 'key': 'ET', 'text': 'Estonian' },
        { 'key': 'FI', 'text': 'Finnish' },
        { 'key': 'FR', 'text': 'French' },
        { 'key': 'DE', 'text': 'German' },
        { 'key': 'EL', 'text': 'Greek' },
        { 'key': 'HU', 'text': 'Hungarian' },
        { 'key': 'IT', 'text': 'Italian' },
        { 'key': 'JA', 'text': 'Japanese' },
        { 'key': 'LV', 'text': 'Latvian' },
        { 'key': 'LT', 'text': 'Lithuanian' },
        { 'key': 'PL', 'text': 'Polish' },
        { 'key': 'PT-PT', 'text': 'Portuguese' },
        { 'key': 'PT-BR', 'text': 'Portuguese (Brazilian)' },
        { 'key': 'RO', 'text': 'Romanian' },
        { 'key': 'RU', 'text': 'Russian' },
        { 'key': 'SK', 'text': 'Slovak' },
        { 'key': 'SL', 'text': 'Slovenian' },
        { 'key': 'ES', 'text': 'Spanish' },
        { 'key': 'SV', 'text': 'Swedish' },
    ]
    # Source Language code
    try:
        if target_language == 'English': target_language = 'English (British)'
        source_language = [x['key'] for x in source_dict if x['text'] == source_language][0]
        target_language = [x['key'] for x in target_dict if x['text'] == target_language][0]
    except:
        pass

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
    
    # List of columns changed
    cols_changed = []
    for cols in df.columns:
        count = 0        
        for row in df[cols]:
            # If row contains objects, then convert to json
            if isinstance(row, dict):
                # Check if there is an object in the column and record column name to convert to json
                cols_changed.append(cols)
                break
            # Only check the first 10 rows of a column
            count += 1
            if count > 10: break
            
        if cols in cols_changed:
            # If the column is in cols_changed then convert to json
            _to_json(df=df, input=cols)
    
    df.to_sql('df', db, if_exists='replace', index = False, method='multi', chunksize=1000)
    
    # Execute the user's query against the database and return the results
    df = _pd.read_sql(command, db)
    db.close()
    
    # Change the columns back to an object
    for new_cols in df.columns:
        
        if new_cols in cols_changed:
            # If the column is in cols changed, then change back to an object
            _from_json(df=df, input=new_cols)
    
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
    

def recipe(df: _pd.DataFrame, name, variables = {}, output_columns = None, functions: _Union[_types.FunctionType, list] = []):
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
    df_temp = _recipe.run(name, variables=variables, functions=functions, dataframe=df)
    
    # column output logic
    if output_columns is None:
        df = df_temp
    else:
        df = original_df.merge(df_temp[output_columns], how='left', left_index=True, right_index=True) # pragma no cover
        
    return df


def date_calculator(df: _pd.DataFrame, input: _Union[str, _pd.Timestamp], operation: str = 'add', output: _Union[str, _pd.Timestamp] = None, time_unit: str = None, time_value: float = None) -> _pd.DataFrame:
    """
    type: object
    description: Add or Subtract time from a date
    additionalProperties: false
    required:
      - input
      - operation
      - kwargs
    properties:
      input:
        type: string
        description: Name of the dates column
      operation:
        type: string
        description: Date operation
        enum:
          - add
          - subtract
      output:
        type: string
        description: Name of the output column of dates
      time_unit:
        type: string
        description: time unit for operation
        enum:
          - years
          - months
          - weeks
          - days
          - hours
          - minutes
          - seconds
          - milliseconds
      time_value:
        type: number
        description: time unit value for operation
    """
    # If the output is not provided
    if output is None: output = input
    
    # Get all of the date parameters for operation
    args = {time_unit: time_value}
    offset = _pd.DateOffset(**args)
    
    # Converting data to datetime
    df[input] = _pd.to_datetime(df[input])
    
    results = []
    if operation == 'add':
        for date in df[input]:
            results.append(date + offset)
            
    elif operation == 'subtract':
        for date in df[input]:
            results.append(date - offset)
            
    else:
        raise ValueError(f'\"{operation}\" is not a valid operation. Available operations: \"add\", \"subtract\"')
    
    df[output] = results
    
    return df

def jinja(df, input: str, template: dict, output: str=None):
    """
    type: object
    description: Create a description from a jinja template
    required:
      - output
      - template
    properties:
      input:
        type: string
        description: Name of column containing a dictionary of elements to be used in jinja template
      template:
        type: object
        description: A dictionary which defines the template/location as well as the form which the template is input
      output_file:
        type: string
        description: File name/path for the file to be output
    """
    if output == None:
        output = input
    if len(template) > 1:
        raise Exception('Template must have only one key specified')
    
    # Template input as a file
    if 'file' in list(template.keys()):
        environment = _Environment(loader=_FileSystemLoader(''),trim_blocks=True, lstrip_blocks=True)
        desc_template = environment.get_template(template['file'])
        df[output] = [desc_template.render(desc) for desc in df[input]]

    # Template input as a column of the dataframe
    elif 'column' in list(template.keys()):
        lst = [_Environment(loader=_BaseLoader).from_string(df[template['column']][i]).render(df[input][i]) for i in range(len(df))]
        df[output] = lst
        
    # Template input as a string
    elif 'string' in list(template.keys()):
        desc_template = _Environment(loader=_BaseLoader).from_string(template['string'])
        df[output] = [desc_template.render(desc) for desc in df[input]]
    else:
        raise Exception("'file', 'column' or 'string' not found")
    return df
