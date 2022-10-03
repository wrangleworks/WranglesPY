"""
Create and execute Wrangling recipes
"""
import pandas as _pandas
import yaml as _yaml
import logging as _logging
from typing import Union as _Union
import types as _types
import os as _os
import fnmatch as _fnmatch
import inspect as _inspect
import warnings as _warnings
import requests as _requests
import re as _re

from . import recipe_wrangles as _recipe_wrangles
from . import connectors as _connectors


_logging.getLogger().setLevel(_logging.INFO)


# Suppress pandas performance warnings
# this appears in some instances during the recipe execution when generating new columns.
# There does not appear to be low performance, despite the warning,
# but will also investigate if there is a better long term solution
_warnings.simplefilter(action='ignore', category=_pandas.errors.PerformanceWarning)


def _load_recipe(recipe: str, variables: dict = {}) -> dict:
    """
    Load yaml recipe file + replace any placeholder variables

    :param recipe: YAML recipe or name of a YAML file to be parsed
    :param variables: (Optional) dictionary of custom variables to override placeholders in the YAML file

    :return: YAML Recipe converted to a dictionary
    """
    _logging.info(": Reading Recipe ::")
    
    # If the recipe to read is from "https://" or "http://"
    if 'https://' == recipe[:8] or 'http://' == recipe[:7]:
        response = _requests.get(recipe)
        if str(response.status_code)[0] != '2':
            raise ValueError(f'Error getting recipe from url: {response.url}\nReason: {response.reason}-{response.status_code}')
        recipe_string = response.text

    # If recipe is a single line, it's probably a file path
    # Otherwise it's a recipe
    elif "\n" in recipe:
        recipe_string = recipe
    else:
        with open(recipe, "r") as f:
            recipe_string = f.read()
    
    # Also add environment variables to list of placeholder variables
    # Q: Should we exclude some?
    for env_key, env_val in _os.environ.items():
        if env_key not in variables.keys():
            variables[env_key] = env_val

    # Replace templated values
    for key, val in variables.items():
        recipe_string = recipe_string.replace("${" + key + "}", val)

    recipe_object = _yaml.safe_load(recipe_string)

    return recipe_object


def _run_actions(recipe: _Union[dict, list], connections: dict = {}, functions: dict = {}) -> None:
    # If user has entered a dictionary, convert to list
    if isinstance(recipe, dict):
        recipe = [recipe]

    for action in recipe:
        for action_type, params in action.items():
            # Use shared connection details if set
            if 'connection' in params.keys():
                params.update(connections[params['connection']])
                params.pop('connection')

            if action_type.split('.')[0] == 'custom':
                # Execute a user's custom function
                functions[action_type[7:]](**params)

            else:
                # Get run function of requested connector and pass user defined params
                obj = _connectors
                for element in action_type.split('.'):
                    obj = getattr(obj, element)

                getattr(obj, 'run')(**params)


def _read_data_sources(recipe: _Union[dict, list], connections: dict = {}, functions: dict = {}) -> _pandas.DataFrame:
    """
    Import data from requested datasources as defined by the recipe

    :param recipe: Read section of a recipe
    :param connections: shared connections
    :param functions: (Optional) A dictionary of named custom functions passed in by the user
    :return: Dataframe of imported data
    """
    # Allow blended imports
    if list(recipe)[0] in ['join', 'concatenate', 'union']:
        dfs = []
        for source in recipe[list(recipe)[0]]['sources']:
            dfs.append(_read_data_sources(source, connections))
        
        recipe_temp = recipe[list(recipe)[0]]
        recipe_temp.pop('sources')

        if list(recipe)[0] == 'join':
            df = _pandas.merge(dfs[0], dfs[1], **recipe['join'])
        elif list(recipe)[0] == 'union':
            df = _pandas.concat(dfs, **recipe['union'])
        elif list(recipe)[0] == 'concatenate':
            recipe['concatenate']['axis'] = 1
            df = _pandas.concat(dfs, **recipe['concatenate'])

    elif list(recipe)[0].split('.')[0] == 'custom':
        # Execute a user's custom function
        read_name = list(recipe)[0]
        params = recipe[read_name]
        df = functions[read_name[7:]](**params)

    else:
        # Single source import
        import_type = list(recipe)[0]
        params = recipe[import_type]

        # Use shared connection details if set
        if 'connection' in params.keys():
            params.update(connections[params['connection']])
            params.pop('connection')

        # Load appropriate data
        df = getattr(getattr(_connectors, import_type), 'read')(**params)
    
    return df
    
