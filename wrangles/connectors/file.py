"""
Connector to read & write from the local filesystem

Supports Excel, CSV, JSON and JSONL files.

### Sample Recipes
~~~

import:
  file:
    name: myfile.xlsx

~~~

export:
  file:
    name: myfile.csv

~~~
"""
import pandas as _pd
import logging as _logging
from typing import Union as _Union


def read(name: str, fields: _Union[str, list] = None, parameters: dict = {}) -> _pd.DataFrame:
    """
    Import a file as defined by user parameters.

    Supports Excel (.xlsx, .xlsx, .xlsm), CSV (.csv, .txt) and JSON (.json) files.
    JSON and CSV may also be gzipped (.csv.gz, .txt.gz, .json.gz) and will be decompressed.

    >>> df = wrangles.connectors.file.read('myfile.csv')

    :param name: Name of the file to import
    :param fields: (Optional) Subset of the fields to be read. If not provided, all fields will be included
    :param parameters: (Optional) Dictionary of custom parameters to pass to the respective pandas function
    :return: A Pandas dataframe of the imported data.
    """
    _logging.info(f": Importing Data :: {name}")

    # Open appropriate file type
    if name.split('.')[-1] in ['xlsx', 'xlsm', 'xls']:
        if 'dtype' not in parameters.keys(): parameters['dtype'] = 'object'
        df = _pd.read_excel(name, **parameters).fillna('')
    elif name.split('.')[-1] in ['csv', 'txt'] or '.'.join(name.split('.')[-2:]) in ['csv.gz', 'txt.gz']:
        df = _pd.read_csv(name, **parameters).fillna('')
    elif name.split('.')[-1] in ['json'] or '.'.join(name.split('.')[-2:]) in ['json.gz']:
        df = _pd.read_json(name, **parameters).fillna('')
    elif name.split('.')[-1] in ['jsonl'] or '.'.join(name.split('.')[-2:]) in ['jsonl.gz']:
        # Set lines to true 
        parameters['lines'] = True
        # Only records orientation is supported for JSONL
        parameters['orient'] = 'records'
        df = _pd.read_json(name, **parameters).fillna('')

    # If the user specifies only certain fields, only include those
    if fields is not None: df = df[fields]

    return df


def write(df: _pd.DataFrame, name: str, fields: _Union[str, list] = None, parameters = {}) -> None:
    """
    Output a file to the local file system as defined by the parameters.

    Supports Excel (.xlsx, .xls), CSV (.csv, .txt) and JSON (.json) files.
    JSON and CSV may also be gzipped (.csv.gz, .txt.gz, .json.gz) and will be compressed.

    :param df: Dataframe to be written to a file
    :param name: Name of the output file
    :param fields: (Optional) Subset of the fields to be written. If not provided, all fields will be output
    :param parameters: Dictionary of parameters to pass to the respective pandas function
    """
    _logging.info(f": Exporting Data :: {name}")

    # Select only specific fields if user requests them
    if fields is not None: df = df[fields]

    # Write appropriate file
    if name.split('.')[-1] in ['xlsx', 'xls']:
        # Write an Excel file
        # Default to not including index if user hasn't explicitly requested it
        if 'index' not in parameters.keys(): parameters['index'] = False
        df.to_excel(name, **parameters)

    elif name.split('.')[-1] in ['csv', 'txt'] or '.'.join(name.split('.')[-2:]) in ['csv.gz', 'txt.gz']:
        # Write a CSV file
        # Default to not including index if user hasn't explicitly requested it
        if 'index' not in parameters.keys(): parameters['index'] = False
        df.to_csv(name, **parameters)

    elif name.split('.')[-1] in ['json'] or '.'.join(name.split('.')[-2:]) in ['json.gz']:
        # Write a JSON file
        df.to_json(name, **parameters)
        
    elif name.split('.')[-1] in ['jsonl'] or '.'.join(name.split('.')[-2:]) in ['jsonl.gz']:
        # Write a line delimited JSONL file
        # Set lines to true 
        parameters['lines'] = True
        # Only records orientation is supported for JSONL
        parameters['orient'] = 'records'
        df.to_json(name, **parameters)