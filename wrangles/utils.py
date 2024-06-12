import re as _re
import logging as _logging

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
