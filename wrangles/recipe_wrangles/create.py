"""
Functions to create new columns
"""
import uuid as _uuid
from typing import Union as _Union
import math as _math
import pandas as _pd
import numpy as _np
from jinja2 import (
    Environment as _Environment,
    FileSystemLoader as _FileSystemLoader,
    BaseLoader as _BaseLoader
)
from ..connectors.test import _generate_cell_values


def bins(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list], bins: _Union[int, list], labels: _Union[str, list] = None, **kwargs) -> _pd.DataFrame:
    """
    type: object
    description: Creates a column that segment and sort data values into bins
    additionalProperties: false
    required:
      - input
      - output
      - bins
    properties:
      input:
        type:
          - array
        description: Name of input column
      output:
        type:
          - array
        description: Name of new column
      bins:
        type:
          - integer
          - array
        description: Defines the number of equal-width bins in the range
      labels:
        type:
          - string
          - array
        description: Labels for the returned bins
    """
    if output is None: output = input
    
    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    for in_col, out_col in zip(input, output):
      # Dealing with positive infinity. At end of bins list
      if isinstance(bins, list):
          if bins[-1] == '+':
              bins[-1] = _math.inf
          
          # Dealing with negative infinity. At start of bins list
          if bins[0] == '-':
              bins[0] = -_math.inf
      
      df[out_col] = _pd.cut(
          x=df[in_col],
          bins=bins,
          labels=labels,
          **kwargs
      )
    
    return df


def column(df: _pd.DataFrame, output: _Union[str, list], value = None) -> _pd.DataFrame:
    """
    type: object
    description: Create column(s) with a user defined value. Defaults to None (empty).
    additionalProperties: false
    required:
      - output
    properties:
      output:
        type:
          - string
          - array
        description: Name or list of names of new columns
      value:
        type: string
        description: (Optional) Value to add in the new column(s). If omitted, defaults to None.
    """
    # Get list of existing columns
    existing_column = df.columns
    
    # Get number of rows in df
    rows = len(df)
    # Get number of columns created
    cols_created = len(output)
    # If a string provided, convert to list
    if isinstance(output, str):
      if output in existing_column:
        raise ValueError(f'"{output}" column already exists in dataFrame.')
      output = [output]
    
    # Allow for user to enter either a list and/or a string in output and value and not error
    if isinstance(value, list) and cols_created == 1:
        value = [value[0] for _ in range(cols_created)]
    elif isinstance(value, str):
        value = [value for _ in range(cols_created)]
    elif value == None:
        value = ['' for _ in range(cols_created)]
        
    # Check if the list of outputs exist in dataFrame
    check_list = [x for x in output if x in existing_column]
    if len(check_list) > 0:
      raise ValueError(f'{check_list} column(s) already exists in the dataFrame') 
    
    for output_column, values_list in zip(output, value):
        # Data to generate
        data = _pd.DataFrame(_generate_cell_values(values_list, rows), columns=[output_column])
        # Merging existing dataframe with values created
        df = _pd.concat([df, data], axis=1)

    return df


def guid(df: _pd.DataFrame, output: _Union[str, list]) -> _pd.DataFrame:
    """
    type: object
    description: Create column(s) with a GUID.
    additionalProperties: false
    required:
      - output
    properties:
      output:
        type:
          - string
          - array
        description: Name or list of names of new columns
    """
    return uuid(df, output)


def index(df: _pd.DataFrame, output: _Union[str, list], start: int = 1, step: int = 1) -> _pd.DataFrame:
    """
    type: object
    description: Create column(s) with an incremental index.
    additionalProperties: false
    required:
      - output
    properties:
      output:
        type:
          - string
          - array
        description: Name or list of names of new columns
      start:
        type: integer
        description: (Optional; default 1) Starting number for the index
      step:
        type: integer
        description: (Optional; default 1) Step between successive rows
    """
    # If a string provided, convert to list
    if isinstance(output, str): output = [output]

    # Loop through and create incremental index
    for output_column in output:
        df[output_column] = _np.arange(start, len(df) * step + start, step=step)

    return df


def jinja(df: _pd.DataFrame, template: dict, output: list, input: str = None) -> _pd.DataFrame:
    """
    type: object
    description: Output text using a jinja template
    additionalProperties: false
    required:
      - output
      - template
    properties:
      input:
        type: string
        description: |
          Specify a name of column containing a dictionary of elements to be used in jinja template.
          Otherwise, the column headers will be used as keys.
      output:
        type: string
        description: Name of the column to be output to.
      template:
        type: object
        description: A dictionary which defines the template/location as well as the form which the template is input
        additionalProperties: false
        properties:
          file:
            type: string
            description: A .jinja file containing the template
          column:
            type: string
            description: A column containing the jinja template - this will apply to the corresponding row.
          string:
            type: string
            description: A string which is used as the jinja template
    """
    if isinstance(output, list):
        output = output[0]
    
    if input:
        input = input[0]
        input_list = df[input]
    else:
        input_list = df.to_dict(orient='records')

    if len(template) > 1:
        raise Exception('Template must have only one key specified')

    # Template input as a file
    if 'file' in template:
        environment = _Environment(loader=_FileSystemLoader(''),trim_blocks=True, lstrip_blocks=True)
        desc_template = environment.get_template(template['file'])
        df[output] = [desc_template.render(row) for row in input_list]

    # Template input as a column of the dataframe
    elif 'column' in list(template.keys()):
        df[output] = [
            _Environment(loader=_BaseLoader).from_string(template).render(row)
            for (template, row) in zip(df[template['column']], input_list)
        ]
        
    # Template input as a string
    elif 'string' in list(template.keys()):
        desc_template = _Environment(loader=_BaseLoader).from_string(template['string'])
        df[output] = [desc_template.render(row) for row in input_list]
  
    else:
        raise Exception("'file', 'column' or 'string' not found")

    return df


def uuid(df: _pd.DataFrame, output: _Union[str, list]) -> _pd.DataFrame:
    """
    type: object
    description: Create column(s) with a UUID.
    additionalProperties: false
    required:
      - output
    properties:
      output:
        type:
          - string
          - array
        description: Name or list of names of new columns
    """
    # If a string provided, convert to list
    if isinstance(output, str): output = [output]

    # Loop through and create uuid for all requested columns
    for output_column in output:
        df[output_column] = [_uuid.uuid4() for _ in range(len(df.index))]

    return df
