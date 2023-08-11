import requests as _requests
import pandas as _pd
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
            # "aud": f"https://{instance_id}.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token",
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
    # url = f"https://{instance_id}.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token"
    '''
    -params:
           grant_type: The value of the grant_type parameter is always client_credentials.
           client_assertion_type: value is always urn:ietf:params:oauth:client-assertion-type:jwt-bearer.
    '''
    params = {
        'grant_type': 'client_credentials',
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


def read(instance_id, client_id, certificate_id, private_key, query):
    encoded_jwt = _jwt.encode(
        payload = {
            "iss": client_id,
            "scope": "rest_webservices,suite_analytics",
            "aud": f"https://{instance_id}.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token",
            "exp": int(_time()) + 59 * 60,
            "iat": int(_time())
        },
        key = private_key,
        algorithm="RS256",
        headers={
            "typ": "JWT",
            "alg": "PS256",
            "kid": certificate_id
        }
    )

    response = _requests.post(
        url=f"https://{instance_id}.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token",
        params={                        
            'grant_type':'client_credentials',
            'client_assertion_type':'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion': encoded_jwt
        },
        headers={'content-type': 'application/x-www-form-urlencoded'}
    )

    token = response.json()['access_token']

    response = _requests.post(
        url = f"https://{instance_id}.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql",
        headers={
            "Authorization": f"Bearer {token}",
            "Prefer": "transient"
        },
        json = {
            "q": query
        }
    )

    return _pd.DataFrame(response.json()['items']).fillna('')


_schema['read'] = """
    type: object
    description: Read data from NetSuite record API
    required:
      - instance_id
      - client_id
      - private_key
      - certificate_id
    properties:
      instance_id:
        type: str
        description: Created when registering the integration in Netsuite
      client_id:
        type: str
        description: Created when registering the integration in Netsuite
      private_key:
        type: str
        description: Created when registering the integration in Netsuite
      certificate_id:
        type: str
        description: Created when registering the integration in Netsuite
      query:
        type: str
        description: SQL query to filter the incoming data
"""


def write(df, host, path, client_id, private_key, certificate_id):
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

    data = df.to_dict(orient='records')

    for row in data:
        id = row['id']
        row.pop('id')
       
        url = f"{host}/services/rest/record/v1/{path}/{id}"
        token = _getToken(host, client_id, private_key, certificate_id)
        headers = {
            "Authorization": f"Bearer {token}"
        }

        response = _requests.patch(url=url, headers=headers, json=row)


_schema['write'] = """
    type: object
    description: Write data to NetSuite 
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
        description: name of record which should be extract
      client_id:
        type: int
        description: created when registering the integration in Netsuite
      private_key:
        type: int
        description: created when registering the integration in Netsuite
      certificate_id:
        type: int
        description: created when registering the integration in Netsuite
"""
