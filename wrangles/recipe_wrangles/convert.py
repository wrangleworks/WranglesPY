"""
Functions to convert data formats and representations
"""
import json as _json
from typing import Union as _Union
import re as _re
import numpy as _np
import pandas as _pd
from fractions import Fraction as _Fraction
import yaml as _yaml
import logging as _logging
import wrangles as _wrangles
try:
    from yaml import CSafeLoader as _YAMLLoader, CSafeDumper as _YAMLDumper
except ImportError:
    from yaml import SafeLoader as _YAMLLoader, SafeDumper as _YAMLDumper


def case(df: _pd.DataFrame, input: _Union[str, int, list], output: _Union[str, list] = None, case: str = 'lower') -> _pd.DataFrame:
    """
    type: object
    description: Change the case of the input.
    additionalProperties: false
    required:
      - input
      - case
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name or list of input columns
      output:
        type:
          - string
          - array
        description: Name or list of output columns
      case:
        type: string
        description: The case to convert to. lower, upper, title or sentence
        enum:
          - lower
          - upper
          - title
          - sentence
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # Get the requested case, default lower
    desired_case = case.lower()

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # Return early for empty dataframe
    if df.empty: 
        df[output] = None
        return df

    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        if desired_case == 'lower':
            df[output_column] = df[input_column].str.lower()
        elif desired_case == 'upper':
            df[output_column] = df[input_column].str.upper()
        elif desired_case == 'title':
            df[output_column] = df[input_column].str.title()
        elif desired_case == 'sentence':
            def getSentenceCase(source: str):
                output = ""
                isFirstWord = True

                if not isinstance(source, str):
                    return source

                for character in source:
                    if isFirstWord and not character.isspace():
                        character = character.upper()
                        isFirstWord = False
                    elif not isFirstWord and character in ".!?":
                        isFirstWord = True
                    else:
                        character = character.lower()

                    output = output + character

                return output

            df[output_column] = df[input_column].apply(getSentenceCase)

    return df


def data_type(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, list] = None,
    data_type: str = 'str',
    default: any = None,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Change the data type of the input.
    additionalProperties: false
    required:
      - input
      - data_type
    properties:
      input:
        type: 
          - string
          - integer
          - array
        description: Name or list of input columns
      output:
        type:
          - string
          - array
        description: Name or list of output columns
      data_type:
        type: string
        description: The new data type
        enum:
          - str
          - float
          - int
          - bool
          - datetime
      default:
        type: 
          - string
          - number
          - array
          - boolean
          - datetime
        description: |-
          Set the default value to return if the input data 
          cannot be converted to the specified data_type.
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    # If the datatype is datetime
    if data_type == 'datetime':
        for input_column, output_column in zip(input, output):
            recursion_stop = kwargs.pop('stop', False)
            temp = _pd.to_datetime(df[input_column], errors="coerce", **kwargs)
            # Recipe to handle defaults, does not run when converting the default value
            if not recursion_stop:
                df['tempadfsgadg'] = temp
                df = _wrangles.recipe.run(
                    recipe = """
                        wrangles:
                        - replace:
                            input: tempadfsgadg
                            find: NaT
                            replace: ''
                            where: tempadfsgadg IS NULL

                        - create.column:
                            output: defaultzdbdfzmngz
                            value: ${default}

                        - convert.data_type:
                            input: defaultzdbdfzmngz
                            data_type: datetime
                            stop: true
                            if: ${default} != None

                        - merge.coalesce:
                            input:
                            - tempadfsgadg
                            - defaultzdbdfzmngz
                            - ${input_col}
                            output: ${output_col}

                        - drop:
                            columns:
                            - defaultzdbdfzmngz
                            - tempadfsgadg
                        """,
                    dataframe = df,
                    variables = {
                        'input_col': input_column,
                        'output_col': output_column,
                        'default': default
                        }
                    )
                
            else:
                df[input_column] = temp

    else:
        dtype_dict = {
            'int': int,
            'float': float,
            'str': str,
            'bool': bool
            }
        
        # Raise an error if the datatype is not supported
        if data_type not in dtype_dict:
            raise ValueError(f"data_type {data_type} is not supported. Supported types are: {list(dtype_dict.keys()) + ['datetime']}")
        else:
            data_type = dtype_dict.get(data_type)

        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):

            # Function that converts data using dtype() and logs a warning only once when the conversion fails
            def _safe_convert(x, dtype, default, row):
                try:
                    return dtype(x)
                except Exception as e:
                    if not getattr(_safe_convert, "_warning_logged", False):
                        _logging.warning(
                            f"Found invalid values at row {row} when converting to {data_type} using convert.datatype."
                            )
                        _safe_convert._warning_logged = True  # mark as logged

                    # Return default if provided, otherwise return original value
                    if default != None:
                        return default
                    else:
                        return x

            df[output_column] = df.apply(lambda row: _safe_convert(row[input_column], data_type, default, row.name), axis=1)

    return df


def fraction_to_decimal(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    decimals: int = 4,
    output: _Union[str, list] = None
) -> _pd.DataFrame:
    """
    type: object
    description: Convert fractions to decimals
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the input column
      output:
        type:
          - string
          - array
        description: Name of the output colum
      decimals:
        type:
          - number
        description: Number of decimals to round fraction
    """
    # Set the output column as input if not provided
    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    for in_col, out_col in zip(input, output):
        results = []
        for item in df[in_col].astype(str):
            fractions = fractions = _re.finditer(r'\b(\d+[\s-])?\d+/\d+\b', item)
            replacement_list = []
            for match in fractions:
                fraction_str = match.group()
                                
                # Get only the fraction part with or without whole number
                fraction = _Fraction(_re.findall(r'\d+\/\d+', fraction_str)[0])
                decimal = round(float(fraction), decimals)
                
                # try to see if there is a whole number
                if _re.findall(r'(\d+[\s-])', fraction_str):
                    # remove the "-" from the whole number
                    whole_number = _re.findall(r'(\d+[\s-])', fraction_str)[0].strip()
                    whole_number = _re.sub(r'-', "", whole_number)
                    whole_number = int(whole_number)
                    decimal = whole_number + decimal
                
                replacement_list.append((fraction_str, str(decimal)))
            for fraction, dec in replacement_list:
                item = item.replace(fraction, dec)
            
            
            results.append(item)
            
        df[out_col] = results
    
    return df


def from_json(
    df: _pd.DataFrame, 
    input: _Union[str, int, list], 
    output: _Union[str, list] = None,
    default = None,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Convert a JSON representation into an object
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the input column.
      output:
        type:
          - string
          - array
        description: Name of the output column. If omitted, the input column will be overwritten
      default:
        type: ["string","array","object","number","boolean","null"]
        description: Value to return if the row is empty or fails to be parsed as JSON
    """
    def _load_with_fallback(value):
        """
        Attempt to load JSON.
        If fails and user has provided a default, return that.
        If no default, raise an error.
        """
        try:
            return _json.loads(value, **kwargs)
        except:
            if default != None:
                return default
            else:
                raise ValueError(
                    "Unable to load all rows as JSON. " +
                    "Set a default to set a value if the row is empty or fails to parse."
                )

    # Set output column as input if not provided
    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
        
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = [
            _load_with_fallback(x)
            for x in df[input_column]
        ]
    
    return df


