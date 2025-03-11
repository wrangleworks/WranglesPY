"""
Connector to read/write from SQLite database
"""
import pandas as _pd
import logging as _logging
import sqlite3 as _sqlite3

_schema = {}

def read(database: str, command: str, **kwargs) -> _pd.DataFrame:
    """
    Import data from a SQLite database.

    >>> from wrangles.connectors import sqlite
    >>> df = sqlite.read(database = 'database.db', command='SELECT * FROM table')

    :param database: Database to be queried
    :param command: SQL command or table name
    """
    _logging.info(f": Reading data from SQLite :: {database}")
    
    with _sqlite3.connect(database) as conn:
        df = _pd.read_sql(command, conn, **kwargs)

    return df

_schema['read'] = r"""
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
"""

def write(df: _pd.DataFrame, database: str, table: str, **kwargs) -> None:
    """
    Write data to a SQLite database.

    >>> from wrangles.connectors import sqlite
    >>> sqlite.write(df, database = 'database.db', table = 'table')

    :param df: Pandas Dataframe to be written
    :param database: The database to connect to including the file path. e.g. directory/database.db
    :param table: Table to be exported to
    """
    _logging.info(f": Writing data to SQLite :: {database} / {table}")

    with _sqlite3.connect(database) as conn:
        df.to_sql(
            table,
            con = conn,
            if_exists = 'append',
            index = False,
            method='multi',
            chunksize=1000,
            **kwargs
        )

_schema['write'] = """
type: object
description: Export data to a SQLite Database
required:
  - database
  - table
properties:
  database:
    type: string
    description: The database to connect to including the file path. e.g. directory/database.db
  table:
    type: string
    description: The table to write to
"""
