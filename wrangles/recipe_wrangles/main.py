"""
Standalone functions

These will be called directly, without belonging to a parent module
"""
import types as _types
import logging as _logging
from typing import Union as _Union
import random as _random
import sqlite3 as _sqlite3
import re as _re
import numexpr as _ne
import requests as _requests
import pandas as _pd
import wrangles as _wrangles
import json as _json
import numpy as _np
import math as _math
import concurrent.futures as _futures
from ..openai import _divide_batches
from ..classify import classify as _classify
from ..standardize import standardize as _standardize
from ..translate import translate as _translate
from ..data import model as _model
from ..lookup import lookup as _lookup
from .. import extract as _extract
from .. import recipe as _recipe
from .convert import to_json as _to_json
from .convert import from_json as _from_json


def accordion(
    df: _pd.DataFrame,
    wrangles: list,
    input: _Union[str, list],
    output: _Union[str, list] = None,
    propagate: _Union[str, list] = None,
    functions: _Union[_types.FunctionType, list] = [],
) -> _pd.DataFrame:
    """
    type: object
    description: >-
      Apply a series of wrangles to column(s) containing lists.
      The wrangles will be applied to each element in the list
      and the results will be returned back as a list.
    additionalProperties: false
    required:
      - input
      - wrangles
    properties:
      input:
        type:
          - string
          - array
        description: >-
          The column(s) containing the list(s) that the
          wrangles will be applied to the elements of.
      propagate:
        type:
          - string
          - array
        description: >-
          Limit the column(s) that will be available to the
          wrangles and replicated for each element.
          If not specified, all columns will be propogated.
          This may be useful to limit the memory use
          for large datasets.
      output:
        type:
          - string
          - array
        description: Output of the wrangles to save back to the dataframe.
      wrangles:
        type: array
        description: List of wrangles to apply
        minItems: 1
        items:
          "$ref": "#/$defs/wrangles/items"
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    if propagate is None: propagate = [item for item in df.columns.tolist() if item not in input]
    if not isinstance(propagate, list): propagate = [propagate]
    
    if not df.index.is_unique:
        raise ValueError("The dataframe index must be unique for the accordion wrangle to work.")

    # Deep copy the dataframe to avoid modifying the original
    df_temp = df[input + propagate].copy()

    # Convert any columns containing JSON arrays to lists
    for col in input:
        if not isinstance(df_temp[col][0], list):
            try:
                df_temp[col] = df_temp[col].apply(_json.loads)
            except:
                pass

    # Save temporary index to be able to merge back later
    random_str = str(_random.randint(0,999999999))
    df_temp[f"index_asbjdbasjk_{random_str}"] = df_temp.index
    
    try:
        df_temp = _wrangles.recipe.run(
            {
                "wrangles": [
                    {"explode": {"input": input, "drop_empty": True}},
                    {"pandas.reset_index": {"parameters": {"drop": True}}},
                ] + wrangles
            },
            dataframe=df_temp,
            functions=functions
        )
    except KeyError as e:
        e.args = (f"Did you forget the column in the accordion input or propagate? - {e.args[0]}",)
        raise e

    try:
        df_temp = _wrangles.recipe.run(
            {"wrangles": [
                {"select.group_by": {"by": f"index_asbjdbasjk_{random_str}", "list": output}},
                {"rename": {x + ".list": x for x in output}}
            ]},
            dataframe=df_temp,
            functions=functions
        )
    except KeyError as e:
        e.args = (f"Did you forget the column in the accordion output? - {e.args[0]}",)
        raise e

    df_temp = df_temp.set_index(f"index_asbjdbasjk_{random_str}")[output]

    original_columns = df.columns.to_list()

    df = df.merge(
        df_temp,
        left_index=True,
        right_index=True,
        how="left",
        suffixes=("_TOBEDROPPED", None)
    ).filter(regex='^(?!.*_TOBEDROPPED)')

    # Ensure output columns contain empty lists if no data remaining
    df[output] = df[output].applymap(lambda d: d if isinstance(d, list) else [])

    # Ensure output columns are in the same order as the original columns
    all_columns = original_columns + [
        col
        for col in df.columns.to_list()
        if col not in original_columns
    ]
    df = df[all_columns]
    return df


def batch(
    df,
    wrangles: list,
    functions: _Union[_types.FunctionType, list] = [],
    batch_size: int = 1000,
    threads: int = 1,
    on_error: dict = None
):
    """
    type: object
    description: >-
      Split the data into batches for executing a list of wrangles.
      Use this in situations such as where the intermediate data
      is too large to fit in memory.
    additionalProperties: false
    required:
      - wrangles
    properties:
      batch_size:
        type: integer
        description: The number of rows to split each batch into
        default: 1000
      wrangles:
        type: array
        description: |-
          The wrangles to execute on the data. Each series of wrangles
          will be run agaisnst the data in batches of the size
          defined by batch_size.
        minItems: 1
        items:
          "$ref": "#/$defs/wrangles/items"
      threads:
        type: integer
        description: The number of threads to use for parallel processing. Default 1.
      on_error:
        type: object
        description: A dictionary of column_name: value to return if an error occurs while attempting to run a batch
    """
    if not isinstance(df, _pd.DataFrame):
        raise ValueError('Input must be a pandas DataFrame')

    if not isinstance(batch_size, int):
        try:
            batch_size = int(batch_size)
        except:
          raise ValueError('batch_size must be an integer greater than 0')
    if batch_size < 1:
        raise ValueError('batch_size must be an integer greater than 0')

    if not isinstance(threads, int):
        try:
            threads = int(threads)
        except:
            raise ValueError('threads must be an integer greater than 0')
    if threads < 1:
        raise ValueError('threads must be an integer greater than 0')
    
    def _batch_thread(df, wrangles, functions):
        try:
            return _wrangles.recipe.run(
                {"wrangles": wrangles},
                dataframe=df,
                functions=functions
            )
        except Exception as err:
            if on_error:
                return df.assign(**{
                    k: [v] * len(df)
                    for k, v in on_error.items()
                })
            else:
                raise err from None

    with _futures.ThreadPoolExecutor(max_workers=threads) as executor:
        batches = list(_divide_batches(df, batch_size))

        results = list(executor.map(
            _batch_thread,
            batches,
            [wrangles] * len(batches),
            [functions] * len(batches)
        ))

    return _pd.concat(results)


def classify(
    df: _pd.DataFrame,
    input: _Union[str, list],
    output: _Union[str, list],
    model_id: str,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: |
      Run classify wrangles on the specified columns.
      Requires WrangleWorks Account and Subscription.
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
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = _classify(
            df[input_column].astype(str).tolist(),
            model_id,
            **kwargs
        )

    return df


def date_calculator(df: _pd.DataFrame, input: _Union[str, _pd.Timestamp], operation: str = 'add', output: _Union[str, _pd.Timestamp] = None, time_unit: str = None, time_value: float = None) -> _pd.DataFrame:
    """
    type: object
    description: Add or Subtract time from a date
    additionalProperties: false
    required:
      - input
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
    # Get all of the date parameters for operation
    offset = _pd.DateOffset(**{time_unit: time_value})

    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        # Converting data to datetime
        df_temp = _pd.to_datetime(df[input_column])
        
        results = []
        if operation == 'add':
            for date in df_temp:
                results.append(date + offset)
                
        elif operation == 'subtract':
            for date in df_temp:
                results.append(date - offset)
                
        else:
            raise ValueError(f'\"{operation}\" is not a valid operation. Available operations: \"add\", \"subtract\"')
        
        df[output_column] = results

    return df


