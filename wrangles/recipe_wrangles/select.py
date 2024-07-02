"""
Functions to select data from within columns
"""
from typing import Union as _Union
import re as _re
import json as _json
import pandas as _pd
from .. import select as _select


def columns(df: _pd.DataFrame, input: _Union[str, list]) -> _pd.DataFrame:
    """
    type: object
    description: Select columns from the dataframe
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - string
          - array
        description: Name of the column(s) to select
    """
    if not isinstance(input, list): input = [input]
    
    # Missing column should be caught by _wildcard_expansion
    
    return df[input]    


def dictionary_element(
    df: _pd.DataFrame,
    input: _Union[str, list],
    element: str,
    output: _Union[str, list] = None,
    default: any = ''
) -> _pd.DataFrame:
    """
    type: object
    description: Select one or more element of a dictionary.
    additionalProperties: false
    required:
      - input
      - element
    properties:
      input:
        type: 
          - string
          - array
        description: Name of the input column
      output:
        type:
          - string
          - array
        description: >-
          Name of the output column.
          If omitted, the input column will be replaced.
      element:
        type:
          - string
          - array
        description: |- 
          The key or keys from the dictionary to select.
          If a single key is provided, the value will be returned
          If a lists of keys are selected,
          the result will be a new dictionary.
      default:
        type: 
          - string
          - number
          - array
          - object
          - boolean
          - 'null'
        description: |-
          Set the default value to return if the specified element doesn't exist.
          If selecting multiple elements, a dict of defaults can be set.
    """
    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The list of inputs and outputs must be the same length for select.dictionary_element')

    for in_col, out_col in zip(input, output):
        df[out_col] = _select.dict_element(df[in_col].tolist(), element, default=default)
    
    return df


def element(
    df: _pd.DataFrame,
    input: _Union[str, list],
    output: _Union[str, list] = None,
    default: any = None
) -> _pd.DataFrame:
    """
    type: object
    description: >-
      Select elements of lists or dicts
      using python syntax like col[0]['key']
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type: 
          - string
          - array
        description: >-
          Name of the input column and sub elements
          This permits by index for lists or dict
          and by key for dicts
          e.g. col[0]['key'] // [{"key":"val"}] -> "val"
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
      default:
        type: 
          - string
          - number
          - array
          - object
          - boolean
        description: Set the default value to return if the specified element doesn't exist.
        default: ""
    """
    def _extract_elements(input_string):
        # Find all occurrences of '[...]' using regex
        pattern = r'\[[^\]]*\]'
        matches = _re.findall(pattern, input_string)

        extracted_elements = []
        for match in matches:
            # Remove brackets and trim whitespace
            element = match.strip('[]')

            # Remove outer quotes if present
            if element.startswith("'") and element.endswith("'"):
                element = element[1:-1]
            elif element.startswith('"') and element.endswith('"'):
                element = element[1:-1]

            # Handle escaped quotes within the element
            element = element.replace("\\'", "'").replace('\\"', '"')

            extracted_elements.append(element)

        return extracted_elements

    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The list of inputs and outputs must be the same length for select.element')
    
    def _int_or_none(val):
        try:
            return int(val)
        except:
            if val:
                raise ValueError(f"{val} is not a valid index to slice on")
            else:
                return None
    
    for in_col, out_col in zip(input, output):
        # If user hasn't specified an output column
        # strip the elements from the input column
        if in_col == out_col:
            out_col = out_col.split("[")[0]
        
        # Get the sequence of elements
        elements = _extract_elements(in_col)
        in_col = in_col.split('[')[0]
        
        output = []
        for row in df[in_col].tolist():
            if isinstance(row, str) and (row.startswith("{") or row.startswith("[")):
                try:
                    row = _json.loads(row)
                except:
                    pass

            for element in elements:
                try:
                    if isinstance(row, (list, str)):
                        if ":" in element:
                            row = row[slice(*map(_int_or_none, element.split(":")))]
                        else:
                            row = row[int(element)]
                    elif isinstance(row, dict):
                        if element in row.keys():
                            row = row[element]
                        else:
                            if element.isdigit() and int(element) < len(row):
                                # Allow getting an element of a dict
                                # using the index of the key
                                row = row[list(row.keys())[int(element)]]
                            else:
                                if default is not None:
                                    row = default
                                    break
                                else:
                                    raise KeyError()
                    else:
                        if default is not None:
                            row = default
                            break
                        else:
                            raise KeyError()
                except:
                    if default is not None:
                        row = default
                        break
                    else:
                        raise KeyError(f"Element {element} not found in {row}") from None

            output.append(row)

        df[out_col] = output
    
    return df


