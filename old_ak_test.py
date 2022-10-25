import json
from wrangles.connectors.akeneo import read, write
import wrangles
import os as _os
import ast

# login stuff
client_id = _os.getenv('AKENEO_CLIENT_ID', '...')
secret = _os.getenv('AKENEO_SECRET', '...')
username = _os.getenv('AKENEO_USERNAME', '...')
password = _os.getenv('AKENEO_PASSWORD', '...')
attributes = ['USD', 'Name', 'Weight', 'In_Stock']

test_df = read(
    user=username,
    password=password,
    host='https://akeneo.wrangle.works/',
    client_id=client_id,
    client_secret=secret
)

# Convert list of attributes into keys
column_header_to_dict = """
read:
  - file:
      name: temp.xlsx
wrangles:
    - merge.to_dict:
        input: ${attributes_list}
        output: values
    - convert.data_type:
        input: identifier
        data_type: str
        
write:
  - file:
      name: input_data.xlsx
"""
vars = {
    'attributes_list': attributes,
}

df = wrangles.recipe.run(recipe=column_header_to_dict, variables=vars)

cat_list = []
for cats in df['categories']:
    cat_list.append(ast.literal_eval(cats))
df['categories'] = cat_list

group_list = []
for groups in df['groups']:
    group_list.append(ast.literal_eval(groups))
df['groups'] = group_list

values_list = []
for item in df['values']:
    values_dict = {}
    for key, value in item.items():
        values_dict[key] = ast.literal_eval(value)
    values_list.append(values_dict)
df['values'] = values_list


df = df[[
    'identifier',
    'family',
    'categories',
    'groups',
    'values'
]]

new_values = []
for item in df['values']:
    new_dict  = {}
    for key, value in item.items():
        
        if key == 'Name':
            value = value[0]['data']
        elif key == 'Weight':
            value = value[0]
        elif key == 'In_Stock':
            value = value[0]['data']
        else: value = [value[0]]
        
        
        if key == 'In_Stock':
            
            static_dict = {
            'locale': None,
            'scope': 'ecommerce',
            'data': value
            }
        else:
            static_dict = {
            'locale': None,
            'scope': None,
            'data': value
            }
        
        new_dict[key] = [static_dict] # Getting an error here for weight
    new_values.append(new_dict)
df['values'] = new_values
    
    
tt = write(
    df=df,
    user=username,
    password=password,
    host='https://akeneo.wrangle.works/',
    client_id=client_id,
    client_secret=secret
)

pass