def filter(
    df: _pd.DataFrame,
    input: _Union[str, list] = [],
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
    where_params: _Union[list, dict] = None,
    **kwargs,
) -> _pd.DataFrame:
    """
    type: object
    description: |-
      Filter the dataframe based on the contents.
      If multiple filters are specified, all must be correct.
      For complex filters, use the where parameter.
    additionalProperties: false
    properties:
      where:
        type: string
        description: Use a SQL WHERE clause to filter the data.
      where_params:
        type: 
          - array
          - object
        description: |-
          Variables to use in conjunctions with where.
          This allows the query to be parameterized.
          This uses sqlite syntax (? or :name)
      input:
        type:
          - string
          - array
        description: |-
          Name of the column to filter on.
          If multiple are provided, all must match the criteria.
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
        # Filter the dataframe based on the where clause
        # and use the index to filter the dataframe
        # to prevent any side effects from passing through the DB
        df = df.loc[
            sql(
                df,
                f"""
                SELECT *
                FROM df
                WHERE {where};
                """,
                where_params,
                preserve_index=True
            ).index.to_list()
        ]

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]

    for input_column in input: 
        if equal != None:
            if not isinstance(equal, list): equal = [equal]
            df = df.loc[df[input_column].isin(equal)]

        if not_equal != None:
            if not isinstance(not_equal, list): not_equal = [not_equal]
            df = df.loc[~df[input_column].isin(not_equal)]
        
        if is_in != None:
            if not isinstance(is_in, list): is_in = [is_in]
            df = df[df[input_column].isin(is_in)]
        
        if not_in != None:
            if not isinstance(not_in, list): not_in = [not_in]
            df = df[~df[input_column].isin(not_in)]
        
        if greater_than != None:
            df = df[df[input_column] > greater_than]
        
        if greater_than_equal_to != None:
            df = df[df[input_column] >= greater_than_equal_to]
        
        if less_than != None:
            df = df[df[input_column] < less_than]
        
        if less_than_equal_to != None:
            df = df[df[input_column] <= less_than_equal_to]
        
        if between != None:
            if len(between) != 2: raise ValueError('Can only use "between" with two values')
            df = df[df[input_column].between(between[0], between[1], **kwargs)]
        
        if contains != None:
            df = df[df[input_column].str.contains(contains, na=False, **kwargs)]
        
        if not_contains != None:
            df = df[~df[input_column].str.contains(not_contains, na=False, **kwargs)]
        
        if is_null == True:
            df = df[df[input_column].isnull()]
        
        if is_null == False:
            df = df[df[input_column].notnull()]

    df = df.reset_index(drop=True)

    return df


def huggingface(
    df: _pd.DataFrame,
    input: _Union[str, list],
    api_token: str,
    model: str,
    output: _Union[str, list] = None,
    parameters = None
):
    """
    type: object
    description: Use a model from huggingface
    required:
      - input
      - api_token
      - model
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
        description: >
          Name of the output column.
          If not provided, will overwrite the input column
      model:
        type: string
        description: Name of the model to use. e.g. facebook/bart-large-cnn
      api_token:
        type: string
        description: Huggingface API Token
      parameters:
        type: object
        description: Optionally, provide additional parameters to define the model behaviour
    """
    if not output: output = input
    if not isinstance(output, list): output = [output]
    if not isinstance(input, list): input = [input]

    json_base = {}
    if parameters:
        json_base['parameters'] = parameters

    for input_col, output_col in zip(input, output):
        df[output_col] = [
            _requests.post(
                f"https://api-inference.huggingface.co/models/{model}",
                headers={
                    "Authorization": f"Bearer {api_token}"
                },
                json={
                    **json_base,
                    **{"inputs": row}
                }
            ).json()
            for row in df[input_col].values
        ]

    return df


def log(
    df: _pd.DataFrame,
    columns: list = None,
    write: list = None,
    error: str = None,
    warning: str = None,
    info: str = None,
    log_data: bool = True
):
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
          "$ref": "#/$defs/write/items"
      error:
        type: string
        description: Log an error to the console
      warning:
        type: string
        description: Log a warning to the console
      info:
        type: string
        description: Log info to the console
      log_data:
        type: boolean
        description: Whether to log a sample of the contents of the dataframe. Default True.
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

    if error:
        _logging.error(error)
    if warning:
        _logging.warning(warning)
    if info:
        _logging.info(info)
    if log_data:
        _logging.info(msg=': Dataframe ::\n\n' + df_tolog.to_string() + '\n')

    if write:
        _wrangles.recipe.run(
            {'write': write},
            dataframe=df
        )

    return df


def lookup(
    df: _pd.DataFrame,
    input: str,
    output: _Union[str, list] = None,
    model_id: str = None,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Lookup values from a saved lookup wrangle
    required:
      - input
      - model_id
    properties:
      input:
        type: string
        description: Name of the column(s) to lookup.
      model_id:
        type: string
        description: The model_id to use lookup against
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
    """
    # Ensure input is only 1 value
    if isinstance(input, list):
        if len(input) == 1:
            input = input[0]
        else:
            raise ValueError('Input only allows one column.')
    
    if output is None: output = input

    # Ensure output is a list
    if not isinstance(output, list): output = [output]

    # If user specified a model_id, use it to lookup values
    if model_id:
        metadata = _model(model_id)
        if metadata.get('message', None) == 'error':
            raise ValueError('Incorrect model_id.\nmodel_id may be wrong or does not exists')
        
        # Split input/output if user differentiated e.g. "wrangle_column: output_column"
        wrangle_output = [
            list(val.keys())[0] if isinstance(val, dict) else val
            for val in output    
        ]
        output = [
            list(val.values())[0] if isinstance(val, dict) else val
            for val in output    
        ]

        if all([col in metadata["settings"]["columns"] for col in wrangle_output]):
            # User specified all columns from the wrangle
            # Add respective columns to the dataframe
            data = _lookup(
                df[input].values.tolist(),
                model_id,
                columns=wrangle_output,
                **kwargs
            )
            df[output] = data
        elif not any([col in metadata["settings"]["columns"] for col in wrangle_output]):
            # User specified no columns from the wrangle
            # Add dict of all values to those columns
            data = _lookup(
                df[input].values.tolist(),
                model_id,
                **kwargs
            )
            for out in output:
                df[out] = data
        else:
            # User specified a mixture of unrecognized columns and columns from the wrangle
            raise ValueError('Lookup may only contain all named or unnamed columns.')
    else:
        raise ValueError('model_id is required for lookup')
    
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
        description: |
          The mathematical expression using column names. e.g. column1 * column2
          + column3.  Note: spaces within column names are replaced by underscores (_).
      output:
        type: string
        description: The column to output the results to
    """
    df_temp = df.copy()
    df_temp.columns = df_temp.columns.str.replace(' ', '_')
    df[output] = _ne.evaluate(input, df_temp.to_dict(orient='list'))
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
        description: |
          The mathematical expression using column names. e.g. column1 * column2
          + column3. Note: spaces within column names are replaced by underscores (_).
      output:
        type: string
        description: The column to output the results to
    """
    df_temp = df.copy()
    df_temp.columns = df_temp.columns.str.replace(' ', '_')
    df[output] = _ne.evaluate(input, df_temp.to_dict(orient='list'))
    return df