def group_by(df, by = [], **kwargs):
    """
    type: object
    description: Group and aggregate the data
    properties:
      by:
        type:
          - string
          - array
        description: List of the input columns to group on
      list:
        type:
          - string
          - array
        description: Group and return all values for these column(s) as a list
      first:
        type:
          - string
          - array
        description: The first value for these column(s)
      last:
        type:
          - string
          - array
        description: The last value for these column(s)
      min:
        type:
          - string
          - array
        description: The minimum value for these column(s)
      max:
        type:
          - string
          - array
        description: The maximum value for these column(s)
      mean:
        type:
          - string
          - array
        description: The mean (average) value for these column(s)
      median:
        type:
          - string
          - array
        description: The median value for these column(s)
      nunique:
        type:
          - string
          - array
        description: The count of unique values for these column(s)
      count:
        type:
          - string
          - array
        description: The count of values for these column(s)
      std:
        type:
          - string
          - array
        description: The standard deviation of values for these column(s)
      sum:
        type:
          - string
          - array
        description: The total of values for these column(s)
      any:
        type:
          - string
          - array
        description: Return true if any of the values for these column(s) are true
      all:
        type:
          - string
          - array
        description: Return true if all of the values for these column(s) are true
      p75:
        type:
          - string
          - array
        description: >-
          Get a percentile. Note, you can use any integer here
          for the corresponding percentile.
    """
    def percentile(n):
        def percentile_(x):
            return x.quantile(n)
        percentile_.__name__ = f'p{int(n*100)}'
        return percentile_

    # If by not specified, fake a column to allow it to be used
    if not by:
        df['absjdkbatgg'] = 1
        by = ['absjdkbatgg']

    # Ensure by is a list
    if not isinstance(by, list): by = [by]

    # Invert kwargs to put column names as keys
    inverted_dict = {}
    for operation, columns in kwargs.items():
        # Interpret percentiles
        if operation[0].lower() == "p" and operation[1:].isnumeric():
            operation = percentile(int(operation[1:])/100)

        # Add option to group as a list
        if operation == "list":
            operation = list

        if not isinstance(columns, list): columns = [columns]
        for column in columns:
            if column in inverted_dict:
                inverted_dict[column].append(operation)
            else:
                inverted_dict[column] = [operation]

    # If any of the columns to group by are also specified
    # as an aggregate column this causes problems.
    # Temporarily rename the column to avoid this.
    if set(by).intersection(set(inverted_dict.keys())):
        for i, val in enumerate(by):
            if val in inverted_dict.keys():
                df[val + ".grouped_asjkdbak"] = df[val]
                by[i] = val + ".grouped_asjkdbak"

    # Create group by object with by and aggregate columns
    df_grouped = df[by + list(inverted_dict.keys())].groupby(
        by = by,
        as_index=False,
        sort=False
    )

    # If agg columns then aggregate else return grouped
    if kwargs:
        df = df_grouped.agg(inverted_dict)
    else:
        df = df_grouped.count()

    # Remove faked column if it was needed
    if 'absjdkbatgg' in df.columns:
        df = df.drop('absjdkbatgg', axis=1, level=0)

    # Flatting multilevel headings back to one
    df.columns = df.columns.map('.'.join).str.strip('.')

    # Rename columns back to original names if altered
    df = df.rename(
        {
            col: col.replace(".grouped_asjkdbak", "")
            for col in df.columns
            if col.endswith(".grouped_asjkdbak")
        },
        axis=1
    )

    return df


