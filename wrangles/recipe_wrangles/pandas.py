import pandas as _pd
from typing import Union as _Union


def copy(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list]) -> _pd.DataFrame:
    """
    type: object
    description: Make a copy of a column or a list of columns
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type:
          - string
          - array
        description: Name of the input columns or columns
      output:
        type:
          - string
          - array
        description: Name of the output columns or columns
    """
    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # If input is a single column and output is multiple columns, repeat input
    if len(input) == 1 and len(output) > 1:
        input = input * len(output)

    # If input is not the same length as output, raise error
    if len(input) != len(output):
        raise ValueError("Input and output must be the same length")
    
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].copy()
        
    return df


def drop(df: _pd.DataFrame, columns: _Union[str, list]) -> _pd.DataFrame:
    """
    type: object
    description: Drop (Delete) selected column(s)
    additionalProperties: true
    required:
      - columns
    properties:
      columns:
        type:
          - array
          - string
        description: Name of the column(s) to drop
    """
    return df.drop(columns=columns)
    

def transpose(df: _pd.DataFrame) -> _pd.DataFrame:
    """
    type: object
    description: Transpose the DataFrame (swap columns to rows)
    additionalProperties: true
    """
    return df.transpose()


def sort(df: _pd.DataFrame, ignore_index=True, **kwargs) -> _pd.DataFrame:
    """
    type: object
    description: Sort the data
    additionalProperties: true
    required:
      - by
    properties:
      by:
        type:
          - string
          - array
        description: Name or list of the column(s) to sort by
      ascending:
        type:
          - boolean
          - array
        items:
          type: boolean
        description: >-
          Sort ascending vs. descending.
          Specify a list to sort multiple columns in different orders.
          If this is a list of bools then it must match the length of the by.
    """
    return df.sort_values(
        ignore_index=ignore_index,
        **kwargs
    )


def round(df: _pd.DataFrame, input: _Union[str, list], decimals: int = 0, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Round column(s) to the specified decimals
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - string
          - array
        description: Name of the input column(s)
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
      decimals:
        type: number
        description: Number of decimal places to round column
    """
    if output is None: output = input
    
    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].round(decimals=decimals)
        
    return df
    
    
def reindex(
        df: _pd.DataFrame,
        labels: list= None,
        index: list = None,
        columns: list = None,
        axis: _Union[str, int] = None,
        **kwargs
        ) -> _pd.DataFrame:
    """
    type: object
    description: Changes the row labels and column labels of a DataFrame.
    additionalProperties: false
    properties:
      labels:
        type: array
        description: New labels / index to conform the axis specified by ‘axis’ to.
      index:
        type: array
        description: New labels for the index. Preferably an Index object to avoid duplicating data.
      columns:
        type: array
        description: New labels for the columns. Preferably an Index object to avoid duplicating data.
      axis:
        type:
          - number
          - string
        description: Axis to target. Can be either the axis name (‘index’, ‘columns’) or number (0, 1).  
    """

    # The following code is due to issue "Get Pandas to work with versions" #199
    # This ensures this works with older and newer pandas versions
    # Adding parameters to dictionary
    params = {"labels": labels, "index": index, "columns": columns, "axis": axis}
    # filter any None values
    params = {k:v for (k, v) in zip(params.keys(), params.values()) if v != None}
    # merge with kwargs
    parameters = {**params, **kwargs}
    
    df = df.reindex(**parameters)
    
    return df


def explode(
    df: _pd.DataFrame,
    input: _Union[str, list],
    reset_index: bool = True
) -> _pd.DataFrame:
    """
    type: object
    description: Explode a column of lists into rows
    additionalProperties: false
    required:
      - input
    properties:
        input:
          type:
            - string
            - array
          description: >-
            Name of the column(s) to explode. If multiple
            columns are included they must contain lists
            of the same length
        reset_index:
          type: boolean
          description: Reset the index after exploding. Default True.
    """    
    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    
    # Check if there are any columns not in df
    if not set(input).issubset(df.columns):
        raise ValueError(f"Columns {input} not in DataFrame")

    return df.explode(input, reset_index)


from ..lookup import lookup as _lookup
from ..data import model as _model

def lookup(
    df: _pd.DataFrame,
    input: str,
    reference: dict = None,
    output: _Union[str, list] = None,
    default: str = None,
    model_id: str = None
) -> _pd.DataFrame:
    """
    type: object
    description: Lookup values in a reference dictionary
    additionalProperties: true
    required:
      - input
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
      overrides:
        type: object
        description: The lookup to apply to the column(s)
      na_action:
        type: string
        description: If 'ignore' propagate NaN values, without passing them to the mapping correspondence.
      default:
        type: string
        description: The default value to use if the input is not found in the reference.
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
            data = _lookup(df[input].values.tolist(), model_id, columns=wrangle_output)
            df[output] = data
        elif not any([col in metadata["settings"]["columns"] for col in wrangle_output]):
            # User specified no columns from the wrangle
            # Add dict of all values to those columns
            data = _lookup(df[input].values.tolist(), model_id)
            for out in output:
                df[out] = data
        else:
            # User specified a mixture of unrecognized columns and columns from the wrangle
            raise ValueError('Lookup may only contain all named or unnamed columns.')

    # for i in range(len(output)):
    #     df[output[i]] = df.loc[:, input].map(arg=reference, na_action=na_action)

    # if default:
    #     df[output] = df[output].fillna(default)
    
    return df
