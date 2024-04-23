"""
Connector to make http(s) requests
"""
import requests as _requests
import pandas as _pd
from typing import Union as _Union


def _get_oauth_token(url, method="POST", **kwargs):
    """
    Get an OAuth token from a given URL

    :param url: The URL to make the request to
    :param method: The http method to use. Default POST.
    :return: The OAuth token
    """
    response = _requests.request(url=url, method=method, **kwargs)
    if not response.ok:
        raise RuntimeError(
            f"OAuth request failed with status code {response.status_code}. Response: {response.text}"
        )
    return response.json()['access_token']

_schema = {}


def run(
    url: str,
    method: str = "GET",
    headers: dict = {},
    params: dict = None,
    json: _Union[dict, list] = None,
    oauth: dict = {},
    **kwargs
) -> None:
    """
    Issue a HTTP(S) request e.g. issue a request to a webhook on success or failure.

    :param url: The URL to make the request to
    :param method: The http method to use. Default GET.
    :param headers: Headers to pass as part of the request
    :param params: Pass URL encoded
    :param json: Pass data as a JSON encoded request body.
    :param oauth: Make a request to get an OAuth token prior
      to sending the main request
    """
    if oauth:
        headers["Authorization"] = f"Bearer {_get_oauth_token(**oauth)}"
    
    response = _requests.request(
       method=method,
       url=url,
       headers=headers,
       params=params,
       json=json,
       **kwargs
    )
    if not response.ok:
        raise RuntimeError(
            f"Request failed with status code {response.status_code}. Response: {response.text}"
        )

_schema['run'] = """
type: object
description: Issue a HTTP(S) request e.g. issue a request to a webhook on success or failure.
required:
  - url
properties:
  url:
    type: string
    description: The URL to make the request to
  method:
    type: string
    description: The http method to use. Default GET.
    enum:
      - GET
      - POST
      - PUT
      - PATCH
      - DELETE
      - HEAD
      - OPTIONS
  headers:
    type: object
    description: Headers to pass as part of the request
  params:
    type: object
    description: Pass URL encoded parameters
  json:
    type: object
    description: Pass data as a JSON encoded request body.
  oauth:
    type: object
    required:
      - url
    description: >-
      Make a request to get an OAuth token prior
      to sending the main request
    properties:
      url:
        type: string
        description: The URL to make the request to
      method:
        type: string
        description: The http method to use. Default POST.
        enum:
          - GET
          - POST
          - PUT
          - PATCH
          - DELETE
          - HEAD
          - OPTIONS
      headers:
        type: object
        description: Headers to pass as part of the request
      params:
        type: object
        description: Pass URL encoded parameters
      json:
        type: object
        description: Pass data as a JSON encoded request body.
"""


def read(
    url: str,
    method: str = "GET",
    headers: dict = {},
    params: dict = None,
    json: _Union[dict, list] = None,
    json_key: str = None,
    oauth: dict = {},
    orient: str = "records",
    **kwargs
) -> _pd.DataFrame:
    """
    Read data from a HTTP(S) endpoint.

    :param url: The URL to make the request to
    :param method: The http method to use. Default GET.
    :param headers: Headers to pass as part of the request
    :param params: Pass URL encoded
    :param json: Pass data as a JSON encoded request body.
    :param json_key: Select sub-elements from the response JSON. Multiple levels can be specified with e.g. key1.key2.key3
    :param oauth: Make a request to get an OAuth token prior
        to sending the main request
    :param orient: The format of the JSON to be converted to a dataframe. Default records.
    :return: A pandas DataFrame
    """
    if oauth:
        headers["Authorization"] = f"Bearer {_get_oauth_token(**oauth)}"

    response = _requests.request(
       method=method,
       url=url,
       headers=headers,
       params=params,
       json=json,
       **kwargs
    )
    if not response.ok:
       raise RuntimeError(f"Request failed with status code {response.status_code}. Response: {response.text}")
    
    response_json = response.json()

    if json_key:
      for element in json_key.split('.'):
        response_json = response_json[element]

    if orient == "tight":
        response_json = {
            k.lower(): v
            for k, v in response_json.items()
        }
        df = _pd.DataFrame(
            data=response_json.get("data", None),
            index=response_json.get("index", None),
            columns=response_json.get("columns", None)
        )
    elif orient == "columns":
        df = _pd.DataFrame(response_json)
    elif orient == "records":
        df = _pd.json_normalize(response_json, max_level=0)
    else:
        raise ValueError(f"Unsupported orient value: {orient}")

    return df

