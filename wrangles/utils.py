import re as _re
import logging as _logging
import types as _types
import inspect as _inspect
from typing import Union as _Union
import yaml as _yaml


def wildcard_expansion_dict(all_columns: list, selected_columns: dict) -> list:
    """
    Finds matching columns for wildcards or regex from all available columns

    This expects the input to be in the format:
    {"in_col": "out_col", "unchanged": "unchanged"}
    
    :param all_columns: List of all available columns in the dataframe
    :param selected_columns: List or string with selected columns. May contain wildcards (*) or regex.
    """
    # Convert wildcards (*) to regex patterns
    tmp_columns = {}
    for k, v in selected_columns.items():
        # If column contains * without escape
        if _re.search(r'[^\\]?\*', str(k)) and not str(k).lower().startswith('regex:'):
            # Convert wildcard to a regex pattern for key
            k = 'regex:' + _re.sub(r'(?<!\\)\*', r'(.*)', k)
            # Convert wildcard to a regex pattern for value
            group_counter = [0]
            def replacer(_):
                """
                Increment group number using a mutable object
                each time this function is called to give
                a unique capture group number for each wildcard
                """
                # Use the current counter value, then increment it
                group_counter[0] += 1                
                return fr'\g<{group_counter[0]}>'
            v = _re.sub(r'(?<!\\)\*', replacer, v)
            tmp_columns[k] = v
        else:
            tmp_columns[k] = v

    selected_columns = tmp_columns

    # Create output dictionary
    result_columns = {}

    # Identify any matching columns using regex within the list
    for column in selected_columns:
        if column.lower().startswith('regex:'):
            # result_columns.update() # Read Note below
            matching_columns = dict.fromkeys(list(
                filter(_re.compile(column[6:].strip()).fullmatch, all_columns)
            ))
            try:
                if column == selected_columns[column]:
                    # If the column is not renamed, maintain the original matching column names
                    renamed_columns = [_re.sub("(" + column[6:].strip() + ")", r"\1", col, count=1) for col in matching_columns]
                else:
                    # Else rename the columns using the provided regex pattern
                    renamed_columns = [_re.sub(column[6:].strip(), selected_columns[column], col, count=1) for col in matching_columns]
            except _re.error as e:
                raise ValueError(f"Invalid regex pattern: {selected_columns[column]}. Are you missing a capture group?") from None
            
            if len(renamed_columns) != len(set(renamed_columns)):
                _logging.warning(
                    "Renamed columns contain duplicate values. Consider including a wildcard or regex capture group."
                )

            result_columns = {
                **{
                    k: v
                    for k, v in zip(matching_columns, renamed_columns)
                },
                **result_columns
            }
        else:
            # Check if a column is indicated as
            # optional with column_name?
            optional_column = False
            if column[-1] == "?" and column not in all_columns:
                column = column[:-1]
                optional_column = True

            if column in all_columns:
                result_columns[column] = selected_columns[column]
            else:
                if not optional_column:
                    raise KeyError(f'Column {column} does not exist')

    return result_columns


def get_nested_function(
    fn_string: str,
    stock_functions: _types.ModuleType = None,
    custom_functions: dict = None,
    default_stock_functions: str = None
):
    """
    Get a nested function from obj as defined by a string
    e.g. 'custom.my_function' or 'my_function' or 'my_module.my_function'

    :param fn_string: String defining the function to get
    :param stock_functions: Module containing stock functions
    :param custom_functions: Dictionary of user defined custom functions
    :param default_stock_functions: Some stock functions use a default final function to call
    """
    if custom_functions is None and stock_functions is None:
        raise ValueError('No functions provided')

    fn_list = fn_string.strip().split('.')
    if fn_list[0] == 'custom':
        if len(fn_list) == 1:
            raise ValueError('Custom function not defined correctly')
        fn_list = fn_list[1:]
        obj = custom_functions
    else:
        if default_stock_functions:
            fn_list.append(default_stock_functions)
        obj = stock_functions
        
    for fn_name in fn_list:
        if isinstance(obj, dict):
            if fn_name not in obj:
                raise ValueError(f'Function {fn_string} not recognized')
            obj = obj[fn_name]
        else:
            if not hasattr(obj, fn_name):
                raise ValueError(f'Function {fn_string} not recognized')
            obj = getattr(obj, fn_name)
    
    return obj


def add_special_parameters(
    params: dict,
    fn: _types.FunctionType,
    functions: dict = {},
    variables: dict = {},
    error: Exception = None,
    common_params: dict = {}
):
    """
    Add special parameters to the params dictionary if they are required by the function

    :param params: Dictionary of parameters to pass to the function
    :param fn: Function to check for special parameters
    :param functions: Dictionary of custom functions
    :param variables: Dictionary of variables
    :param error: Exception object
    :param common_params: These are parameters that are common to all functions. \
        They will only be passed as a parameter if the function requests them.
    """
    # Check args and pass on special parameters if requested
    argspec = _inspect.getfullargspec(fn).args
    if ("functions" not in params and "functions" in argspec):
        params['functions'] = functions
    if ("variables" not in params and "variables" in argspec):
        params['variables'] = variables

    if error and "error" not in params and "error" in argspec:
        params['error'] = error

    # Allow functions to access common
    # parameters only if they need them
    if common_params:
        params = {
            **params,
            **{
                k: v
                for k, v in common_params.items()
                if k in argspec
            }
        }

    return params


