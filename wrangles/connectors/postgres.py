"""
Connector to read/write from a PostgreSQL Database.
"""
import pandas as _pd
from typing import Union as _Union
import logging as _logging


def read(host: str, user: str, password: str, command: str, port = 5432, database: str = '', fields: _Union[str, list] = None) -> _pd.DataFrame:
    """
    Import data from a PostgreSQL database.

    >>> from wrangles.connectors import postgres
    >>> df = postgres.read(host='sql.domain', user='user', password='password', command='SELECT * FROM table')

    :param host: Hostname or IP of the database
    :param user: User with access to the database
    :param password: Password of user
    :param command: SQL command or table name
    :param port: (Optional) If not provided, the default port will be used
    :param database: (Optional) Database to be queried
    :param fields: (Optional) Subset of fields to be returned. This is less efficient than specifying in the SQL command.
    :return: Pandas Dataframe of the imported data
    """
    _logging.info(f": Importing Data :: {host}")

    conn = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    df = _pd.read_sql(command, conn)

    if fields is not None: df = df[fields]
    
    return df


def write(df: _pd.DataFrame, host: str, database: str, table: str, user: str, password: str, action = 'INSERT', port = 5432, fields: _Union[str, list] = None) -> None:
    """
    Export data to a PostgreSQL database.

    >>> from wrangles.connectors import postgres
    >>> postgres.write(df, host='sql.domain', database='database', table='table', user='user', password='password')

    :param df: Dataframe to be exported
    :param host: Hostname or IP of the database
    :param database: Database to be exported to
    :param table: Table to be exported to
    :param user: User with access to the database
    :param password: Password of user
    :param action: Only INSERT is supported at this time, defaults to INSERT
    :param port: (Optional) If not provided, the default port will be used
    :param fields: (Optional) Subset of the fields to be written. If not provided, all fields will be output
    """
    _logging.info(f": Exporting Data :: {host}/{table}")

    # Create appropriate connection string
    conn = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

    # Select only specific fields if user requests them
    if fields is not None: df = df[fields]

    if action.upper() == 'INSERT':
        df.to_sql(table, conn, if_exists='append', index=False, method='multi', chunksize=1000)
    else:
        # TODO: Add UPDATE AND UPSERT
        raise ValueError('UPDATE and UPSERT are not implemented yet.')
