"""
Connector to read/write from DuckDB database files.
"""
import logging as _logging
from typing import Union as _Union

import pandas as _pd

from ..utils import (
    LazyLoader as _LazyLoader,
    wildcard_expansion as _wildcard_expansion,
)


_duckdb = _LazyLoader('duckdb')

_schema = {}


def _quote_identifier(identifier: str) -> str:
    return '.'.join(
        f'"{part.replace(chr(34), chr(34) * 2)}"'
        for part in str(identifier).split('.')
    )


def read(
    database: str,
    command: str,
    columns: _Union[str, list] = None,
    params: _Union[list, tuple, dict] = None,
    **kwargs
) -> _pd.DataFrame:
    """
    Read data from a DuckDB database.

    >>> from wrangles.connectors import duckdb
    >>> df = duckdb.read(database='database.duckdb', command='SELECT * FROM table')

    :param database: The database to connect to including the file path. Use ':memory:' for an in-memory database.
    :param command: SQL command to select data.
    :param columns: (Optional) Subset of columns to be returned. This is less efficient than specifying in the SQL command.
    :param params: (Optional) Variables to pass to a parameterized query.
    """
    _logging.info(f": Reading data from DuckDB :: {database}")

    with _duckdb.connect(database=database, **kwargs) as conn:
        df = conn.execute(command, params or ()).fetchdf()

    if columns is not None:
        columns = _wildcard_expansion(df.columns, columns)
        df = df[columns]

    return df


_schema['read'] = r"""
type: object
description: Import data from a DuckDB Database
required:
  - database
  - command
properties:
  database:
    type: string
    description: The database to connect to including the file path. Use ':memory:' for an in-memory database.
  command:
    type: string
    description: |-
      SQL command to select data.
      Note - using variables here can make your recipe vulnerable
      to sql injection. Use params if using variables from
      untrusted sources.
  columns:
    type:
      - string
      - array
    description: A list with a subset of the columns to import. This is less efficient than specifying in the command.
  params:
    type:
      - array
      - object
    description: Variables to pass to a parameterized query.
"""


def write(
    df: _pd.DataFrame,
    database: str,
    table: str,
    action: str = 'INSERT',
    columns: _Union[str, list] = None,
    **kwargs
) -> None:
    """
    Write data to a DuckDB database.

    >>> from wrangles.connectors import duckdb
    >>> duckdb.write(df, database='database.duckdb', table='table')

    :param df: Pandas Dataframe to be written.
    :param database: The database to connect to including the file path. Use ':memory:' for an in-memory database.
    :param table: Table to be exported to.
    :param action: INSERT appends, REPLACE recreates the table, FAIL errors if the table exists. Defaults to INSERT.
    :param columns: (Optional) Subset of the columns to be written. If not provided, all columns will be output.
    """
    _logging.info(f": Writing data to DuckDB :: {database} / {table}")

    action = action.upper()
    if columns is not None:
        columns = _wildcard_expansion(df.columns, columns)
        df = df[columns]

    table_name = _quote_identifier(table)
    with _duckdb.connect(database=database, **kwargs) as conn:
        conn.register('_wrangles_df', df)

        if action == 'FAIL':
            conn.execute(f'CREATE TABLE {table_name} AS SELECT * FROM _wrangles_df')
        elif action == 'REPLACE':
            conn.execute(f'CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM _wrangles_df')
        elif action == 'INSERT':
            conn.execute(f'CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM _wrangles_df WHERE false')
            conn.execute(f'INSERT INTO {table_name} SELECT * FROM _wrangles_df')
        else:
            raise ValueError('Invalid action. Expected INSERT, REPLACE, or FAIL.')


_schema['write'] = """
type: object
description: Export data to a DuckDB Database
required:
  - database
  - table
properties:
  database:
    type: string
    description: The database to connect to including the file path. Use ':memory:' for an in-memory database.
  table:
    type: string
    description: The table to write to
  action:
    type: string
    description: INSERT appends, REPLACE recreates the table, FAIL errors if the table exists. Defaults to INSERT.
    enum:
      - INSERT
      - REPLACE
      - FAIL
  columns:
    type:
      - string
      - array
    description: A list of the columns to write to the table. If omitted, all columns will be written.
"""


def run(
    database: str,
    command: _Union[str, list],
    params: _Union[list, tuple, dict] = None,
    **kwargs
) -> None:
    """
    Run a command on a DuckDB database.

    >>> wrangles.connectors.duckdb.run(
    >>>    database='database.duckdb',
    >>>    command='<SQL COMMAND>'
    >>> )

    :param database: The database to connect to including the file path. Use ':memory:' for an in-memory database.
    :param command: SQL command or a list of SQL commands to execute.
    :param params: Variables to pass to a parameterized query.
    """
    _logging.info(f": Executing DuckDB Command :: {database}")

    if isinstance(command, str):
        command = [command]

    with _duckdb.connect(database=database, **kwargs) as conn:
        for sql in command:
            conn.execute(sql, params or ())


_schema['run'] = r"""
type: object
description: Run a command against a DuckDB Database
required:
  - database
  - command
properties:
  database:
    type: string
    description: The database to connect to including the file path. Use ':memory:' for an in-memory database.
  command:
    type:
      - string
      - array
    description: SQL command or a list of SQL commands to execute
  params:
    type:
      - array
      - object
    description: Variables to pass to a parameterized query.
"""
