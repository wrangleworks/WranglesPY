from difflib import SequenceMatcher
import wrangles
import pandas as pd



data = pd.DataFrame({
    'col1': ['mario', 'luigi', 'peach', 'yoshi', 'equal', '', 'no match', ''],
    'col2': ['supermario', 'superluigi', 'superpeach', 'superyoshi', 'equal', 'no match', '', ''],
})

recipe = """
wrangles:
  - find_match:
      input_a: col1
      input_b: col2
      output: TEST
"""

df = wrangles.recipe.run(
    recipe=recipe,
    dataframe=data,
)

print(df.to_markdown(index=False))