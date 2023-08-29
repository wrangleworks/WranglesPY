"""
Connector to run a recipe.

Run a recipe, from a recipe! Recipe-ception.
"""
from typing import Union as _Union
import types as _types
from .. import recipe as _recipe
import pandas as _pd


_schema = {}


def run(
    name: str = None,
    variables: dict = {},
    functions: _Union[_types.FunctionType, list] = [],
    **kwargs
) -> None:
    """
    Run a recipe, from a recipe! Recipe-ception. This will trigger another recipe.

    >>> from wrangles.connectors import recipe
    >>> recipe.run('recipe.wrgl.yml')

    :param name: Name of the recipe to run
    :param variables: (Optional) A dictionary of custom variables to override placeholders in the recipe. Variables can be indicated as ${MY_VARIABLE}. Variables can also be overwritten by Environment Variables.
    :param functions: Pass in a custom function or list of custom functions that can be called in the recipe.
    """
    if not name: name = kwargs
    _recipe.run(name, variables=variables, functions=functions)

_schema['run'] = """
anyOf:
  - "$ref": "#"
  - type: object
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


def read(
    name: str = None,
    variables: dict = {},
    columns: list = None,
    functions: _Union[_types.FunctionType, list] = [],
    **kwargs
) -> _pd.DataFrame:
    """
    Run a recipe, from a recipe! Recipe-ception. This will read the output of another recipe.

    >>> from wrangles.connectors import recipe
    >>> df = recipe.read('recipe.wrgl.yml')

    :param name: Name of the recipe to run
    :param variables: (Optional) A dictionary of custom variables to override placeholders in the recipe. Variables can be indicated as ${MY_VARIABLE}. Variables can also be overwritten by Environment Variables.
    :param columns: (Optional) Subset of the columns to include from the output of the recipe. If not provided, all columns will be included.
    :param functions: Pass in a custom function or list of custom functions that can be called in the recipe.
    """
    if not name: name = kwargs
    df = _recipe.run(name, variables=variables, functions=functions)

    # Select only specific columns if user requests them
    if columns is not None: df = df[columns]
    
    return df


_schema['read'] = """
anyOf:
  - "$ref": "#"
  - type: object
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
        description: >-
          Subset of the columns to include from the output of the recipe.
          If not provided, all columns will be included.
"""


def write(
    df: _pd.DataFrame,
    name: str = None,
    variables: dict = {},
    columns: list = None,
    functions: _Union[_types.FunctionType, list] = [],
    **kwargs
) -> None:
    """
    Run a recipe, from a recipe! Recipe-ception. This will trigger a new recipe with the contents of the current recipe.

    >>> from wrangles.connectors import recipe
    >>> recipe.write(dataframe=df, name='recipe.wrgl.yml')

    :param df: Dataframe to start the recipe with
    :param name: Name of the recipe to run
    :param variables: (Optional) A dictionary of custom variables to override placeholders in the recipe. Variables can be indicated as ${MY_VARIABLE}. Variables can also be overwritten by Environment Variables.
    :param columns: (Optional) A list of the columns to pass to the recipe. If omitted, all columns will be included.
    :param functions: Pass in a custom function or list of custom functions that can be called in the recipe.
    """
    if not name: name = kwargs
    # Select only specific columns if user requests them
    if columns is not None: df = df[columns]

    _recipe.run(name, dataframe=df, variables=variables, functions=functions)


_schema['write'] = """
anyOf:
  - "$ref": "#"
  - type: object
    required:
      - name
    properties:
      name:
        type: string
        description: The name of the recipe to read from
      variables:
        type: object
        description: A dictionary of variables to pass to the recipe
"""
