import pytest
import wrangles
import pandas as pd


def test_read_recipe_connector():
    recipe = """
    read:
      - recipe:
          name: 'tests/samples/recipe_sample.wrgl.yaml'
          variables:
            inputFile: 'tests/samples/data.csv'
    """
    df = wrangles.recipe.run(recipe)
    assert df['Find2'].iloc[0] == 'brg'
    
    
# Recipe as a connector
from wrangles.connectors.recipe import read, run
def test_read_recipe_connector_2():
  recipe = """
  read:
      - recipe:
          name: 'tests/samples/recipe_sample.wrgl.yaml'
          variables:
            inputFile: 'tests/samples/data.csv'
  """
  df = read(recipe)
  assert df['Find2'].iloc[0] == 'brg'
  
# writing
def test_write_recipe_connector():
  recipe = """
  read:
      - recipe:
          name: 'tests/samples/recipe_sample.wrgl.yaml'
          variables:
            inputFile: 'tests/samples/data.csv'
  write:
      - recipe:
          name: 'tests/samples/recipe_sample.wrgl.yaml'
          variables:
            inputFile: 'tests/samples/data.csv'
  """
  df = read(recipe)
  assert df['Find2'].iloc[0] == 'brg'


# Running recipe
def test_run_recipe_connector():
  recipe = """
  run:
    on_start:
      - recipe:
          name: 'tests/samples/recipe_sample.wrgl.yaml'
          variables:
            inputFile: 'tests/samples/data.csv'
  """
  assert run(recipe) == None
  
  
### Custom function to a sub recipes

# Functions
def read_data(columns):
    data = pd.DataFrame({
    'col1': ['mario', 'fey'],
    'col2': ['TACOS', 'RIBEYE'],
    'Not this': ['No', 'No']
    })
    return data[columns]

def custom_func_1(df, case):
    if case == 'upper':
        df['col1'] = df['col1'].str.upper()
    else:
        df['col1'] = df['col1'].str.lower()
    return df
    
def write_1(df, type):
    df.to_excel(f"temp_excel.{type}")
    
main_recipe = 'tests/samples/sub_rec_main.wrgl.yaml'

functions = [
    custom_func_1,
    write_1,
    read_data,
]

def test_function_sub_recipe():
    df = wrangles.recipe.run(recipe=main_recipe, functions=functions)
    assert df['col1'][0] == 'MARIO'


