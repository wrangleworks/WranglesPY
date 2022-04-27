"""
Connector to read/write from SQL Database.
"""
import pandas


def read(params):
    """
    Import data from a SQL database.

    :param params: Dictionary of parameters to define import
    :return: Pandas Dataframe of the imported data
    """
    if params['type'] == 'mssql':
        conn = f"mssql+pymssql://{params['user']}:{params['password']}@{params['host']}:{params.get('port', '1433')}/{params.get('database', '')}?charset=utf8"
    elif params['type'] == 'postgres':
        conn = f"postgresql+psycopg2://{params['user']}:{params['password']}@{params['host']}:{params.get('port', '5432')}/{params['database']}"
        pass

    df = pandas.read_sql(params['command'], conn)

    if 'fields' in params.keys(): df = df[params['fields']]
    
    return df