def wildcard_expansion(all_columns: list, selected_columns: _Union[str, list]) -> list:
    """
    Finds matching columns for wildcards or regex from all available columns
    
    :param all_columns: List of all available columns in the dataframe
    :param selected_columns: List or string with selected columns. May contain wildcards (*) or regex.
    """
    def escape_except(text, chars_not_to_escape):
        """
        Escape regex characters except for those specified
        """
        # Define all regex special characters
        special_chars = set(r'[]{}()^$.|*+?\\')
        # Determine the characters to escape
        chars_to_escape = special_chars - set(chars_not_to_escape)
        # Create a regex pattern to match any of the characters to escape
        pattern = _re.compile(f"[{_re.escape(''.join(chars_to_escape))}]")
        # Use re.sub to replace each match with the escaped version
        escaped_text = pattern.sub(lambda match: f"\\{match.group(0)}", text)
        return escaped_text

    if not isinstance(selected_columns, list): selected_columns = [selected_columns]

    # Convert wildcards to regex pattern
    for i in range(len(selected_columns)):
        # Catch not syntax errors
        if isinstance(selected_columns[i], list):
            newline = '\n'
            raise ValueError(
                "Column name is not formatted correctly. " + 
                f"Got: {_yaml.dump(selected_columns[i]).strip(newline)}. " +
                "Did you mean to use '-column_name' without a space? "
            )

        # If column contains * without escape
        if (
            _re.search(r'[^\\]?\*', str(selected_columns[i])) and
            not 'regex:' in str(selected_columns[i]).lower()
        ):
            # Replace with a regex pattern and escape
            # other regex special characters
            selected_columns[i] = 'regex:' + _re.sub(
                r'(?<!\\)\*', r'(.*)',
                escape_except(selected_columns[i], ['*', '\\'])
            )

    # Using a dict to preserve insert order.
    # Order is preserved for Dictionaries from Python 3.7+
    if (
        all([str(column).startswith('-') for column in selected_columns]) and
        not any([col in all_columns for col in selected_columns])
    ):
        # If all selected columns are not columns then
        # initialize with all columns
        result_columns = dict.fromkeys(all_columns)
    else:
        # Otherwise initialize with no columns
        result_columns = {}

    # Identify any matching columns using regex within the list
    for column in selected_columns:
        # Rearrange -regex: to regex:- to allow either to work
        if str(column).lower().startswith('-regex:'):
            column = "regex:-" + column[7:]

        if column.lower().startswith('regex:'):
            pattern = column[6:].strip() 
            if pattern.startswith("-"):
                # Remove columns that match the negative regex pattern
                result_columns = {
                    k: None
                    for k in result_columns
                    if not _re.compile(pattern[1:]).fullmatch(k)
                }
            else:
                # Add columns that match the regex pattern
                result_columns.update(dict.fromkeys(list(
                    filter(_re.compile(pattern).fullmatch, all_columns)
                ))) # Read Note below
        else:
            if column not in all_columns and str(column).startswith('-'):
                # Columns prefixed with - indicate not to include them
                result_columns.pop(column[1:], None)
                continue

            # Check if a column is indicated as
            # optional with column_name?
            optional_column = False
            if column[-1] == "?" and column not in all_columns:
                column = column[:-1]
                optional_column = True

            if column in all_columns:
                result_columns[column] = None
            else:
                if not optional_column:
                    raise KeyError(f'Column {column} does not exist')
    
    # Return, preserving original order
    return list(result_columns.keys())


def evaluate_conditional(statement, variables: dict = {}):
    """
    Evaluate a conditional statement using the variables provided
    to determine if the statement is true or false

    Recipe variables of the style ${var} will be parameterized

    :param statement: Python style statement
    :param variables: Dictionary of variables to use in the statement
    """
    try:
        statement_modified = _re.sub(r'\$\{([A-Za-z0-9_]+)\}', r'\1', statement)

        if _re.match(r'\$\{(.+)\}', statement_modified):
            raise ValueError(f"Variables used in if statements may only contain chars A-z, 0-9, and _ (underscore). Got: '{statement}'")

        # Create a template with your conditional statement
        result = eval(statement_modified, variables, {})

        # Convert the result to a boolean
        result = str(result).strip().lower()
    except:
        raise ValueError(f"An error occurred when trying to evaluate if condition '{statement}'") from None

    if result not in ['true', 'false']:
        raise ValueError(f"If conditions must evaluate to true or false. Got: '{statement}'")

    return result == 'true'
