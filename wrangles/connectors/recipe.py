"""
Connector to run a recipe.

Run a recipe, from a recipe! Recipe-ception.
"""
from typing import Union as _Union
import types as _types
from .. import recipe as _recipe
import pandas as _pd
from ..utils import wildcard_expansion as _wildcard_expansion


_schema = {}


def run(
    name: str = None,
    variables: dict = None,
    functions: _Union[_types.FunctionType, list] = [],
    export_runtime_variables: _Union[str, list] = None,
    export_conflict_policy: str = "error",
    **kwargs
) -> None:
    """
    Run a recipe, from a recipe! Recipe-ception. This will trigger another recipe.

    >>> from wrangles.connectors import recipe
    >>> recipe.run('recipe.wrgl.yml')

    :param name: Name of the recipe to run
    :param variables: (Optional) A dictionary of custom variables to override placeholders in the recipe. Variables can be indicated as ${MY_VARIABLE}. Variables can also be overwritten by Environment Variables.
    :param functions: Pass in a custom function or list of custom functions that can be called in the recipe.
    :param export_runtime_variables: Runtime variable name(s) to export back to the parent recipe.
    :param export_conflict_policy: How to resolve parent collisions when exporting runtime variables.
    """
    if variables is None:
        variables = {}
    if not name: name = kwargs
    if export_runtime_variables is None:
        _recipe.run(name, variables=variables, functions=functions)
        return

    _, exported = _recipe.run(
        name,
        variables=variables,
        functions=functions,
        _return_runtime_variables=export_runtime_variables
    )

    if export_conflict_policy not in ["error", "overwrite"]:
        raise ValueError("export_conflict_policy must be 'error' or 'overwrite'.")

    if export_conflict_policy == "error":
        collisions = [
            key
            for key, value in exported.items()
            if key in variables and variables[key] != value
        ]
        if collisions:
            raise ValueError(
                f"Runtime export collision for variables {collisions}. "
                "Use export_conflict_policy: overwrite to allow replacing parent values."
            )

    _recipe._apply_runtime_variable_updates(variables, set_values=exported)

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
      export_runtime_variables:
        type:
          - string
          - array
        description: Runtime variable names to export from the nested recipe back to the parent runtime variables.
      export_conflict_policy:
        type: string
        enum:
          - error
          - overwrite
        description: Collision policy when exporting runtime variables back to the parent recipe.
"""


def read(
    name: str = None,
    variables: dict = None,
    columns: list = None,
    functions: _Union[_types.FunctionType, list] = [],
    export_runtime_variables: _Union[str, list] = None,
    export_conflict_policy: str = "error",
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
    :param export_runtime_variables: Runtime variable name(s) to export back to the parent recipe.
    :param export_conflict_policy: How to resolve parent collisions when exporting runtime variables.
    """
    if variables is None:
        variables = {}
    if not name: name = kwargs
    if export_runtime_variables is None:
        df = _recipe.run(name, variables=variables, functions=functions)
    else:
        df, exported = _recipe.run(
            name,
            variables=variables,
            functions=functions,
            _return_runtime_variables=export_runtime_variables
        )
        if export_conflict_policy not in ["error", "overwrite"]:
            raise ValueError("export_conflict_policy must be 'error' or 'overwrite'.")
        if export_conflict_policy == "error":
            collisions = [
                key
                for key, value in exported.items()
                if key in variables and variables[key] != value
            ]
            if collisions:
                raise ValueError(
                    f"Runtime export collision for variables {collisions}. "
                    "Use export_conflict_policy: overwrite to allow replacing parent values."
                )
        _recipe._apply_runtime_variable_updates(variables, set_values=exported)

    # Select only specific columns if user requests them
    if columns is not None:
        columns = _wildcard_expansion(df.columns, columns)
        df = df[columns]
    
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
      export_runtime_variables:
        type:
          - string
          - array
        description: Runtime variable names to export from the nested recipe back to the parent runtime variables.
      export_conflict_policy:
        type: string
        enum:
          - error
          - overwrite
        description: Collision policy when exporting runtime variables back to the parent recipe.
"""


def write(
    df: _pd.DataFrame,
    name: str = None,
    variables: dict = None,
    columns: list = None,
    functions: _Union[_types.FunctionType, list] = [],
    export_runtime_variables: _Union[str, list] = None,
    export_conflict_policy: str = "error",
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
    :param export_runtime_variables: Runtime variable name(s) to export back to the parent recipe.
    :param export_conflict_policy: How to resolve parent collisions when exporting runtime variables.
    """
    if variables is None:
        variables = {}
    if not name: name = kwargs
    # Select only specific columns if user requests them
    if columns is not None:
        columns = _wildcard_expansion(df.columns, columns)
        df = df[columns]

    if export_runtime_variables is None:
        _recipe.run(name, dataframe=df, variables=variables, functions=functions)
        return

    _, exported = _recipe.run(
        name,
        dataframe=df,
        variables=variables,
        functions=functions,
        _return_runtime_variables=export_runtime_variables
    )

    if export_conflict_policy not in ["error", "overwrite"]:
        raise ValueError("export_conflict_policy must be 'error' or 'overwrite'.")
    if export_conflict_policy == "error":
        collisions = [
            key
            for key, value in exported.items()
            if key in variables and variables[key] != value
        ]
        if collisions:
            raise ValueError(
                f"Runtime export collision for variables {collisions}. "
                "Use export_conflict_policy: overwrite to allow replacing parent values."
            )
    _recipe._apply_runtime_variable_updates(variables, set_values=exported)


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
      export_runtime_variables:
        type:
          - string
          - array
        description: Runtime variable names to export from the nested recipe back to the parent runtime variables.
      export_conflict_policy:
        type: string
        enum:
          - error
          - overwrite
        description: Collision policy when exporting runtime variables back to the parent recipe.
"""
