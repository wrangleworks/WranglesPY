"""
Connector for PriceFx
"""
import pandas as _pd
import requests as _requests
import logging as _logging
import json as _json


# TODO: JWT auth rather than basic auth


_schema = {}


# PriceFx table identification codes
_target_types = {
    'products': 'P',
    'product extensions': 'PX',
    'customers': 'C',
    'customer extensions': 'CX',
    'data source': 'DS'
}


def read(host: str, partition: str, source: str, user: str, password: str, columns: list = None, data_source: str = None) -> _pd.DataFrame:
    """
    Import data from a PriceFx instance.

    >>> from wrangles.connectors import pricefx
    >>> df = pricefx.read(host='node.pricefx.eu', partition='partition', source='Products', user='user', password='password')

    :param host: Hostname of the instance
    :param partition: Partition to write to
    :param source: Source of the data. Products, Customers, Data Source, etc.
    :param user: User with access to write
    :param password: Password of user
    :param columns: (Optional) Subset of the columns to be written. If not provided, all columns will be output.
    :param data_source: If the source is a Data Source, set the specific table.
    """
    # TODO: read master tables
    # TODO: Batch calls for larger tables
    _logging.info(f": Importing Data :: {host} / {partition} / {source}")

    url = f"https://{host}/pricefx/{partition}/datamart.getfcs/DMDS"
    payload = {
        "data": {
            "_constructor": "AdvancedCriteria",
            "operator": "and",
            "criteria": [
                {
                    "fieldName": "uniqueName",
                    "operator": "equals",
                    "value": data_source
                }
            ]
        }
    }
    response = _requests.post(url, json=payload, auth=(f'{partition}/{user}', password))
    typed_id = response.json()["response"]["data"][0]['typedId']

    url = f"https://{host}/pricefx/{partition}/datamart.fetchnocount/{typed_id}"
    response = _requests.post(url, auth=(f'{partition}/{user}', password))
    df = _pd.json_normalize(response.json()["response"]["data"]).fillna("")
    
    # Reduce to user's columns if specified
    if columns is not None: df = df[columns]

    return df

_schema['read'] = """
type: object
description: Import data from a PriceFx instance.
required:
  - host
  - partition
  - source
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
  source:
    type: string
    description: Source of the data. Products, Customers, Data Source, etc.
    enum:
      - Products
      - Product Extensions
      - Customers
      - Customer Extensions
      - Data Source
  columns:
    type: array
    description: Specify which columns to include
  data_source:
    type: string
    description: If the source is a Data Source, set the specific table.
"""


def write(df: _pd.DataFrame, host: str, partition: str, target: str, user: str, password: str, columns: list = None, data_source: str = None) -> None:
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
    :param data_source: If the target is a Data Source, set the specific table.
    """
    # TODO: batch large data sets?

    _logging.info(f": Exporting Data :: {host} / {partition} / {target}")

    # Convert target name to code
    target_code = _target_types.get(target.lower(), target)

    # Reduce to user's columns if specified
    if columns is not None: df = df[columns]
    
    # Get list of headers
    header_list = df.columns.tolist()

    # If not a data_source, convert column labels to IDs
    if target_code not in ['DS']:
      field_map = {}
      url = f"https://{host}/pricefx/{partition}/fetch/{target_code}AM"
      field_map_list = _requests.post(url, auth=(f'{partition}/{user}', password)).json()['response']['data']
      for row in field_map_list:
        # Add labels and labelTranslations to map for alternative lookups
        field_map[row['label']] = row['fieldName']
        for _, val in _json.loads(row["labelTranslations"]).items():
          field_map[val] = row['fieldName']
      
      header_list = [field_map.get(header, header) for header in header_list]

    # Create payload
    payload = {
        "data": {
            "header": header_list,
            "options": {
                "direct2ds": False,
                "detectJoinFields": True,
                "maxJoinFieldsLengths": []
            },
            "data": df.values.tolist()
        }
    }

    # Upload to target
    if target_code in ['DS']:
      # Data Source requires upload + trigger a 'flush'
      url = f"https://{host}/pricefx/{partition}/datamart.loaddata/{data_source}"
      _requests.post(url, json=payload, auth=(f'{partition}/{user}', password))
      url = f"https://{host}/pricefx/{partition}/datamart.rundataload"
      payload = {
        "data": {
          "type": "DS_FLUSH",
          "targetName": f"DMDS.{data_source}",
          "sourceName": f"DMF.{data_source}"
        }
      }
      _requests.post(url, json=payload, auth=(f'{partition}/{user}', password))

    else:
      url = f"https://{host}/pricefx/{partition}/loaddata/{target_code}"
      _requests.post(url, json=payload, auth=(f'{partition}/{user}', password))
    

_schema['write'] = """
type: object
description: Write data to a PriceFx instance. The names of the columns must match to the names within PriceFx.
required:
  - host
  - partition
  - target
  - user
  - password
  - columns
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
      - Products
      - Product Extensions
      - Customers
      - Customer Extensions
      - Data Source
  columns:
    type: array
    description: A list of the columns to write to the table.
  data_source:
    type: string
    description: If the target is a Data Source, set the specific table.
"""