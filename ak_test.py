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
rec = "akeneo_test.wrgl.yaml"
vars = {'None_Value': None}
df = wrangles.recipe.run(recipe=rec, variables=vars)

# Merging two dictionaries together

df['In_Stock'] = [{**df['scope_ecom'][x], **df['In_Stock'][x]} for x in range(len(df))]

df.drop(['data', 'unit', 'amount', 'currency', 'scope_ecom', 'scope', 'locale'], axis=1, inplace=True)
pass

tt = write(
    df=df,
    user=username,
    password=password,
    host='https://akeneo.wrangle.works/',
    client_id=client_id,
    client_secret=secret
)

pass