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
from . import connectors as _connectors
from .standardize import standardize as _standardize

# Temporary imports, used for Eric Demo Assets - replace these with long term solutions
from . import match
from .make_table import make_table
from . import ww_pd


_logging.getLogger().setLevel(_logging.INFO)


def _load_config(config: str, params: dict = {}) -> dict:
    """
    Load yaml config file + replace any placeholder variables

    :param config: Dictionary of parameters to define import
    :param params: (Optional) dictionary of custom parameters to override placeholders in the YAML file
    """
    # config = None
    if "\n" in config:
        config_string = config
    else:
        with open(config, "r") as f:
            config_string = f.read()
    
    # Replace templated values
    for key, val in params.items():
        config_string = config_string.replace(r"{{" + key + r"}}", val)

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
                # df[params['output']] = df[params['input']].tolist()

            elif wrangle.split('.')[0] == 'pandas':
                # Execute a pandas method
                # TODO: disallow any hidden methods
                df = getattr(df, wrangle.split('.')[1])(**params)

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

            elif wrangle == 'placeholder.common_words':
                df = df.ww_pd.common_words(params['input'], params['parameters']['subtract'], WordsOnly=True)

            elif wrangle == 'match':
                df = _pandas.concat([df, match.run(df[params['input']])], axis=1)

            else:
                _logging.error(f"UNKNOWN WRANGLE :: {wrangle} ::")

    return df


def run(recipe: str, params: dict = {}):
    """
    Execute a YAML defined Wrangling pipeline
    
    :param recipe: YAML recipe or path to a YAML file containing the recipe
    :param params: (Optional) dictionary of custom parameters to override placeholders in the YAML file
    """
    # Parse recipe
    _logging.info(": Loading Config ::")
    config = _load_config(recipe, params)

    _logging.info(": Importing Data ::")
    for import_type, params in config['import'].items():
        if import_type == 'file':
            _logging.info(f": Importing File :: {params['name']}")
            df = _connectors.file.read(params)
        elif import_type == 'sql':
            _logging.info(f": Importing from SQL DB :: {params['host']}")
            df = _connectors.sql.read(params)

    if 'wrangles' in config.keys():
        _logging.info(": Running Wrangles ::")
        df = _execute_wrangles(df, config['wrangles'])

    if 'export' in config.keys():
        _logging.info(": Exporting Data ::")
        # Loop through all exports, get type and execute appropriate export
        for export in config['export']:
            for export_type, params in export.items():
                if export_type == 'file':
                    _logging.info(f": Exporting File :: {params['name']}")
                    _connectors.file.write(df, params)
                elif export_type == 'sql':
                    pass
                elif export_type == 'table':
                    if 'fields' in params.keys():
                        output_df = df[params['fields']]
                    else:
                        output_df = df
                    make_table(output_df, config['export']['name'], config['export'].get('sheet', 'Sheet1'))

    return df