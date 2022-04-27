"""
Connector to read/write from a local filesystem
"""
import pandas


def read(params):
    """
    Import a file as defined by user parameters.
    Supports Excel (.xlsx, .xlsx, .xlsm), CSV (.csv, .txt) and JSON (.json) files.
    JSON and CSV may also be gzipped (.csv.gz, .txt.gz, .json.gz) and will be decompressed.

    :param params: Dictionary of parameters to define import
    :return: A Pandas dataframe of the imported data.
    """
    # df = None

    # Add empty parameters dict if user hasn't entered any
    if 'parameters' not in params: params['parameters'] = {}

    # Open appropriate file type
    if params['name'].split('.')[-1] in ['xlsx', 'xlsm', 'xls']:
        if 'dtype' not in params['parameters'].keys(): params['parameters']['dtype'] = 'object'
        df = pandas.read_excel(params['name'], **params['parameters']).fillna('')
    elif params['name'].split('.')[-1] in ['csv', 'txt'] or '.'.join(params['name'].split('.')[-2:]) in ['csv.gz', 'txt.gz']:
        df = pandas.read_csv(params['name'], **params['parameters']).fillna('')
    elif params['name'].split('.')[-1] in ['json'] or '.'.join(params['name'].split('.')[-2:]) in ['json.gz']:
        df = pandas.read_json(params['name'], **params['parameters']).fillna('')

    # If the user specifies only certain fields, only include those
    if 'fields' in params.keys(): df = df[params['fields']]

    return df


def write(df, params):
    """
    Export a file as defined by user parameters.
    Supports Excel (.xlsx, .xls), CSV (.csv, .txt) and JSON (.json) files.
    JSON and CSV may also be gzipped (.csv.gz, .txt.gz, .json.gz) and will be compressed.

    :param df: Dataframe to be written to a file
    :param params: Dictionary of parameters that define the file to write
    """
    # Add empty parameters dict if user hasn't entered any
    if 'parameters' not in params: params['parameters'] = {}

    # Select only specific fields if user requests them
    if 'fields' in params.keys(): df = df[params['fields']]

    # Write appropriate file
    if params['name'].split('.')[-1] in ['xlsx', 'xls']:
        # Default to not including index if user hasn't explicitly requested it
        if 'index' not in params['parameters'].keys(): params['parameters']['index'] = False
        df.to_excel(params['name'], **params['parameters'])
    elif params['name'].split('.')[-1] in ['csv', 'txt'] or '.'.join(params['name'].split('.')[-2:]) in ['csv.gz', 'txt.gz']:
        # Default to not including index if user hasn't explicitly requested it
        if 'index' not in params['parameters'].keys(): params['parameters']['index'] = False
        df.to_csv(params['name'], **params['parameters'])
    elif params['name'].split('.')[-1] in ['json'] or '.'.join(params['name'].split('.')[-2:]) in ['json.gz']:
        df.to_json(params['name'], **params['parameters'])

    # return df