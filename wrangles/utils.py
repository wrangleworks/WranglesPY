import re as _re
import logging as _logging
from jinja2 import Template as _Template

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


def _key_generator():
    """
    Generate a list of incrementing characters
    a, b, c, ... z, aa, ab, ac, ... zz, aaa, ...
    """
    from itertools import product
    from string import ascii_lowercase

    for length in range(1, len(ascii_lowercase) + 1):
        for letters in product(ascii_lowercase, repeat=length):
            yield ''.join(letters)

def _replace_keys_with_chars(input_dict):
    """
    Replace dictionary keys with incrementing characters

    { "key1": "value1", "key2": "value2", ... }

    ->
    
    { "a": "value1", "b": "value2", ... }
    """
    gen = _key_generator()
    return {next(gen): v for v in input_dict.values()}

def evaluate_conditional(statement, variables: dict = {}):
    """
    Use Jinja2 to safely evaluate a conditional statement
    and return the result as a boolean
    :param statement: A conditional statement to evaluate
    :param variables: A dictionary of variables to use in the statement
    :return: Whether the statement evaluates to True or False
    """
    original_statement = statement

    try:
        # Replace variable keys with an incrementing character - a, b, c, ...
        # This is to avoid Jinja2 from throwing an error when it encounters
        # variables names that are not an allowed format. In particular,
        # our variable syntax like ${variable_name}
        formatted_variables = _replace_keys_with_chars(variables)
        for k, v in zip(variables.keys(), formatted_variables.keys()):
            statement = statement.replace(k, v)

        # Create a template with your conditional statement
        result = _Template("{{ " + statement + " }}").render(formatted_variables)

        # Convert the result to a boolean
        result = str(result).strip().lower()
    except:
        raise ValueError(f"An error occurred when trying to evaluate if condition '{original_statement}'") from None

    if result not in ['true', 'false']:
        raise ValueError(f"If conditions must evaluate to true or false. Got: '{original_statement}'")

    return result == 'true'