def to_json(
    df: _pd.DataFrame, 
    input: _Union[str, int, list], 
    output: _Union[str, list] = None, 
    ensure_ascii: bool = False,
    **kwargs
) -> _pd.DataFrame:
    r"""
    type: object
    description: Convert an object to a JSON representation.
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the input column.
      output:
        type:
          - string
          - array
        description: Name of the output column. If omitted, the input column will be overwritten
      indent:
        type:
          - string
          - integer
        description: >-
          If indent is a non-negative integer or string, then JSON array elements and object members will be pretty-printed 
          with that indent level. An indent level of 0, negative, or "" will only insert newlines. None (the default) selects the most 
          compact representation. Using a positive integer indent indents that many spaces per level. If indent is a string (such as '\t'), 
          that string is used to indent each level.
      sort_keys:
        type: boolean
        description: If sort_keys is true (defaults to False), then the output of dictionaries will be sorted by key.
      ensure_ascii:
        type: boolean
        description: If true, non-ASCII characters will be escaped. Default is false 
    """
    def handle_unusual_datatypes(o):
        if isinstance(o, _np.ndarray):
            return o.tolist()
        if isinstance(o, (_np.integer, _np.floating)):
            return o.item()
        else:
            return o.__str__()

    # Set output column as input if not provided
    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    # Ensure input and output are equal lengths
    if len(input) == len(output):
        # Loop through and apply for all columns
        for input_columns, output_column in zip(input, output):
            df[output_column] = [
                _json.dumps(
                    row,
                    ensure_ascii=ensure_ascii,
                    default=handle_unusual_datatypes,
                    **kwargs
                ) 
                for row in df[input_columns].values
            ]
    elif len(input) > 1 and len(output) == 1:
        df[output] = [
            _json.dumps(
                row,
                ensure_ascii=ensure_ascii,
                default=handle_unusual_datatypes,
                **kwargs
            ) 
            for row in df[input].to_dict(orient="records")
        ]
    else:
        raise ValueError('The lists for input and output must be the same length.')

    return df

 
