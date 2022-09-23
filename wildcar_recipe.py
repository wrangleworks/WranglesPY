import wrangles
import pandas as pd



data = pd.DataFrame({
    'Col': ['Hello'],
    'Col1': ['Fey'],
    'Col2': ['!'],
    'Not_This': ['Mario Last'],
    'Col*': ['THIS?']
})
recipe = """
wrangles:
  - merge.concatenate:
      input:
        - Col*
        - Not_This
      output: Join
      char: ', '
"""
df = wrangles.recipe.run(recipe, dataframe=data)
print(df.to_markdown(index=False))

pass

