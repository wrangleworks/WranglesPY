"""
Connector to read and write data from Akeneo PIM.

https://www.akeneo.com/

See https://api.akeneo.com/api-reference-index.html
for detailed REST API docs.
"""
import json as _json
import pandas as _pd
import requests as _requests


_schema = {}


def read(
    host: str,
    user: str,
    password: str,
    client_id: str,
    client_secret: str,
    source: str,
    columns: list = None,
    parameters: dict = {}
):
    """
    Read data from an Akeneo PIM

    >>> from wrangles.connectors import akeneo
    >>> df = akeneo.read(
    >>>     host = 'https://akeneo.example.com',
    >>>     user = 'username',
    >>>     password = 'password',
    >>>     client_id = 'generated_id',
    >>>     client_secret = 'generated_secret',
    >>>     source = 'products'
    >>> )

    :param host: Hostname of the Akeneo PIM instance e.g. https://akeneo.example.com
    :param user: User with access to read the data
    :param password: Password for the user
    :param client_id: Client ID. These need to be generated in the PIM.
    :param client_secret: Client Secret
    :param source: Type of data to return
    :param columns: Specify which columns to return
    :param parameters: Set parameters for the query such as filtering the results.
    :return: A Pandas dataframe of the returned results
    """
    # Set to max temporarily
    parameters['limit'] = 100

    # TODO: deal with errors appropriately
    token = _requests.post(
        f"{host}/api/oauth/v1/token",
        auth = (client_id, client_secret),
        json = {
            "username" : user,
            "password" : password,
            "grant_type" : "password"
        }
    ).json()['access_token']
    
    # TODO: Needs to deal with pagination
    data = _requests.get(
        f"{host}/api/rest/v1/{source}",
        params=parameters,
        headers={
            'Accept': 'application/json',
            'Authorization': f"Bearer {token}"
        }
    ).json()['_embedded']['items']
    
    df = _pd.json_normalize(data, max_level=0)

    if columns:
        df = df[columns]
        
    return df


_schema['read'] = """
type: object
description: Read data from an Akeneo PIM
required:
  - host
  - user
  - password
  - client_id
  - client_secret
  - source
properties:
  host:
    type: string
    description: |
        Hostname of the Akeneo PIM instance
        e.g. https://akeneo.example.com
  user:
    type: string
    description: User with access to read the data
  password:
    type: string
    description: Password for the user
  client_id:
    type: string
    description: |
        Client ID. These need to be generated in the PIM.
        See https://api.akeneo.com/documentation/authentication.html
  client_secret:
    type: string
    description: Client Secret
  source:
    type: string
    description: Type of data to return
    enum:
      - products
      - products-uuid
      - product-models
      - media-files
      - published-products
      - families
      - attributes
      - attribute-groups
      - association-types
      - categories
      - channels
      - locales
      - currencies
      - measure-families
      - measurement-families
      - reference-entities
      - reference-entities-media-files
      - asset-families
      - asset-media-files
  columns:
    type: array
    description: Specify which columns to return
  parameters:
    type: object
    description: |
        Set parameters for the query such as filtering the results.
        See the Akeneo query parameters for specifics.
        e.g. https://api.akeneo.com/api-reference.html#get_products for products.
"""


def write(
    df: _pd.DataFrame,
    host: str,
    user: str,
    password: str,
    client_id: str,
    client_secret: str,
    source: str,
    columns: list = None,
) -> None:
    """
    Write data into an Akeneo PIM

    >>> from wrangles.connectors import akeneo
    >>> akeneo.write(
    >>>     df,
    >>>     host = 'https://akeneo.example.com',
    >>>     user = 'username',
    >>>     password = 'password',
    >>>     client_id = 'generated_id',
    >>>     client_secret = 'generated_secret',
    >>>     source = 'products'
    >>> )

    :param host: Hostname of the Akeneo PIM instance e.g. https://akeneo.example.com
    :param user: User with access to read the data
    :param password: Password for the user
    :param client_id: Client ID. These need to be generated in the PIM.
    :param client_secret: Client Secret
    :param source: Type of data to return
    """
    # TODO: handle errors appropriately
    token = _requests.post(
        f"{host}/api/oauth/v1/token",
        auth = (client_id, client_secret),
        json={
            "username" : user,
            "password" : password,
            "grant_type" : "password"
        }
    ).json()['access_token']
    
    # TODO: batch this if required??
    # Create payload for Akeneo
    # JSONL formatted
    payload = '\n'.join([_json.dumps(row) for row in df.to_dict(orient='records')])

    # Upload data
    response = _requests.patch(
        f"{host}/api/rest/v1/{source}",
        headers={
            'Content-type': 'application/vnd.akeneo.collection+json',
            'Authorization': f"Bearer {token}"
        },
        data=payload
    )
    
    # Returning error message if any
    # Looping through response if 200 main response
    if str(response.status_code)[0] == '2':
        list_of_responses = [_json.loads(x) for x in response.text.split('\n')]
        status_error = [x for x in list_of_responses if str(x['status_code'])[0] != '2']
        if status_error:
            raise ValueError(f"Error in the following data:\n{status_error[:5]}")
    else:
        json_response = _json.loads(response.text)
        raise ValueError(f"Status Code: {json_response['code']} Message: {json_response['message']}")


_schema['write'] = """
type: object
description: Write data into an Akeneo PIM
required:
  - host
  - user
  - password
  - client_id
  - client_secret
  - source
properties:
  host:
    type: string
    description: |
        Hostname of the Akeneo PIM instance
        e.g. https://akeneo.example.com
  user:
    type: string
    description: User with access to write the data
  password:
    type: string
    description: Password for the user
  client_id:
    type: string
    description: |
        Client ID. These need to be generated in the PIM.
        See https://api.akeneo.com/documentation/authentication.html
  client_secret:
    type: string
    description: Client Secret
  source:
    type: string
    description: Type of data to write
    enum:
      - products
      - products-uuid
      - product-models
      - families
      - attributes
      - attribute-groups
      - association-types
      - categories
      - channels
      - measurement-families
"""