def from_yaml(
    df: _pd.DataFrame, 
    input: _Union[str, int, list], 
    output: _Union[str, list] = None,
    default = None,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Convert a YAML representation into an object
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the input column.
      output:
        type:
          - string
          - array
        description: >-
          Name of the output column.
          If omitted, the input column will be overwritten
      default:
        type: ["string","array","object","number","boolean","null"]
        description: Value to return if the row is empty or fails to be parsed as JSON
    """
    def _load_with_fallback(value):
        """
        Attempt to load JSON.
        If fails and user has provided a default, return that.
        If no default, raise an error.
        """
        try:
            return _yaml.load(value, Loader=_YAMLLoader, **kwargs) or default
        except:
            if default != None:
                return default
            else:
                raise ValueError(
                    "Unable to load all rows as YAML. " +
                    "Set a default to set a value if the row is empty or fails to parse."
                )

    # Set output column as input if not provided
    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
        
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = [
            _load_with_fallback(x)
            for x in df[input_column]
        ]
    
    return df


def to_yaml(
    df: _pd.DataFrame, 
    input: _Union[str, int, list], 
    output: _Union[str, list] = None,
    sort_keys: bool = False,
    allow_unicode: bool = True,
    **kwargs
) -> _pd.DataFrame:
    r"""
    type: object
    description: Convert an object to a YAML representation.
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the input column.
      output:
        type:
          - string
          - array
        description: >-
          Name of the output column.
          If omitted, the input column will be overwritten
      indent:
        type: integer
        description: >-
          Specify the number of spaces for indentation to 
          specify nested elements
      sort_keys:
        type: boolean
        description: >-
          If sort_keys is true (default: False),
          then the output of dictionaries will be sorted by key.
    """
    # Set output column as input if not provided
    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    # Ensure input and output are equal lengths
    if len(input) == len(output):
        # Loop through and apply for all columns
        for input_columns, output_column in zip(input, output):
            df[output_column] = [
                _yaml.dump(
                    row,
                    sort_keys=sort_keys,
                    allow_unicode=allow_unicode,
                    Dumper=_YAMLDumper,
                    **kwargs
                )
                for row in df[input_columns].values
            ]
    elif len(input) > 1 and len(output) == 1:
        # User specified multiple inputs but only one output
        # Merge the inputs into a single dictionary before converting
        df[output] = [
            _yaml.dump(
                row,
                sort_keys=sort_keys,
                allow_unicode=allow_unicode,
                Dumper=_YAMLDumper,
                **kwargs
            )
            for row in df[input].to_dict(orient="records")
        ]
    else:
        raise ValueError('The lists for input and output must be the same length.')
        
    return df
