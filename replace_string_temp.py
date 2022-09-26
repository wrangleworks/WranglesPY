import wrangles
import pandas as pd

data = pd.DataFrame({
    'col': ['Hello, Fey, !'],
    'Extra': ['Extra Data']
})

vars = {
    'Input1': 'col',
    'Output1': 'out1',
    'Input2': 'col',
    'Output2': 'out2',
    'ExtraValue': 'Extra',
    'fileName': 'TEST.xlsx',
}

rec = 'replace_string_temp.wrgl.yaml'
df = wrangles.recipe.run(recipe=rec, dataframe=data, variables=vars)
print(df.to_markdown(index=False))
pass

