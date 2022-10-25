import json
from wrangles.connectors.akeneo import read, write
import wrangles
import os as _os

# login stuff
client_id = _os.getenv('AKENEO_CLIENT_ID', '...')
secret = _os.getenv('AKENEO_SECRET', '...')
username = _os.getenv('AKENEO_USERNAME', '...')
password = _os.getenv('AKENEO_PASSWORD', '...')

# Writing from a file (Excel)
rec = """
read:
  - file:
      name: Akeneo Test Data.xlsx
      sheet_name: Data to Write Test 1
"""

df = wrangles.recipe.run(recipe=rec)

# Dealing with Required Values

# Identifier must be a string
df['identifier'] = df['identifier'].astype(str)

# family must be a string
df['family'] = df['family'].astype(str)

# categories must be an array
df['categories'] = [x.split(", ") for x in df['categories']]

# groups must be an array
df['groups'] = [x.split(", ") for x in df['groups']]



# Dealing with Name - Text and Text Area Attributes - pim_catalog_text or pim_catalog_textarea

# the name of the columns is the key here
# the list will be populated by objects in format {"data" : "Name of the columns item"}
name_list = []
for item in df['Name']:
    name_list.append([{"locale": None, "scope": None, "data": item}])
df['Name'] = name_list

# Weight Attribute - Metric Attributes - pim_catalog_metric

# Standardizing units to full name and upper case
input_list = df['Weight'].tolist()
clean_list = wrangles.standardize(input_list, '49b583d9-114f-4303')

df['Weight'] = clean_list

weight_list = []
for weight_item in df['Weight']:
    weight_list.append([{"locale": None, "scope": None, "data": {"amount": weight_item.split(" ")[0], "unit": weight_item.split(" ")[1]}}])
df['Weight'] = weight_list



# Putting all attributes under 'values'

attributes = ['Name', 'Weight']
values_list = []
for df_index in range(len(df)):
    value_obj = {}
    for attr in attributes:
        value_obj[attr] = df[attr][df_index]
    values_list.append(value_obj)
df['values'] = values_list
# Dropping attribute columns as they are no longer needed
df.drop(attributes, axis=1, inplace=True)




    
# tt = write(
#     df=df,
#     user=username,
#     password=password,
#     host='https://akeneo.wrangle.works/',
#     client_id=client_id,
#     client_secret=secret
# )

pass