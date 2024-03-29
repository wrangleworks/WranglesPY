import wrangles


def test_read():
    recipe = """
    read:
      - http:
          url: https://pokeapi.co/api/v2/pokemon/charizard
    """
    df = wrangles.recipe.run(recipe)
    assert df['abilities'][0][0]['ability']['name'] == 'blaze'
    
def test_read_json_key():
    recipe = """
    read:
      - http:
          url: https://pokeapi.co/api/v2/pokemon/charizard
          json_key: abilities
    """
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0]['ability']['name'] == 'blaze'
    

def test_run():
    from wrangles.connectors import http
    test = http.run('https://pokeapi.co/api/v2/pokemon/charizard')
    assert test == None