def python(
    df: _pd.DataFrame,
    command: str,
    output: _Union[str, list],
    input: _Union[str, list] = None,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: |-
      Apply a simple single-line python command. For more complex python use a custom function.
      Note, this evaluates the python command - be especially cautious including
      variables from untrusted sources within the command string.
      The python command will be evaluated once for each row and the result returned.
      Reference column values by using their name.
      Non-alphanumeric characters within column names are replaced by underscores (_)
      Additionally, all columns are available as a dict named kwargs.
      Additional parameters set for the wrangle will also be available to the command.
    required:
      - command
      - output
    properties:
      input:
        type:
          - string
          - array
        description: |
          Name or list of input column(s) to filter the data available
          to the command. Useful in conjunction with kwargs to target
          a variable range of columns.
          If not specified, all columns will be available.
      output:
        type:
          - string
          - array
        description: |
          Name or list of output column(s). To output multiple columns,
          return a list of the corresponding length.
      command:
        type: string
        description: |
          Python command. This must return a value.
          Note: any non-alphanumeric characters in variable names
          are replaced by underscores (_).
    """
    # Ensure input is a list and if not
    # specified then set to all columns
    if not input:
        input = list(df.columns)
    if not isinstance(input, list):
        input = [input]

    # Create rename dict to rename variables
    # that can't be used as python variables
    rename_dict = {
        **{
            k: _re.sub(r'[^a-zA-Z0-9_]', '_', k)
            for k in kwargs.keys()
        },
        **{
            k: _re.sub(r'[^a-zA-Z0-9_]', '_', k)
            for k in input
        }
    }

    # Set whether to output as a single or multiple columns
    if isinstance(output, list) and len(output) > 1:
        result_type = "expand"
    else:
        result_type = "reduce"
    
    def _apply_command(**kwargs):
        return eval(
            command,
            {
                **{
                    rename_dict.get(k, k): v
                    for k, v in kwargs.items()
                },
                **{"kwargs": kwargs}
            },
            {}
        )
    
    df[output] = df[input].apply(
        lambda x: _apply_command(**x, **kwargs),
        axis=1,
        result_type=result_type
    )

    return df


def recipe(
    df: _pd.DataFrame,
    name: str = None,
    variables = {},
    output_columns = None,
    functions: _Union[_types.FunctionType, list] = [],
    **kwargs
) -> _pd.DataFrame:
    """
    anyOf:
      - "$ref": "#"
      - type: object
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
    if not name: name = kwargs

    original_df = df.copy() # copy of the original df
    
    # Running recipe wrangle
    df_temp = _recipe.run(name, variables=variables, functions=functions, dataframe=df)
    
    # column output logic
    if output_columns is None:
        df = df_temp
    else:
        df = original_df.merge(df_temp[output_columns], how='left', left_index=True, right_index=True)
        
    return df


def remove_words(
    df: _pd.DataFrame,
    input: _Union[str, list],
    to_remove: str,
    output: _Union[str, list] = None,
    tokenize_to_remove: bool = False,
    ignore_case: bool = True
    ) -> _pd.DataFrame:
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
        type: 
          - string
          - array
        description: Name of the output columns
      tokenize_to_remove:
        type: boolean
        description: Tokenize all to_remove inputs
      ignore_case:
        type: boolean
        description: Ignore input and to_remove case
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = _extract.remove_words(df[input_column].values.tolist(), df[to_remove].values.tolist(), tokenize_to_remove, ignore_case)
    
    return df


def rename(
    df: _pd.DataFrame,
    input: _Union[str, list] = None,
    output: _Union[str, list] = None,
    wrangles: list = None,
    **kwargs
) -> _pd.DataFrame:
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
      wrangles:
        type: array
        description: |-
          Use wrangles to transform the column names.
          The input is named 'columns' and the final result
          must also include the column named 'columns'.
          This can only be used instead of the standard rename.
        minItems: 1
        items:
          "$ref": "#/$defs/wrangles/items"
    """
    # Allow using wrangles to manipulate the column names
    if wrangles:
        input = df.columns.tolist()
        try:
            output = _wrangles.recipe.run(
                {"wrangles": wrangles},
                dataframe=_pd.DataFrame({
                    "columns": input
                }),
                functions=kwargs.get("functions", {})
            )["columns"].tolist()
        except:
            raise RuntimeError("If using wrangles to rename, a column named 'columns' must be returned.")
    
        if len(input) != len(output):
            raise RuntimeError(
                "If using wrangles to rename columns, " +
                "the results must be the same length as the input columns."
            )
    else:
        # Drop functions if not needed
        if (
            "functions" in kwargs and
            isinstance(kwargs["functions"], dict)
        ):
            del kwargs["functions"]

    # If short form of paired names is provided, use that
    if input is None:
        # Check that column name exists
        rename_cols = list(kwargs.keys())
        for x in rename_cols:
            if x not in list(df.columns): raise ValueError(f'Rename column "{x}" not found.')
        # Check if the new column names exist if so drop them
        df = df.drop(columns=[x for x in list(kwargs.values()) if x in df.columns])
        
        rename_dict = kwargs
    else:
        if not output:
            raise ValueError('If an input is provided, an output must also be provided.')

        # If a string provided, convert to list
        if not isinstance(input, list): input = [input]
        if not isinstance(output, list): output = [output]

        # Ensure input and output are equal lengths
        if len(input) != len(output):
            raise ValueError('The lists for input and output must be the same length.')
        
        # Check that the output columns don't already exist if so drop them
        df = df.drop(columns=[x for x in output if x in df.columns])
        
        # Otherwise create a dict from input and output columns
        rename_dict = dict(zip(input, output))

    return df.rename(columns=rename_dict)


def replace(df: _pd.DataFrame, input: _Union[str, list], find: str, replace: str, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Quick find and replace for simple values. Can use regex in the find field.
    additionalProperties: false
    required:
      - input
      - find
      - replace
    properties:
      input:
        type:
          - string
          - array
        description: Name or list of input column
      output:
        type:
          - string
          - array
        description: Name or list of output column
      find:
        type: string
        description: Pattern to find using regex
      replace:
        type: string
        description: Value to replace the pattern found
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].apply(lambda x: _re.sub(str(find), str(replace), str(x)))
        
    return df


def similarity(df: _pd.DataFrame, input: list,  output: str, method: str = 'cosine') -> _pd.DataFrame:
    """
    type: object
    description: Calculate the cosine similarity of two vectors
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: array
        description: Two columns of vectors to compare the similarity of.
        minItems: 2
        maxItems: 2
      output:
        type: string
        description: Name of the output column.
      method:
        type: string
        description: >-
          The type of similarity to calculate (cosine or euclidean).
          Adjusted cosine adjusts the default cosine calculation
          to cover a range of 0-1 for typical comparisons.
        enum:
          - cosine
          - adjusted cosine
          - euclidean
    """
    # Check to see that two columns were passed through input
    if not isinstance(input, list) or len(input) != 2:
        raise ValueError('Input must consist of a list of two columns')

    if method == 'cosine':
        similarity_list = [
            _np.dot(x, y)
            /
            (_np.linalg.norm(x) * _np.linalg.norm(y)) 
            for x, y in zip(df[input[0]].values, df[input[1]].values)
        ]
    elif method == 'adjusted cosine': # Normalizes output from 0-1
        similarity_list = [
            round(max(min(
              1 - _math.acos(
                  round(
                    _np.dot(x, y)
                    /
                    (_np.linalg.norm(x) * _np.linalg.norm(y)),
                    3
                  )
            ), 1), 0), 3)
            for x, y in zip(df[input[0]].values, df[input[1]].values)
        ]
    elif method == 'euclidean':
        similarity_list = [
            _math.sqrt(
                sum(
                    pow(a -b, 2)
                    for a, b in zip(x, y)
                )
            )
            for x, y in zip(df[input[0]].values, df[input[1]].values)
        ]
    else:
        # Ensure method is of a valid type
        raise TypeError('Invalid method, must be "cosine", "adjusted cosine" or "euclidean"')

    # Ensure values are python float
    df[output] = [
        float(x)
        for x in similarity_list
    ]

    return df


def sql(
    df: _pd.DataFrame,
    command: str,
    params: _Union[list, dict] = None,
    preserve_index: bool = False
) -> _pd.DataFrame:
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
      params:
        type: 
          - array
          - object
        description: |-
          Variables to use in conjunctions with query.
          This allows the query to be parameterized.
          This uses sqlite syntax (? or :name)
    """
    # Copy to ensure the index of the original dataframe isn't mutated
    df = df.copy()

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
            if isinstance(row, dict) or isinstance(row, list):
                # Check if there is an object in the column and record column name to convert to json
                cols_changed.append(cols)
                break
            # Only check the first 10 rows of a column
            count += 1
            if count > 10: break
            
        if cols in cols_changed:
            # If the column is in cols_changed then convert to json
            _to_json(df=df, input=cols)

    if preserve_index:
        # Preserve original index and replace with an distinctive name
        index_names = list(df.index.names)
        df.index.names = ["wrwx_sql_temp_index"]

        # Write the dataframe to the database
        df.to_sql('df', db, if_exists='replace', index = True, method='multi', chunksize=1000)
        
        # Execute the user's query against the database and return the results
        df = _pd.read_sql(command, db, params = params, index_col="wrwx_sql_temp_index")

        # Restore the original index names
        df.index.names = index_names
    else:
        # Write the dataframe to the database
        df.to_sql('df', db, if_exists='replace', index = True, method='multi', chunksize=1000)
        # Execute the user's query against the database and return the results
        df = _pd.read_sql(command, db, params = params)

    db.close()
    
    # Change the columns back to an object
    for new_cols in df.columns:
        if new_cols in cols_changed:
            # If the column is in cols changed, then change back to an object
            _from_json(df=df, input=new_cols)
    
    return df


def standardize(
    df: _pd.DataFrame,
    input: _Union[str, list],
    model_id: _Union[str, list],
    output: _Union[str, list] = None,
    case_sensitive: bool = False,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Standardize data using a DIY or bespoke standardization wrangle. Requires WrangleWorks Account and Subscription.
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
      case_sensitive:
        type: bool
        description: Allows the wrangle to be case sensitive if set to True, default is False.
    """
    # If user hasn't specified an output column, overwrite the input
    if output is None: output = input

    # If user provides a single string, convert all the arguments to lists for consistency
    if isinstance(input, str): input = [input]
    if isinstance(output, str): output = [output]
    if isinstance(model_id, str): model_id = [model_id]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # If Several model ids applied to a column in place
    if all(len(x) == 1 for x in [input, output]) and isinstance(model_id, list):
        tmp_output = input
        df_copy = df.loc[:, [input[0]]]
        for model in model_id:
            for input_column, output_column in zip(input, tmp_output):
                df_copy[output_column] = _standardize(
                    df_copy[output_column].astype(str).tolist(),
                    model,
                    case_sensitive,
                    **kwargs
                )

        # Adding the result of the df_copy to the original dataframe
        df[output[0]] = df_copy[output_column]
        return df

    for model in model_id:
        for input_column, output_column in zip(input, output):
            df[output_column] = _standardize(
                df[input_column].astype(str).tolist(),
                model,
                case_sensitive,
                **kwargs
            )

    return df


def translate(
    df: _pd.DataFrame,
    input: _Union[str, list],
    output: _Union[str, list],
    target_language: str,
    source_language: str = 'AUTO',
    case: str = None,
    **kwargs
) -> _pd.DataFrame:
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
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = _translate(
            df[input_column].astype(str).tolist(),
            target_language,
            source_language,
            case,
            **kwargs
        )

    return df
