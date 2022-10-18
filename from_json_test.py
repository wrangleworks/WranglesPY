import wrangles
import pandas as pd
import json

data = pd.DataFrame({
    'Col': [{'name':'Fey'}],
})

rec = """
wrangles:
  - convert.to_json:
      input: Col
      output: obj_col
"""

df = wrangles.recipe.run(recipe=rec, dataframe=data)
print(df.to_markdown())