def _wildcard_expansion(df_columns: list, params: dict) -> list:
    """
    Expand wildcards and set the columns in order for Wrangle inputs
    
    :param df_columns: List of dataframe columns
    :param params: Wrangle parameters to use (inputs)
    """
    if isinstance(params.get('input', ''), str): params['input'] = [params['input']]
    wildcard_check = [x for x in params['input'] if '*' in x]
    columns_to_use = []
    temp_cols = []
    # Check if there are any asterisks in columns to use
    if len(wildcard_check):
        for iter in wildcard_check:
            
            # Do nothing id the user enters an escape character
            if '\\' in iter:
                column = iter.replace('\\', '')
                columns_to_use.append(column)
            # Add all columns with similar names
            else:
                column = iter.replace('*', '')
                re_pattern = r"^\b{}(\s)?(\d+)?\b$".format(column)
                list_re = [_re.search(re_pattern, x) for x in df_columns]
                temp_cols.extend([x.string for x in list_re if x != None])
    
    # Remove columns that have '*' as they are handled above
    no_wildcard = [x for x in params['input'] if '*' not in x]
    
    # Arrange the columns in columns order
    columns_to_use.extend(no_wildcard)
    columns_to_use.extend(temp_cols)
    
    index_keys = {}
    for col_name in columns_to_use:
        index_keys[df_columns.index(col_name)] = col_name
    
    sorted_index = list(index_keys.keys())
    sorted_index.sort()
    
    sorted_columns_to_use = [index_keys[x] for x in sorted_index]
    
    return sorted_columns_to_use


def _execute_wrangles(df, wrangles_list, functions: dict = {}) -> _pandas.DataFrame:
    """
    Execute a list of Wrangles on a dataframe

    :param df: Dateframe that the Wrangles will be run against
    :param wrangles_list: List of Wrangles + their definitions to be executed
    :param functions: (Optional) A dictionary of named custom functions passed in by the user
    :return: Pandas Dataframe of the Wrangled data
    """
    for step in wrangles_list:
        for wrangle, params in step.items():
            if params is None: params = {}
            _logging.info(f": Wrangling :: {wrangle} :: {params.get('input', 'None')} >> {params.get('output', 'Dynamic')}")

            if wrangle.split('.')[0] == 'pandas':
                # Execute a pandas method
                # TODO: disallow any hidden methods
                # TODO: remove parameters, allow selecting in/out columns
                try:
                    df[params['output']] = getattr(df[params['input']], wrangle.split('.')[1])(**params.get('parameters', {}))
                except:
                    df = getattr(df, wrangle.split('.')[1])(**params.get('parameters', {}))

            elif wrangle.split('.')[0] == 'custom':
                # Execute a user's custom function
                try:
                    custom_function = functions[wrangle[7:]]
                except:
                    raise ValueError(f'Custom Wrangle function: "{wrangle}" not found')

                # Get user's function arguments
                function_args = _inspect.getfullargspec(custom_function).args

                if function_args[0] == 'df':
                    # If user's first argument is df, pass them the whole dataframe
                    df = functions[wrangle[7:]](df, **params)
                elif function_args[0] == 'cell':
                    # If user's first function is cell, pass them the cells defined by the parameter input individually
                    input_column = params['input']
                    params.pop('input')
                    if params.get('output') is None:
                        output_column = input_column
                    else:
                        output_column = params['output']
                        params.pop('output')
                    df[output_column] = [custom_function(cell, **params) for cell in df[input_column].to_list()]

                else:
                    pass # pragma: no cover
                    # shouldn't get here

            else:
                # Blacklist of Wrangles not to allow wildcards for
                if wrangle not in ['math', 'maths', 'merge.key_value_pairs', 'split.text', 'split.list', 'split.dictionary']:
                    
                    # Allow user to specify a wildcard (*) for the input columns
                    if '*' in params.get('input', '') or len([x for x in params.get('input', ['']) if '*' in x]):
                    
                        # Set the params to the new columns to use from Expand Wildcard function
                        params['input'] = _wildcard_expansion(df_columns=df.columns.tolist(), params=params)
                        
                # Get the requested function from the recipe_wrangles module
                obj = _recipe_wrangles
                for element in wrangle.split('.'):
                    obj = getattr(obj, element)

                # Execute the requested function and return the value
                df = obj(df, **params)

    return df


