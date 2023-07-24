import requests as _requests
import pandas as _pd
import logging as _logging
import jwt as _jwt
from time import time as _time

_schema = {}

# token is going to use while creating authorization header
def _getToken(host, client_id, private_key, certificate_id):
    '''

    params:
       host : Hostname or IP of API--> https://<accountID>.suitetalk.api.netsuite.com
       client_id: created when registering the integration in Netsuite. 
       private_key:created when registering the integration in Netsuite. 
       certificate_id:created when registering the integration in Netsuite. 
    '''

    '''
     jwt token create
     https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_158081952044.html

    '''
    encoded_jwt = _jwt.encode(
        payload={
            "iss": client_id,
            "scope": "rest_webservices,suite_analytics",
            "aud": f"{host}/services/rest/auth/oauth2/v1/token",
            "exp": int(_time()) + 59 * 60,  # maximum now + 60 mins
            "iat": int(_time())
        },
        key=private_key,
        algorithm="RS256",
        headers={
            "typ": "JWT",
            "alg": "PS256",
            "kid": certificate_id
        }

    )
    url = f"{host}/services/rest/auth/oauth2/v1/token"
    '''
    -params:
           grant_type: The value of the grant_type parameter is always client_credentials.
           client_assertion_type: value is always urn:ietf:params:oauth:client-assertion-type:jwt-bearer.
    '''
    params = {
        'grant_type': 'client credential',
        'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
        'client_assertion': encoded_jwt  # generate from client application

    }
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    try:
        response = _requests.post(url=url, params=params, headers=headers)
    except _requests.exceptions.RequestException as e:
        raise SystemExit(e)

    # request body
    data = response.json()
    # token
    token = data['access_token']
    return token


def read(host, path, client_id, private_key, certificate_id, filter=None, limit=1000, offset=0) -> _pd.DataFrame:
    """
    :param host: Hostname or IP of API
    :param path: name of record which which should be extract
    :param filter: it can filter the entire data
    :client_id: created when registering the integration in Netsuite.
    :private_key:created when registering the integration in Netsuite.
    :certificate_id:created when registering the integration in Netsuite.
    :param limit: The limit used to specify the number of results on a single page.
                  Default value is 1000.
    :param offset:The offset used for selecting a specific page of results.
                  Default value is 0.
    :return: Pandas Dataframe of the imported data
    """
    logger = _logging.getLogger()
    logger.setLevel(_logging.DEBUG)
    logger.info(f": Exporting Data :: {host}")

    '''requesting api'''

    url = f"{host}/services/rest/record/v1/{path}"

    # generating token
    token = _getToken(host, client_id, private_key, certificate_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Prefer": "transient",
    }
    # checking filter value is none or not, if it None --> remove from params
    if filter == None:
        params = {
            'limit': limit,
            'offset': offset
        }
    else:
        params = {
            'q': filter,
            'limit': limit,
            'offset': offset
        }

    # paginated response
    # increasing offset value by 1 , so we get data of pages one by one
    # if there is no data on next page then loop terminated

    data = []
    while True:
        params = {
            'q': filter,
            'limit': limit,
            'offset': offset
        }

        response = _requests.get(url=url, headers=headers, params=params)
        if response.json()['items'] is None:
            break
        if response.status_code == '200':
            data.append(response.json())
            offset += 1
        else:
            # error handling
            # https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_156570709583.html
            raise RuntimeError(response.errorDetails)

    # https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_156414087576.html
    # converting json object into pandas dataframe
    df = _pd.json_normalize(data['items'], max_level=0)
    return df


_schema['read'] = """
    type: object
    description: Read data from NetSuite record API
    required:
      - host
      - path
      - client_id
      - private_key
      - certificate_id
    properties:
      host:
        type: string
        description: Hostname of the API provider
            e.g. https://[accountid].suitetalk.api.netsuite.com
      path:
        type: string
        description: Name of record which should be extract
      client_id:
        type: int
        description: Created when registering the integration in Netsuite
      private_key:
        type: int
        description: Created when registering the integration in Netsuite
      certificate_id:
        type: int
        description: Created when registering the integration in Netsuite
      filter:
        type: object
        description: API filters
      limit:
        type: int
        description: The limit used to specify the number of results on a single page.
                  Default value is 1000
      offset:
        type: int
        description: The offset used for selecting a specific page of results.
                  Default value is 0
"""


# defining schema
# _Schema['read'] = """
#         type: object
#         description: Read data from NetSuite
#         required:
#         - host:https://[accountid].suitetalk.api.netsuite.com
#         - path: name of record which should be fetch
#         parameters:
#         -filter
#         -limit: default value 1000
#         -offset: default value 0
#         """


# pytest
class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


