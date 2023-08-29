"""
Create and execute Wrangling recipes
"""
import yaml as _yaml
import json as _json
import logging as _logging
from typing import Union as _Union
import types as _types
import typing as _typing
import os as _os
import inspect as _inspect
import re as _re
import warnings as _warnings
import pandas as _pandas
import requests as _requests
from . import recipe_wrangles as _recipe_wrangles
from . import connectors as _connectors
from .config import no_where_list
from . import data as _data
from types import ModuleType as _ModuleType
from inspect import isfunction as _isfunction


_logging.getLogger().setLevel(_logging.INFO)


# Suppress pandas performance warnings
# this appears in some instances during the recipe execution when generating new columns.
# There does not appear to be low performance, despite the warning,
# but will also investigate if there is a better long term solution
_warnings.simplefilter(action='ignore', category=_pandas.errors.PerformanceWarning)


def _replace_templated_values(
    recipe_object: _typing.Any,
    variables: dict,
    ignore_unknown_variables: bool = False
) -> _typing.Any:
    """
    Replace templated values of the format ${} within a recipe.
    This function can be called recursively to iterate through an arbitrary number of levels within the main object
    
    :param recipe_object: Recipe object that may contain values to replace
    :param variables: List of variables that contain any templated values to update
    :param ignore_unknown_variables: Do not raise an error for unrecognized variables from this point \
        down the stack. e.g. for matrix which uses runtime variables.
    :return: Updated Recipe object with variables replaced by their corresponding values
    """
    if isinstance(recipe_object, list):
        # Iterate over all of the elements in a list recursively
        new_recipe_object = [
            _replace_templated_values(element, variables, ignore_unknown_variables)
            for element in recipe_object
        ]
            
    elif isinstance(recipe_object, dict):
        # Iterate over all of the keys and value in a dictionary recursively
        new_recipe_object = {
            _replace_templated_values(
                key,
                variables,
                any([ignore_unknown_variables, key in ["matrix"]])
            )
            : 
            _replace_templated_values(
                val,
                variables,
                any([ignore_unknown_variables, key in ["matrix"]])
            )
            for key, val in recipe_object.items()
        }

    elif isinstance(recipe_object, str):
        # Search string for one or more variables to replace
        new_recipe_object = recipe_object

        # Pattern matching ${<something here>}
        variable_pattern = _re.compile(r"\$\{[^\}]+\}")

        # Whole string is a variable
        if variable_pattern.fullmatch(new_recipe_object):
            try:
                replacement_value = variables[new_recipe_object[2:-1]]
            except:
                if ignore_unknown_variables:
                    return new_recipe_object
                else:
                    raise ValueError(f"Variable {new_recipe_object} was not found.")

            # Test if replacement is JSON
            if (isinstance(replacement_value, str)
                and replacement_value[0] in ['{', '[']
                and replacement_value[-1] in ['}', ']']
            ):
                try:
                    replacement_value = _json.loads(replacement_value)
                except:
                    # Replacement wasn't JSON
                    pass

            # Test if replacement is YAML
            if (isinstance(replacement_value, str) 
                and ':' in replacement_value 
                and '\n' in replacement_value
            ):
                try:
                    replacement_value = _yaml.safe_load(replacement_value)
                except:
                    # Replacement wasn't YAML
                    pass

            new_recipe_object = _replace_templated_values(
                replacement_value,
                variables,
                ignore_unknown_variables
            )

        # Variable is found within the string e.g. file-${number}.csv
        # Since this is within a string, the type is forced to also be a string
        elif variable_pattern.search(new_recipe_object):
            for var in variable_pattern.findall(new_recipe_object):
                try:
                    replacement_value = variables[var[2:-1]]
                except:
                    if ignore_unknown_variables:
                        replacement_value = var
                    else:
                        raise ValueError(f"Variable {var} was not found.")

                new_recipe_object = new_recipe_object.replace(var, str(replacement_value))

    # Otherwise, just return unchanged    
    else:
        new_recipe_object = recipe_object

    return new_recipe_object


