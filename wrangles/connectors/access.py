"""
Connector to read/write from Microsoft Access databases using ODBC.
"""
import logging as _logging
from typing import Union as _Union

import pandas as _pd
from pandas.api import types as _pd_types

from ..utils import (
    LazyLoader as _LazyLoader,
    wildcard_expansion as _wildcard_expansion,
)


_pyodbc = _LazyLoader('pyodbc')

_schema = {}


def _quote_identifier(identifier: str) -> str:
    return f"[{str(identifier).replace(']', ']]')}]"


def _connection_string(
    database: str = None,
    connection_string: str = None,
    driver: str = 'Microsoft Access Driver (*.mdb, *.accdb)',
    password: str = None,
) -> str:
    if connection_string:
        return connection_string
    if database is None:
        raise ValueError('database or connection_string must be provided')

    conn = f"DRIVER={{{driver}}};DBQ={database};"
    if password:
        conn += f"PWD={password};"
    return conn


def _access_type(dtype) -> str:
    if _pd_types.is_bool_dtype(dtype):
        return 'BIT'
    if _pd_types.is_integer_dtype(dtype):
        return 'INTEGER'
    if _pd_types.is_float_dtype(dtype):
        return 'DOUBLE'
    if _pd_types.is_datetime64_any_dtype(dtype):
        return 'DATETIME'
    return 'LONGTEXT'


def _table_exists(cursor, table: str) -> bool:
    return cursor.tables(table=table, tableType='TABLE').fetchone() is not None


def _create_table(cursor, table: str, df: _pd.DataFrame) -> None:
    columns = ', '.join(
        f"{_quote_identifier(column)} {_access_type(dtype)}"
        for column, dtype in df.dtypes.items()
    )
    cursor.execute(f"CREATE TABLE {_quote_identifier(table)} ({columns})")


def read(
    command: str,
    database: str = None,
    connection_string: str = None,
    driver: str = 'Microsoft Access Driver (*.mdb, *.accdb)',
    password: str = None,
    columns: _Union[str, list] = None,
    params: _Union[list, tuple] = None,
    **kwargs
) -> _pd.DataFrame:
    """
    Read data from a Microsoft Access database.

    >>> from wrangles.connectors import access
    >>> df = access.read(database='database.accdb', command='SELECT * FROM table')

    :param command: SQL command to select data.
    :param database: Access database file path. Not required if connection_string is supplied.
    :param connection_string: Full ODBC connection string. If provided, database, driver, and password are ignored.
    :param driver: ODBC driver name. Defaults to Microsoft Access Driver (*.mdb, *.accdb).
    :param password: Optional database password.
    :param columns: (Optional) Subset of columns to be returned. This is less efficient than specifying in the SQL command.
    :param params: (Optional) Variables to pass to a parameterized query.
    """
    target = database or connection_string
    _logging.info(f": Reading data from Microsoft Access :: {target}")

    conn_string = _connection_string(database, connection_string, driver, password)
    with _pyodbc.connect(conn_string) as conn:
        df = _pd.read_sql(command, conn, params=params, **kwargs)

    if columns is not None:
        columns = _wildcard_expansion(df.columns, columns)
        df = df[columns]

    return df


_schema['read'] = r"""
type: object
description: Import data from a Microsoft Access Database
required:
  - command
properties:
  database:
    type: string
    description: Access database file path. Not required if connection_string is supplied.
  connection_string:
    type: string
    description: Full ODBC connection string. If provided, database, driver, and password are ignored.
  driver:
    type: string
    description: ODBC driver name. Defaults to Microsoft Access Driver (*.mdb, *.accdb).
  password:
    type: string
    description: Optional database password.
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
    type: array
    description: Variables to pass to a parameterized query.
"""


