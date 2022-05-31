"""
Connector to make http(s) requests
"""
import requests


_schema = {}


def execute(url: str, method:str = "GET", headers: dict = None) -> None:
    requests.request(method=method, url=url, headers=headers)

_schema['execute'] = """
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


# TODO: read and write