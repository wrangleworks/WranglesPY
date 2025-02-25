"""
Connector to read/write from SQLite database
"""
import pandas as _pd
from typing import Union as _Union
import logging as _logging
import sqlite3 as _sqlite3

_schema = {}

def read(database: str, command: str, columns: _Union[str, list] = None, params: _Union[list, dict] = None) -> _pd.DataFrame:
    """
    Import data from a SQLite database.

    >>> from wrangles.connectors import sqlite
    >>> df = sqlite.read(database = 'database.db', command='SELECT * FROM table')


    :param database: Database to be queried
    :param command: SQL command or table name
    :param columns: (Optional) Subset of columns to be returned. This is less efficient than specifying in the SQL command.
    :param params: (Optional) List of parameters to pass to execute method. The syntax used to pass parameters is database driver dependent.
    :return: Pandas Dataframe of the imported data
    """

    _logging.info(f": Reading data from SQLite :: {database}")
    
    conn = _sqlite3.connect(database)
    df = _pd.read_sql(command, conn, params)

    if columns is not None: df = df[columns]

    return df

_schema['read'] = """
type: object
description: Import data from a SQLite Database
required:
  - database
  - command
properties:
  database:
    type: string
    description: The database to connect to
  command:
    type: string
    description: |-
      Table name or SQL command to select data.
      Note - using variables here can make your recipe vulnerable
      to sql injection. Use params if using variables from
      untrusted sources.
  columns:
    type: array
    description: A list with a subset of the columns to import. This is less efficient than specifying in the command.
  params:
    type: 
      - array
      - object
    description: |-
      List of parameters to pass to execute method.
      This may use %s or %(name)s syntax
"""

def write(df: _pd.DataFrame, database: str, table: str, action = 'INSERT', columns: _Union[str, list] = None) -> None:
    """
    Write data to a SQLite database.

    >>> from wrangles.connectors import sqlite
    >>> sqlite.write(df, database = 'database.db')

    :param df: Pandas Dataframe to be written
    :param database: Database to be written to
    :param table: Table to be exported to
    :param action: Action to be taken on the database, defaults to 'INSERT'. Options are 'INSERT', 'UPDATE', 'DELETE', etc
    :param columns: (Optional) Subset of columns to be written. If not provided, all columns will be output
    """

    _logging.info(f": Writing data to SQLite :: {database}")

    conn = _sqlite3.connect(database)
    df.to_sql(table, conn, if_exists = 'append', index = False, method='multi', chunksize=1000)

_schema['write'] = """
type: object
description: Export data to a SQLite Database
required:
  - df
  - database
  - table
properties:
  df:
    type: object
    description: Pandas Dataframe to be written
  database:
    type: string
    description: The database to connect to
  table:
    type: string
    description: The table to write to
  action:
    type: string
    description: Action to be taken on the database, defaults to 'INSERT'. Options are 'INSERT', 'UPDATE', 'DELETE', etc
  columns:
    type: array
    description: A list with a subset of the columns to import. If ommitted, all columns will be written to
"""