def _read_recipe(recipe: str, functions,  variables: dict = {}) -> dict:
    """
    Read recipe from various methods (website or gist, file path, model id or string)

    :param recipe: YAML recipe or name of a YAML file to be parsed

    :return: YAML Recipe as a string
    """
    _logging.info(": Reading Recipe ::")
    
    if not isinstance(recipe, str):
        try:
            # If user passes in a pre-parsed recipe, convert back to YAML
            recipe = _yaml.dump(recipe)
        except:
            raise ValueError('Recipe passed in as an invalid type')

    # If the recipe to read is from "https://" or "http://"
    if 'https://' == recipe[:8] or 'http://' == recipe[:7]:
        response = _requests.get(recipe)
        if str(response.status_code)[0] != '2':
            raise ValueError(f'Error getting recipe from url: {response.url}\nReason: {response.reason}-{response.status_code}')
        recipe_string = response.text

    # If recipe is a single line, it's probably a file path
    elif "\n" in recipe:
        recipe_string = recipe
    # If recipe matches xxxxxxxx-xxxx-xxxx, it's probably a model
    elif _re.search(r"[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}", recipe):
        model = _data.model_content(recipe)
        recipe_string = model['recipe']
    # Otherwise it's a recipe
    else:
        with open(recipe, "r", encoding='utf-8') as f:
            recipe_string = f.read()

        # Also add environment variables to list of placeholder variables
    # Q: Should we exclude some?
    for env_key, env_val in _os.environ.items():
        if env_key not in variables.keys():
            variables[env_key] = env_val

    recipe_object = _yaml.safe_load(recipe_string)
    
    # Check if there are any templated valued to update
    recipe_object = _replace_templated_values(recipe_object=recipe_object, variables=variables)

    # Check that functions is an empty list and recipe is being passed as a model_id
    if functions == [] and _re.search(r"[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}", recipe):
        # Read functions from model_id
        functions = _data.model_content(recipe)['functions']
        if functions != '':
            custom_module = _ModuleType('custom_module')
            exec(functions, custom_module.__dict__)
            functions = [getattr(custom_module, method) for method in dir(custom_module) if not method.startswith('_')]
            # getting only the functions
            functions = [x for x in functions if _isfunction(x)]
        else:
            functions = []

    return recipe_object, functions

def _load_functions(recipe: str, functions):
    """
    Loads functions when recipe is passed as a model id, passes functions through otherwise

    :param recipe: YAML recipe, name of a YAML file to be parsed or recipe model id
    :param functions: (Optional) A function or list of functions that can be called as part of the recipe. Functions can be referenced as custom.function_name

    :return: functions read from model id or passed through 
    """
    _logging.info(": Loading Functions ::")

    # Check that functions is an empty list and recipe is being passed as a model_id
    if functions == [] and _re.search(r"[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}", recipe):
        # Read functions from model_id
        functions = _data.model_content(recipe)['functions']
        if functions != '':
            custom_module = _ModuleType('custom_module')
            exec(functions, custom_module.__dict__)
            functions = [getattr(custom_module, method) for method in dir(custom_module) if not method.startswith('_')]
            # getting only the functions
            functions = [x for x in functions if _isfunction(x)]
        else:
            functions = []

    return functions

def _interpret_recipe(recipe_string: str, variables: dict = {}) -> dict:
    """
    Load yaml recipe file + replace any placeholder variables

    :param recipe: YAML recipe or name of a YAML file to be parsed
    :param variables: (Optional) dictionary of custom variables to override placeholders in the YAML file

    :return: YAML Recipe converted to a dictionary
    """
    # Also add environment variables to list of placeholder variables
    # Q: Should we exclude some?
    for env_key, env_val in _os.environ.items():
        if env_key not in variables.keys():
            variables[env_key] = env_val

    recipe_object = _yaml.safe_load(recipe_string)
    
    # Check if there are any templated valued to update
    recipe_object = _replace_templated_values(recipe_object=recipe_object, variables=variables)

    return recipe_object

