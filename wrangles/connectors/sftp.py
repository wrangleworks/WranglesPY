"""
Import a file from an SFTP server

Supports Excel, CSV, JSON and JSONL files.
"""
from typing import Union as _Union
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
    with _fabric.Connection(
        host,
        user=user,
        port=port,
        connect_kwargs={'password': password}
    ) as conn:
        try:
            conn.get(file, local=tempFile)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found on SFTP server :: {file}") from None

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
    _file.write(df, name=file.split("/")[-1], file_object=tempFile, **kwargs)
    tempFile.seek(0)  # Reset file to start

    # Export to SFTP server
    _logging.info(f": Exporting data via SFTP :: {host}")
    with _fabric.Connection(
        host,
        user=user,
        port=port,
        connect_kwargs={'password': password}
    ) as conn:
        conn.put(tempFile, remote=file)


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

class download_files:
    """
    Download files from an SFTP host and save to the local file system.
    """
    _schema = {
        "run": """
            type: object
            description: Download files from an SFTP host and save to the local file system.
            required:
              - host
              - user
              - password
              - files
            properties:
              host:
                type: string
                description: The hostname of the SFTP server.
                examples:
                  - sftp.domain.com
              user:
                type: string
                description: The user to authenticate as.
              password:
                type: string
                description: The password for the user.
              files:
                type:
                  - string
                  - array
                description: >-
                  A file, or list of files, to download.
                  If local is not specified, they will be
                  saved to the current directory.
              local:
                type:
                  - string
                  - array
                description: >-
                  (Optional) The local filename(s) to save
                  the remote files as.
              port:
                type: integer
                description: The port to connect to. Default 22.
        """
    }

    def run(
        host: str,
        user: str,
        password: str,
        files: _Union[str, list],
        local: _Union[str, list] = None,
        port: int = 22
    ):
        """
        Download files from an SFTP host and save to the local file system.

        :param host: The hostname of the SFTP server.
        :param user: The user to authenticate as.
        :param password: The password for the user.
        :param files: A file, or list of files to download.
        :param local: (Optional) The local filename(s) and/or directories to save as.
        :param port: The port to connect to. Default 22.
        """
        _logging.info(f": Downloading files from SFTP :: host={host} files={files}")

        # Ensure files and local are both lists and 
        if not isinstance(files, list): files = [files]
        if not isinstance(local, list): local = [local]

        # If only a single local is provided, e.g. a directory,
        # expand to the same length as files.
        if len(local) == 1:
            local = local * len(files)

        if len(files) != len(local):
            raise ValueError(
                "If provided, the lists of files and local files must be the same length"
            )

        with _fabric.Connection(
            host,
            user=user,
            port=port,
            connect_kwargs={'password': password}
        ) as conn:
            for f, l in zip(files, local):
                try:
                    conn.get(remote=f, local=l)
                except FileNotFoundError:
                    raise FileNotFoundError(f"File not found on SFTP server :: {f}") from None

class upload_files:
    """
    Upload files from the local file system to an SFTP host.
    """
    _schema = {
        "run": """
            type: object
            description: Upload files from the local file system to an SFTP host.
            required:
              - host
              - user
              - password
              - files
            properties:
              host:
                type: string
                description: The hostname of the SFTP server.
                examples:
                  - sftp.domain.com
              user:
                type: string
                description: The user to authenticate as.
              password:
                type: string
                description: The password for the user.
              files:
                type:
                  - string
                  - array
                description: >-
                  A file, or list of files, to upload.
                  If remote is not specified, they will be
                  saved to the SFTP user's default directory.
              remote:
                type:
                  - string
                  - array
                description: >-
                  (Optional) The remote filename(s) to save
                  the files as.
              port:
                type: integer
                description: The port to connect to. Default 22.
        """
    }

    def run(
        host: str,
        user: str,
        password: str,
        files: _Union[str, list],
        remote: _Union[str, list] = None,
        port: int = 22
    ):
        """
        Upload files from the local file system to an SFTP host.

        :param host: The hostname of the SFTP server.
        :param user: The user to authenticate as.
        :param password: The password for the user.
        :param files: A file, or list of files, to upload.
        :param remote: (Optional) The remote filename(s) and/or directories to save to.
        :param port: The port to connect to. Default 22.
        """
        _logging.info(f": Uploading files to SFTP :: host={host} files={files}")

        # Ensure files and remote are both lists
        if not isinstance(files, list): files = [files]
        if not isinstance(remote, list): remote = [remote]

        # If only a single remote is provided, e.g. a directory,
        # expand to the same length as files.
        if len(remote) == 1:
            remote = remote * len(files)

        if len(files) != len(remote):
            raise ValueError(
                "If provided, the lists of files and remote files must be the same length"
            )

        with _fabric.Connection(
            host,
            user=user,
            port=port,
            connect_kwargs={'password': password}
        ) as conn:
            for f, r in zip(files, remote):
                conn.put(local=f, remote=r)
