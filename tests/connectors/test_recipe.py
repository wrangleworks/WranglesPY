import wrangles
import pandas as pd
import pytest
import yaml
import requests
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

def test_write_optional_col():
    """
    Test write defined within the recipe with an optional column
    """
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
        wrangles:
          - convert.case:
              input: header1
              output: HEADER!
              case: upper
        write:
          - recipe:
              columns:
                - header1
                - HEADER!?
              write:
                - memory:
                    id: recipe_write
        """
    )
    assert memory.dataframes['recipe_write']['columns'] == ['header1', 'HEADER!']

def test_write_optional_no_col():
    """
    Test write defined within the recipe with an optional column that does not exist
    """
    wrangles.recipe.run(
        """
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
          - recipe:
              columns:
                - header1
                - HEADER!?
              write:
                - memory:
                    id: recipe_write
        """
    )
    assert memory.dataframes['recipe_write']['columns'] == ['header1']

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

def test_model_id():
    """
    Test reading a recipe with a model ID
    """
    df = wrangles.recipe.run(
        """
        read:
          - recipe:
              name: 1e13e845-bc3f-4b27
        """
    )
    assert (
        len(df) == 15 and
        list(df.columns[:3]) == ["Part Number", "Description", "Brand"]
    )

def test_model_with_custom_functions():
    """
    Test a model that includes custom functions
    """
    df = wrangles.recipe.run(
        """
        read:
          - recipe:
              name: 42f319a8-0849-4177
        """
    )
    assert (
        df['header1'][0] == "value1" and
        df['header2'][0] == "value2" and
        df['header3'][0] == "VALUE2"
    )


def test_recipe_error_suggestion():
        """
        Ensure that recipe errors include a Suggestion in the enhanced message
        """
        data = pd.DataFrame({'col': ['a'], 'col2': ['b']})
        recipe = """
        wrangles:
        - copy:
                input:
                    - col
                    - col2
                output:
                    - col-copy
        """
        with pytest.raises(ValueError) as info:
                wrangles.recipe.run(recipe=recipe, dataframe=data)

        assert info.typename == 'ValueError'
        msg = str(info.value)
        assert 'Suggestion:' in msg
        assert 'Validate parameter formats' in msg or 'types match expectations' in msg


def test_wrap_and_raise_suggestions_various():
    """
    Directly call the internal _wrap_and_raise helper with different
    exception types to ensure suggestions are included and relevant.
    """
    import wrangles.recipe as recipe_module

    # Provide a simple recipe string so line lookups can succeed
    recipe_module._CURRENT_RECIPE_STRING = "\n- extract.attributes:\n- copy:\n- explode:\n"

    cases = [
        (FileNotFoundError("missing"), 'Check the file path'),
        (KeyError('k'), 'missing keys'),
        (ValueError('v'), 'Validate parameter formats'),
        (TypeError('t'), 'Verify function argument types'),
        (NotImplementedError('n'), 'not implemented'),
        (RuntimeError('r'), 'expected types'),
        (yaml.YAMLError('y'), 'Check YAML syntax'),
        (requests.exceptions.RequestException('req'), 'Verify the recipe URL')
    ]

    for exc, expected in cases:
        with pytest.raises(type(exc)) as ei:
            recipe_module._wrap_and_raise('wrangle', 'extract.attributes', 1, exc)

        em = str(ei.value)
        assert 'Suggestion:' in em
        assert expected in em
