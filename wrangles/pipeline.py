"""
Create and execute Wrangling pipelines
"""

import pandas as _pandas
import yaml as _yaml
import logging as _logging
from . import connectors as _connectors
import os as _os
from . import pipeline_wrangles as _pipeline_wrangles

# Temporary imports, used for Eric Demo Assets - replace these with long term solutions
from .make_table import make_table as _make_table


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


def _execute_wrangles(df, wrangles_list):
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
                # Get the requested function from the pipeline_wrangles module
                obj = _pipeline_wrangles
                for element in wrangle.split('.'):
                    obj = getattr(obj, element)

                # Execute the requested function and return the value
                df = obj(df, params)

    return df


def run(recipe: str, params: dict = {}, dataframe = None):
    """
    Execute a YAML defined Wrangling pipeline
    
    :param recipe: YAML recipe or path to a YAML file containing the recipe
    :param params: (Optional) dictionary of custom parameters to override placeholders in the YAML file
    :param dataframe: (Optional) Pass in a pandas dataframe, instead of defining an import within the YAML
    """
    # Parse recipe
    recipe = _load_recipe(recipe, params)

    # Get requested data
    if 'import' in recipe.keys():
        # Allow blended imports
        if list(recipe['import'])[0] in ['concatenate', 'merge']:
            # Get data from sources
            dfs = []
            for source in recipe['import'][list(recipe['import'])[0]]['sources']:
                import_type = list(source)[0]
                params = source[import_type]
                dfs.append(getattr(getattr(_connectors, import_type), 'read')(**params))

            if list(recipe['import'])[0] == 'concatenate':
                # Blend as a concatenation - stack data depending on axis (e.g. union)
                df = _pandas.concat(dfs, **recipe['import']['concatenate'].get('parameters', {}))
            elif list(recipe['import'])[0] == 'merge':
                # Blend as a merge - equivalent to database join
                df = _pandas.merge(dfs[0], dfs[1], **recipe['import']['merge'].get('parameters', {}))
            # Clear from memory in case this is a large object
            del dfs
        else:
            # Load appropriate data
            for import_type, params in recipe['import'].items():
                df = getattr(getattr(_connectors, import_type), 'read')(**params)
    elif dataframe is not None:
        # User has passed in a pre-created dataframe
        df = dataframe
    else:
        # User hasn't provided anything
        raise ValueError('No input was provided. Either an import section must be added to the provided recipe, or a dataframe passed in as an argument.')

    # Execute any Wrangles required
    if 'wrangles' in recipe.keys():
        df = _execute_wrangles(df, recipe['wrangles'])

    # Set initial dateframe to be as Wrangled
    df_return = df

    if 'export' in recipe.keys():
        # If user has entered a dictionary, add to a list
        if isinstance(recipe['export'], dict):
            exports = [recipe['export']]
        else:
            exports = recipe['export']

        # Loop through all exports, get type and execute appropriate export
        for export in exports:
            for export_type, params in export.items():
                if export_type == 'dataframe':
                    # Define the dataframe that is returned
                    df_return = df[params['fields']]

                elif export_type == 'table':
                    # Eric's custom code for demo
                    if 'fields' in params.keys():
                        output_df = df[params['fields']]
                    else:
                        output_df = df
                    _make_table(output_df, export['name'], export.get('sheet', 'Sheet1'))
                
                else:
                    # Get output function of requested connector and pass dataframe + user defined params
                    getattr(getattr(_connectors, export_type), 'write')(df, **params)

    return df_return