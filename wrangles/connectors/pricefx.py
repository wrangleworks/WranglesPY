"""
Connector for PriceFx
"""
import pandas as _pd
import requests as _requests
import logging as _logging

# TODO: batch large data sets?
# read data?
# execute stuff?
# DataSources - need a 'flush'?
# JWT auth rather than basic


_schema = {}


# PriceFx table identification codes
_target_types = {
    'products': 'P',
    'product extensions': 'PX',
    'customers': 'C',
    'customer extensions': 'CX'
}


def write(df: _pd.DataFrame, host: str, partition: str, target: str, user: str, password: str, columns: list = None) -> None:
    """
    
    """
    _logging.info(f": Exporting Data :: {host} / {partition} / {target}")

    if columns is not None: df = df[columns]

    field_map = {}
    url = f"https://{host}/pricefx/{partition}/fetch/{_target_types.get(target.lower(), target)}AM"
    field_map_list = _requests.post(url, auth=(f'{partition}/{user}', password)).json()['response']['data']
    for row in field_map_list:
      field_map[row['label']] = row['fieldName']

    header_list = df.columns.tolist()
    header_list = [field_map.get(header, header) for header in header_list]

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

    url = f"https://{host}/pricefx/{partition}/loaddata/{_target_types.get(target.lower(), target)}"

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
    description: Target data set
    enum:
      - Products
      - Product Extensions
      - Customers
      - Customer Extensions
  columns:
    type: array
    description: A list of the columns to write to the table.
"""