def _write_data(df: _pandas.DataFrame, recipe: dict, connections: dict = {}, functions: dict = {}) -> _pandas.DataFrame:
    """
    Export data to the requested targets as defined by the recipe

    :param df: Dataframe to be exported
    :param recipe: write section of a recipe
    :param connections: shared connections
    :param functions: (Optional) A dictionary of named custom functions passed in by the user
    :return: Dataframe, a subset if the 'dataframe' write type is set with specific columns
    """
    # Initialize returned df as df to start
    df_return = df

    # If user has entered a dictionary, convert to list
    if isinstance(recipe, dict):
        recipe = [recipe]

    # Loop through all exports, get type and execute appropriate export
    for export in recipe:
        for export_type, params in export.items():
            if export_type == 'dataframe':
                # Define the dataframe that is returned
                df_return = df[params['columns']]
            
            # Execute a user's custom function
            elif export_type.split('.')[0] == 'custom':
                df = functions[export_type[7:]](df, **params)

            else:
                # Use shared connection details if set
                if 'connection' in params.keys():
                    params.update(connections[params['connection']])
                    params.pop('connection')

                # Get output function of requested connector and pass dataframe + user defined params
                getattr(getattr(_connectors, export_type), 'write')(df, **params)

    return df_return


def run(recipe: str, variables: dict = {}, dataframe: _pandas.DataFrame = None, functions: _Union[_types.FunctionType, list, dict] = []) -> _pandas.DataFrame:
    """
    Execute a Wrangles Recipe. Recipes are written in YAML and allow a set of steps to be run in an automated sequence. Read, wrangle, then write your data.

    >>> wrangles.recipe.run('recipe.wrgl.yml')
    
    :param recipe: YAML recipe or path to a YAML file containing the recipe
    :param variables: (Optional) A dictionary of custom variables to override placeholders in the recipe. Variables can be indicated as ${MY_VARIABLE}. Variables can also be overwritten by Environment Variables.
    :param dataframe: (Optional) Pass in a pandas dataframe, instead of defining a read section within the YAML
    :param functions: (Optional) A function or list of functions that can be called as part of the recipe. Functions can be referenced as custom.function_name

    :return: The result dataframe. The dataframe can be defined using write: - dataframe in the recipe.
    """
    # Parse recipe
    recipe = _load_recipe(recipe, variables)

    try:
        # Format custom functions
        # If user has passed in a single function, convert to a list
        if callable(functions): functions = [functions]
        # Convert custom functions from a list to a dict using the name as a key
        if isinstance(functions, list):
            functions = {custom_function.__name__: custom_function for custom_function in functions}

        # Run any actions required before the main recipe runs
        if 'on_start' in recipe.get('run', {}).keys():
            _run_actions(recipe['run']['on_start'], recipe.get('connections', {}), functions)

        # Get requested data
        if 'read' in recipe.keys():
            # Execute requested data imports
            if isinstance(recipe['read'], list):
                df = _read_data_sources(recipe['read'][0], recipe.get('connections', {}), functions)
            else:
                df = _read_data_sources(recipe['read'], recipe.get('connections', {}), functions)
        elif dataframe is not None:
            # User has passed in a pre-created dataframe
            df = dataframe
        else:
            # User hasn't provided anything - initialize empty dataframe
            df = _pandas.DataFrame()

        # Execute any Wrangles required (allow single or plural)
        if 'wrangles' in recipe.keys():
            df = _execute_wrangles(df, recipe['wrangles'], functions)
        elif 'wrangle' in recipe.keys():
            df = _execute_wrangles(df, recipe['wrangle'], functions)

        # Execute requested data exports
        if 'write' in recipe.keys():
            df = _write_data(df, recipe['write'], recipe.get('connections', {}), functions)

        # Run any actions required after the main recipe finishes
        if 'on_success' in recipe.get('run', {}).keys():
            _run_actions(recipe['run']['on_success'], recipe.get('connections', {}), functions)

        return df

    except Exception as e:
        try:
            # Run any actions requested if the recipe fails
            if 'on_failure' in recipe.get('run', {}).keys():
                _run_actions(recipe['run']['on_failure'], functions=functions)
        except:
            pass

        raise e