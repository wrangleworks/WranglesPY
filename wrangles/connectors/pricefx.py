"""
Connector for PriceFx
"""
import pandas as _pd
import requests as _requests
import logging as _logging
import json as _json


# TODO: JWT auth rather than basic auth
# TODO: enable use of labels for read criteria as well as column Ids


_schema = {}


# PriceFx table identification codes
_target_types = {
    'products': 'P',
    'product extensions': 'PX',
    'product references': 'PXREF',
    'product competition': 'PCOMP',
    'customers': 'C',
    'customer extensions': 'CX',
    'data source': 'DS',
    'company parameters': 'LT',
}

_lookup_table_codes = {
    'MATRIX': {
        'MATRIX': 'MLTV',
        'MATRIX2': 'MLTV2',
        'MATRIX3': 'MLTV3',
        'MATRIX4': 'MLTV4',
        'MATRIX5': 'MLTV5',
        'MATRIX6': 'MLTV6'
    },
    'JSON': {
        'JSON': 'JLTV',
        'JSON2': 'JLTV2'
    },
    'SIMPLE': {
        'STRING': 'LTV',
        'REAL': 'LTV'
    }
}

_meta_tables = {
    'C': 'CAM',
    'CX': 'CXAM',
    'P': 'PAM',
    'PX': 'PXAM',
    'MLTV': 'MLTVM',
    'MLTV2': 'MLTVM',
    'MLTV3': 'MLTVM',
    'MLTV4': 'MLTVM',
    'MLTV5': 'MLTVM',
    'MLTV6': 'MLTVM',
    'JLTV': 'JLTVM',
    'JLTV2': 'JLTVM'
}


def _get_field_map(host: str, partition: str, target_code: str, user: str, password: str, to_label: bool = True, source = None) -> dict:
    """
    Generate a mapping of pricefx field labels to ids for master tables

    :param host: The host
    :param partition: The partition
    :param target_code: The code corresponding to the data type e.g. Products = P
    :param user: The user to connect as
    :param password: Password for the user
    :param to_label: If true, return id -> label, else label -> id
    :returns: A dictionary of the field mappings
    """
    field_map = {}
    url = f"https://{host}/pricefx/{partition}/fetch/{target_code}AM"
    field_map_list = _requests.post(url, auth=(f'{partition}/{user}', password)).json()['response']['data']
    for row in field_map_list:
        # Add labels and labelTranslations to map for alternative lookups
        if source is None or source == row['name']:
            if to_label:
                field_map[row['fieldName']] = row['label']
            else:
                field_map[row['label']] = row['fieldName']
            for _, val in _json.loads(row.get("labelTranslations", "{}")).items():
                if to_label:
                    field_map[row['fieldName']] = val
                else:
                    field_map[val] = row['fieldName']

    return field_map


