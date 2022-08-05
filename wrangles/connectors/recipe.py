"""
Connector to run a recipe.

Run a recipe, from a recipe! Recipe-ception.
"""
from .. import recipe as _recipe
import pandas as _pd
import requests
import os


_schema = {}


def run(name: str, variables: dict = {}) -> None:
    """
    Run a recipe, from a recipe! Recipe-ception. This will trigger another recipe.

    >>> from wrangles.connectors import recipe
    >>> recipe.run('recipe.wrgl.yml')

    :param name: Name of the recipe to run
    :param variables: (Optional) A dictionary of custom variables to override placeholders in the recipe. Variables can be indicated as ${MY_VARIABLE}. Variables can also be overwritten by Environment Variables.
    """
    _recipe.run(name, variables=variables)

_schema['run'] = """
type: object
description: Run a recipe, from a recipe! Recipe-ception. This will trigger another recipe.
required:
  - name
properties:
  name:
    type: string
    description: The name of the recipe to execute
  variables:
    type: object
    description: A dictionary of variables to pass to the recipe
"""


def read(name: str, variables: dict = {}, columns: list = None) -> _pd.DataFrame:
    """
    Run a recipe, from a recipe! Recipe-ception. This will read the output of another recipe.

    >>> from wrangles.connectors import recipe
    >>> df = recipe.read('recipe.wrgl.yml')

    :param name: Name of the recipe to run
    :param variables: (Optional) A dictionary of custom variables to override placeholders in the recipe. Variables can be indicated as ${MY_VARIABLE}. Variables can also be overwritten by Environment Variables.
    :param columns: (Optional) Subset of the columns to include from the output of the recipe. If not provided, all columns will be included.
    """
    
    # If the recipe to read is from an "https//"
    if 'https://' in name:
        name = name.replace("/blob/", "/")
        name = name.replace("/raw/", "/")
        name = name.replace("/tree/", "/")
        name = name.replace("github.com/", "raw.githubusercontent.com/")

        token = os.getenv('GITHUB_TOKEN', '')
        headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3.raw'}
        response = requests.get(name, headers=headers)
            
        # Checking if file is 'yml' or 'yaml'
        file = response.url.split('/')[-1]
        if file.split('.')[-1] in ['yml', 'yaml']:
            # Write temp file
            with open('temp_recipe_from_https.yaml', 'w') as f:
                f.write(response.text)
            name = 'temp_recipe_from_https.yaml'
            # delete file later
        else:
            raise ValueError('Recipes can only be yaml files')
    
    df = _recipe.run(name, variables=variables)

    # Select only specific columns if user requests them
    if columns is not None: df = df[columns]
    
    # delete file if imported using "https://"
    try:
        os.remove('temp_recipe_from_https.yaml')
    except:
        pass

    return df


_schema['read'] = """
type: object
description: Run a recipe, from a recipe! Recipe-ception. This will read the output of another recipe.
required:
  - name
properties:
  name:
    type: string
    description: The name of the recipe to read from
  variables:
    type: object
    description: A dictionary of variables to pass to the recipe
  columns:
    type: array
    description: Subset of the columns to include from the output of the recipe. If not provided, all columns will be included.
"""


def write(df: _pd.DataFrame, name: str, variables: dict = {}, columns: list = None) -> None:
    """
    Run a recipe, from a recipe! Recipe-ception. This will trigger a new recipe with the contents of the current recipe.

    >>> from wrangles.connectors import recipe
    >>> recipe.write(dataframe=df, name='recipe.wrgl.yml')

    :param df: Dataframe to start the recipe with
    :param name: Name of the recipe to run
    :param variables: (Optional) A dictionary of custom variables to override placeholders in the recipe. Variables can be indicated as ${MY_VARIABLE}. Variables can also be overwritten by Environment Variables.
    :param columns: (Optional) A list of the columns to pass to the recipe. If omitted, all columns will be included.
    """
    # Select only specific columns if user requests them
    if columns is not None: df = df[columns]

    _recipe.run(name, dataframe=df, variables=variables)


_schema['write'] = """
type: object
description: Run a recipe, from a recipe! Recipe-ception. This will trigger a new recipe with the contents of the current recipe.
required:
  - name
properties:
  name:
    type: string
    description: The name of the recipe to read from
  variables:
    type: object
    description: A dictionary of variables to pass to the recipe
  columns:
    type: array
    description: (Optional) A list of the columns to pass to the recipe. If omitted, all columns will be included.
"""