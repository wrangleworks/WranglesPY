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
rec = "data_to_akeneo.wrgl.yaml"
vars = {'None_Value': None}
df = wrangles.recipe.run(recipe=rec, variables=vars)
pass
# Writing to Akeneo
cols_to_use = [
    'identifier',
    'family',
    'categories',
    'groups',
    'Blade Dia.',
    'Max. RPM',
    'Tool Weight',
    'Tool Length',
    'Voltage',
    'BOSCH CATEGORY',
    'Item',
    'USD'
    ]

write(
    df=df,
    user=username,
    password=password,
    host='https://akeneo.wrangle.works/',
    client_id=client_id,
    client_secret=secret,
    columns=cols_to_use
)

pass


