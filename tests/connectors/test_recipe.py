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


#
# importing templated values
#

# recipe as a templated value
def test_templated_values_1():
    case_var = "upper"
    inputs = ['col', 'col2']
    templated_rec = """
        convert.case:
          input:
            ${inputs}
          output:
            - out
            - out2
          case: ${case_value}
    """
    data = pd.DataFrame({
        'col': ['Hello World'],
        'col2': ['hello world'],
    })
    recipe = """
    wrangles:
      - ${wrgl1}
    """
    vars = {
        'wrgl1': templated_rec,
        'case_value': case_var,
        'inputs': inputs,
    }
    df = wrangles.recipe.run(recipe, variables=vars, dataframe=data)
    assert df.iloc[0]['out'] == "HELLO WORLD"
    
    
# templated value in a sql command
def test_templated_values_2():
    data = pd.DataFrame({
        'col': ['Hello SQL']
    })
    templated_sql = """
    SELECT * from df
    """
    recipe = """
    wrangles:
      - sql: 
          command: ${sql_command}
    """
    vars = {
        "sql_command": templated_sql,
    }
    df = wrangles.recipe.run(recipe, variables=vars, dataframe=data)
    assert 1

#
# Wild card Expansion escape character
#

def test_wildcard_expansion_1():
    data = pd.DataFrame({
        'col1': ['HEllO'],
        'col*': ['WORLD'],
    })
    recipe = """
    wrangles:
      - convert.case:
          input:
            - col\*
          output:
            - out
          case: lower
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out'] == 'world'
    
#
# Custom function not found error message
#

def test_custom_func_not_found():
    data = pd.DataFrame({
        'col':['Hello World']
    })
    recipe = """
    wrangles:
      - custom.does_not_exists:
          input: col
          output: out
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Custom Wrangle function: "custom.does_not_exists" not found'