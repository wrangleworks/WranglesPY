import logging as _logging
import pandas as _pd
from ..train import train as _train
from .. import data as _data

class classify():
    def read(model_id: str) -> _pd.DataFrame:
        """
        Read the training data for a Classify Wrangle.

        :param model_id: Specific model to read.
        :returns: DataFrame containing the model's training data
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

        :param df: DataFrame to be written to a file
        :param columns: Subset of columns to use from the DataFrame
        :param name: Name to give to a new Wrangle that will be created
        :param model_id: Model to be updated. Either this or name must be provided
        """
        _logging.info(": Training Classify Wrangle")

        # Select only specific columns if user requests them
        if columns is not None: df = df[columns]

        required_columns = ['Example', 'Category', 'Notes']
        if not required_columns == list(df.columns):
            raise ValueError(f"The columns {', '.join(required_columns)} must be provided for train.classify.")

        _train.classify(df[required_columns].values.tolist(), name, model_id)


class extract():
    def read(model_id: str) -> _pd.DataFrame:
        """
        Read the training data for an Extract Wrangle.

        :param model_id: Specific model to read.
        :returns: DataFrame containing the model's training data
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

        :param df: DataFrame to be written to a file
        :param columns: Subset of columns to use from the DataFrame
        :param name: Name to give to a new Wrangle that will be created
        :param model_id: Model to be updated. Either this or name must be provided
        """
        _logging.info(f": Training Extract Wrangle")

        # Select only specific columns if user requests them
        if columns is not None: df = df[columns]

        required_columns = ['Entity to Find', 'Variation (Optional)', 'Notes']
        if not required_columns == list(df.columns):
            raise ValueError(f"The columns {', '.join(required_columns)} must be provided for train.extract.")

        _train.extract(df[required_columns].values.tolist(), name, model_id)


class standardize():
    def read(model_id: str) -> _pd.DataFrame:
        """
        Read the training data for a Standardize Wrangle.

        :param model_id: Specific model to read.
        :returns: DataFrame containing the model's training data
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

        :param df: DataFrame to be written to a file
        :param columns: Subset of columns to use from the DataFrame
        :param name: Name to give to a new Wrangle that will be created.
        :param model_id: Model to be updated. Either this or name must be provided.
        """
        _logging.info(f": Training Standardize Wrangle")

        # Select only specific columns if user requests them
        if columns is not None: df = df[columns]

        required_columns = ['Find', 'Replace', 'Notes']
        if not required_columns == list(df.columns):
            raise ValueError(f"The columns {', '.join(required_columns)} must be provided for train.standardize.")

        _train.standardize(df[required_columns].values.tolist(), name, model_id)
