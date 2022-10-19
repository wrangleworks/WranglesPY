import wrangles
import pandas as pd

data = pd.DataFrame({
    'main': [13, 26],
    'col1': ['Hello', 'Mario'],
    'col2': ['Hello', 'Fey'],
    'col3': ['Hello', 'Stranger'],
    'objects': [{'Name': 'obj1'}, {'Name': 'obj2'}],
})

comm = """
SELECT *
FROM df
WHERE main > 14
"""

rec = f"""
wrangles:
  - sql:
      command: |
        SELECT *
        FROM df
        WHERE main > 14
"""

df = wrangles.recipe.run(recipe=rec, dataframe=data)

pass