def _run_actions(recipe: _Union[dict, list], functions: dict = {}, error: Exception = None) -> None:
    # If user has entered a dictionary, convert to list
    if isinstance(recipe, dict):
        recipe = [recipe]

    for action in recipe:
        for action_type, params in action.items():
            if action_type.split('.')[0] == 'custom':
                # Get custom function
                custom_function = functions[action_type[7:]]

                # Check if error is one of the user's function arguments
                if 'error' in _inspect.getfullargspec(custom_function).args:
                    params['error'] = error

                # Execute a user's custom function
                custom_function(**params)
            else:
                # Get run function of requested connector and pass user defined params
                obj = _connectors
                for element in action_type.split('.'):
                    obj = getattr(obj, element)

                if action_type == 'recipe':
                    params['functions'] = functions

                getattr(obj, 'run')(**params)


def _read_data_sources(recipe: _Union[dict, list], functions: dict = {}) -> _pandas.DataFrame:
    """
    Import data from requested datasources as defined by the recipe

    :param recipe: Read section of a recipe
    :param functions: (Optional) A dictionary of named custom functions passed in by the user
    :return: Dataframe of imported data
    """
    # Allow blended imports
    if list(recipe)[0] in ['join', 'concatenate', 'union']:
        dfs = []
        for source in recipe[list(recipe)[0]]['sources']:
            dfs.append(_read_data_sources(source, functions))
        
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
        if not isinstance(df, _pandas.DataFrame):
            raise RuntimeError(f"Function {read_name} did not return a dataframe")
    else:
        # Single source import
        import_type = list(recipe)[0]
        params = recipe[import_type]

        # Get read function of requested connector and pass user defined params
        obj = _connectors
        for element in import_type.split('.'):
            obj = getattr(obj, element)

        if import_type == 'recipe':
            params['functions'] = functions

        df = getattr(obj, 'read')(**params)
    
    return df

   