def write(
    df: _pd.DataFrame,
    table: str,
    database: str = None,
    connection_string: str = None,
    driver: str = 'Microsoft Access Driver (*.mdb, *.accdb)',
    password: str = None,
    action: str = 'INSERT',
    columns: _Union[str, list] = None,
) -> None:
    """
    Write data to a Microsoft Access database.

    >>> from wrangles.connectors import access
    >>> access.write(df, database='database.accdb', table='table')

    :param df: Pandas Dataframe to be written.
    :param table: Table to be exported to.
    :param database: Access database file path. Not required if connection_string is supplied.
    :param connection_string: Full ODBC connection string. If provided, database, driver, and password are ignored.
    :param driver: ODBC driver name. Defaults to Microsoft Access Driver (*.mdb, *.accdb).
    :param password: Optional database password.
    :param action: INSERT appends, REPLACE recreates the table, FAIL errors if the table exists. Defaults to INSERT.
    :param columns: (Optional) Subset of the columns to be written. If not provided, all columns will be output.
    """
    target = database or connection_string
    _logging.info(f": Writing data to Microsoft Access :: {target} / {table}")

    action = action.upper()
    if action not in ('INSERT', 'REPLACE', 'FAIL'):
        raise ValueError('Invalid action. Expected INSERT, REPLACE, or FAIL.')

    if columns is not None:
        columns = _wildcard_expansion(df.columns, columns)
        df = df[columns]

    conn_string = _connection_string(database, connection_string, driver, password)
    with _pyodbc.connect(conn_string) as conn:
        cursor = conn.cursor()
        exists = _table_exists(cursor, table)

        if action == 'FAIL' and exists:
            raise ValueError(f"Table already exists: {table}")
        if action == 'REPLACE' and exists:
            cursor.execute(f"DROP TABLE {_quote_identifier(table)}")
            exists = False
        if not exists:
            _create_table(cursor, table, df)

        if not df.empty:
            table_name = _quote_identifier(table)
            column_names = ', '.join(_quote_identifier(column) for column in df.columns)
            placeholders = ', '.join('?' for _ in df.columns)
            sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
            cursor.executemany(sql, df.where(_pd.notnull(df), None).itertuples(index=False, name=None))

        conn.commit()


_schema['write'] = """
type: object
description: Export data to a Microsoft Access Database
required:
  - table
properties:
  database:
    type: string
    description: Access database file path. Not required if connection_string is supplied.
  connection_string:
    type: string
    description: Full ODBC connection string. If provided, database, driver, and password are ignored.
  driver:
    type: string
    description: ODBC driver name. Defaults to Microsoft Access Driver (*.mdb, *.accdb).
  password:
    type: string
    description: Optional database password.
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
    command: _Union[str, list],
    database: str = None,
    connection_string: str = None,
    driver: str = 'Microsoft Access Driver (*.mdb, *.accdb)',
    password: str = None,
    params: _Union[list, tuple] = None,
) -> None:
    """
    Run a command on a Microsoft Access database.

    >>> wrangles.connectors.access.run(
    >>>    database='database.accdb',
    >>>    command='<SQL COMMAND>'
    >>> )

    :param command: SQL command or a list of SQL commands to execute.
    :param database: Access database file path. Not required if connection_string is supplied.
    :param connection_string: Full ODBC connection string. If provided, database, driver, and password are ignored.
    :param driver: ODBC driver name. Defaults to Microsoft Access Driver (*.mdb, *.accdb).
    :param password: Optional database password.
    :param params: Variables to pass to a parameterized query.
    """
    target = database or connection_string
    _logging.info(f": Executing Microsoft Access Command :: {target}")

    if isinstance(command, str):
        command = [command]

    conn_string = _connection_string(database, connection_string, driver, password)
    with _pyodbc.connect(conn_string) as conn:
        cursor = conn.cursor()
        for sql in command:
            cursor.execute(sql, params or ())
        conn.commit()


_schema['run'] = r"""
type: object
description: Run a command against a Microsoft Access Database
required:
  - command
properties:
  database:
    type: string
    description: Access database file path. Not required if connection_string is supplied.
  connection_string:
    type: string
    description: Full ODBC connection string. If provided, database, driver, and password are ignored.
  driver:
    type: string
    description: ODBC driver name. Defaults to Microsoft Access Driver (*.mdb, *.accdb).
  password:
    type: string
    description: Optional database password.
  command:
    type:
      - string
      - array
    description: SQL command or a list of SQL commands to execute
  params:
    type: array
    description: Variables to pass to a parameterized query.
"""
