import logging as _logging
import pandas as _pd
from ..train import train as _train
from .. import data as _data
from ..utils import wildcard_expansion as _wildcard_expansion
from ..data import model as _model

class classify():
    _schema = {}

    def read(model_id: str) -> _pd.DataFrame:
        """
        Read the training data for a Classify Wrangle.

        :param model_id: Specific model to read.
        :returns: DataFrame containing the model's training data
        """
        _logging.info(f": Reading Classify Wrangle data :: {model_id}")

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
        if columns is not None:
            columns = _wildcard_expansion(df.columns, columns)
            df = df[columns]

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
        _logging.info(f": Reading Extract Wrangle data :: {model_id}")

        tmp_data = _data.model_content(model_id)

        if 'Columns' in tmp_data:
            columns = tmp_data['Columns']
        elif len(tmp_data['Data'][0]) == 2:
            # Add a third column for Notes of empty strings
            [x.append('') for x in tmp_data['Data']]
            columns = ['Find', 'Output', 'Notes']
        elif len(tmp_data['Data'][0]) == 3:
            columns = ['Find', 'Output', 'Notes']
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

    def write(
        df: _pd.DataFrame,
        columns: list = None,
        name: str = None,
        model_id: str = None,
        variant: str = None
    ) -> None:
        """
        Train a new or existing extract wrangle

        :param df: DataFrame to be written to a file
        :param columns: Subset of columns to use from the DataFrame
        :param name: Name to give to a new Wrangle that will be created
        :param model_id: Model to be updated. Either this or name must be provided
        """
        _logging.info(f": Training Extract Wrangle")

        # Error handling for name, model_id and settings
        if name and model_id:
            raise ValueError("Extract: Name and model_id cannot both be provided, please use name to create a new model or model_id to update an existing model.")
        
        if name is None and model_id is None:
            raise ValueError("Extract: Either a name or a model id must be provided. Use name to create a new model or model_id to update an existing model.")

        if variant not in ['pattern', 'ai', None]:
            raise ValueError("The variant must be either 'pattern' or 'ai'")

        # Error handling for variant
        if variant == 'ai':
            variant = 'extract-ai'

        if model_id and variant:
            raise ValueError(f"It is not possible to set the variant of an existing model.")

        # Select only specific columns if user requests them
        if columns is not None:
            columns = _wildcard_expansion(df.columns, columns)
            df = df[columns]

        # Older versions do not have a variant, default to pattern
        if variant is None and name:
            variant = 'pattern'
        # Lookup the variant if retraining a model
        if variant is None and model_id:
            variant = _model(model_id).get('variant') or 'pattern'

        if variant == 'pattern':
            versions = [
                {'columns': ['Find', 'Output', 'Notes'], 'version': 'pattern 3.0'},
                {'columns': ['Find', 'Output (Optional)', 'Notes'], 'version': 'pattern 2.0'},
                {'columns': ['Entity to Find', 'Variation (Optional)', 'Notes'], 'version': 'pattern 1.0'}
            ]
            try:
                required_columns = [
                        version for version in versions
                        if set(version["columns"]).issubset(set(df.columns.to_list()))
                    ][0]['columns']
            except:
                required_columns = ['Find', 'Output', 'Notes']
            col_len = 3
        elif variant == 'extract-ai':
            required_columns = ['Find', 'Description', 'Type', 'Default', 'Examples', 'Enum', 'Notes']
            col_len = 7
        if not required_columns == list(df.columns[:col_len]):
            raise ValueError(f"The columns {', '.join(required_columns)} must be provided for train.extract.")

        _train.extract(df[required_columns].values.tolist(), name, model_id, variant)

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
        _logging.info(f": Reading Lookup Wrangle data :: {model_id}")

        content = _data.model_content(model_id)
        return _pd.DataFrame(content['Data'], columns=content['Columns'])

    _schema["read"] = """
        type: object
        description: Read the training data for a Lookup Wrangle
        additionalProperties: false
        required:
          - model_id
        properties:
          model_id:
            type: string
            description: Specific model to read
        """

    def write(df: _pd.DataFrame, name: str = None, model_id: str = None, settings: dict = {}, variant: str = 'key', action: str = 'overwrite') -> None:
        """
        Train a new or existing lookup wrangle

        :param df: DataFrame to be written to a file
        :param name: Name to give to a new Wrangle that will be created
        :param model_id: Model to be updated. Either this or name must be provided
        :param settings: Specific settings to apply to the wrangle
        :param variant: Variant of the Lookup Wrangle that will be created (key or semantic)
        :param action: Action to take when training the lookup wrangle (insert, update, upsert)
        """
        _logging.info(f": Training Lookup Wrangle")

        # Error handling for name, model_id and settings
        if name and model_id:
            raise ValueError("Lookup: Name and model_id cannot both be provided, please use name to create a new model or model_id to update an existing model.")
        

        # Normalize inputs and avoid mutating default args
        act = (action or 'overwrite').upper()
        settings = dict(settings or {})

        def _get_columns_from_payload(payload):
            # payload can be a DataFrame or the 'tight' dict produced by _to_tight
            if isinstance(payload, dict) and 'Columns' in payload:
                return payload['Columns']
            try:
                return list(payload.columns)
            except Exception:
                return []

        def _validate_matching_columns(payload, settings_dict):
            matching = settings_dict.get('MatchingColumns')
            if not matching:
                return
            # Accept both string and list for MatchingColumns
            if isinstance(matching, str):
                matching = [matching]
            elif not isinstance(matching, list):
                raise TypeError("MatchingColumns must be a string or a list of strings")
            cols = _get_columns_from_payload(payload)
            missing = [c for c in matching if c not in cols]
            if missing:
                raise ValueError(
                    "Lookup: The following MatchingColumns are not present in the provided data: "
                    + ", ".join(missing)
                )

        def _to_tight(dataframe: _pd.DataFrame) -> dict:
            return {
                k.title(): v
                for k, v in dataframe.to_dict(orient="tight").items()
                if k in ["columns", "data"]
            }

        def _normalize_variant(mid: str, var: str) -> str:
            v = var
            if mid:
                try:
                    md = _data.model(mid)
                    v = md.get('variant', v)
                except Exception:
                    pass
            if v == 'semantic':
                v = 'embedding'
            return v

        def _set_variant(mid: str, var: str) -> str:
            v = _normalize_variant(mid, var)
            settings['variant'] = v
            return v

        
        _set_variant(model_id, variant)
        if act.upper() not in ['INSERT', 'UPDATE', 'UPSERT', 'OVERWRITE']:
            raise ValueError(f"Unsupported action: {action}. Use INSERT, UPDATE, UPSERT or OVERWRITE(default)")

        elif act == 'OVERWRITE' or name:
            row_count = len(df)
            _validate_matching_columns(df, settings)
            _train.lookup(
                _to_tight(df),
                name,
                model_id,
                settings
            )
            _logging.info(f"Lookup OVERWRITE: {row_count} rows written. Total rows: {row_count}.")

        elif act == 'UPSERT':
            new_data = _to_tight(df)
            if model_id:
                # Row-level upsert for existing model
                existing_content = _data.model_content(model_id)
                existing_df_all = _pd.DataFrame(
                    existing_content['Data'],
                    columns=existing_content['Columns']
                )

                # Validate column compatibility with existing model
                requested_cols = new_data['Columns']
                missing_in_existing = [c for c in requested_cols if c not in existing_df_all.columns]
                if missing_in_existing:
                    raise ValueError(
                        "Lookup: The following columns are not present in the existing model: "
                        + ", ".join(missing_in_existing)
                    )

                existing_df = existing_df_all[requested_cols]  # Ensure same column order

                # For key variant, ensure new data contains Key column
                normalized_variant = settings.get('variant', variant)
                if normalized_variant == 'key' and 'Key' not in df.columns:
                    raise ValueError("Lookup: 'Key' column must be provided for 'key' variant")

                inserted = 0
                updated = 0

                # Merge data - avoid duplicates based on Key column
                if variant== 'key' and 'Key' in existing_df.columns and 'Key' in df.columns:
                    if df['Key'].duplicated().any():
                        raise ValueError("Lookup: All Keys must be unique")
                    existing_keys = set(existing_df['Key'].tolist())

                    # Start with current data
                    merged_df = existing_df.copy()

                    # Apply updates for matching keys
                    for _, row in df.iterrows():
                        key = row['Key']
                        if key in existing_keys:
                            mask = merged_df['Key'] == key
                            for col in df.columns:
                                if col != 'Key' and col in merged_df.columns:
                                    merged_df.loc[mask, col] = row[col]
                            updated += 1
                        else:
                            # Insert new rows for non-existing keys
                            merged_df = _pd.concat(
                                [merged_df, _pd.DataFrame([row[merged_df.columns].tolist()], columns=merged_df.columns)],
                                ignore_index=True
                            )
                            inserted += 1
                else:
                    # For non-key variants, just append all data
                    merged_df = _pd.concat([existing_df, df], ignore_index=True)
                    inserted = len(df)

                merged_data = {
                    'Columns': merged_df.columns.tolist(),
                    'Data': merged_df.values.tolist()
                }
                _validate_matching_columns(merged_data, settings)
                total_rows = len(merged_df)
                _train.lookup(merged_data, None, model_id, settings)
                _logging.info(f"Lookup UPSERT: {inserted} rows inserted, {updated} rows updated. Total rows: {total_rows}.")
            else:
                inserted = len(df)
                _validate_matching_columns(new_data, settings)
                _train.lookup(new_data, name, None, settings)
                _logging.info(f"Lookup UPSERT (new): {inserted} rows inserted. Total rows: {inserted}.")

        elif act == 'UPDATE':
            metadata = _data.model(model_id)

            # Get existing model data
            existing_data = _data.model_content(model_id)
            existing_df = _pd.DataFrame(existing_data['Data'], columns=existing_data['Columns'])

            updated = 0

            # Determine the effective variant for this model (normalize semantic -> embedding)
            normalized_variant = _normalize_variant(model_id, metadata.get('variant', 'key'))

            # Column alignment check
            missing_in_existing = [c  for c in df.columns if c not in existing_df.columns]
            if missing_in_existing:
                raise ValueError(
                    "Lookup: The following columns are not present in the existing model: "
                    + ", ".join(missing_in_existing)
                )

            if normalized_variant == 'key':
                # Key-based model: require 'Key' in both DataFrames and perform merge/update
                if 'Key' in df.columns and 'Key' in existing_df.columns:
                    # Only update records that exist in the model
                    existing_keys = set(existing_df['Key'].tolist())
                    df_filtered = df[df['Key'].isin(existing_keys)].copy()

                    if df_filtered.empty:
                        _logging.info("No matching keys found in existing model. No updates performed.")
                        return

                    # Merge with existing data
                    merged_df = existing_df.copy()
                    for idx, row in df_filtered.iterrows():
                        key = row['Key']
                        mask = merged_df['Key'] == key
                        for col in df_filtered.columns:
                            if col != 'Key':
                                merged_df.loc[mask, col] = row[col]
                        updated += 1

                    df = merged_df
                else:
                    raise ValueError("Both DataFrames must contain 'Key' column")
                settings['variant'] = normalized_variant
                total_rows = len(df)
                _train.lookup(
                    _to_tight(df),
                    None,
                    model_id,
                    settings
                )
                _logging.info(f"Lookup UPDATE: {updated} rows updated. Total rows: {total_rows}.")
            else:
                # Semantic/embedding model: allow UPDATE without 'Key' and replace model content
                settings['variant'] = normalized_variant
                _validate_matching_columns(df, settings)
                total_rows = len(df)
                _train.lookup(
                    _to_tight(df),
                    None,
                    model_id,
                    settings
                )
                _logging.info(f"Lookup UPDATE: replaced model data. Total rows: {total_rows}.")
                return

        elif act == 'INSERT':  
            if not model_id:  
                raise ValueError("INSERT action requires 'model_id' parameter for existing model")  
            if name:  
                raise ValueError("INSERT action cannot use 'name' parameter when updating existing model")  
            
            # Get existing data  
            existing_content = _data.model_content(model_id)  
            existing_df = _pd.DataFrame(  
                existing_content['Data'],  
                columns=existing_content['Columns']  
            )  
            
            # Column alignment check
            missing_in_existing = [c for c in df.columns if c not in existing_df.columns]
            if missing_in_existing:
                raise ValueError(
                    "Lookup: The following columns are not present in the existing model: "
                    + ", ".join(missing_in_existing)
                )

            inserted = 0
            # Only add rows with new keys (skip existing keys)  
            if variant == 'key' and 'Key' in existing_df.columns and 'Key' in df.columns:  
                if df['Key'].duplicated().any():  
                    raise ValueError("Lookup: All Keys must be unique")  
                existing_keys = set(existing_df['Key'].tolist())  
                new_rows = df[~df['Key'].isin(existing_keys)]  
                inserted = len(new_rows)
                merged_df = _pd.concat([existing_df, new_rows], ignore_index=True)  
            else:  
                # For non-key variants, just append all data  
                inserted = len(df)
                merged_df = _pd.concat([existing_df, df], ignore_index=True)  
            
            merged_data = {  
                'Columns': merged_df.columns.tolist(),  
                'Data': merged_df.values.tolist()  
            }  
            _validate_matching_columns(merged_data, settings)
            total_rows = len(merged_df)
            _train.lookup(merged_data, None, model_id, settings)
            _logging.info(f"Lookup INSERT: {inserted} rows inserted. Total rows: {total_rows}.")

    _schema["write"] = """
        type: object
        description: Train a new or existing Lookup Wrangle
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
          variant:
            type: string
            description: Variant of the Lookup Wrangle that will be created
            enum:
              - key
              - semantic
        action:
            type: string
            description: Action to take when training the lookup wrangle
            enum:
              - insert
              - update
              - upsert
              - overwrite
        """

class standardize():
    _schema = {}

    def read(model_id: str) -> _pd.DataFrame:
        """
        Read the training data for a Standardize Wrangle.

        :param model_id: Specific model to read.
        :returns: DataFrame containing the model's training data
        """
        _logging.info(f": Reading Standardize Wrangle data :: {model_id}")

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
        if columns is not None:
            columns = _wildcard_expansion(df.columns, columns)
            df = df[columns]

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