def _wildcard_expansion(all_columns: list, selected_columns: _Union[str, list]) -> list:
    """
    Finds matching columns for wildcards or regex from all available columns
    
    :param all_columns: List of all available columns in the dataframe
    :param selected_columns: List or string with selected columns. May contain wildcards (*) or regex.
    """
    if not isinstance(selected_columns, list): selected_columns = [selected_columns]

    # Convert wildcards to regex pattern
    for i in range(len(selected_columns)):
        # If column contains * without escape
        if _re.search(r'[^\\]?\*', selected_columns[i]) and not selected_columns[i].lower().startswith('regex:'):
            selected_columns[i] = 'regex:' + _re.sub(r'(?<!\\)\*', r'(.*)', selected_columns[i])

    # Using a dict to preserve insert order.
    # Order is preserved for Dictionaries from Python 3.7+
    result_columns = {}

    # Identify any matching columns using regex within the list
    for column in selected_columns:
        if column.lower().startswith('regex:'):
            result_columns.update(dict.fromkeys(list(filter(_re.compile(column[6:].strip()).fullmatch, all_columns)))) # Read Note below
        else:
            if column in all_columns:
                result_columns[column] = None
            else:
                raise KeyError(f'Column {column} does not exist')
    
    # Return, preserving original order
    return list(result_columns.keys())


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

            original_params = params.copy()
            if 'where' in params.keys() and wrangle not in no_where_list:
                df_original = df.copy()
                
                # Save original index, filter data, then restore index
                df['original_index_ikdejsrvjazl'] = df.index
                df = _filter_dataframe(
                    df,
                    where = params.pop('where'),
                    where_params= params.pop('where_params', None)
                )
                df = df.set_index(df['original_index_ikdejsrvjazl'])
                df = df.drop('original_index_ikdejsrvjazl', axis = 1)
                df.index.names = [None]

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
                fn_argspec = _inspect.getfullargspec(custom_function)

                # Check for function_args and df
                if 'df' in fn_argspec.args:
                    # If user's first argument is df, pass them the whole dataframe
                    df = custom_function(df=df, **params)
                    if not isinstance(df, _pandas.DataFrame):
                        raise RuntimeError(f"Function {wrangle} did not return a dataframe")

                # Dealing with no function_args
                else:
                    # Use a temp copy of dataframe as not to affect original
                    df_temp = df

                    # If user specifies an input, reduce dataframe down as required
                    if 'input' in params:
                        df_temp = df_temp[
                            _wildcard_expansion(
                                all_columns=df.columns.tolist(),
                                selected_columns=params['input']
                            )
                        ]

                    # If the user hasn't explicitly requested input or output
                    # then remove them so they will not be included in kwargs
                    params_temp = params.copy()
                    for special_parameter in ['input', 'output']:
                        if special_parameter in params_temp and special_parameter not in fn_argspec.args:
                            params_temp.pop(special_parameter)

                    # If the user's custom function does not have kwargs available
                    # then we need to remove any unmatched function arguments
                    # from the parameters or the columns
                    if not fn_argspec.varkw:
                        params_temp2 = params_temp.copy()
                        for param in params_temp2.keys():
                            if param not in fn_argspec.args:
                                params_temp.pop(param)

                        cols = df_temp.columns.to_list()
                        cols_renamed = [col.replace(' ', '_') for col in cols]

                        # Create a dictionary of columns with spaces and their replacement
                        # with an underscore. Used in df_temp.rename
                        colDict = {
                            col: col.replace(' ', '_') for col in cols
                            if (' ' in col and col.replace(' ', '_') in fn_argspec.args)
                        }

                        df_temp.rename(columns=colDict, inplace=True)
                        cols_renamed = [col for col in cols_renamed if col in fn_argspec.args]

                        # Ensure we don't remove all columns
                        # if user hasn't specified any
                        if cols_renamed:
                            df_temp = df_temp[cols_renamed]
                    
                    # If user specifies multiple outputs, expand any list output
                    # across the columns else return as a single column
                    if isinstance(params['output'], list) and len(params['output']) > 1:
                        result_type = 'expand'
                    else:
                        result_type = 'reduce'

                    # {**x, **params_temp} deals with columns in 
                    # function args and **params_temp without columns
                    # There may be no columns in the case that the user
                    # does not specify any columns in their function parameters
                    try:
                        df[params['output']] = df_temp.apply(
                            lambda x: custom_function(**{**x, **params_temp}),
                            axis=1,
                            result_type=result_type
                        )
                    except:
                        df[params['output']] = df_temp.apply(
                            lambda _: custom_function(**params_temp),
                            axis=1,
                            result_type=result_type
                        )

            else:
                # Blacklist of Wrangles not to allow wildcards for
                if wrangle not in ['math', 'maths', 'merge.key_value_pairs', 'split.text', 'split.list', 'split.dictionary', 'select.element'] and 'input' in params:
                    # Expand out any wildcards or regex in column names
                    params['input'] = _wildcard_expansion(all_columns=df.columns.tolist(), selected_columns=params['input'])
                        
                # Get the requested function from the recipe_wrangles module
                obj = _recipe_wrangles
                for element in wrangle.split('.'):
                    obj = getattr(obj, element)

                if wrangle == 'recipe':
                    params['functions'] = functions

                df = obj(df, **params)

            # If the user specified a where, we need to merge this back to the original dataframe
            if 'where' in original_params and wrangle not in no_where_list:
                if 'output' in params.keys():
                    # Wrangle explictly defined the output
                    output_columns = (
                        params['output']
                        if isinstance(params['output'], list)
                        else [params['output']]
                    )
                    df = _pandas.merge(
                        df_original,
                        df[output_columns],
                        left_index=True,
                        right_index=True,
                        how='left',
                        suffixes=('_x',None)
                    )
                    for output_col in output_columns:
                        if output_col + '_x' in df.columns:
                            df = _recipe_wrangles.merge.coalesce(
                                df,
                                [output_col, output_col+'_x'],
                                output_col
                            )
                            df.drop([output_col+'_x'], axis = 1, inplace=True)
                elif list(df.columns) == list(df_original.columns) and 'input' in list(params.keys()):
                    # Wrangle overwrote the input
                    output_columns = params['input']
                    df = _pandas.merge(
                        df_original,
                        df[output_columns],
                        left_index=True,
                        right_index=True,
                        how='left',
                        suffixes=('_x',None)
                    )
                    for input_col in params['input']:
                        if input_col + '_x' in df.columns:
                            df = _recipe_wrangles.merge.coalesce(
                                df,
                                [input_col, input_col+'_x'],
                                input_col
                            )
                            df.drop([input_col+'_x'], axis = 1, inplace=True)
                elif list(df.columns) != list(df_original.columns):
                    # Wrangle added columns
                    output_columns = [col for col in list(df.columns) if col not in list(df_original.columns)]
                    df = _pandas.merge(
                        df_original,
                        df[output_columns],
                        left_index=True,
                        right_index=True,
                        how='left'
                    )

            # Clean up NaN's
            df.fillna('', inplace = True)
            # Run a second pass of df.fillna() in order to fill NaT's (not picked up before) with zeros
            # Could also use _pandas.api.types.is_datetime64_any_dtype(df) as a check
            df.fillna('0', inplace = True)

    return df