def head(df: _pd.DataFrame, n: int) -> _pd.DataFrame:
    """
    type: object
    description: Return the first n rows
    required:
      - n
    properties:
      n:
        type: integer
        description: Number of rows to return
    """
    if not isinstance(n, int) or n <= 0:
        raise ValueError("n must be a positive integer")
    return df.head(n)


def highest_confidence(df: _pd.DataFrame, input: list, output: _Union[str, list]) -> _pd.DataFrame:
    """
    type: object
    description: Select the option with the highest confidence from multiple columns. Inputs are expected to be of the form [<<value>>, <<confidence_score>>].
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: array
        description: List of the input columns to select from
      output:
        type:
          - array
          - string
        description: If two columns; the result and confidence. If one column; [result, confidence]
    """
    df[output] = _select.highest_confidence(df[input].values.tolist())
    return df


def left(
    df: _pd.DataFrame,
    input: _Union[str, list],
    length: int,
    output: _Union[str, list] = None
) -> _pd.DataFrame:
    """
    type: object
    description: >-
      Return characters from the left of text.
      Strings shorter than the length defined will be unaffected.
    additionalProperties: false
    required:
      - input
      - length
    properties:
      input:
        type:
          - string
          - array
        description: Name of the column(s) to edit
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
      length:
        type: integer
        description: >-
          Number of characters to include from the left.
          If negative, this will remove the specified
          number of characters from the left.
          May not equal 0.
    """
    # If user hasn't provided an output, replace input
    if output is None: output = input

    # If a string provided, convert to list
    if isinstance(input, str): input = [input]
    if isinstance(output, str): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # If length is a string like '1', convert to integer
    if isinstance(length, str) and length.isdigit():
        length = int(length)

    # Ensure length is an integer
    if not isinstance(length, int):
        raise TypeError('Length must be an integer')

    # Ensure length is not 0
    if length == 0:
        raise ValueError('Length may not equal 0')

    if length > 0:
        # Loop through and get characters from the left
        for input_column, output_column in zip(input, output):
            df[output_column] = df[input_column].str[:length]
    else:
        # Loop through and remove characters from the left
        for input_column, output_column in zip(input, output):
            df[output_column] = df[input_column].str[-1*length:]

    return df


def list_element(
    df: _pd.DataFrame,
    input: _Union[str, list],
    output: _Union[str, list] = None,
    element: int = 0,
    default: any = ''
) -> _pd.DataFrame:
    """
    type: object
    description: Select a numbered element of a list (zero indexed).
    additionalProperties: false
    required:
      - input
      - element
    properties:
      input:
        type: 
          - string
          - array
        description: Name of the input column
      output:
        type: 
          - string
          - array
        description: Name of the output column
      element:
        type: integer
        description: |-
          The numbered element of the list to select.
          Starts from zero.
          This may use python slicing syntax to select a subset of the list.
      default:
        type:
          - string
          - number
          - array
          - object
          - boolean
          - 'null'
        description: Set the default value to return if the specified element doesn't exist.
    """
    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The list of inputs and outputs must be the same length for select.list_element')
    
    for in_col, out_col in zip(input, output):
        df[out_col] = _select.list_element(df[in_col].tolist(), element, default=default)
    
    return df


