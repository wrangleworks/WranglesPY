"""
Methods to apply wrangles to a dataframe

Designed to fit into the yaml recipe framework for pipelines
"""
from . import classify as _classify
from . import extract as _extract
from . import format as _format
from . import select as _select
from .standardize import standardize as _standardize
from . import translate as _translate

import uuid as _uuid
import numpy as _np
import pandas as _pd

# Temporary imports, used for Eric Demo Assets - replace these with long term solutions
from . import match as _match
from . import ww_pd


def rename(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
    return df.rename(columns=params)


def classify(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
    """
    Run classify wrangles on the specified columns
    """
    if isinstance(params['input'], str):
        df[params['output']] = _classify(df[params['input']].astype(str).tolist(), **params['parameters'])
    elif isinstance(params['input'], list):
        # If a list of inputs is provided, ensure the list of outputs is the same length
        if len(params['input']) != len(params.get('output')):
            raise ValueError('If providing a list of inputs, a corresponding list of outputs must also be provided.')
        for input, output in zip(params['input'], params['output']):
            df[output] = _classify(df[input].astype(str).tolist(), **params['parameters'])
        
    return df


class convert():
    """
    Functions to convert data formats and representations
    """
    def case(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        if params['parameters']['case'].lower() == 'lower':
            df[params['output']] = df[params['input']].str.lower()
        elif params['parameters']['case'].lower() == 'upper':
            df[params['output']] = df[params['input']].str.upper()
        elif params['parameters']['case'].lower() == 'title':
            df[params['output']] = df[params['input']].str.title()
        elif params['parameters']['case'].lower() == 'sentence':
            df[params['output']] = df[params['input']].str.capitalize()

        return df

    def data_type(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        df[params['output']] = df[params['input']].astype(params['parameters']['dataType'])
        return df


class create():
    """
    Create a new column
    """
    def column(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        """
        Create a column with a user defined value. Defaults to None.
        """
        df[params['output']] = params.get('parameters', {}).get('value', None)
        return df

    def guid(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        """
        Create a column with a GUID
        """
        return create.uuid(df, params)

    def index(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        """
        Create a new incremental index.
        """
        start = params.get('parameters', {}).get('start', 1)
        df[params['output']] = _np.arange(start, len(df) + start)
        return df

    def uuid(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        """
        Create a column with a UUID
        """
        df[params['output']] = [_uuid.uuid4() for _ in range(len(df.index))]
        return df


class extract():
    """
    Run extraction wrangles
    """
    def address(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        df[params['output']] = _extract.address(df[params['input']].astype(str).tolist())
        return df

    def attributes(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        df[params['output']] = _extract.attributes(df[params['input']].astype(str).tolist())
        return df

    def codes(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        df[params['output']] = _extract.codes(df[params['input']].astype(str).tolist())
        return df

    def custom(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        df[params['output']] = _extract.custom(df[params['input']].astype(str).tolist(), **params['parameters'])
        return df

    def properties(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        df[params['output']] = _extract.properties(df[params['input']].astype(str).tolist())
        return df

class format():
    def price_breaks(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        """
        Rearrange price breaks
        """
        df = _pd.concat([df, _format.price_breaks(df[params['input']], params['parameters']['categoryLabel'], params['parameters']['valueLabel'])], axis=1)
        return df

class select():
    """
    Functions to select data from within columns
    """
    def list_element(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        """
        Select a numbered element of a list (zero indexed)
        """
        df[params['output']] = _select.list_element(df[params['input']].tolist(), params['parameters']['element'])
        return df

    def dictionary_element(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        """
        Select a named element of a dictionary
        """
        df[params['output']] = _select.dict_element(df[params['input']].tolist(), params['parameters']['element'])
        return df

    def highest_confidence(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        """
        Select the option with the highest confidence from multiple columns. Inputs are expected to be of the form [<<value>>, <<confidence_score>>]
        """
        df[params['output']] = _select.highest_confidence(df[params['input']].values.tolist())
        return df

    def threshold(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        """
        Select the first option if it exceeds a given threshold, else the second option

        The first option must be of the form [<<value>>, <<confidence_score>>]
        """
        df[params['output']] = _select.confidence_threshold(df[params['input'][0]].tolist(), df[params['input'][1]].tolist(), params['parameters']['threshold'])
        return df


def standardize(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
    """
    """
    df[params['output']] = _standardize(df[params['input']].astype(str).tolist(), **params['parameters'])
    return df

def translate(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
    """
    """
    df[params['output']] = _translate(df[params['input']].astype(str).tolist(), **params['parameters'])
    return df




def join(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
    """
    Join a list to a string e.g. ['ele1', 'ele2', 'ele3'] -> 'ele1,ele2,ele3'
    """
    df[params['output']] = _format.join_list(df[params['input']].tolist(), params['parameters']['char'])
    return df

def concatenate(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
    """
    Concatenate multiple columns into one
    """
    df[params['output']] = _format.concatenate(df[params['input']].astype(str).values.tolist(), params['parameters']['char'])
    return df

def split(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
    """
    Split to a string to multiple columns
    """
    df[params['output']] = _format.split(df[params['input']].astype(str).tolist(), params['parameters']['char'])
    return df

def expand(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
    """
    Expand an object to multiple columns
    """
    df[params['output']] = [x for x in df[params['input']].tolist()]
    return df


class placeholder():
    def common_words(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
        df = df.ww_pd.common_words(params['input'], params['parameters']['subtract'], WordsOnly=True)
        return df

def match(df: _pd.DataFrame, params: dict = {}) -> _pd.DataFrame:
    df = _pd.concat([df, _match.run(df[params['input']])], axis=1)
    return df