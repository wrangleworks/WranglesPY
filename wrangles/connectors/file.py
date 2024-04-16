"""
Connector to read & write from the local filesystem

Supports Excel, CSV, JSON and JSONL files.
"""
import pandas as _pd
import logging as _logging
from typing import Union as _Union
from io import BytesIO as _BytesIO
import os as _os
import re as _re


_schema = {}


def read(name: str, columns: _Union[str, list] = None, file_object = None, **kwargs) -> _pd.DataFrame:
    """
    Import a file as defined by user parameters.

    Supports:
      - Excel (.xlsx, .xlsx, .xlsm)
      - CSV (.csv, .txt)
      - JSON (.json), JSONL (.jsonl)
      - Pickle (.pkl, .pickle) files.

    JSON, JSONL, CSV and Pickle files may also be gzipped (e.g. .csv.gz, .json.gz) and will be decompressed.

    >>> df = wrangles.connectors.file.read('myfile.csv')

    :param name: Name of the file to import
    :param columns: (Optional) Subset of the columns to be read. If not provided, all columns will be included
    :param file_object: (Optional) File object to read. If provided, this will be read instead of from the file system. A name is still required to infer the file type.
    :param kwargs: (Optional) Named arguments to pass to respective pandas function.
    :return: A Pandas dataframe of the imported data.
    """
    _logging.info(f": Importing Data :: {name}")
    
    # If user does not pass a file object then use name
    if file_object is None:
        file_object = name
    
    # Open appropriate file type
    if name.split('.')[-1] in ['xlsx', 'xlsm', 'xls']:
        if 'dtype' not in kwargs.keys(): kwargs['dtype'] = 'object'
        df = _pd.read_excel(file_object, **kwargs).fillna('')
    elif name.split('.')[-1] in ['csv', 'txt'] or '.'.join(name.split('.')[-2:]) in ['csv.gz', 'txt.gz']:
        df = _pd.read_csv(file_object, **kwargs).fillna('')
    elif name.split('.')[-1] in ['json'] or '.'.join(name.split('.')[-2:]) in ['json.gz']:
        df = _pd.read_json(file_object, **kwargs).fillna('')
    elif name.split('.')[-1] in ['jsonl'] or '.'.join(name.split('.')[-2:]) in ['jsonl.gz']:
        # Set lines to true 
        kwargs['lines'] = True
        # Only records orientation is supported for JSONL
        kwargs['orient'] = 'records'
        df = _pd.read_json(file_object, **kwargs).fillna('')
    elif (
        name.split('.')[-1] in ['pkl', "pickle"] or 
        (len(name.split('.')) >= 3 and name.split('.')[-2] in ['pkl', "pickle"])
    ):
        df = _pd.read_pickle(file_object, **kwargs).fillna('')
    else:
      # If file type is not recognised
      raise ValueError(f"File type '{name.split('.')[-1]}' is not supported by the file connector.")

    # If the user specifies only certain columns, only include those
    if columns is not None: df = df[columns]

    return df

_schema['read'] = """
type: object
description: Import a file
required:
  - name
properties:
  name:
    type: string
    description: The name of the file to import
  columns:
    type: array
    description: Columns to select
  nrows:
    type: integer
    description: Number of rows to read
    minimum: 1
  header:
    type: integer
    description: Set the header row number.
    minimum: 0
  sheet_name:
    type: string
    description: Used for Excel files. Specify the sheet to read.
  orient:
    type: string
    description: Used for JSON files. Specifies the input arrangement
    enum:
      - split
      - records
      - index
      - columns
      - values
  sep:
    type: string
    description: Used for CSV files. Set the separation character. Default , (comma)
  encoding:
    type: string
    description: Used for CSV files. Set the encoding used for the file. Default utf-8
  decimal:
    type: string
    description: "Used for CSV files. Character to recognize as the decimal point (e.g. ',' for European data)."
  thousands:
    type: string
    description: Used for CSV files. Character to recognize as the thousands separator
"""


