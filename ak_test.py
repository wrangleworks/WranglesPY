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
      
wrangles:
  - create.column:
      output: data
      value: data

  - merge.key_value_pairs:
      input:
        data: Name
      output: Name

  - split.text:
      input: Weight
      output:
        - amount
        - unit
      char: ' '
      
  - standardize:
      input: unit
      model_id: 49b583d9-114f-4303
  
  - merge.to_dict:
      input:
        - amount
        - unit
      output: Weight

  - merge.key_value_pairs:
      input:
        data: Weight
      output: Weight

      
"""
df = wrangles.recipe.run(recipe=rec)
df.drop(['data', 'unit', 'amount'], axis=1, inplace=True)
   
tt = write(
    df=df,
    user=username,
    password=password,
    host='https://akeneo.wrangle.works/',
    client_id=client_id,
    client_secret=secret
)

pass