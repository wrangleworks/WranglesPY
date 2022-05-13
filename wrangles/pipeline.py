"""
Create and execute Wrangling pipelines
"""

import pandas as _pandas
import numpy as _np
import yaml as _yaml
import logging as _logging
import re as _re
from . import select as _select
from . import format as _format
from . import classify as _classify
from . import extract as _extract
from . import translate as _translate
from . import connectors as _connectors
from .standardize import standardize as _standardize
import os as _os

# Temporary imports, used for Eric Demo Assets - replace these with long term solutions
from . import match as _match
from .make_table import make_table as _make_table
from . import ww_pd


_logging.getLogger().setLevel(_logging.INFO)


def _load_config(config: str, params: dict = {}) -> dict:
    """
    Load yaml config file + replace any placeholder variables

    :param config: Dictionary of parameters to define import
    :param params: (Optional) dictionary of custom parameters to override placeholders in the YAML file
    """
    # If config is a single line, it's probably a file path
    # Otherwise it's a recipe
    if "\n" in config:
        config_string = config
    else:
        with open(config, "r") as f:
            config_string = f.read()
    
    # Also add environment variables to list of placeholder variables
    # Q: Should we exclude some?
    for env_key, env_val in _os.environ.items():
        if env_key not in params.keys():
            params[env_key] = env_val

    # Replace templated values
    for key, val in params.items():
        config_string = config_string.replace("${" + key + "}", val)

    config_object = _yaml.safe_load(config_string)

    return config_object