def write(df: _pd.DataFrame, name: str, columns: _Union[str, list] = None, file_object: _BytesIO  = None, **kwargs) -> None:
    """
    Output a file to the local file system as defined by the parameters.

    Supports:
    - Excel (.xlsx, .xls)
    - CSV (.csv, .txt)
    - JSON (.json), JSONL (.jsonl)
    - Pickle (.pkl, .pickle)
    
    JSON, JSONL, CSV and pickle may also be gzipped (e.g. .csv.gz, .json.gz) and will be compressed.

    :param df: Dataframe to be written to a file
    :param name: Name of the output file
    :param columns: (Optional) Subset of the columns to be written. If not provided, all columns will be output
    :param file_object: (Optional) A bytes file object to be written in memory. If passed, file will be written in memory instead of to the file system.
    :param kwargs: (Optional) Named arguments to pass to respective pandas function.
    """
    _logging.info(f": Exporting Data :: {name}")

    # Select only specific columns if user requests them
    if columns is not None: df = df[columns]

    # If user does not pass a file object then write to disk
    if file_object is None:
        # Ensure directory exists
        path_matched = _re.search(r'^.+(?=\/\w+\.\w+)', name)
        if path_matched:
            _os.makedirs(path_matched[0], exist_ok=True)

        # Set file object to name
        file_object = name

    # Write appropriate file
    if name.split('.')[-1] in ['xlsx', 'xls']:
        # Write an Excel file
        # Default to not including index if user hasn't explicitly requested it
        if 'index' not in kwargs.keys(): kwargs['index'] = False
        df.to_excel(file_object, **kwargs)

    elif name.split('.')[-1] in ['csv', 'txt'] or '.'.join(name.split('.')[-2:]) in ['csv.gz', 'txt.gz']:
        # Write a CSV file
        # Default to not including index if user hasn't explicitly requested it
        if 'index' not in kwargs.keys(): kwargs['index'] = False
        df.to_csv(file_object, **kwargs)

    elif name.split('.')[-1] in ['json'] or '.'.join(name.split('.')[-2:]) in ['json.gz']:
        # Write a JSON file
        # If user doesn't explicitly set orient, assume records - this seems a better default
        if 'orient' not in kwargs.keys(): kwargs['orient'] = 'records'
        df.to_json(file_object, **kwargs)

    elif name.split('.')[-1] in ['jsonl'] or '.'.join(name.split('.')[-2:]) in ['jsonl.gz']:
        # Write a line delimited JSONL file
        # Set lines to true 
        kwargs['lines'] = True
        # Only records orientation is supported for JSONL
        kwargs['orient'] = 'records'
        df.to_json(file_object, **kwargs)

    elif (
        name.split('.')[-1] in ['pkl', "pickle"] or 
        (len(name.split('.')) >= 3 and name.split('.')[-2] in ['pkl', "pickle"])
    ):
        df.to_pickle(file_object, **kwargs)
    else:
      # If file type is not recognised
      raise ValueError(f"File type '{name.split('.')[-1]}' is not supported by the file connector.")

_schema['write'] = """
type: object
description: Export data to a file
required:
  - name
properties:
  name:
    type: string
    description: The name of the file to write.
  columns:
    type: array
    description: A list of the columns to write. If omitted, all columns will be written.
  orient:
    type: string
    description: Used for JSON files. Specifies the output arrangement
    enum:
      - split
      - records
      - index
      - columns
      - values
  sheet_name:
    type: string
    description: Used for Excel files. Specify the sheet to write.
  sep:
    type: string
    description: Used for CSV files. Set the separation character. Default , (comma)
  encoding:
    type: string
    description: Used for CSV files. Set the encoding used for the file. Default utf-8
  mode:
    type: string
    description: Used for CSV files. Set whether to append to (a) or overwrite (w) the file if it already exists. Default w - overwrite
    enum:
      - w
      - a
  decimal:
    type: string
    description: "Used for CSV files. Character to use as the decimal point (e.g. ',' for European data)."
  header:
    type:
      - boolean
      - array
    description: Used for CSV files. Whether to write the column headers. Default true. Alternatively, provide a list to overwrite the headings.
"""