import pandas as _pd
import requests as _requests
import json as _json

from ..recipe_wrangles import merge


def read(user: str, password: str, host: str, client_id: str, client_secret: str):
    """
    Import data from Akeneo
    """
    payload = {"username" : user, "password" : password, "grant_type" : "password"}
    response = _requests.request("POST", host + "api/oauth/v1/token", auth=(client_id, client_secret), json=payload)
    res =  response.json()['access_token']

    headers = {
                'Accept': 'application/json', # For reading
                'Authorization': 'Bearer ' + res
            }
    
    data = _json.loads(_requests.get(host + "api/rest/v1/products", headers=headers).text)
    number_items = len(data['_embedded']['items'])
    
    akeneo_data = {
        'identifier': [],
        'family': [],
        'categories': [],
        'groups': [],
    }
    # # Getting data
    for item_index in range(number_items):
        akeneo_data['identifier'].append(data['_embedded']['items'][item_index]['identifier'])
        akeneo_data['family'].append(data['_embedded']['items'][item_index]['family'])
        akeneo_data['categories'].append(data['_embedded']['items'][item_index]['categories'])
        akeneo_data['groups'].append(data['_embedded']['items'][item_index]['groups'])
        
        # Further extraction needed for values (contains attributes)
        for attr, attr_data in data['_embedded']['items'][item_index]['values'].items():
            if akeneo_data.get(attr, "") == "":
                akeneo_data[attr] = []
                akeneo_data[attr].append(attr_data)
            else:
                akeneo_data[attr].append(attr_data)
                
    # Convert dictionary to dataframe
    df = _pd.DataFrame(akeneo_data)
    
    return df


# Write data

def write(
        df: _pd.DataFrame,
        user: str, password: str,
        host: str, client_id: str,
        client_secret: str, 
        locale: str = None,
        scope: str = None,
        columns: list = None) -> None:
    """
    Write data into Akeneo
    """
    payload = {"username" : user, "password" : password, "grant_type" : "password"}
    response = _requests.request("POST", host + "api/oauth/v1/token", auth=(client_id, client_secret), json=payload)
    res =  response.json()['access_token']

    headers = {
                'Content-type': 'application/vnd.akeneo.collection+json', # For Writing
                'Authorization': 'Bearer ' + res
            }
    
    # If the user specifies only certain columns
    if columns is not None:
        df = df[columns]    
    
    ### Data pre-cleaning for Akeneo Format ###
    
    # Required metadata Keys
    metadata_keys_str = ['identifier','family'] # string format
    df[metadata_keys_str] = df[metadata_keys_str].astype(str)
    
    metadata_keys_array = ['categories', 'groups'] # array format
    for col_arr in metadata_keys_array:
        df[col_arr] = [x.split(", ") for x in df[col_arr]]
        
        
    # Data Format
    # Format for data under values. Check if the columns headers are not under special name columns
    special_col_names = ['identifier', 'family', 'categories', 'groups']
    locale_scope = {'locale': locale, 'scope': scope}
    values_cols = [] # columns that will need to be merged
    
    # Iterating through non special columns to format in Akeneo way
    for cols in df.columns:
        if cols not in special_col_names:
            # Adding locale and scope to the column dictionary
            if 'scope' not in df[cols][0].keys() and 'locale' not in df[cols][0].keys():
                df[cols] = [[{**locale_scope, **x}] if x != {} else '' for x in df[cols]]
            else:
                # locale and scope are in the data
                df[cols] = [[x] for x in df[cols]]
            values_cols.append(cols)
    
    # Merging all non special columns to values dictionary
    merge.to_dict(df=df, input=values_cols, output='values')
    # Dropping all non special columns
    df.drop(values_cols, axis=1, inplace=True)

    # Sending payload to Akeneo
    payload_batch = ''
    for row in range(len(df)):
        payload_batch =  payload_batch +  _json.dumps(df.to_dict(orient='records')[row]) + '\n'
    
    response = _requests.patch(host + "api/rest/v1/products", headers=headers, data=payload_batch)
    
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
    



