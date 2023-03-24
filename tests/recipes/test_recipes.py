"""
Tests for misc general recipe logic and operation

Specific tests for individual connectors or wrangles should be placed within
a file for the respective wrangle/connector.
"""
import wrangles
import pandas as pd
import pytest


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

    
# Testing reading a recipe from an https:// source
def test_recipe_online():
  data = pd.DataFrame({
    'col1': ['hello world'],
  })
  recipe = "https://public.wrangle.works/tests/recipe.wrgl.yml"
  df = wrangles.recipe.run(recipe, dataframe=data)
  assert df.iloc[0]['out1'] == 'HELLO WORLD'

def test_recipe_online_2():
    """
    Test that if a user passes in a recipe as a URL and the 
    URL produces an error, that a sensible error is communicated
    to the user
    """
    data = pd.DataFrame({
    'col1': ['hello world'],
    })
    recipe = "https://public.wrangle.works/tests/recipe.wrgl.yaaml"
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Error getting recipe from url: https://public.wrangle.works/tests/recipe.wrgl.yaaml\nReason: Not Found-404'
  
  
# Testing on success
def test_on_success():
    data = pd.DataFrame({
        'col1': ['hello world'],
    })
    success_rec = """
    write:
      - file:
          name: tests/temp/temp2.csv
    """
    recipe = """
    run:
      on_success:
        - recipe:
            name: ${rec2}
    wrangles:
      - convert.case:
          input: col1
          output: out1
          case: upper
    """
    vars = {
        "rec2": success_rec
    }
    df = wrangles.recipe.run(recipe, dataframe=data, variables=vars)
    assert df.iloc[0]['out1'] == 'HELLO WORLD'
    
# Testing on failure
def test_on_failure():
    data = pd.DataFrame({
        'col1': ['hello world'],
    })
    failure_rec = """
    write:
      - file:
          name: tests/temp/temp3.csv
    """
    recipe = """
    run:
      on_failure:
        - recipe:
            name: ${rec2}
    wrangles:
        - convert.case:
            input: col111
            output: out
            case: upper
    """
    vars = {
        "rec2": failure_rec
    }
    with pytest.raises(KeyError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data, variables=vars)
    assert info.typename == 'KeyError' and info.value.args[0].startswith("Column col111")
