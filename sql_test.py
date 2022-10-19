import wrangles
import pandas as pd

data = pd.DataFrame({
    'main': [13, 26],
    'col1': ['Hello', 'Mario'],
    'col2': ['Hello', 'Fey'],
    'col3': ['Hello', 'Stranger'],
    'objects': ['Non obj', {'Name': 'obj1'}],
})

comm = """
SELECT *
FROM df
WHERE main > 14
"""

variables = {
    'sql_comm': comm
}

rec = """
wrangles:
  - sql:
      command: ${sql_comm}
"""

df = wrangles.recipe.run(recipe=rec, variables=variables, dataframe=data)

pass