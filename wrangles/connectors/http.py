"""
Connector to make http(s) requests
"""
import requests as _requests
import pandas as _pd


_schema = {}


def run(url: str, method: str = "GET", headers: dict = None) -> None:
    _requests.request(method=method, url=url, headers=headers)

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
"""


def read(url: str, method: str = "GET", headers: dict = None, json_key: str = None, columns: list = None) -> None:
    response = _requests.request(method=method, url=url, headers=headers)
    response_json = response.json()
    if json_key:
      for element in json_key.split('.'):
        response_json = response_json[element]
    df = _pd.json_normalize(response_json, max_level=0)

    if columns is not None: df = df[columns]

    return df

_schema['read'] = """
type: object
description: Get data from a HTTP endpoint.
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
  json_key:
    type: string
    description: Select sub-elements from the response JSON. Multiple levels can be specified with e.g. key1.key2.key3
  columns:
    type: array
    description: Subset of columns to be returned.
"""


# TODO: write