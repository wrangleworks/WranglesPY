"""
Import a file from an SFTP server

Supports Excel, CSV, JSON and JSONL files.
"""
import fabric as _fabric
import pandas as _pd
import io as _io
import logging as _logging
from . import file as _file


_schema = {}


def read(host: str, user: str, password: str, file: str, port: int = 22, **kwargs) -> _pd.DataFrame:
    """
    Read files from an SFTP server

    >>> from wrangles.connectors import sftp
    >>> df = sftp.read(host='sftp.domain', user='user', password='password', file='myfile.csv')

    :param host: The domain or IP of the SFTP server
    :param user: The user to connect as
    :param password: The password for the user
    :param file: The filename including path on the remote server
    :param kwargs: Other arguments from the file connector may also be used
    :return: A dataframe with the imported data
    """
    _logging.info(f": Importing Data from SFTP :: {host}")

    # Get the file from the SFTP server
    tempFile = _io.BytesIO()
    _fabric.Connection(host, user=user, port=port, connect_kwargs={'password': password}).get(file, local=tempFile)
    tempFile.seek(0)
    
    # Read the data using the file connector
    df = _file.read(file, file_object=tempFile, **kwargs)

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


def write(df, host: str, user: str, password: str, file: str, port: int = 22, **kwargs) -> None:
    """
    Write files to an SFTP server

    Supports Excel (.xlsx, .xls), CSV (.csv, .txt) and JSON (.json) files.
    JSON and CSV may also be gzipped (.csv.gz, .txt.gz, .json.gz) and will be compressed.

    >>> from wrangles.connectors import sftp
    >>> df = sftp.write(df, host='sftp.domain', user='user', password='password', file='myfile.csv')

    :param df: Dataframe to be written to a file
    :param host: The domain or IP of the SFTP server
    :param user: The user to connect as
    :param password: The password for the user
    :param file: The filename including path on the remote server
    :param port: (Optional) Specify the port to connect to
    :param kwargs: Other arguments from the file connector may also be used
    """
    # Create file in memory using the file connector
    tempFile = _io.BytesIO()
    _file.write(df, name=file, file_object=tempFile, **kwargs)
    tempFile.seek(0)  # Reset file to start

    # Export to SFTP server
    _logging.info(f": Exporting data via SFTP :: {host}")
    _fabric.Connection(host, user=user, port=port, connect_kwargs={'password': password}).put(tempFile, remote=file)


_schema['write'] = """
type: object
description: Export a file to an SFTP server
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
    description: Choose only a subset of the columns to export
  sheet_name:
    type: string
    description: Used for Excel files. Specify the sheet to create.
  orient:
    type: string
    description: Used for JSON files. Specifies the output arrangement
    enum:
      - split
      - records
      - index
      - columns
      - values
"""