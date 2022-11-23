import logging as _logging
import pandas as _pd
from ..train import train as _train
from .. import data as _data

class classify():
    def read(model_id: str) -> _pd.DataFrame:
        """
        """
        tmp_data = _data.model_data(model_id, 'classify')

        if len(tmp_data[0]) == 2:
            columns = ['Example', 'Category']
        elif len(tmp_data[0]) == 3:
            columns = ['Example', 'Category', 'Notes']
        else:
            columns = None

        return _pd.DataFrame(tmp_data, columns=columns)

    def write(df: _pd.DataFrame, columns: list = None, name: str = None, model_id: str = None) -> None:
        """
        Train a new or existing classify wrangle

        :param df: Dataframe to be written to a file
        :param model_id: Model to be updated
        """
        _logging.info(": Training Classify Wrangle")

        # Select only specific columns if user requests them
        if columns is not None: df = df[columns]

        _train.classify(df.values.tolist(), name, model_id)


class extract():
    def read(model_id: str) -> _pd.DataFrame:
        """
        """
        tmp_data = _data.model_data(model_id, 'extract')

        if len(tmp_data[0]) == 2:
            columns = ['Entity to Find', 'Variation (Optional)']
        elif len(tmp_data[0]) == 3:
            columns = ['Entity to Find', 'Variation (Optional)', 'Notes']
        else:
            columns = None

        return _pd.DataFrame(tmp_data, columns=columns)

    def write(df: _pd.DataFrame, columns: list = None, name: str = None, model_id: str = None) -> None:
        """
        Train a new or existing extract wrangle

        :param df: Dataframe to be written to a file
        :param model_id: Model to be updated
        """
        _logging.info(f": Training Extract Wrangle")

        # Select only specific columns if user requests them
        if columns is not None: df = df[columns]

        _train.extract(df.values.tolist(), name, model_id)


class standardize():
    def read(model_id: str) -> _pd.DataFrame:
        """
        """
        tmp_data = _data.model_data(model_id, 'standardize')

        if len(tmp_data[0]) == 2:
            columns = ['Find', 'Replace']
        elif len(tmp_data[0]) == 3:
            columns = ['Find', 'Replace', 'Notes']
        else:
            columns = None

        return _pd.DataFrame(tmp_data, columns=columns)

    def write(df: _pd.DataFrame, columns: list = None, name: str = None, model_id: str = None) -> None:
        """
        Train a new or existing standardize wrangle

        :param df: Dataframe to be written to a file
        :param model_id: Model to be updated
        """
        _logging.info(f": Training Standardize Wrangle")

        # Select only specific columns if user requests them
        if columns is not None: df = df[columns]

        _train.standardize(df.values.tolist(), name, model_id)