def right(
    df: _pd.DataFrame,
    input: _Union[str, list],
    length: int,
    output: _Union[str, list] = None
) -> _pd.DataFrame:
    """
    type: object
    description: >-
      Return characters from the right of text.
      Strings shorter than the length defined will be unaffected.
    additionalProperties: false
    required:
      - input
      - length
    properties:
      input:
        type:
          - string
          - array
        description: Name of the column(s) to edit
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
      length:
        type: integer
        description: >-
          Number of characters to include from the right.
          If negative, this will remove the specified
          number of characters from the right.
          May not equal 0.
    """
    # If user hasn't provided an output, replace input
    if output is None: output = input

    # If a string provided, convert to list
    if isinstance(input, str): input = [input]
    if isinstance(output, str): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # If length is a string like '1', convert to integer
    if isinstance(length, str) and length.isdigit():
        length = int(length)

    # Ensure length is an integer
    if not isinstance(length, int):
        raise TypeError('Length must be an integer')

    # Ensure length is not 0
    if length == 0:
        raise ValueError('Length may not equal 0')
    
    if length > 0:
        # Loop through and get characters from the right
        for input_column, output_column in zip(input, output):
            df[output_column] = df[input_column].str[-length:]
    else:
        # Loop through and remove characters from the right
        for input_column, output_column in zip(input, output):
            df[output_column] = df[input_column].str[:length]

    return df


def sample(df: _pd.DataFrame, rows: _Union[int, float], **kwargs) -> _pd.DataFrame:
    """
    type: object
    description: Return a random sample of the rows
    required:
      - rows
    properties:
      rows:
        type:
          - integer
          - number
        description: |-
          If a whole number, will select that number of rows.
          If a decimal between 0 and 1 will select that fraction 
          of the rows e.g. 0.1 => 10% of rows will be returned
        exclusiveMinimum: 0
    """
    if not isinstance(rows, (int, float)):
        try:
          rows = float(rows)
        except:
          raise ValueError(
              "rows must be a positive integer or a decimal between 0 and 1"
          )

    if rows <= 0:
        raise ValueError(
            "rows must be a positive integer or a decimal between 0 and 1"
        )
    elif rows >= 1:
        if rows > len(df):
            return df.sample(n=len(df), ignore_index=True, **kwargs)
        else:
            return df.sample(n=int(rows), ignore_index=True, **kwargs)
    else:
        return df.sample(frac=rows, ignore_index=True, **kwargs)


def substring(df: _pd.DataFrame, input: _Union[str, list], start: int = None, length: int = None, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Return characters from the middle of text.
    additionalProperties: false
    required:
      - input
      - start
      - length
    properties:
      input:
        type:
          - string
          - array
        description: Name of the column(s) to edit
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
      start:
        type: integer
        description: |
          The position of the first character to select.
          If ommited will start from the beginning and length must 
          be provided.
        minimum: 1
      length:
        type: integer
        description: |
          The length of the string to select. If ommited
          will select to the end of the string and start must be provided.
        minimum: 1
    """
    # If user hasn't provided an output, replace input
    if output is None: output = input

    # If a string provided, convert to list
    if isinstance(input, str): input = [input]
    if isinstance(output, str): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # Ensure start or length have been provided
    if start is None and length is None:
        raise ValueError('Either start or length must be provided.')
    
    # Set start and end parameters
    if start is None:
        start = 1
        start_param = None
    else:
        start_param = start - 1
    
    if length is None:
        end_param = None
    else:
        end_param = start + length - 1

    # Loop through and get the substring requested for all requested columns
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].str[start_param:end_param]

    return df


def tail(df: _pd.DataFrame, n: int) -> _pd.DataFrame:
    """
    type: object
    description: Return the last n rows
    required:
      - n
    properties:
      n:
        type: integer
        description: Number of rows to return
    """
    if not isinstance(n, int) or n <= 0:
        raise ValueError("n must be a positive integer")
    return df.tail(n)


def threshold(df: _pd.DataFrame, input: list, output: str, threshold: float) -> _pd.DataFrame:
    """
    type: object
    description: Select the first option if it exceeds a given threshold, else the second option.
    additionalProperties: false
    required:
      - input
      - output
      - threshold
    properties:
      input:
        type: array
        description: List of the input columns to select from
      output:
        type: string
        description: Name of the output column
      threshold:
        type: number
        description: Threshold above which to choose the first option, otherwise the second
        minimum: 0
        maximum: 1
    """
    df[output] = _select.confidence_threshold(df[input[0]].tolist(), df[input[1]].tolist(), threshold)
    return df
