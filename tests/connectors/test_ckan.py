import random
import string
import wrangles
import pytest


def test_write_and_read():
    """
    Write a random string to CKAN server,
    then read results back to verify
    """
    random_string = ''.join(random.choices(string.ascii_lowercase, k=8))
    recipe = """
    read:
      - test:
          rows: 5
          values:
            header: ${RANDOM_VALUE}
    
    write:
      - ckan:
          host: https://catalog.wrangle.works
          dataset: test
          file: test.csv
          api_key: ${CKAN_API_KEY}
    """
    wrangles.recipe.run(
        recipe,
        variables={
            'RANDOM_VALUE': random_string
        }
    )

    recipe = """
    read:
      - ckan:
          host: https://catalog.wrangle.works
          dataset: test
          file: test.csv
          api_key: ${CKAN_API_KEY}
    """
    df = wrangles.recipe.run(recipe)
    assert df['header'].values[0] == random_string

def test_missing_apikey():
    """
    Check error if user omits API KEY
    """
    recipe = """
    read:
      - ckan:
          host: https://catalog.wrangle.works
          dataset: test
          file: test.csv
    """
    with pytest.raises(RuntimeError) as info:
        raise wrangles.recipe.run(recipe)
    
    assert info.typename == 'RuntimeError' and info.value.args[0].startswith('Access Denied')

def test_invalid_apikey():
    """
    Check error if user has invalid API KEY
    """
    recipe = """
    read:
      - ckan:
          host: https://catalog.wrangle.works
          dataset: test
          file: test.csv
          api_key: aaaaaa
    """
    with pytest.raises(RuntimeError) as info:
        raise wrangles.recipe.run(recipe)
    
    assert info.typename == 'RuntimeError' and info.value.args[0].startswith('Access Denied')

def test_missing_dataset():
    """
    Check error if dataset isn't found
    """
    recipe = """
    read:
      - ckan:
          host: https://catalog.wrangle.works
          dataset: aaaaaaaaaaaaa
          file: test.csv
          api_key: ${CKAN_API_KEY}
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe)
    
    assert info.typename == 'ValueError' and info.value.args[0][:22] == 'Unable to find dataset'


def test_missing_file():
    """
    Check error if file isn't found in the dataset
    """
    recipe = """
    read:
      - ckan:
          host: https://catalog.wrangle.works
          dataset: test
          file: aaaaaaaaaaaaaa.csv
          api_key: ${CKAN_API_KEY}
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe)
    
    assert info.typename == 'ValueError' and info.value.args[0][:14] == 'File not found'