def _execute_wrangles(df, wrangles_config):
    """
    Execute a list of Wrangles on a dataframe

    :param df: Dateframe that the Wrangles will be run against
    :param wrangles_config: List of Wrangles + their definitions to be executed
    :return: Pandas Dataframe of the Wrangled data
    """
    for step in wrangles_config:
        for wrangle, params in step.items():
            _logging.info(f": Wrangling :: {wrangle} :: {params.get('input', 'None')} >> {params.get('output', 'Dynamic')}")

            if wrangle == 'rename':
                # Rename a column
                df = df.rename(columns=params)

            elif wrangle.split('.')[0] == 'pandas':
                # Execute a pandas method
                # TODO: disallow any hidden methods
                df = getattr(df, wrangle.split('.')[1])(**params.get('parameters', {}))

            elif wrangle == 'create_column.own_index':
                # Create new counter colm that starts where we want
                start = params['parameters']['start']
                df[params['output']] = _np.arange(start, len(df)+start)

            elif wrangle == 'create_column.empty':
                df[params['output']] = None

            elif wrangle == 'create_column.constant':
                df[params['output']] = params['parameters']['value']

            elif wrangle == 'join':
                # Join a list to a string e.g. ['ele1', 'ele2', 'ele3'] -> 'ele1,ele2,ele3'
                df[params['output']] = _format.join_list(df[params['input']].tolist(), params['parameters']['char'])

            elif wrangle == 'concatenate':
                # Concatenate multiple inputs into one
                df[params['output']] = _format.concatenate(df[params['input']].astype(str).values.tolist(), params['parameters']['char'])

            elif wrangle == 'split':
                df[params['output']] = _format.split(df[params['input']].astype(str).tolist(), params['parameters']['char'])

            elif wrangle == 'convert.data_type':
                # 'int', 'float', 'str'
                df[params['output']] = df[params['input']].astype(params['parameters']['dataType'])
            
            elif wrangle == 'convert.case':
                if params['parameters']['case'].lower() == 'lower':
                    df[params['output']] = df[params['input']].str.lower()
                elif params['parameters']['case'].lower() == 'upper':
                    df[params['output']] = df[params['input']].str.upper()
                elif params['parameters']['case'].lower() == 'title':
                    df[params['output']] = df[params['input']].str.title()
                elif params['parameters']['case'].lower() == 'sentence':
                    df[params['output']] = df[params['input']].str.capitalize()

            elif wrangle == 'select.list_element':
                # Select a numbered element of a list (zero indexed)
                df[params['output']] = _select.list_element(df[params['input']].tolist(), params['parameters']['element'])

            elif wrangle == 'select.dictionary_element':
                # Select a named element of a dictionary
                df[params['output']] = _select.dict_element(df[params['input']].tolist(), params['parameters']['element'])

            elif wrangle == 'select.highest_confidence':
                # Select the option with the highest confidence. Inputs are expected to be of the form [<<value>>, <<confidence_score>>]
                df[params['output']] = _select.highest_confidence(df[params['input']].values.tolist())

            elif wrangle == 'select.threshold':
                # Select the first option if it exceeds a given threshold, else the second option
                df[params['output']] = _select.confidence_threshold(df[params['input'][0]].tolist(), df[params['input'][1]].tolist(), params['parameters']['threshold'])

            elif wrangle == 'format.price_breaks':
                df = _pandas.concat([df, _format.price_breaks(df[params['input']], params['parameters']['categoryLabel'], params['parameters']['valueLabel'])], axis=1)

            elif wrangle == 'classify':
                df[params['output']] = _classify(df[params['input']].astype(str).tolist(), **params['parameters'])

            elif wrangle == 'extract.attributes':
                df[params['output']] = _extract.attributes(df[params['input']].astype(str).tolist())

            elif wrangle == 'extract.codes':
                df[params['output']] = _extract.codes(df[params['input']].astype(str).tolist())

            elif wrangle == 'extract.custom':
                df[params['output']] = _extract.custom(df[params['input']].astype(str).tolist(), **params['parameters'])

            elif wrangle == 'extract.properties':
                df[params['output']] = _extract.properties(df[params['input']].astype(str).tolist())
            
            elif wrangle == 'standardize':
                df[params['output']] = _standardize(df[params['input']].astype(str).tolist(), **params['parameters'])

            elif wrangle == 'translate':
                df[params['output']] = _translate(df[params['input']].astype(str).tolist(), **params['parameters'])

            elif wrangle == 'placeholder.common_words':
                df = df.ww_pd.common_words(params['input'], params['parameters']['subtract'], WordsOnly=True)

            elif wrangle == 'match':
                df = _pandas.concat([df, _match.run(df[params['input']])], axis=1)

            else:
                _logging.error(f"UNKNOWN WRANGLE :: {wrangle} ::")

    return df


def run(recipe: str, params: dict = {}, dataframe = None):
    """
    Execute a YAML defined Wrangling pipeline
    
    :param recipe: YAML recipe or path to a YAML file containing the recipe
    :param params: (Optional) dictionary of custom parameters to override placeholders in the YAML file
    :param dataframe: (Optional) Pass in a pandas dataframe, instead of defining an import within the YAML
    """
    # Parse recipe
    _logging.info(": Loading Config ::")
    config = _load_config(recipe, params)

    if 'import' in config.keys():
        # Load appropriate data
        for import_type, params in config['import'].items():
            df = getattr(getattr(_connectors, import_type), 'input')(**params)
    elif dataframe is not None:
        df = dataframe
    else:
        raise ValueError('No input was provided. Either an import section must be added to the provided recipe, or a dataframe passed in as an argument.')

    # Execute any Wrangles required
    if 'wrangles' in config.keys():
        _logging.info(": Running Wrangles ::")
        df = _execute_wrangles(df, config['wrangles'])

    # Set initial dateframe to be as Wrangled
    df_return = df

    if 'export' in config.keys():
        _logging.info(": Exporting Data ::")

        # If user has entered a dictionary, add to a list
        # Used by following code
        if isinstance(config['export'], dict):
            exports = [config['export']]
        else:
            exports = config['export']

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
                    # Get export function of requested connector and pass dataframe + user defined params
                    getattr(getattr(_connectors, export_type), 'output')(df, **params)

    return df_return