"""
Tests for misc general recipe logic and operation

Specific tests for individual connectors or wrangles should be placed within
a file for the respective wrangle/connector.
"""
import wrangles
import pandas as pd
import pytest


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

#
# Wild card Expansion escape character
#
def test_wildcard_expansion_1():
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