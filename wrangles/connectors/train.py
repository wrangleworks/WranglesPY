import logging as _logging
import pandas as _pd
from ..train import train as _train
from .. import data as _data

class classify():
    _schema = {}

    def read(model_id: str) -> _pd.DataFrame:
        """
        Read the training data for a Classify Wrangle.

        :param model_id: Specific model to read.
        :returns: DataFrame containing the model's training data
        """
        tmp_data = _data.model_content(model_id)

        if 'Columns' in tmp_data:
            columns = tmp_data['Columns']
        elif len(tmp_data['Data'][0]) == 2:
            # Add a third column for Notes of empty strings
            [x.append('') for x in tmp_data['Data']]
            columns = ['Example', 'Category', 'Notes']
        elif len(tmp_data['Data'][0]) == 3:
            columns = ['Example', 'Category', 'Notes']
        else:
            raise ValueError("Classify Wrangle data should contain three columns. Check Wrangle data")

        return _pd.DataFrame(tmp_data['Data'], columns=columns)

    _schema["read"] = """
        type: object
        description: Read the training data for a Classify Wrangle
        additionalProperties: false
        required:
          - model_id
        properties:
          model_id:
            type: string
            description: Specific model to read
        """

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
        if not required_columns == list(df.columns[:3]):
            raise ValueError(f"The columns {', '.join(required_columns)} must be provided for train.classify.")

        _train.classify(df[required_columns].values.tolist(), name, model_id)

    _schema["write"] = """
        type: object
        description: Train a new or existing Classify Wrangle
        additionalProperties: false
        properties:
          name:
            type: string
            description: Name to give to a new Wrangle that will be created
          model_id:
            type: string
            description: Model to be updated. Either this or a name must be provided
          columns:
            type: array
            description: Columns to submit
        """


class extract():
    _schema = {}

    def read(model_id: str) -> _pd.DataFrame:
        """
        Read the training data for an Extract Wrangle.

        :param model_id: Specific model to read.
        :returns: DataFrame containing the model's training data
        """
        tmp_data = _data.model_content(model_id)

        if 'Columns' in tmp_data:
            columns = tmp_data['Columns']
        elif len(tmp_data['Data'][0]) == 2:
            # Add a third column for Notes of empty strings
            [x.append('') for x in tmp_data['Data']]
            columns = ['Entity to Find', 'Variation (Optional)', 'Notes']
        elif len(tmp_data['Data'][0]) == 3:
            columns = ['Entity to Find', 'Variation (Optional)', 'Notes']
        else:
            raise ValueError("Extract Wrangle data should contain three columns. Check Wrangle data")

        return _pd.DataFrame(tmp_data['Data'], columns=columns)

    _schema["read"] = """
        type: object
        description: Read the training data for an Extract Wrangle
        additionalProperties: false
        required:
          - model_id
        properties:
          model_id:
            type: string
            description: Specific model to read
        """

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
        if not required_columns == list(df.columns[:3]):
            raise ValueError(f"The columns {', '.join(required_columns)} must be provided for train.extract.")

        _train.extract(df[required_columns].values.tolist(), name, model_id)

    _schema["write"] = """
        type: object
        description: Train a new or existing Extract Wrangle
        additionalProperties: false
        properties:
          name:
            type: string
            description: Name to give to a new Wrangle that will be created
          model_id:
            type: string
            description: Model to be updated. Either this or a name must be provided
          columns:
            type: array
            description: Columns to submit
        """


class lookup():
    _schema = {}

    def read(model_id: str) -> _pd.DataFrame:
        """
        Read the training data for a Lookup Wrangle.

        :param model_id: Specific model to read.
        :returns: DataFrame containing the model's training data
        """
        content = _data.model_content(model_id)
        return _pd.DataFrame(content['Data'], columns=content['Columns'])

    # _schema["read"] = """
    #     type: object
    #     description: Read the training data for a Lookup Wrangle
    #     additionalProperties: false
    #     required:
    #       - model_id
    #     properties:
    #       model_id:
    #         type: string
    #         description: Specific model to read
    #     """

    def write(df: _pd.DataFrame, name: str = None, model_id: str = None, settings: dict = {}) -> None:
        """
        Train a new or existing lookup wrangle

        :param df: DataFrame to be written to a file
        :param name: Name to give to a new Wrangle that will be created
        :param model_id: Model to be updated. Either this or name must be provided
        :param settings: Specific settings to apply to the wrangle
        """
        _logging.info(": Training Lookup Wrangle")

        _train.lookup(
            {
                k.title(): v
                for k, v in df.to_dict(orient="tight").items()
                if k in ["columns", "data"]
            },
            name,
            model_id,
            settings
        )

    # _schema["write"] = """
    #     type: object
    #     description: Train a new or existing Classify Wrangle
    #     additionalProperties: false
    #     properties:
    #       name:
    #         type: string
    #         description: Name to give to a new Wrangle that will be created
    #       model_id:
    #         type: string
    #         description: Model to be updated. Either this or a name must be provided
    #       columns:
    #         type: array
    #         description: Columns to submit
    #     """

class standardize():
    _schema = {}

    def read(model_id: str) -> _pd.DataFrame:
        """
        Read the training data for a Standardize Wrangle.

        :param model_id: Specific model to read.
        :returns: DataFrame containing the model's training data
        """
        tmp_data = _data.model_content(model_id)

        if 'Columns' in tmp_data:
            columns = tmp_data['Columns']
        elif len(tmp_data['Data'][0]) == 2:
            # Add a third column for Notes of empty strings
            [x.append('') for x in tmp_data['Data']]
            columns = ['Find', 'Replace', 'Notes']
        elif len(tmp_data['Data'][0]) == 3:
            columns = ['Find', 'Replace', 'Notes']
        else:
            raise ValueError("Standardize Wrangle data should contain three columns. Check Wrangle data")

        return _pd.DataFrame(tmp_data['Data'], columns=columns)

    _schema["read"] = """
        type: object
        description: Read the training data for a Standardize Wrangle
        additionalProperties: false
        required:
          - model_id
        properties:
          model_id:
            type: string
            description: Specific model to read
        """

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
        if not required_columns == list(df.columns[:3]):
            raise ValueError(f"The columns {', '.join(required_columns)} must be provided for train.standardize.")

        _train.standardize(df[required_columns].values.tolist(), name, model_id)

    _schema["write"] = """
        type: object
        description: Train a new or existing Standardize Wrangle
        additionalProperties: false
        properties:
          name:
            type: string
            description: Name to give to a new Wrangle that will be created
          model_id:
            type: string
            description: Model to be updated. Either this or a name must be provided
          columns:
            type: array
            description: Columns to submit
        """