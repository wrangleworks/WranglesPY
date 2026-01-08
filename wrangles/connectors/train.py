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

        # Lookup the variant if retraining a model
        if variant == None:
            variant = _model(model_id)['variant']
            if variant == None: # Older versions do not have a variant, default to pattern
                variant = 'pattern'

        if variant == 'pattern':
            versions = [
                {'columns': ['Find', 'Output (Optional)', 'Notes'], 'version': 'pattern 2.0'},
                {'columns': ['Entity to Find', 'Variation (Optional)', 'Notes'], 'version': 'pattern 1.0'},
                {'columns': ['Find', 'Output', 'Notes'], 'version': 'pattern 3.0'},
            ]
            try:
                required_columns = [
                        version for version in versions
                        if set(version["columns"]).issubset(set(df.columns.to_list()))
                    ][0]['columns']
            except:
                required_columns = ['Find', 'Output (Optional)', 'Notes']
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
        if action.upper() == 'OVERWRITE':
            # Read in variant if there is a model_id
            if name and model_id:
                raise ValueError("Name and model_id cannot both be provided, please use name to create a new model or model_id to update an existing model.") 
            if model_id:
                metadata = _data.model(model_id)
                variant = metadata['variant']
        
            if variant == 'semantic':
                variant = 'embedding'

            settings['variant'] = variant

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
        elif action.upper() == 'UPSERT':
            if name and model_id:
                raise ValueError("Name and model_id cannot both be provided, please use name to create a new model or model_id to update an existing model.") 
            # Prepare new data  
            new_data = {  
                k.title(): v  
                for k, v in df.to_dict(orient="tight").items()  
                if k in ["columns", "data"]  
            }  
            
            if model_id:  
                # Row-level upsert for existing model  
                existing_content = _data.model_content(model_id)  
                existing_df = _pd.DataFrame(  
                    existing_content['Data'],   
                    columns=existing_content['Columns']  
                )[new_data['Columns']]  # Ensure same column order
                
                # Get variant from existing model  
                metadata = _data.model(model_id)  
                variant = metadata['variant']  
                if variant == 'semantic':  
                    variant = 'embedding'  
                settings['variant'] = variant  
                
                # Merge data - avoid duplicates based on Key column  
                if variant == 'key' and 'Key' in existing_df.columns and 'Key' in df.columns:            
                    if df['Key'].duplicated().any():  
                        raise ValueError("Lookup: All Keys must be unique")
                    # For key lookups, remove existing keys from new data  
                    existing_keys = set(existing_df['Key'].tolist())  
                    new_rows = df[~df['Key'].isin(existing_keys)]  
                    merged_df = _pd.concat([existing_df, new_rows], ignore_index=True)  
                else:  
                    # For semantic lookups or no Key column, append all new data  
                    merged_df = _pd.concat([existing_df, df], ignore_index=True)  
                
                # Convert merged data back to required format  
                merged_data = {  
                    'Columns': merged_df.columns.tolist(),  
                    'Data': merged_df.values.tolist()  
                }  
                
                # Update with merged data  
                _train.lookup(merged_data, None, model_id, settings)            
            else:  
                # Standard create/update logic  
                if model_id:  
                    metadata = _data.model(model_id)  
                    variant = metadata['variant']  
                if variant == 'semantic':  
                    variant = 'embedding'  
                settings['variant'] = variant  
                _train.lookup(new_data, name, model_id, settings)
    

        elif action.upper() == 'UPDATE':  
            # Verify model exists  
            try:  
                metadata = _data.model(model_id)  
                if metadata.get('message') == 'error':  
                    raise ValueError(f"Lookup model '{model_id}' not found")  
            except:  
                raise ValueError(f"Lookup model '{model_id}' not found")  
            
            # Get existing model data  
            existing_data = _data.model_content(model_id)  
            existing_df = _pd.DataFrame(existing_data['Data'], columns=existing_data['Columns'])  
             
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
                    
                df = merged_df  
            else:  
                raise ValueError("Both DataFrames must contain 'Key' column")  
        
            # Preserve existing variant  
            variant = metadata.get('variant', 'key')  
            if variant == 'semantic':  
                variant = 'embedding'  
            settings['variant'] = variant  
                
            # Retrain the model with updated data  
            _train.lookup(  
                {  
                    k.title(): v  
                    for k, v in df.to_dict(orient="tight").items()  
                    if k in ["columns", "data"]  
                },  
                None,  # No name for update  
                model_id,  
                settings  
)
        elif action.upper() == 'INSERT':  
            if not name:  
                raise ValueError("INSERT action requires 'name' parameter")  
            if model_id:  
                raise ValueError("INSERT action cannot use 'model_id' parameter")  

            settings['variant'] = variant 
            
            _train.lookup(  
                {k.title(): v for k, v in df.to_dict(orient="tight").items()   
                if k in ["columns", "data"]},  
                name, None, settings  
            )  
        
        else:  
            raise ValueError(f"Unsupported action: {action}. Use INSERT, UPDATE, UPSERT or OVERWRITE")

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
