"""
Import a file from an SFTP server

Supports Excel, CSV, JSON and JSONL files.
"""
import fabric as _fabric
import pandas as _pd
import io as _io
import logging as _logging

# TODO: add write
# TODO: add run to move/copy/delete files?


_schema = {}


def read(host: str, user: str, password: str, file: str, port: int = 22, columns: list = None, **kwargs) -> _pd.DataFrame:
    """
    Read files from an SFTP server

    >>> from wrangles.connectors import sftp
    >>> df = sftp.read(host='sftp.domain', user='user', password='password', file='myfile.csv')

    :param host: The domain or IP of the SFTP server
    :param user: The user to connect as
    :param password: The password for the user
    :param file: The filename including path on the remote server
    :return: A dataframe with the imported data
    """
    _logging.info(f": Importing Data from SFTP :: {host}")

    # Get the file from the SFTP server
    tempFile = _io.BytesIO()
    _fabric.Connection(host, user=user, port=port, connect_kwargs={'password': password}).get(file, local=tempFile)
    tempFile.seek(0)
    
    # Open appropriate file type
    if file.split('.')[-1] in ['xlsx', 'xlsm', 'xls']:
        if 'dtype' not in kwargs.keys(): kwargs['dtype'] = 'object'
        df = _pd.read_excel(tempFile, **kwargs).fillna('')
    elif file.split('.')[-1] in ['csv', 'txt'] or '.'.join(file.split('.')[-2:]) in ['csv.gz', 'txt.gz']:
        df = _pd.read_csv(tempFile, **kwargs).fillna('')
    elif file.split('.')[-1] in ['json'] or '.'.join(file.split('.')[-2:]) in ['json.gz']:
        df = _pd.read_json(tempFile, **kwargs).fillna('')
    elif file.split('.')[-1] in ['jsonl'] or '.'.join(file.split('.')[-2:]) in ['jsonl.gz']:
        # Set lines to true 
        kwargs['lines'] = True
        # Only records orientation is supported for JSONL
        kwargs['orient'] = 'records'
        df = _pd.read_json(tempFile, **kwargs).fillna('')

    # If the user specifies only certain columns, only include those
    if columns is not None: df = df[columns]

    return df

_schema['read'] = """
type: object
description: Import a file from an SFTP server
required:
  - host
  - user
  - password
  - file
properties:
  host:
    type: string
    description: The domain or IP of the SFTP server
  user:
    type: string
    description: The user to connect as
  password:
    type: string
    description: The password for the user
  file:
    type: string
    description: The filename including path on the remote server
  columns:
    type: array
    description: Choose only a subset of the columns
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
"""