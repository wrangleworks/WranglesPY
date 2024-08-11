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
    reset_index: bool = True,
    drop_empty: bool = False
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
        drop_empty:
          type: boolean
          description: |- 
            If true, any rows that contain an empty list will be dropped.
            If false, rows that contain empty lists will keep 1 row with an empty value.
            Default False.
    """    
    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    
    # Check if there are any columns not in df
    if not set(input).issubset(df.columns):
        raise ValueError(f"Columns {input} not in DataFrame")

    df = df.explode(input, reset_index)

    # Drop any rows that contain na after exploding
    if drop_empty:
        df = df.dropna(subset=input, how='all')

    return df
