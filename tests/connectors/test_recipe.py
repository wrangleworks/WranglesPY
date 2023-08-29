import wrangles
import pandas as pd
from wrangles.connectors import memory


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


def test_function_sub_recipe():
    """
    Test that custom functions are able to
    be called by sub-recipes.
    """
    main_recipe = 'tests/samples/sub_rec_main.wrgl.yaml'

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
        df.to_excel(f"tests/temp/excel.{type}")

    df = wrangles.recipe.run(
        recipe=main_recipe,
        functions=[
            custom_func_1,
            write_1,
            read_data,
        ]
    )
    assert df['col1'][0] == 'MARIO'

def test_read():
    """
    Test read defined within the recipe
    """
    df = wrangles.recipe.run(
        """
        read:
          - recipe:
              read:
                - test:
                    rows: 5
                    values:
                      header1: value1
              wrangles:
                - convert.case:
                    input: header1
                    case: upper
        """
    )
    assert df["header1"][0] == "VALUE1"

def test_wrangles():
    """
    Test wrangles defined within the recipe
    """
    df = wrangles.recipe.run(
        """
        read:
            - test:
                rows: 5
                values:
                    header1: value1
        wrangles:
          - recipe:
              wrangles:
                - convert.case:
                    input: header1
                    case: upper
        """
    )
    assert df["header1"][0] == "VALUE1"

def test_write():
    """
    Test write defined within the recipe
    """
    wrangles.recipe.run(
        """
        read:
            - test:
                rows: 5
                values:
                    header1: value1
        write:
          - recipe:
              wrangles:
                - convert.case:
                    input: header1
                    case: upper
              write:
                - memory:
                    id: recipe_write
        """
    )
    assert memory.dataframes["recipe_write"]["data"][0][0] == "VALUE1"

def test_run():
    """
    Test run defined within the recipe
    """
    wrangles.recipe.run(
        """
        run:
          on_start:
          - recipe:
              read:
                - test:
                    rows: 5
                    values:
                      header1: value1
              wrangles:
                - convert.case:
                    input: header1
                    case: upper
              write:
                - memory:
                    id: recipe_run
        """
    )
    assert memory.dataframes["recipe_run"]["data"][0][0] == "VALUE1"
