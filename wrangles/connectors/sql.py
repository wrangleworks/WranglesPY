"""
Connector to read/write from SQL Database.
"""
import pandas as _pd
from typing import Union


def input(type: str, host: str, user: str, password: str, command: str, port = None, database: str = '', fields: Union[str, list] = None):
    """
    Import data from a SQL database.

    :param type: Type of SQL database - mssql or postgres
    :param host: Hostname or IP of the database
    :param user: User with access to the database
    :param password: Password of user
    :param database: Database to be exported to
    :param table: Table to be exported to
    :param port: (Optional) If not provided, the default port for the respective SQL type will be used
    :return: Pandas Dataframe of the imported data
    """
    if type == 'mssql':
        conn = f"mssql+pymssql://{user}:{password}@{host}:{port or 1433}/{database}?charset=utf8"
    elif type == 'postgres':
        conn = f"postgresql+psycopg2://{user}:{password}@{host}:{port or 5432}/{database}"
    # TODO: Add mysql
    else:
        raise ValueError('Unknown SQL Database type. Supported types are mssql and postgres.')

    df = _pd.read_sql(command, conn)

    if fields is not None: df = df[fields]
    
    return df


def output(df, type: str, host: str, database: str, table: str, user: str, password: str, action = 'INSERT', port = 0, fields: Union[str, list] = None):
    """
    Export data to a SQL database.

    :param df: Dataframe to be exported
    :param type: Type of SQL database - mssql or postgres
    :param host: Hostname or IP of the database
    :param database: Database to be exported to
    :param table: Table to be exported to
    :param user: User with access to the database
    :param password: Password of user
    :param action: Only INSERT is supported at this time, defaults to INSERT
    :param port: (Optional) If not provided, the default port for the respective SQL type will be used
    :param fields: (Optional) Subset of the fields to be written. If not provided, all fields will be output
    """
    # Create appropriate connection string
    if type == 'mssql':
        conn = f"mssql+pymssql://{user}:{password}@{host}:{port or 1433}/{database}?charset=utf8"
    elif type == 'postgres':
        conn = f"postgresql+psycopg2://{user}:{password}@{host}:{port or 5432}/{database}"
    # TODO: Add mysql
    else:
        raise ValueError('Unknown SQL Database type. Supported types are mssql and postgres.')

    # Select only specific fields if user requests them
    if fields is not None: df = df[fields]

    if action.upper() == 'INSERT':
        df.to_sql(table, conn, if_exists='append', index=False, method='multi', chunksize=1000)
    else:
        # TODO: Add UPDATE AND UPSERT
        raise ValueError('UPDATE and UPSERT are not implemented yet.')
