import pandas as _pd
import requests as _requests
import json as _json
import os as _os

# login stuff
client_id = _os.getenv('AKENEO_CLIENT_ID', '...')
secret = _os.getenv('AKENEO_SECRET', '...')
username = _os.getenv('AKENEO_USERNAME', '...')
password = _os.getenv('AKENEO_PASSWORD', '...')

host = 'https://akeneo.wrangle.works/'

payload = {"username" : username, "password" : password, "grant_type" : "password"}
response = _requests.request("POST", host + "api/oauth/v1/token", auth=(client_id, secret), json=payload)
res =  response.json()['access_token']


headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + res
        }
        
# Get the data
data = _json.loads(_requests.get(host + "api/rest/v1/products", headers=headers).text)

# for key, items in data.items():
    

pass

