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
    # variables = {
    #     'inputFile': 'tests/samples/data.csv'
    # }
    df = wrangles.recipe.run(recipe)
    assert df['Find2'].iloc[0] == 'brg'