def _filter_dataframe(
    df: _pandas.DataFrame,
    columns: list = None,
    not_columns: list = None,
    where: str = None,
    where_params: _Union[list, dict] = None, 
    **_
) -> _pandas.DataFrame:
    """
    Filter a DataFrame

    :param df: Input DataFrame
    :param columns: List of columns to include
    :param not_columns: List of columns to exclude
    :param where: SQL where criteria to filter based on
    :param params: List of parameters to pass to execute method. The syntax used to pass parameters is database driver dependent.
    """
    if where:
        df = _recipe_wrangles.sql(
            df,
            f"""
            SELECT *
            FROM df
            WHERE {where};
            """,
            where_params
        )

    # Reduce to user chosen columns
    if columns:
        columns = _wildcard_expansion(df.columns.tolist(), columns)
        df = df[columns]

    # Remove any columns specified by the user
    if not_columns:
        not_columns = _wildcard_expansion(df.columns.tolist(), not_columns)
        # List comprehension is used below to preserve order of columns 
        remaining_columns = [column for column in list(df.columns) if column not in not_columns]
        df = df[remaining_columns]

    return df


def _write_data(df: _pandas.DataFrame, recipe: dict, functions: dict = {}) -> _pandas.DataFrame:
    """
    Export data to the requested targets as defined by the recipe

    :param df: Dataframe to be exported
    :param recipe: write section of a recipe
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
            # Filter the dataframe as requested before passing
            # to the desired write function
            df_temp = _filter_dataframe(df, **params)
            for key in ['columns', 'not_columns', 'where', 'where_params']:
                if key in params:
                    params.pop(key)

            if export_type == 'dataframe':
                # Define the dataframe that is returned
                df_return = df_temp
            
            # Execute a user's custom function
            elif export_type.split('.')[0] == 'custom':
                functions[export_type[7:]](df_temp, **params)

            else:
                # Get write function of requested connector and pass dataframe and user defined params
                obj = _connectors
                for element in export_type.split('.'):
                    obj = getattr(obj, element)
                
                if export_type in ['recipe', 'matrix']:
                    params['functions'] = functions
                
                getattr(obj, 'write')(df_temp, **params)

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
    # Load recipe and functions
    recipe, functions = _read_recipe(recipe, functions, variables)

    try:
        # Format custom functions
        # If user has passed in a single function, convert to a list
        if callable(functions): functions = [functions]
        # Convert custom functions from a list to a dict using the name as a key
        if isinstance(functions, list):
            functions = {custom_function.__name__: custom_function for custom_function in functions}

        # Run any actions required before the main recipe runs
        if 'on_start' in recipe.get('run', {}).keys():
            _run_actions(recipe['run']['on_start'], functions)

        # Get requested data
        if 'read' in recipe.keys():
            # Execute requested data imports
            if isinstance(recipe['read'], list):
                df = _read_data_sources(recipe['read'][0], functions)
            else:
                df = _read_data_sources(recipe['read'], functions)
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
            df = _write_data(df, recipe['write'], functions)

        # Run any actions required after the main recipe finishes
        if 'on_success' in recipe.get('run', {}).keys():
            _run_actions(recipe['run']['on_success'], functions)

        return df

    except Exception as e:
        try:
            # Run any actions requested if the recipe fails
            if 'on_failure' in recipe.get('run', {}).keys():
                _run_actions(recipe['run']['on_failure'], functions, e)
        except:
            pass

        raise