def read(
    host: str,
    partition: str,
    target: str,
    user: str,
    password: str,
    columns: list = None,
    source: str = None,
    criteria: dict = None,
    batch_size: int = 10000
) -> _pd.DataFrame:
    """
    Import data from a PriceFx instance.

    >>> from wrangles.connectors import pricefx
    >>> df = pricefx.read(host='node.pricefx.eu', partition='partition', target='Products', user='user', password='password')

    :param host: Hostname of the instance
    :param partition: Partition to write to
    :param target: Type of Data. Products, Customers, Data Source, etc. For Data Sources or Product/Customer Extensions a source must also be provided.
    :param user: User with access to write
    :param password: Password of user
    :param columns: (Optional) Specify which columns to include
    :param source: If the data type is a Data Source or Extension, set the specific table
    :param batch_size: Queries are broken into batches for large data sets. Set the size of the batch. If you're having trouble with timeouts, try reducing this. Default 10,000.
    :param criteria: (Optional) Filter the returned data set
    """
    _logging.info(f": Importing Data :: {host} / {partition} / {target}")

    # Convert target name to code
    source_code = _target_types.get(target.lower(), target)

    # Generate the appropriate API call info for the requested data
    if source_code == 'DS':
        url = f"https://{host}/pricefx/{partition}/datamart.getfcs/DMDS"
        payload = {
            "data": {
                "_constructor": "AdvancedCriteria",
                "operator": "and",
                "criteria": [
                    {
                        "fieldName": "uniqueName",
                        "operator": "equals",
                        "value": source
                    }
                ]
            }
        }
        response = _requests.post(url, json=payload, auth=(f'{partition}/{user}', password))
        typed_id = response.json()["response"]["data"][0]['typedId']

        url = f"https://{host}/pricefx/{partition}/datamart.fetchnocount/{typed_id}"

    elif source_code == 'PX':
        url = f"https://{host}/pricefx/{partition}/productmanager.fetch/*/PX/{source}"

    elif source_code == 'PXREF':
        url = f"https://{host}/pricefx/{partition}/productmanager.fetchproductxref"

    elif source_code == 'PCOMP':
        url = f"https://{host}/pricefx/{partition}/productmanager.fetchproductcompetition"

    elif source_code == 'P':
        url = f"https://{host}/pricefx/{partition}/productmanager.fetchformulafilteredproducts"

    elif source_code == 'C':
        url = f"https://{host}/pricefx/{partition}/customermanager.fetchformulafilteredcustomers"

    elif source_code == 'CX':
        url = f"https://{host}/pricefx/{partition}/customermanager.fetch/*/CX/{source}"

    elif source_code == 'LT' and not source:
        # Requested company parameters, but no source provided
        # then get list of all tables
        url = f"https://{host}/pricefx/{partition}/lookuptablemanager.fetch"

    elif source_code == 'LT' and source:
        # Requested company parameters + a specific table
        # Look up table data
        df_tables = read(host, partition, target, user, password)

        url = None
        # Get ID for source requested
        for row in df_tables.to_dict('records'):
            if row['uniqueName'] == source:
                url = f"https://{host}/pricefx/{partition}/lookuptablemanager.fetch/{row['id']}"
                break

        if not url:
            raise ValueError('Company Parameter table not found.')

    payload = {}
    params = {}

    # If user has specified a set of filters, apply those
    if criteria:
        payload = {
            "data": {
                "_constructor": "AdvancedCriteria",
                "operator": "and",
                "criteria": criteria
            }
        }

    continue_query = True
    i = 0
    df = None

    # Query for data in batches
    while continue_query:
        payload['startRow'] = i
        payload['endRow'] = i + batch_size

        response = _requests.post(url, auth=(f'{partition}/{user}', password), params=params, json=payload)
        if str(response.status_code)[0] != '2':
            raise RuntimeError('Failed to read data. Check your input settings. If using column/table lables, consider trying names instead.')

        if df is None:
            df = _pd.json_normalize(response.json()["response"]["data"]).fillna("")
        else:
            df = _pd.concat([df, _pd.json_normalize(response.json()["response"]["data"]).fillna("")])

        if len(df) % batch_size or len(df) == 0:
            # Reached the end of the batch - stop looping
            continue_query = False

        i += batch_size

    if source_code in ['P', 'PX', 'C', 'CX']:
        df = df.rename(
            columns=_get_field_map(host, partition, source_code, user, password, source=source)
        )

    # Reduce to user's columns if specified
    if columns is not None: df = df[columns]

    return df

_schema['read'] = """
type: object
description: Import data from a PriceFx instance.
required:
  - host
  - partition
  - target
  - user
  - password
properties:
  host:
    type: string
    description: Hostname e.g. example.pricefx.com
  partition:
    type: string
    description: Partition
  user:
    type: string
    description: The user to connect as
  password:
    type: string
    description: Password for the specified user
  target:
    type: string
    description: Type of Data. Products, Customers, Data Source, etc. For Data Sources or Product/Customer Extensions a source must also be provided.
    enum:
      - Products
      - Product Extensions
      - Customers
      - Customer Extensions
      - Data Source
  columns:
    type: array
    description: Specify which columns to include
  source:
    type: string
    description: If the data type is a Data Source or Extension, set the specific table.
  batch_size:
    type: integer
    description: Queries are broken into batches for large data sets. Set the size of the batch. If you're having trouble with timeouts, try reducing this. Default 10,000.
  critera:
    type: array
    description: Filter the returned data set.
"""