_schema['read'] = """
type: object
description: Get data from a HTTP(S) endpoint.
required:
  - url
properties:
  url:
    type: string
    description: The URL to make the request to
  method:
    type: string
    description: The http method to use. Default GET.
    enum:
      - GET
      - POST
      - PUT
      - PATCH
      - DELETE
      - HEAD
      - OPTIONS
  headers:
    type: object
    description: Headers to pass as part of the request
  params:
    type: object
    description: Pass URL encoded parameters
  json:
    type: object
    description: Pass data as a JSON encoded request body.
  json_key:
    type: string
    description: Select sub-elements from the response JSON. Multiple levels can be specified with e.g. key1.key2.key3
  orient:
    type: string
    description: |-
      The format of the JSON to be converted to a dataframe. Default records.
    enum:
      - records
      - columns
      - tight
  oauth:
    type: object
    required:
      - url
    description: >-
      Make a request to get an OAuth token prior
      to sending the main request
    properties:
      url:
        type: string
        description: The URL to make the request to
      method:
        type: string
        description: The http method to use. Default POST.
        enum:
          - GET
          - POST
          - PUT
          - PATCH
          - DELETE
          - HEAD
          - OPTIONS
      headers:
        type: object
        description: Headers to pass as part of the request
      params:
        type: object
        description: Pass URL encoded parameters
      json:
        type: object
        description: Pass data as a JSON encoded request body.
"""


def write(
    df: _pd.DataFrame,
    url: str,
    method: str = "POST",
    headers: dict = {},
    orient: str = "records",
    batch: bool = True,
    oauth: dict = {},
    **kwargs
) -> None:
    """
    Write data to a HTTP(S) endpoint.

    :param df: The DataFrame to be written
    :param url: The URL to make the request to
    :param method: The http method to use. Default POST.
    :param orient: The format of the JSON to send. Default records.
    :param batch: If True, send the entire DataFrame as a single request.
        If False, send each row as a separate request.
        If an integer, send the DataFrame in batches of that size.
    """
    if oauth:
        headers["Authorization"] = f"Bearer {_get_oauth_token(**oauth)}"

    if batch is True:
        response = _requests.request(
            method=method,
            url=url,
            json=df.to_dict(orient=orient),
            **kwargs
        )
        if not response.ok:
            raise RuntimeError(
                f"Request failed with status code {response.status_code}. Response: {response.text}"
            )
    elif batch is False:
        for row in df.to_dict(orient="records"):
            response = _requests.request(method=method, url=url, json=row, **kwargs)
            if not response.ok:
                raise RuntimeError(
                    f"Request failed with status code {response.status_code}. Response: {response.text}"
                )
    elif isinstance(batch, int):
        # Ensure the dataframe is using the default index
        df = df.reset_index(drop=True)
        for i in range(0, len(df), batch):
            response = _requests.request(
                method=method,
                url=url,
                json=df.iloc[i:i+batch].to_dict(orient=orient),
                **kwargs
            )
    else:
        raise ValueError("Batch must be a boolean or an integer")

_schema['write'] = """
type: object
description: Write data to a HTTP endpoint.
required:
  - url
properties:
  url:
    type: string
    description: The URL to make the request to
  method:
    type: string
    description: The http method to use. Default POST.
    enum:
      - GET
      - POST
      - PUT
      - PATCH
      - DELETE
      - HEAD
      - OPTIONS
  headers:
    type: object
    description: Headers to pass as part of the request
  params:
    type: object
    description: Pass URL encoded parameters
  orient:
    type: string
    description: |-
      The format of the JSON to send. Default records.
      For allowed values see:
      https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_json.html#pandas.DataFrame.to_json
    enum:
      - records
      - split
      - index
      - columns
      - values
      - table
  batch:
    type:
      - boolean
      - integer
    description: >-
      If True, send the entire DataFrame as a single request.
      If False, send each row as a separate request.
      If an integer, send the DataFrame in batches of that size.
      default: True
  oauth:
    type: object
    required:
      - url
    description: >-
      Make a request to get an OAuth token prior
      to sending the main request
    properties:
      url:
        type: string
        description: The URL to make the request to
      method:
        type: string
        description: The http method to use. Default POST.
        enum:
          - GET
          - POST
          - PUT
          - PATCH
          - DELETE
          - HEAD
          - OPTIONS
      headers:
        type: object
        description: Headers to pass as part of the request
      params:
        type: object
        description: Pass URL encoded parameters
      json:
        type: object
        description: Pass data as a JSON encoded request body.
"""
