import pandas as _pd
from typing import Union as _Union
from numpy import nan as _nan


def copy(
    df: _pd.DataFrame,
    input: _Union[str, int, list] = None,
    output: _Union[str, list] = None,
    **kwargs
) -> _pd.DataFrame:
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
          - integer
          - array
        description: Name of the input columns or columns
      output:
        type:
          - string
          - array
        description: Name of the output columns or columns
    """
    # If short form of paired names is provided, use that
    if input is None:
        # Check that column name exists
        copy_cols = list(kwargs.keys())
        for x in copy_cols:
            if x not in list(df.columns): raise ValueError(f'Column to copy "{x}" not found.')
        # Check if the new column names exist if so drop them
        df = df.drop(columns=[x for x in list(kwargs.values()) if x in df.columns and x not in list(kwargs.keys())])
        
        copy_dict = kwargs

        return copy(df, input=list(copy_dict.keys()), output=list(copy_dict.values()))
    
    else:
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
    

def transpose(df: _pd.DataFrame, header_column = 0) -> _pd.DataFrame:
    """
    type: object
    description: Transpose the DataFrame (swap columns to rows)
    additionalProperties: false
    properties:
      header_column:
        type: 
          - string
          - integer
          - null
        description: >- 
          Name or position of the column that will be used as the column headings
          for the transposed DataFrame. Default 0 (first column).
          Use header_column = null to not use any column as header.
    """
    if header_column is not None:
        if isinstance(header_column, int):
            # If header_column is an integer, use it as the column index
            header_column = df.columns[header_column]

        df = df.set_index(header_column).transpose()

        # convert index to column
        df.index.name = df.columns.name
        df.columns.name = None

        df = df.reset_index()
        return df

    else:
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


def round(df: _pd.DataFrame, input: _Union[str, int, list], decimals: int = 0, output: _Union[str, list] = None) -> _pd.DataFrame:
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
          - integer
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
        # coerce input column to floats (nan on error)
        # replace nan with empty string
        df[output_column] = _pd.to_numeric(df[input_column], errors='coerce').round(decimals=decimals).map(float).replace(_nan, '')
        
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
    input: _Union[str, int, list],
    reset_index: bool = True,
    drop_empty: bool = False,
    where = None
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
            - integer
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
    
    # If using where, we need to maintain the index
    # to be able to merge back later
    if where:
        reset_index = False

    df = df.explode(input, reset_index)

    # Drop any rows that contain na after exploding
    if drop_empty:
        df = df.dropna(subset=input, how='all')

    return df
