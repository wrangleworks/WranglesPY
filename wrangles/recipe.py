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
import importlib as _importlib
import re as _re
import warnings as _warnings
import concurrent.futures as _futures
import pandas as _pandas
import requests as _requests
from . import recipe_wrangles as _recipe_wrangles
from . import connectors as _connectors
from . import data as _data
from .config import (
    reserved_word_replacements as _reserved_word_replacements,
    where_overwrite_output as _where_overwrite_output,
    where_not_implemented as _where_not_implemented
)
from .utils import (
    evaluate_conditional as _evaluate_conditional,
    get_nested_function as _get_nested_function,
    validate_function_args as _validate_function_args,
    add_special_parameters as _add_special_parameters,
    wildcard_expansion as _wildcard_expansion
)
try:
    from yaml import CSafeLoader as _YamlLoader, CSafeDumper as _YAMLDumper
except ImportError:
    from yaml import SafeLoader as _YamlLoader, SafeDumper as _YAMLDumper

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
        # Use a temporary copy of variables to allow for nested variable definitions
        temp_vars = variables.copy()
        if 'variables' in recipe_object and isinstance(recipe_object['variables'], dict):
            for key in recipe_object['variables'].keys():
                if key in temp_vars and key != recipe_object['variables'][key][2:-1]:
                    temp_vars[key] = recipe_object['variables'][key]
        
        # Iterate over all of the keys and value in a dictionary recursively
        new_recipe_object = {
            _replace_templated_values(
                key,
                temp_vars,
                any([ignore_unknown_variables, key in ["matrix"]])
            )
            :
            (
                _replace_templated_values(
                    val,
                    temp_vars,
                    any([ignore_unknown_variables, key in ["matrix"]])
                )
                if key not in ["if", "python"]
                else val
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
            if (
                isinstance(replacement_value, str)
                and len(replacement_value) > 0
                and replacement_value[0] in ['{', '[']
                and replacement_value[-1] in ['}', ']']
            ):
                try:
                    replacement_value = _json.loads(replacement_value)
                except:
                    # Replacement wasn't JSON
                    pass

            # Test if replacement is YAML
            if (
                isinstance(replacement_value, str) 
                and ':' in replacement_value 
                and '\n' in replacement_value
            ):
                try:
                    replacement_value = _yaml.load(replacement_value, Loader=_YamlLoader)
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


def _load_recipe(
    recipe: str,
    variables: dict = {},
    functions: _Union[_types.FunctionType, list, dict, str] = []
) -> dict:
    """
    Load yaml recipe file + replace any placeholder variables

    :param recipe: YAML recipe or name of a YAML file to be parsed
    :param variables: (Optional) dictionary of custom variables to override placeholders in the YAML file
    :param functions: (Optional) function, list of functions or a file of functions.

    :return: YAML Recipe converted to a dictionary
    """
    if isinstance(recipe, str) and "\n" not in recipe:
        _logging.info(f": Reading Recipe :: {recipe}")
    
    # Load the recipe from the various supported formats
    if not isinstance(recipe, str):
        try:
            # If user passes in a pre-parsed recipe, convert back to YAML
            recipe = _yaml.dump(recipe, sort_keys=False, Dumper=_YAMLDumper, allow_unicode=True)
        except:
            raise ValueError('Recipe passed in as an invalid type')

    # Dict to store functions stored within a model
    model_functions = {}

    # If the recipe to read is from "https://" or "http://"
    if 'https://' == recipe[:8] or 'http://' == recipe[:7]:
        response = _requests.get(recipe)
        if str(response.status_code)[0] != '2':
            raise ValueError(f'Error getting recipe from url: {response.url}\nReason: {response.reason}-{response.status_code}')
        recipe_string = response.text

    # If recipe matches xxxxxxxx-xxxx-xxxx, it's probably a model
    elif _re.match(r"^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}$", recipe.split(':')[0].strip()):
        model_id = recipe.split(':')[0].strip()
        version_id = recipe.split(':')[1].strip() if ':' in recipe else None

        metadata = _data.model(model_id)
        # If model_id format is correct but no mode_id exists
        if metadata.get('message', None) == 'error':
            raise ValueError('Incorrect model_id.\nmodel_id may be wrong or does not exists')
        
        # Using model_id in wrong function
        purpose = metadata['purpose']
        if purpose != 'recipe':
            raise ValueError(
                f'Using {purpose} model_id {model_id} in a recipe wrangle.'
            )
        
        model_contents = _data.model_content(model_id, version_id)
        recipe_string = model_contents['recipe']
        model_functions = model_contents.get('functions', {})
        if model_functions:
            spec = _importlib.util.spec_from_loader('custom_functions', loader=None)
            module = _importlib.util.module_from_spec(spec)
            exec(model_functions, module.__dict__)

            model_functions = [
                getattr(module, method)
                for method in dir(module)
                if not method.startswith('_')
            ]
            model_functions = {
                x.__name__: x
                for x in model_functions
                if _inspect.isfunction(x)
            }
        else:
            model_functions = {}

    # If recipe is a single line, it's probably a file path
    elif "\n" in recipe:
        recipe_string = recipe

    # Otherwise it's a recipe
    else:
        # Read the recipe
        try:
            with open(recipe, "r", encoding='utf-8') as f:
                recipe_string = f.read()
        except:
            raise RuntimeError(
                f'Error reading recipe: "{recipe}". ' \
                + 'The recipe should be a YAML file using utf-8 encoding.'
            )

    # Load the custom functions from the supported formats
    # If user has passed in a single function, convert to a list
    if callable(functions): functions = [functions]

    # If the user has specified a file of custom function, import those
    if isinstance(functions, str):
        custom_module = _types.ModuleType('custom_module')
        exec(open(functions, "r").read(), custom_module.__dict__)
        functions = [
            getattr(custom_module, method)
            for method in dir(custom_module)
            if not method.startswith('_')
        ]
        # getting only the functions
        functions = [
            x
            for x in functions
            if _inspect.isfunction(x)
        ]

    # Convert custom functions from a list to a dict using the name as a key
    if isinstance(functions, list):
        functions = {
            custom_function.__name__: custom_function
            for custom_function in functions
        }

    # Merge user input functions and any from remote model
    functions = {**model_functions, **functions}

    # Also add environment variables to list of placeholder variables
    for env_key, env_val in _os.environ.items():
        if env_key not in variables.keys():
            variables[env_key] = env_val

    # Interpret any variables defined by a custom function
    for k, v in variables.items():
        if isinstance(v, str) and v.lower().startswith("custom."):
            func = _get_nested_function(v, None, functions)
            fn_argspec = _inspect.getfullargspec(func)
            args = {}

            # Full variables dict required
            if "variables" in fn_argspec.args:
                args["variables"] = variables

            if fn_argspec.varkw:
                # Pass all variables if function has **kwargs
                args = {**args, **variables}
            else:
                # Add any named args
                for x in fn_argspec.args:
                    if x in variables.keys():
                        args[x] = variables[x]
            
            _validate_function_args(func, args, v)

            variables[k] = func(**args)

    recipe_object = _yaml.safe_load(recipe_string)

    # Check if there are any templated valued to update
    recipe_object = _replace_templated_values(recipe_object, variables)

    return recipe_object, functions


def _run_actions(
    recipe: _Union[dict, list],
    functions: dict = {},
    variables: dict = {},
    error: Exception = None
) -> None:
    """
    Run any actions defined in the recipe

    :param recipe: Run section of the recipe
    :param functions: (Optional) A dictionary of named custom functions passed in by the user
    :param variables: (Optional) A dictionary of variables to pass to the recipe
    :param error: (Optional) If the action is triggered by an exception, this contains the error object
    """
    # Ensure recipe object is a list
    if not isinstance(recipe, list):
        recipe = [recipe]

    for action in recipe:
        if not isinstance(action, dict):
            if isinstance(action, str):
                # Add empty params
                action = {action: {}}
            else:
                raise ValueError('The run section of the recipe is not correctly structured')

        for action_type, params in action.items():
            try:
                # If the action is conditional, check if it should be run
                if (
                    "if" in params and
                    not _evaluate_conditional(params["if"], variables)
                ):
                    continue
                
                common_params = {}
                # Add to common_params dict and remove from params
                for key in ['if']:
                    if key in params.keys():
                        common_params[key] = params.pop(key)

                func = _get_nested_function(action_type, _connectors, functions, 'run')
                if action_type == "matrix":
                    params['variables'] = {**variables, **params['variables']} if 'variables' in params else variables

                args = _add_special_parameters(params, func, functions, variables, error, common_params)

                _validate_function_args(func, args, action_type)

                # Execute the function
                func(**args)
            except Exception as e:
                # Append name of wrangle to message and pass through exception
                raise e.__class__(f"{action_type} - {e}").with_traceback(e.__traceback__) from None


def _read_data(
    recipe: _Union[dict, list],
    functions: dict = {},
    variables: dict = {},
    input_dataframe: _pandas.DataFrame = None
) -> _pandas.DataFrame:
    """
    Import data from requested datasources as defined by the recipe

    :param recipe: Read section of a recipe
    :param functions: (Optional) A dictionary of named custom functions passed in by the user
    :return: Dataframe of imported data
    """
    # Ensure recipe is a list
    if not isinstance(recipe, list):
        recipe = [recipe]
    
    results = []
    for read in recipe:
        if not isinstance(read, dict):
            if isinstance(read, str):
                # Add empty params
                read = {read: {}}
            else:
                raise ValueError('The read section of the recipe is not correctly structured')
            
        for read_type, read_params in read.items():
            try:
                # If the action is conditional, check if it should be run
                if (
                    "if" in read_params and
                    not _evaluate_conditional(read_params["if"], variables)
                ):
                    return None

                # Divide parameters into general and specific to that type of read
                params_general = ['columns', 'not_columns', 'where', 'where_params', 'order_by', 'if']
                params_specific = {
                    key: read_params[key]
                    for key in read_params
                    if key not in params_general
                }
                params_general = {
                    key: read_params[key]
                    for key in params_general
                    if key in read_params
                }

                # Reference the recipe execution input dataframe
                if read_type == "input":
                    df = input_dataframe
                # Allow blended imports
                elif read_type in ['join', 'concatenate', 'union']:
                    dfs = []
                    # Recursively call sub-reads
                    for source in params_specific['sources']:
                        result = _read_data(source, functions, variables, input_dataframe)
                        if result is None:
                            # Skip if None returned
                            # e.g. in the case of a false if condition
                            continue

                        if isinstance(result, list):
                            dfs.extend(result)
                        else:
                            dfs.append(result)

                    params_specific.pop('sources')

                    if read_type == 'join':
                        df = _pandas.merge(dfs[0], dfs[1], **params_specific)
                    elif read_type == 'union':
                        df = _pandas.concat(dfs, **params_specific)
                    elif read_type == 'concatenate':
                        params_specific['axis'] = 1
                        df = _pandas.concat(dfs, **params_specific)
                    df = df.reset_index(drop=True)
                else:
                    # Get the requested function from the connectors module or user defined functions
                    func = _get_nested_function(read_type, _connectors, functions, 'read')

                    args = _add_special_parameters(
                        params_specific,
                        func,
                        functions,
                        variables,
                        common_params=params_general
                    )

                    _validate_function_args(func, args, read_type)

                    # Execute the function
                    df = func(**args)

                if isinstance(df, _pandas.DataFrame):
                    # Response is a single dataframe, filter appropriately
                    results.append(_filter_dataframe(df, **params_general))
                elif isinstance(df, list) and all([isinstance(x, _pandas.DataFrame) for x in df]):
                    # Response is a list of dataframes, filter each appropriately
                    results.extend([_filter_dataframe(x, **params_general) for x in df])
                else:
                    raise RuntimeError(f"Function {read_type} did not return a dataframe")

            except Exception as e:
                # Append name of read to message and pass through exception
                raise e.__class__(f"{read_type} - {e}").with_traceback(e.__traceback__) from None

    if len(results) == 1:
        return results[0]
    else:
        return results

def _execute_wrangles(
    df: _pandas.DataFrame,
    wrangles_list: list,
    functions: dict = {},
    variables: dict = None
) -> _pandas.DataFrame:
    """
    Execute a list of Wrangles on a dataframe

    :param df: Dateframe that the Wrangles will be run against
    :param wrangles_list: List of Wrangles + their definitions to be executed
    :param functions: (Optional) A dictionary of named custom functions passed in by the user
    :param variables: (Optional) A dictionary of variables to pass to the recipe
    :return: Pandas Dataframe of the Wrangled data
    """
    if variables is None:
        variables = {}

    # Ensure wrangles are defined as a list
    if not isinstance(wrangles_list, list):
        wrangles_list = [wrangles_list]

    for step in wrangles_list:
        # Ensure step is a dictionary
        if not isinstance(step, dict):
            if isinstance(step, str):
                # Default to be empty parameters
                step = {step: {}}
            else:
                raise ValueError('The wrangles section of the recipe is not correctly structured')

        for wrangle, params in step.items():
            try:
                if params is None: params = {}
                # Replace any conflicting reserved words with a safe alternative
                wrangle = _reserved_word_replacements.get(wrangle, wrangle)

                original_params = params.copy()

                # Used to store parameters common to all wrangles - e.g where
                common_params = {}

                # Blacklist of Wrangles not to allow wildcards for
                original_input = params.get('input') # Save for later reference
                if (
                    'input' in params and 
                    wrangle not in [
                        'math',
                        'maths',
                        'merge.key_value_pairs',
                        'split.text',
                        'split.list',
                        'select.element'
                    ]
                ):
                    # Expand out any wildcards or regex in column names
                    params['input'] = _wildcard_expansion(
                        all_columns=df.columns.tolist(),
                        selected_columns=params['input']
                    )

                # Filter dataframe if a where clause is present
                if 'where' in params.keys():
                    if wrangle in _where_not_implemented:
                        raise NotImplementedError(f"where parameter is not implemented for {wrangle}")

                    # Save original so we can merge back later
                    df_original = df.copy()
                    
                    # Save original index, filter data, then restore index
                    df = _filter_dataframe(
                        df,
                        where = params.get('where'),
                        where_params= params.get('where_params', None),
                        preserve_index=True
                    )

                # If the action is conditional, check if it should be run
                if (
                    "if" in params and
                    not _evaluate_conditional(
                        params["if"],
                        {
                            **variables,
                            **{
                                "row_count": len(df),
                                "column_count": len(df.columns),
                                "columns": df.columns.tolist(),
                                "df": df
                            }
                        }
                    )
                ):
                    continue

                _logging.info(f": Wrangling :: {wrangle} :: {params.get('input', 'None')} >> {params.get('output', 'Dynamic')}")


                # Add to common_params dict and remove from params
                for key in ['where', 'where_params', 'if']:
                    if key in params.keys():
                        common_params[key] = params.pop(key)

                if wrangle.split('.')[0] == 'pandas':
                    # Execute a pandas method
                    # TODO: disallow any hidden methods
                    # TODO: remove parameters, allow selecting in/out columns
                    try:
                        df[params['output']] = getattr(df[params['input']], wrangle.split('.')[1])(**params.get('parameters', {}))
                    except:
                        df = getattr(df, wrangle.split('.')[1])(**params.get('parameters', {}))

                elif wrangle.split('.')[0] == 'custom':
                    # For backwards compatibility 
                    # if user provided a single input and it is unchanged by the wildcard expansion,
                    # restore it to be a scalar rather than a list
                    if (
                        not isinstance(original_input, list) and
                        isinstance(params.get('input'), list) and
                        len(params.get('input', [])) == 1 and 
                        params['input'][0] == original_input
                    ):

                        params['input'] = original_input

                    # Get the requested function from the user defined functions
                    func = _get_nested_function(wrangle, None, functions)

                    # Get user's function arguments
                    fn_argspec = _inspect.getfullargspec(func)

                    # If function's arguments contain df, pass them the whole dataframe
                    if 'df' in fn_argspec.args:
                        args = _add_special_parameters(
                            params,
                            func,
                            functions,
                            variables,
                            common_params=common_params
                        )
                        # Validate with a placeholder for df
                        _validate_function_args(func, {"df": None, **args}, wrangle)

                        df = func(df=df, **args)

                        if not isinstance(df, _pandas.DataFrame):
                            raise RuntimeError(f"Function {wrangle} did not return a dataframe")

                    # Otherwise, do a row-wise apply
                    else:
                        # Use a temp copy of dataframe as not to affect original
                        df_temp = df

                        if 'output' not in params:
                            raise ValueError(f'Must set 1 or more output columns')

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

                            df_temp = df_temp.rename(columns=colDict)
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

                        # If the custom functions has kwargs or a parameter
                        # matching a column name, execute including those
                        if fn_argspec.varkw or cols_renamed:
                            df[params['output']] = df_temp.apply(
                                lambda x: func(**{**x, **params_temp}),
                                axis=1,
                                result_type=result_type
                            )
                        else:
                            df[params['output']] = df_temp.apply(
                                lambda _: func(**params_temp),
                                axis=1,
                                result_type=result_type
                            )

                else:
                    # Get the requested function from the recipe_wrangles module
                    func = _get_nested_function(wrangle, _recipe_wrangles, None)

                    # Add any special params if requested by the function
                    params = _add_special_parameters(
                        params,
                        func,
                        functions,
                        variables,
                        common_params=common_params
                    )
                    # Validate with a placeholder for df
                    _validate_function_args(func, {"df": None, **params}, wrangle)

                    # Add functions for rename due to special syntax
                    if wrangle == "rename" and "functions" not in params:
                        params["functions"] = functions

                    if wrangle == "python":
                        params['variables'] = variables

                    if wrangle == "matrix":
                        params['variables'] = {**variables, **params['variables']} if 'variables' in params else variables

                    # Execute the function
                    df = func(df=df, **params)

                # If the user specified a where, we need to merge this back to the original dataframe
                # Certain wrangles (e.g. transpose, select.group_by) manipulate the structure of the 
                # dataframe and do not make sense to merge back to the original
                if 'where' in original_params and wrangle not in _where_overwrite_output:

                    # Wrangle explictly defined the output
                    if 'output' in params.keys():
                        # Get the columns that should have been added
                        if isinstance(params['output'], list):
                            # Wrangle output was a list
                            # this may be a list of columns or
                            # a list of dictionaries with renamed outputs
                            output_columns = [
                                list(col.values()) if isinstance(col, dict) else [col]
                                for col in params['output']
                            ]
                            # Spread to a 1D list
                            output_columns = [
                                item
                                for sublist in output_columns
                                for item in sublist
                            ]
                        elif isinstance(params['output'], dict):
                            # Wrangle output was a dictionary,
                            # the keys should be the columns that were added
                            output_columns = list(params['output'].keys())
                        else:
                            # Scalar value
                            output_columns = [params['output']]

                        # Expand the columns if using any wildcards
                        output_columns = _wildcard_expansion(df.columns, output_columns)

                        df = df[output_columns]

                    # Wrangle appears to have overwritten the input column(s)
                    elif list(df.columns) == list(df_original.columns) and 'input' in list(params.keys()):
                        # Ensure input is a list if not already
                        if not isinstance(params['input'], list):
                            params['input'] = [params['input']]

                        df = df[params['input']]

                    # Wrangle added columns
                    elif len([col for col in list(df.columns) if col not in list(df_original.columns)]) > 0:
                        df = df[[
                            col
                            for col in list(df.columns)
                            if col not in list(df_original.columns)
                        ]]

                    else:
                        # Not clear what changed - overwrite everything
                        pass
                    
                    # Merge back to original dataframe
                    df = _pandas.merge(
                        df_original,
                        df,
                        left_index=True,
                        right_index=True,
                        how='left',
                        suffixes=('_x',None)
                    )

                    # Combine any duplicated columns and drop the _x columns
                    for col in df.columns:
                        if str(col).endswith('_x'):
                            df[col[:-2]] = df[col[:-2]].combine_first(df[col])

                    df = df.drop([col for col in df.columns if str(col).endswith('_x')], axis=1)

                    # Ensure the column order follows the original dataframe
                    df = df[
                        [x for x in df_original.columns if x in df.columns]
                        +
                        [x for x in df.columns if x not in df_original.columns]
                    ]

                with _pandas.option_context('future.no_silent_downcasting', True):
                    # Clean up NaN's
                    df = df.fillna('')
                    # Run a second pass of df.fillna() in order to fill NaT's (not picked up before) with zeros
                    # Could also use _pandas.api.types.is_datetime64_any_dtype(df) as a check
                    df = df.fillna('0')

            except Exception as e:
                # Append name of wrangle to message and pass through exception
                raise e.__class__(f"{wrangle} - {e}").with_traceback(e.__traceback__) from None

    return df


def _filter_dataframe(
    df: _pandas.DataFrame,
    columns: list = None,
    not_columns: list = None,
    where: str = None,
    where_params: _Union[list, dict] = None,
    order_by: str = None,
    preserve_index: bool = False,
    **_
) -> _pandas.DataFrame:
    """
    Filter a DataFrame

    :param df: Input DataFrame
    :param columns: List of columns to include
    :param not_columns: List of columns to exclude
    :param where: SQL where criteria to filter based on
    :param where_params: List of parameters to pass to execute method. \
        The syntax used to pass parameters is database driver dependent.
    :param order_by: SQL order by criteria to sort based on
    :param preserve_index: Whether the maintain the index after filtering or reset to the default order
    """
    if where or order_by:
        sql = (
            f"""
            SELECT *
            FROM df
            {("WHERE " + where if where else "")}
            {("ORDER BY " + order_by if order_by else "")}
            ;
            """
        )
        # Use SQL to get the indexes of filtered rows and
        # only pass those through the dataframe
        df = df.loc[
            _recipe_wrangles.sql(
                df,
                sql,
                where_params,
                preserve_index=True,
                preserve_data_types=False
            ).index.to_list()
        ]
        if not preserve_index:
            df = df.reset_index(drop=True)

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


def _write_data(
    df: _pandas.DataFrame,
    recipe: dict,
    functions: dict = {},
    variables: dict = {}
) -> _pandas.DataFrame:
    """
    Export data to the requested targets as defined by the recipe

    :param df: Dataframe to be exported
    :param recipe: write section of a recipe
    :param functions: (Optional) A dictionary of named custom functions passed in by the user
    :param variables: (Optional) A dictionary of variables passed to the recipe
    :return: Dataframe, a subset if the 'dataframe' write type is set with specific columns
    """
    # Initialize returned df as df to start
    df_return = df

    # Ensure writes are defined as a list
    if not isinstance(recipe, list):
        recipe = [recipe]

    # Loop through all exports, get type and execute appropriate export
    for export in recipe:
        if not isinstance(export, dict):
            if isinstance(export, str):
                # Add empty params
                export = {export: {}}
            else:
                raise ValueError('The write section of the recipe is not correctly structured')

        for export_type, params in export.items():
            try:
                # Filter the dataframe as requested before passing
                # to the desired write function
                df_temp = _filter_dataframe(df, **params)

                # If the action is conditional, check if it should be run
                if (
                    "if" in params and
                    not _evaluate_conditional(
                        params["if"],
                        {
                            **variables,
                            **{
                                "row_count": len(df_temp),
                                "column_count": len(df_temp.columns),
                                "columns": df_temp.columns.tolist(),
                                "df": df_temp
                            }
                        }
                    )
                ):
                    continue

                # Separate any parameters that are commmon to all write functions
                common_params = {}
                for key in ['columns', 'not_columns', 'where', 'where_params', 'order_by', 'if']:
                    if key in params:
                        common_params[key] = params.pop(key)

                if export_type == 'dataframe':
                    # Define the dataframe that is returned
                    df_return = df_temp
                else:
                    # Get the appropriate function to use
                    func = _get_nested_function(export_type, _connectors, functions, 'write')
                    if export_type == "matrix":
                        params['variables'] = {**variables, **params['variables']} if 'variables' in params else variables

                    args = _add_special_parameters(
                        params,
                        func,
                        functions,
                        variables,
                        common_params=common_params
                    )

                    # Validate with a placeholder for df
                    _validate_function_args(func, {"df": None, **args}, export_type)

                    # Execute the function
                    func(df_temp, **args)
            except Exception as e:
                # Append name of wrangle to message and pass through exception
                raise e.__class__(f"{export_type} - {e}").with_traceback(e.__traceback__) from None

    return df_return


def _run_thread(
    recipe: str,
    variables: dict = None,
    dataframe: _pandas.DataFrame = None,
    functions: _Union[_types.FunctionType, list, dict, str] = None
) -> _pandas.DataFrame:
    """
    Execute a Wrangles Recipe. Recipes are written in YAML and allow 
    a set of steps to be run in an automated sequence.
    Read, wrangle, then write your data.

    >>> wrangles.recipe.run('recipe.wrgl.yml')
    
    :param recipe: YAML recipe or path to a YAML file containing the recipe
    :param variables: (Optional) A dictionary of custom variables to \
        override placeholders in the recipe. Variables can be indicated \
        as ${MY_VARIABLE}. Variables can also be overwritten by Environment Variables.
    :param dataframe: (Optional) Pass in a pandas dataframe, instead of defining \
        a read section within the YAML
    :param functions: (Optional) A function, list of functions or file path \
        that can be called as part of the recipe. Functions can be referenced \
        as custom.function_name

    :return: The result dataframe. The dataframe can be defined using \
        write: - dataframe in the recipe.
    """
    if variables is None:
        variables = {}
    
    # Parse recipe and custom functions from the various
    # supported sources such as files, url, model id
    # Run any actions required before the main recipe runs
    if 'on_start' in recipe.get('run', {}).keys():
        _run_actions(recipe['run']['on_start'], functions, variables)

    # Get requested data
    if 'read' in recipe.keys():
        # Execute requested data imports
        df = _read_data(recipe['read'], functions, variables, dataframe)

        # If no data is returned, initialize an empty dataframe
        if df is None:
            df = _pandas.DataFrame()

        # If multiple dataframes are returned, union them
        if isinstance(df, list) and all([isinstance(x, _pandas.DataFrame) for x in df]):
            df = _pandas.concat(df, ignore_index=True)

        if not isinstance(df, _pandas.DataFrame):
            raise RuntimeError("Read did not return a valid dataframe")

    elif dataframe is not None:
        # User has passed in a pre-created dataframe
        df = dataframe
    else:
        # User hasn't provided anything - initialize empty dataframe
        df = _pandas.DataFrame()

    # Execute any Wrangles required (allow single or plural)
    if 'wrangles' in recipe.keys():
        df = _execute_wrangles(df, recipe['wrangles'], functions, variables)
    elif 'wrangle' in recipe.keys():
        df = _execute_wrangles(df, recipe['wrangle'], functions, variables)

    # Execute requested data exports
    if 'write' in recipe.keys():
        df = _write_data(df, recipe['write'], functions, variables)

    # Run any actions required after the main recipe finishes
    if 'on_success' in recipe.get('run', {}).keys():
        _run_actions(recipe['run']['on_success'], functions, variables)

    return df


def run(
    recipe: str,
    variables: dict = None,
    dataframe: _pandas.DataFrame = None,
    functions: _Union[_types.FunctionType, list, dict] = [],
    timeout: float = None
) -> _pandas.DataFrame:
    """
    Execute a Wrangles Recipe. Recipes are written in YAML and allow 
    a set of steps to be run in an automated sequence.
    Read, wrangle, then write your data.

    >>> wrangles.recipe.run('recipe.wrgl.yml')
    
    :param recipe: YAML recipe or path to a YAML file containing the recipe
    :param variables: (Optional) A dictionary of custom variables to override placeholders in the recipe. Variables can be indicated as ${MY_VARIABLE}. Variables can also be overwritten by Environment Variables.
    :param dataframe: (Optional) Pass in a pandas dataframe, instead of defining a read section within the YAML
    :param functions: (Optional) A function or list of functions that can be called as part of the recipe. Functions can be referenced as custom.function_name
    :param timeout: (Optional) Set a timeout for the recipe in seconds. If not provided, the time is unlimited.

    :return: The result dataframe. The dataframe can be defined using \
        write: - dataframe in the recipe.
    """
    if variables is None:
        variables = {}

    # Parse recipe
    recipe, functions = _load_recipe(
        recipe,
        variables,
        functions or {}
    )

    with _futures.ThreadPoolExecutor(max_workers=1) as executor:
        try:
            future = executor.submit(
                _run_thread,
                recipe,
                variables,
                dataframe,
                functions
            )
            return future.result(timeout)
        
        except _futures.TimeoutError as e:
            try:
                executor._threads.clear()
                # Run any actions requested if the recipe fails
                if 'on_failure' in recipe.get('run', {}).keys():
                    _run_actions(recipe['run']['on_failure'], functions, variables, e)
            except:
                pass
            raise TimeoutError(f"Recipe timed out. Limit: {timeout}s")

        except Exception as e:
            try:
                # Run any actions requested if the recipe fails
                if 'on_failure' in recipe.get('run', {}).keys():
                    _run_actions(recipe['run']['on_failure'], functions, variables, e)
            except:
                pass
            raise
