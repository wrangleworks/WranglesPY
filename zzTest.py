import wrangles
import pandas as pd

data = pd.DataFrame({
    'text': ['the green mile', 'the shawshank redemption', 'the matrix'],
    'remove': ['Green', "Shawshank", "Matrix"]
})

df = wrangles.recipe.run(
  recipe="""
    wrangles:
      - remove_words:
          input: text
          output: New Title
          to_remove:
            - remove
          tokenize_to_remove: True
          ignore_case: True
  """,
  dataframe=data
)

print(df.to_markdown(index=False))



