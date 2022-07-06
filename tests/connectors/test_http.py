import requests
import wrangles
import pandas as pd


def test_http_read_1():
    recipe = """
    read:
      - http:
          url: https://pokeapi.co/api/v2/pokemon/charizard
    """
    df = wrangles.recipe.run(recipe)
    assert df['abilities'][0][0]['ability']['name'] == 'blaze'
    
def test_http_read_2():
    recipe = """
    read:
      - http:
          url: https://pokeapi.co/api/v2/pokemon/charizard
          json_key: abilities
    """
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0]['ability']['name'] == 'blaze'
    
from wrangles.connectors.http import run
def test_http_run():
    test = run('https://pokeapi.co/api/v2/pokemon/charizard')
    assert test == None