"""
Tests for misc general recipe logic and operation

Specific tests for individual connectors or wrangles should be placed within
a file for the respective wrangle/connector.
"""
import wrangles
from wrangles.connectors import memory
import pandas as pd
import pytest
import time


def test_recipe_from_file():
    """
    Testing recipe passed as a filename
    """
    df = wrangles.recipe.run(
        "tests/samples/recipe_sample.wrgl.yaml",
        variables= {
            "inputFile": 'tests/samples/data.csv',
            "outputFile": 'tests/temp/write_data.xlsx'
        }
    )
    assert df.columns.tolist() == ['ID', 'Find2']

def test_recipe_from_url():
    """
    Testing reading a recipe from an https:// source
    """
    data = pd.DataFrame({
        'col1': ['hello world'],
    })
    recipe = "https://public.wrangle.works/tests/recipe.wrgl.yml"
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == 'HELLO WORLD'

def test_recipe_from_url_not_found():
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
    assert (
        info.typename == 'ValueError' and
        info.value.args[0] == 'Error getting recipe from url: https://public.wrangle.works/tests/recipe.wrgl.yaaml\nReason: Not Found-404'
    )

def test_wildcard_expansion_1():
    """
    Wild card Expansion escape character
    """
    data = pd.DataFrame({
        'col1': ['HEllO'],
        'col*': ['WORLD'],
    })
    recipe = r"""
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

def test_recipe_special_character():
    """
    Tests special character encoding when reading a recipe containing special characters
    """
    recipe = 'tests/samples/recipe_special_character.wrgl.yml'
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0]['column'] == 'this is a ° symbol'

def test_recipe_model():
    """
    Test running a recipe using a model ID
    """
    df = wrangles.recipe.run("1e13e845-bc3f-4b27")
    assert (
        len(df) == 15 and
        list(df.columns[:3]) == ["Part Number", "Description", "Brand"]
    )

def test_timeout():

    def sleep(df, seconds):
        time.sleep(seconds)
        return df

    with pytest.raises(TimeoutError) as info:
        raise wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: value1
            
            wrangles:
            - custom.sleep:
                seconds: 10
            """
            ,
            functions=sleep,
            timeout=5
        )
    
    assert info.typename == 'TimeoutError'

def test_timeout_failure_actions():

    def sleep(df, seconds):
        time.sleep(seconds)
        return df

    def fail():
        memory.variables["timeout fail action"] = "got here"
    
    with pytest.raises(TimeoutError) as info:
        raise wrangles.recipe.run(
            """
            run:
              on_failure:
                - custom.fail: {}

            read:
            - test:
                rows: 5
                values:
                    header1: value1
            
            wrangles:
            - custom.sleep:
                seconds: 10
            """
            ,
            functions=[sleep,fail],
            timeout=5
        )
    
    assert (
        info.typename == 'TimeoutError' and
        memory.variables["timeout fail action"] == "got here"
    )
