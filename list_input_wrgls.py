import wrangles
import pandas as pd

data = pd.DataFrame({
    'Col': ['red ferrari'],
    'Col1': ['white ferrari'],
})

rec = """
wrangles:
  - extract.properties:
      input: Col*
      output: 
        - Out 1
        - Out 2
      property_type: colours
"""

df = wrangles.recipe.run(recipe=rec, dataframe=data)
print(df.to_markdown(index=False))

pass

