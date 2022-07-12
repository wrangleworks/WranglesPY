"""
Connector to run a recipe.

Run a recipe, from a recipe! Recipe-ception.
"""
from .. import recipe as _recipe
import pandas as _pd


_schema = {}


def run(name: str, variables: dict = {}) -> None:
    """
    Run a recipe.

    >>> from wrangles.connectors import recipe
    >>> recipe.run('recipe.wrgl.yml')

    :param name: Name of the recipe to run
    :param variables: (Optional) A dictionary of custom variables to override placeholders in the recipe. Variables can be indicated as ${MY_VARIABLE}. Variables can also be overwritten by Environment Variables.
    """
    _recipe.run(name, variables=variables)

_schema['run'] = """
type: object
description: Run a recipe, from a recipe! Recipe-ception.
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
    Read a recipe.

    >>> from wrangles.connectors import recipe
    >>> df = recipe.read('recipe.wrgl.yml')

    :param name: Name of the recipe to run
    :param variables: (Optional) A dictionary of custom variables to override placeholders in the recipe. Variables can be indicated as ${MY_VARIABLE}. Variables can also be overwritten by Environment Variables.
    :param columns: (Optional) Subset of the columns to include from the output of the recipe. If not provided, all columns will be included.
    """
    df = _recipe.run(name, variables=variables)

    # Select only specific columns if user requests them
    if columns is not None: df = df[columns]

    return df


_schema['read'] = """
type: object
description: Run a recipe, from a recipe! Recipe-ception.
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
    Read a recipe.

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