def test_read(mocker):
    """
    Test a successful request
    # https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2023.1/index.html#/definitions/customer
    """
    mock_request = mocker.patch('requests.get')
    mock_request.return_value = MockResponse(
        json_data={
            "count": 1,
            "hasMore": True,
            "items": [
                {
                    "endDate": "22-3-2023",
                    "entityId": "100",
                    "firstName": "customer name here",
                    "isAutogeneratedRepresentingEntity": True,
                    "isBudgetApproved": True,
                    "isInactive": True,
                },
            ],
            "links": [
                {
                    "rel": "self",
                    "href": "http://demo123.suitetalk.api.netsuite.com/services/rest/record/v1/customer/107/addressbook"
                }
            ],
            "offset": 10,
            "totalResults": 10
        },
        status_code=200
    )

    df = read(
        host='example.netsuite.com',
        path='stuff',
        filter='select something',

    )
    assert (
            len(df) == 1 and
            df['entityId'][0] == "100"
    )


def test_paginated_response(mocker):
    """
    Test a request that is paginated into multiple responses
    # https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2023.1/index.html#/definitions/customer
    """

    mock_request = mocker.patch('requests.get')
    mock_request.return_value = MockResponse(
        json_data={
            "count": 1,
            "hasMore": True,
            "items": [
                {
                    "endDate": "22-3-2023",
                    "entityId": "100",
                    "firstName": "customer name here",
                    "isAutogeneratedRepresentingEntity": True,
                    "isBudgetApproved": True,
                    "isInactive": True,
                },
            ],
            "links": [
                {
                    "rel": "self",
                    "href": "http://demo123.suitetalk.api.netsuite.com/services/rest/record/v1/customer/107/addressbook"
                }
            ],
            "offset": 10,
            "totalResults": 10
        },
        status_code=200
    )
    assert (

            mock_request.return_value.status_code == 200

    )


def test_failure(mocker):
    """
    Test a request where the user does not provide correct inputs.
   
    https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_156570709583.html
    """

    mock_request = mocker.patch('requests.get')
    mock_request.return_value = MockResponse(
        json_data={

            "type": "https://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.1",
            "title": "Bad Request",
            "status": 400,
            "o:errorDetails": [
                {
                    "detail": "Error while accessing resource: You have entered an Invalid Field Value 9999 for the following field: item",
                    "o:errorCode": "INVALID_CONTENT",
                    "o:errorPath": "item.items[0].item"
                }
            ]
        },
        status_code=400
    )

    assert (
            mock_request.return_value.status_code == 400
    )


def write(host, path, id, data, client_id, private_key, certificate_id, sublist=None):
    """
    :param host: Hostname or IP of API
    :param path: name of record which which should be extract
    :param sublist: The names of sublists on this record. 
                    All sublist lines will be replaced with lines specified in the request. 
                    The names are delimited by comma.
    :param data: request body of paramters.
    :param id: id of one particular customer which should be updated 
    :client_id: created when registering the integration in Netsuite. 
    :private_key:created when registering the integration in Netsuite. 
    :certificate_id:created when registering the integration in Netsuite.
    """
    """
    response body 
    https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2023.1/index.html#/definitions/billingAccount

    api docs
    https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2023.1/index.html#tag-account

    api response error
    https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2023.1/index.html#/definitions/nsError
    
    for upsert opeartion
    https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_156335203191.html

    OAuth 2.0 for REST Web Services
    https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_157780312610.html
    
    
    """
    # this is the upsert operation api--->PUT METHOD
    # it will create user if not exit or if exit then it will update based on id passed
    # it will do both insert & update operation

    url = f"{host}/services/rest/record/v1/{path}/{id}"
    token = _getToken(host, client_id, private_key, certificate_id)
    headers = {
        "Authorization": f"Bearer {token}"
    }
    params = {
        "replace": sublist
    }
    response = _requests.post(url=url, headers=headers, params=params, data=data)
    if response.status_code == 204:
        return response.status_code
    else:
        raise RuntimeError(response.errorDetails)


_schema['write'] = """
    type: object
    description: Read data from NetSuit record API
    required:
      - host
      - path
      - id
      - data
      - client_id
      - private_key
      - certificate_id
    properties:
      host:
        type: string
        description: Hostname of the API provider
            e.g. https://[accountid].suitetalk.api.netsuite.com
      path:
        type: string
        description: name of record which should be extract
      id:
        type: int
        description: detail of name record which should be extract
      data:
        type: object
        description: data to upsert(create/update) record.
      client_id:
        type: int
        description: created when registering the integration in Netsuite
      private_key:
        type: int
        description: created when registering the integration in Netsuite
      certificate_id:
        type: int
        description: created when registering the integration in Netsuite
      sublist:
        type: object
        description: API filters
"""
