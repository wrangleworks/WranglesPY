"""
Create and execute Wrangling pipelines
"""
import pandas as _pandas
import yaml as _yaml
import logging as _logging
from typing import Union as _Union
import os as _os
import fnmatch

from . import pipeline_wrangles as _pipeline_wrangles
from . import connectors as _connectors


_logging.getLogger().setLevel(_logging.INFO)


def _load_recipe(recipe: str, params: dict = {}) -> dict:
    """
    Load yaml recipe file + replace any placeholder variables

    :param recipe: YAML recipe or name of a YAML file to be parsed
    :param params: (Optional) dictionary of custom parameters to override placeholders in the YAML file
    """
    _logging.info(": Reading Recipe ::")

    # If recipe is a single line, it's probably a file path
    # Otherwise it's a recipe
    if "\n" in recipe:
        recipe_string = recipe
    else:
        with open(recipe, "r") as f:
            recipe_string = f.read()
    
    # Also add environment variables to list of placeholder variables
    # Q: Should we exclude some?
    for env_key, env_val in _os.environ.items():
        if env_key not in params.keys():
            params[env_key] = env_val

    # Replace templated values
    for key, val in params.items():
        recipe_string = recipe_string.replace("${" + key + "}", val)

    recipe_object = _yaml.safe_load(recipe_string)

    return recipe_object


def _execute_actions(recipe: _Union[dict, list], connections: dict = {}) -> None:
    # If user has entered a dictionary, convert to list
    if isinstance(recipe, dict):
        recipe = [recipe]

    for action in recipe:
        for action_type, params in action.items():
            # Use shared connection details if set
            if 'connection' in params.keys():
                params.update(connections[params['connection']])
                params.pop('connection')

            # Get execute function of requested connector and pass user defined params
            getattr(getattr(_connectors, action_type), 'execute')(**params)


def _read_data_sources(recipe: _Union[dict, list], connections: dict = {}) -> _pandas.DataFrame:
    """
    Import data from requested datasources as defined by the recipe

    :param recipe: Read section of a recipe
    :param connections: shared connections
    :return: Dataframe of imported data
    """
    # Allow blended imports
    if list(recipe)[0] in ['concatenate', 'merge']:
        # Get data from list of sources
        dfs = []
        for source in recipe[list(recipe)[0]]['sources']:
            import_type = list(source)[0]
            params = source[import_type]
            
            # Use shared connection details if set
            if 'connection' in params.keys():
                params.update(connections[params['connection']])
                params.pop('connection')

            dfs.append(getattr(getattr(_connectors, import_type), 'read')(**params))

        if list(recipe)[0] == 'concatenate':
            # Blend as a concatenation - stack data depending on axis (e.g. union)
            df = _pandas.concat(dfs, **recipe['concatenate'].get('parameters', {}))
        elif list(recipe)[0] == 'merge':
            # Blend as a merge - equivalent to database join
            df = _pandas.merge(dfs[0], dfs[1], **recipe['merge'].get('parameters', {}))
        # Clear from memory in case this is a large object
        del dfs
    else:
        # Single source import
        if isinstance(recipe, dict):
            # If user has entered a dict, get first key and value
            import_type = list(recipe)[0]
            params = recipe[import_type]
        elif isinstance(recipe, list):
            # If they've entered a list, get the first key and value from the first element
            import_type = list(recipe[0])[0]
            params = recipe[0][import_type]

        # Use shared connection details if set
        if 'connection' in params.keys():
            params.update(connections[params['connection']])
            params.pop('connection')

        # Load appropriate data
        df = getattr(getattr(_connectors, import_type), 'read')(**params)
    
    return df


def _execute_wrangles(df, wrangles_list) -> _pandas.DataFrame:
    """
    Execute a list of Wrangles on a dataframe

    :param df: Dateframe that the Wrangles will be run against
    :param wrangles_list: List of Wrangles + their definitions to be executed
    :return: Pandas Dataframe of the Wrangled data
    """
    for step in wrangles_list:
        for wrangle, params in step.items():
            _logging.info(f": Wrangling :: {wrangle} :: {params.get('input', 'None')} >> {params.get('output', 'Dynamic')}")

            if wrangle.split('.')[0] == 'pandas':
                # Execute a pandas method
                # TODO: disallow any hidden methods
                df = getattr(df, wrangle.split('.')[1])(**params.get('parameters', {}))

            else:
                # Allow user to specify a wildcard (? or *) for the input columns
                if isinstance(params.get('input', ''), str) and ('*' in params.get('input', '') or '?' in params.get('input', '')):
                    params['input'] = fnmatch.filter(df.columns, params['input'])

                # Get the requested function from the pipeline_wrangles module
                obj = _pipeline_wrangles
                for element in wrangle.split('.'):
                    obj = getattr(obj, element)

                # Execute the requested function and return the value
                df = obj(df, **params)

    return df


def _write_data(df: _pandas.DataFrame, recipe: dict, connections: dict = {}) -> _pandas.DataFrame:
    """
    Export data to the requested targets as defined by the recipe

    :param df: Dataframe to be exported
    :param recipe: write section of a recipe
    :param connections: shared connections
    :return: Dataframe, a subset if the 'dataframe' write type is set with specific fields
    """
    # Initialize returned df as df to start
    df_return = df

    # If user has entered a dictionary, convert to list
    if isinstance(recipe, dict):
        recipe = [recipe]

    # Loop through all exports, get type and execute appropriate export
    for export in recipe:
        for export_type, params in export.items():
            if export_type == 'dataframe':
                # Define the dataframe that is returned
                df_return = df[params['fields']]
            else:
                # Use shared connection details if set
                if 'connection' in params.keys():
                    params.update(connections[params['connection']])
                    params.pop('connection')

                # Get output function of requested connector and pass dataframe + user defined params
                getattr(getattr(_connectors, export_type), 'write')(df, **params)

    return df_return


def run(recipe: str, params: dict = {}, dataframe = None) -> _pandas.DataFrame:
    """
    Execute a YAML defined Wrangling pipeline

    >>> wrangles.pipeline.run(recipe)
    
    :param recipe: YAML recipe or path to a YAML file containing the recipe
    :param params: (Optional) dictionary of custom parameters to override placeholders in the YAML file
    :param dataframe: (Optional) Pass in a pandas dataframe, instead of defining a read section within the YAML
    """
    # Parse recipe
    recipe = _load_recipe(recipe, params)

    if 'execute' in recipe.keys():
        # Execute any actions required before the pipeline runs
        _execute_actions(recipe['execute'], recipe.get('connections', {}))

    # Get requested data
    if 'read' in recipe.keys():
        # Execute requested data imports
        df = _read_data_sources(recipe['read'], recipe.get('connections', {}))
    elif dataframe is not None:
        # User has passed in a pre-created dataframe
        df = dataframe
    else:
        # User hasn't provided anything - initialize empty dataframe
        df = _pandas.DataFrame()

    # Execute any Wrangles required (allow single or plural)
    if 'wrangles' in recipe.keys():
        df = _execute_wrangles(df, recipe['wrangles'])
    elif 'wrangle' in recipe.keys():
        df = _execute_wrangles(df, recipe['wrangle'])

    # Execute requested data exports
    if 'write' in recipe.keys():
        df = _write_data(df, recipe['write'], recipe.get('connections', {}))

    return df