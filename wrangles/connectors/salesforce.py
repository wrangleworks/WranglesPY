"""
Sample:

read:
  - salesforce:
      instance: 
      user: 
      password: 
      token: 
      object: Contact
      command: |
        SELECT Id, Email, Name
        FROM Contact

write:
  - salesforce:
      instance: 
      user: 
      password: 
      token: 
      object: Contact
      id: Id
"""
from simple_salesforce import (
    Salesforce as _Salesforce,
    format_soql as _format_soql
)
import pandas as _pd
import logging as _logging


_schema = {}


def read(
    instance: str,
    user: str,
    password: str,
    token: str,
    object: str,
    command: str,
    columns: list = None,
    params: dict = {},
    domain: str = None
) -> _pd.DataFrame:
    """
    Read data from Salesforce

    >>> from wrangles.connectors import salesforce
    >>> df = salesforce.read(instance='sf.domain', object='object', user='user', password='password', token='token', command='SELECT Id, Name FROM Contact')

    :param instance: The salesforce instance to read from. e.g. <custom>.my.salesforce.com
    :param user: User with read permission
    :param password: Password for the user
    :param token: Security token for the user
    :param object: Object to read data from e.g. Contact
    :param command: SOQL query
    :param columns: (Optional) Subset of the columns to be read. If not provided, all columns will be included
    :param params: (Optional) Parameters to be used in the SOQL query
    :param domain: (Optional) Use test to connect to a sandbox instance
    :return: A Pandas dataframe of the imported data.
    """
    _logging.info(f": Importing Data :: {instance} /  {object}")

    sf = _Salesforce(
        instance=instance,
        username=user,
        password=password,
        security_token=token,
        domain=domain
    )

    sf_object = getattr(sf.bulk, object)

    if params:
        command = _format_soql(command, **params)
    
    responses = sf_object.query(command, lazy_operation=True)

    results = []
    for response in responses:
        results.extend(response)

    df = _pd.DataFrame(results).drop('attributes',axis=1)

    # Select only specific columns if user requests them
    if columns is not None: df = df[columns]

    return df

_schema['read'] = """
type: object
description: Import data from Salesforce
required:
  - instance
  - user
  - password
  - token
  - object
  - command
properties:
  instance:
    type: string
    description: The salesforce instance to read from. e.g. <custom>.my.salesforce.com
  user:
    type: string
    description: User with read permission
  password:
    type: string
    description: Password for the user
  token:
    type: string
    description: Security token for the user
  object:
    type: string
    description: Object to read data from e.g. Contact
  command:
    type: string
    description: SOQL query
  columns:
    type: array
    description: Subset of the columns to select
  params:
    type: object
    description: >-
      (Optional) Parameters to be used in the SOQL query
      Use {my_key} in the command to insert a parameter.
  domain:
    type: string
    description: (Optional) Use test to connect to a sandbox instance.
"""


def write(
    df: _pd.DataFrame,
    instance: str,
    object: str,
    id: str,
    user: str,
    password: str,
    token: str,
    columns: list = None,
    domain: str = None
) -> None:
    """
    Write data to Salesforce.

    >>> from wrangles.connectors import salesforce
    >>> salesforce.write(df, instance='sf.domain', object='object', id='Id', user='user', password='password', token='token')

    :param df: Dataframe to be written to a file
    :param instance: The salesforce instance to read from. e.g. <custom>.my.salesforce.com
    :param object: Object to upload to data to e.g. Contact
    :param id: Id field. If the Id exists and is provided, the record will be updated, otherwise inserted.
    :param user: User with write permission
    :param password: Password for the user
    :param token: Security token for the user
    :param columns: (Optional) A subset of the columns to be written
    :param domain: (Optional) Use test to connect to a sandbox instance
    """
    # Select only specific columns if user requests them
    if columns is not None: df = df[columns]

    sf = _Salesforce(
        instance=instance,
        username=user,
        password=password,
        security_token=token,
        domain=domain
    )
    getattr(sf.bulk, object).upsert(df.to_dict('records'), id)

    # TODO: the response provides a success/failure for each individual record. React appropriately to notify user of failures.

_schema['write'] = """
type: object
description: Write data to Salesforce
required:
  - instance
  - user
  - password
  - token
  - object
  - id
properties:
  instance:
    type: string
    description: The salesforce instance to write to e.g. <custom>.my.salesforce.com
  user:
    type: string
    description: User with write permission
  password:
    type: string
    description: Password for the user
  token:
    type: string
    description: Security token for the user
  object:
    type: string
    description: Object to write the data to e.g. Contact
  id:
    type: string
    description: Indicate the Id field. If the Id exists and is provided, the record will be updated, otherwise inserted.
  columns:
    type: array
    description: (Optional) A subset of the columns to be written
  domain:
    type: string
    description: (Optional) Use test to connect to a sandbox instance
"""
