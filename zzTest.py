import wrangles
import pandas as pd

data = pd.DataFrame({
    'text': ['the GrEEn MiLe', ['the shawSHAnk redemptiOn'], 'THE matRIX'],
    'remove': ['Green something mile', "Shawshank", "Matrix"],
    'remove2': ['the', 'the', 'the']
})

df = wrangles.recipe.run(
  recipe="""
    wrangles:
      - remove_words:
          input: text
          output: New Title
          to_remove:
            - remove
            - remove2
          tokenize_to_remove: False
          case_sensitive: True
  """,
  dataframe=data
)

print(df.to_markdown(index=False))