def write(
    df: _pd.DataFrame,
    host: str,
    partition: str,
    target: str,
    user: str,
    password: str,
    columns: list = None,
    source: str = None,
    autoflush: bool = True
) -> None:
    """
    Export data to a PriceFx instance. Column names must match the ID or label of the respective pricefx columns.

    >>> from wrangles.connectors import pricefx
    >>> pricefx.write(df, host='node.pricefx.eu', partition='partition', target='Products', user='user', password='password')

    :param df: Dataframe to be exported
    :param host: Hostname of the instance
    :param partition: Partition to write to
    :param target: Target for the data. Products, Customers, Data Source, etc.
    :param user: User with access to write
    :param password: Password of user
    :param columns: (Optional) Subset of the columns to be written. If not provided, all columns will be output.
    :param source: Required for Data Sources. Set the specific table.
    :param autoflush: Only relevant for Data Sources. If true, automatically trigger a flush after writing the data to a Data Source. Default True.
    """
    _logging.info(f": Exporting Data :: {host} / {partition} / {target}")

    # Convert target name to code
    target_code = _target_types.get(target.lower(), target)

    # Reduce to user's columns if specified
    if columns is not None: df = df[columns]

    # LookupTables (LT) have multiple specific subtypes.
    # Find the specific code for the user's requested table.
    if target_code == 'LT':
        # Look up table data
        df_tables = read(host, partition, target, user, password)

        # Get ID for source requested
        for row in df_tables.to_dict('records'):
            if row['uniqueName'] == source:
                target_code = _lookup_table_codes[row['type']][row['valueType']]
                source = row['id']
                break

    # Translate column labels to IDs if we have a meta table to reference
    meta_table = _meta_tables.get(target_code, None)
    if meta_table:
        field_map = {}
        url = f"https://{host}/pricefx/{partition}/fetch/{meta_table}"
        payload = { 'startRow': 0, 'endRow': 100000 }
        response = _requests.post(url, auth=(f'{partition}/{user}', password), json=payload)
        for row in response.json()['response']['data']:
            # Skip if this isn't the right lookup table
            if meta_table in ['JLTVM', 'MLTVM'] and row['lookupTableId'] != source:
                continue

            # Skip is this isn't the right extension table
            if meta_table in ['PXAM', 'CXAM'] and row['name'] != source:
                continue

            # Add labels and labelTranslations to map for alternative lookups
            field_map[row['label']] = row['fieldName']
            for _, val in _json.loads(row.get("labelTranslations", "{}")).items():
                field_map[val] = row['fieldName']

        df = df.rename(columns=field_map)

    # If user hasn't explicitly defined the extension table then add it here
    if target_code in ['PX', 'CX'] and 'name' not in df.columns:
        df['name'] = source

    # Upload to target
    if target_code == 'DS':
        # Data Source requires upload + trigger a 'flush'
        # Upload new data
        url = f"https://{host}/pricefx/{partition}/datamart.loaddata/{source}"
        # Create payload
        payload = {
            "data": {
                "header": df.columns.tolist(),
                "options": {
                    "direct2ds": False,
                    "detectJoinFields": True,
                    "maxJoinFieldsLengths": []
                },
                "data": df.values.tolist()
            }
        }
        response = _requests.post(url, json=payload, auth=(f'{partition}/{user}', password))

        # If the response is not 2XX then raise an error
        if str(response.status_code)[0] != '2':
            raise ValueError(f"Status Code {response.status_code} - {response.reason}\n{_json.loads(response.text)['response']['data']}")

        # Trigger flush
        if autoflush:
            url = f"https://{host}/pricefx/{partition}/datamart.rundataload"
            payload = {
                "data": {
                    "type": "DS_FLUSH",
                    "targetName": f"DMDS.{source}",
                    "sourceName": f"DMF.{source}"
                }
            }
            response = _requests.post(url, json=payload, auth=(f'{partition}/{user}', password))

            # If the response is not 2XX then raise an error
            if str(response.status_code)[0] != '2':
                raise ValueError(f"Status Code {response.status_code} - {response.reason}\n{_json.loads(response.text)['response']['data']}")

    elif target.lower() == 'company parameters':
        df['lookupTable'] = source

        url = f"https://{host}/pricefx/{partition}/lookuptablemanager.loaddata/{target_code}"

        # Create payload
        payload = {
            "data": {
                "header": df.columns.tolist(),
                "data": df.values.tolist()
            }
        }

        response = _requests.post(url, json=payload, auth=(f'{partition}/{user}', password))
        # If the response is not 2XX then raise an error
        if str(response.status_code)[0] != '2':
            raise ValueError(f"Status Code {response.status_code} - {response.reason}\n{_json.loads(response.text)['response']['data']}")

    else:
        url = f"https://{host}/pricefx/{partition}/loaddata/{target_code}"
        payload = {
            "data": {
                "header": df.columns.tolist(),
                "options": {
                    "direct2ds": False,
                    "detectJoinFields": True,
                    "maxJoinFieldsLengths": []
                },
                "data": df.values.tolist()
            }
        }
        response = _requests.post(url, json=payload, auth=(f'{partition}/{user}', password))
        # If the response is not 2XX then raise an error
        if str(response.status_code)[0] != '2':
            raise ValueError(f"Status Code {response.status_code} - {response.reason}\n{_json.loads(response.text)['response']['data']}")


_schema['write'] = """
type: object
description: Write data to a PriceFx instance. The names of the columns must match to the names within PriceFx.
required:
  - host
  - partition
  - target
  - user
  - password
properties:
  host:
    type: string
    description: Hostname e.g. example.pricefx.com
  partition:
    type: string
    description: Partition
  user:
    type: string
    description: The user to connect as
  password:
    type: string
    description: Password for the specified user
  target:
    type: string
    description: Target for the data. Products, Customers, Data Source, etc.
    enum:
      - Company Parameters
      - Customers
      - Customer Extensions
      - Data Source
      - Products
      - Product Extensions
      - Product References
      - Product Competition
  columns:
    type: array
    description: A list of the columns to write to the table.
  source:
    type: string
    description: Required for Data Sources. Set the specific table.
  autoflush:
    type: boolean
    description: >-
      Only relevant for Data Sources. If true, automatically
      trigger a flush after writing the data to a Data Source. Default True.
"""