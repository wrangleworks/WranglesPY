"""
Train new models
"""
from typing import Union as _Union
from . import config as _config
from . import auth as _auth
from . import utils as _utils
from . import data as _data
import logging as _logging
import requests as _requests


class train():
    """
    Train new models
    """
    def classify(training_data: list, name: str = None, model_id: str = None):
        """
        Train a classification model. This can predict the category of a text input.
        Requires WrangleWorks Account and Subscription.
        
        :param training_data: paired list of examples and labels.
        :param name: If provided, will create a new model with this name.
        :param model_id: If provided, will update this model.
        """
        # If input is a list, check to make sure that all sublists are length of 2
        if isinstance(training_data, list):
            check_index = [training_data.index(x) for x in training_data if len(x) != 3 or '' in x[:2]]
            if len(check_index) != 0:
                raise ValueError(f'Training_data list must contain a list of two non-empty elements, plus optional Notes. Check element(s) {check_index} in training_list.\nFormat:\nFirst element is "Example"\nSecond Element is "Category" -- \'\' is not valid.\n'
                "Example:[['Rice', 'Grain', '']]")
            # checking the first element in training list
            if training_data[0] != ['Example', 'Category', 'Notes']:
                training_data = [['Example', 'Category', 'Notes']] + training_data
        
        if name:
            _logging.info(f": Creating new classify model :: {name}")
            response = _requests.post(
                        f'{_config.api_host}/model/content',
                        params={'type':'classify', 'name': name},
                        headers={'Authorization': f'Bearer {_auth.get_access_token()}'},
                        json=training_data
                    )
        elif model_id:
            # Only use retries when retraining an existing model
            _logging.info(f": Updating classify model :: {model_id}")
            response = _utils.request_retries(
                        request_type='PUT',
                        url=f'{_config.api_host}/model/content',
                        **{
                            'params': {'type':'classify', 'model_id': model_id},
                            'headers': {'Authorization': f'Bearer {_auth.get_access_token()}'},
                            'json': training_data
                        }
                    )
        else:
            raise ValueError('Either a name or a model id must be provided')

        # If we created a new model, try to log the new model id for users
        try:
            if name and response is not None and response.ok:
                _json = response.json()
                modelid = (
                    _json.get('model_id') or _json.get('id') or _json.get('modelId') or _json.get('model')
                )
                if modelid:
                    _logging.info(f": New classify model created :: {modelid}")
                else:
                    _logging.info(f": Classify model created. Response: {response.text}")
        except Exception:
            _logging.info(": Classify model created (could not parse model id from response)")

        return response

    def extract(training_data: list, name: str = None, model_id: str = None, variant: str = None):
        """
        Train an extraction model. This can extract custom entities from the input.
        Requires WrangleWorks Account and Subscription.
        
        :param training_data: paired list of entities to find and optional standard representation of that entitiy.
        :param name: If provided, will create a new model with this name.
        :param model_id: If provided, will update this model.
        """
        # If input is a list, check to make sure that all sublists are length of 2
        # Must have both values filled ('' counts as filled, None does not count)
        if isinstance(training_data, list) and variant in (None, 'pattern'):
            check_index = [training_data.index(x) for x in training_data if len(x) != 3]
            if len(check_index) != 0: # If an index does not have len() of 2 then raise error
                raise ValueError(f"Training_data list must contain a list of two elements, plus optional Notes. Check element(s) {check_index} in training_list.\nFormat:\nFirst element is 'Entity to Find'\nSecond Element is 'Variation', If no variation, use \'\'\n"
                "Example:[['Television', 'TV', '']]")
            # checking the first element in training list
            if training_data[0] != ['Find', 'Output', 'Notes']:
                training_data = [['Find', 'Output', 'Notes']] + training_data
        
        # If input is a list, check to make sure that all sublists are length of 7
        # Must have all values filled ('' counts as filled, None does not count)
        if isinstance(training_data, list) and variant == 'extract-ai':
            check_index = [training_data.index(x) for x in training_data if len(x) != 7]
            if len(check_index) != 0: # If an index does not have len() of 6 then raise error
                raise ValueError(f"Training_data list must contain a list of six elements, plus optional Notes. Check element(s) {check_index} in training_list.\nFormat:\nFirst element is 'Find'\nSecond Element is 'Description', If no variation, use \'\'\n"
                # This example needs to be updated with the 5 other columns
                "Example:[['Colour', 'The colour of the item']]")
            # checking the first element in training list
            if training_data[0] != ['Find', 'Description', 'Type', 'Default', 'Examples', 'Enum', 'Notes']:
                training_data = [['Find', 'Description', 'Type', 'Default', 'Examples', 'Enum', 'Notes']] + training_data
        
        if name:
            _logging.info(f": Creating new extract model :: {name}")
            response = _requests.post(
                        f'{_config.api_host}/model/content',
                        params={'type':'extract', 'name': name, 'variant': variant},
                        headers={'Authorization': f'Bearer {_auth.get_access_token()}'},
                        json=training_data
                    )
        elif model_id:
            _logging.info(f": Updating extract model :: {model_id}")
            # Only use retries when retraining an existing model
            response = _utils.request_retries(
                        request_type='PUT',
                        url=f'{_config.api_host}/model/content',
                        **{
                            'params': {'type':'extract', 'model_id': model_id},
                            'headers': {'Authorization': f'Bearer {_auth.get_access_token()}'},
                            'json': training_data
                        }
                    )
        else:
            raise ValueError('Either a name or a model id must be provided')

        # Log model id when a new extract model is created
        try:
            if name and response is not None and response.ok:
                _json = response.json()
                modelid = (
                    _json.get('model_id') or _json.get('id') or _json.get('modelId') or _json.get('model')
                )
                if modelid:
                    _logging.info(f": New extract model created :: {modelid}")
                else:
                    _logging.info(f": Extract model created. Response: {response.text}")
        except Exception:
            _logging.info(": Extract model created (could not parse model id from response)")

        return response

    def lookup(
        data: _Union[dict, list],
        name: str = None,
        model_id: str = None,
        settings: dict = None
    ):
        """
        Train a lookup model. This can be used as reference data to look values up from.

        Requires WrangleWorks Account and Subscription.
        
        :param training_data: 2D array of training data. Must contain the column Key as the first column.
        :param name: If provided, will create a new model with this name.
        :param model_id: If provided, will update this model.
        :param settings: Specific settings to apply to the lookup wrangle.
        """
        # Ensure settings is a dictionary even if not provided
        if settings is None:
            settings = {}

        # Read in variant
        if name:
            variant = settings.get("variant", "key")
        elif model_id:
            metadata = _data.model(model_id)
            variant = metadata['variant']
        else:
            raise ValueError('Lookup: Either a name or a model id must be provided')

        # Validate input
        if isinstance(data, list):
            if len(data) < 2:
                raise ValueError("Lookup: The data must contain at least 1 header row and 1 row of contents")
            
            if not isinstance(data[0], list):
                raise ValueError("Lookup: The data must be a 2D array.")

            if variant == "key" and not data[0][0] == "Key":
                raise ValueError("Lookup: Column 1 must be named Key")
            
        elif isinstance(data, dict):
            if not "Columns" in data or not "Data" in data:
                raise ValueError(
                    "Lookup: The data must be a dictionary of the format {'Data': [[]], 'Columns': [], 'Settings': {}}"
                )
            if variant =='key':
                # Check that one of the columns is named Key
                if "Key" not in data["Columns"]:
                    raise ValueError("Lookup: Data must contain one column named Key")

                # Check that all keys are unique
                key_index = data['Columns'].index('Key')

                keys = [row[key_index] for row in data['Data']]
                number_keys = len(keys)
                without_duplicates = len(set(keys))
                if number_keys != without_duplicates:
                    raise ValueError("Lookup: All Keys must be unique")
            
        if name is not None and variant not in ["key", "embedding", "fuzzy", "recipe"]:
            raise ValueError(
                "A new lookup must contain a value (key or semantic) for setting/variant."
            )
        
        # Raise error if MatchingColumns are passed that do not exist in the data
        if "MatchingColumns" in settings:
            match_columns = settings["MatchingColumns"]
            if not isinstance(match_columns, list):
                match_columns = [match_columns]
            if isinstance(data, list):
                header = data[0]
            else:
                header = data["Columns"]
            for column in match_columns:
                if column not in header:
                    raise ValueError(f"Lookup: Matching Column {column} does not exist in the data")

        if name:
            _logging.info(f": Creating new lookup model :: {name}")
            response = _requests.post(
                        f'{_config.api_host}/model/content',
                        params={'type':'lookup', 'name': name, **settings},
                        headers={'Authorization': f'Bearer {_auth.get_access_token()}'},
                        json=data
                    )
        elif model_id:
            # Only use retries when retraining an existing model
            _logging.info(f": Updating lookup model :: {model_id}")
            response = _utils.request_retries(
                        request_type='PUT',
                        url=f'{_config.api_host}/model/content',
                        **{
                            'params': {'type':'lookup', 'model_id': model_id, **settings},
                            'headers': {'Authorization': f'Bearer {_auth.get_access_token()}'},
                            'json': data
                        }
                    )
        else:
            raise ValueError('Either a name or a model id must be provided')

        # If we created a new lookup model, log the model id
        try:
            if name and response is not None and response.ok:
                _json = response.json()
                modelid = (
                    _json.get('model_id') or _json.get('id') or _json.get('modelId') or _json.get('model')
                )
                if modelid:
                    _logging.info(f": New lookup model created :: {modelid}")
                else:
                    _logging.info(f": Lookup model created. Response: {response.text}")
        except Exception:
            _logging.info(": Lookup model created (could not parse model id from response)")

        if not response.ok:
            raise RuntimeError(f"Training Lookup Failed. {response.status_code} : {response.text}")
        
        return response

    def standardize(training_data: list, name: str = None, model_id: str = None):
        """
        Train a standardize model. This can standardize text to a desired format.
        Requires WrangleWorks Account and Subscription.
        
        :param training_data: paired list of entities to find and replace.
        :param name: If provided, will create a new model with this name.
        :param model_id: If provided, will update this model.
        """
        # If input is a list, check to make sure that all sublists are length of 2
        if isinstance(training_data, list):
            check_index = [training_data.index(x) for x in training_data if len(x) != 3]
            if len(check_index) != 0:
                raise ValueError(f'Training_data list must contain a list of two elements, plus optional Notes. Check element(s) {check_index} in training_list.\nFormat:\nFirst element is "Entity to Find"\nSecond Element is "Variation", If no variation, use \'\'\n'
                "Example:[['USA', 'United States of America', '']]")
                
            # checking the first element in training list
            if training_data[0] != ['Find', 'Replace', 'Notes']:
                training_data = [['Find', 'Replace', 'Notes']] + training_data
        else:
            raise ValueError('A list is expected for training_data')
        
        if name:
            _logging.info(f": Creating new standardize model :: {name}")
            response = _requests.post(
                        f'{_config.api_host}/model/content',
                        params={'type':'standardize', 'name': name},
                        headers={'Authorization': f'Bearer {_auth.get_access_token()}'},
                        json=training_data
                    )
        elif model_id:
            # Only use retries when retraining an existing model
            _logging.info(f": Updating standardize model :: {model_id}")
            response = _utils.request_retries(
                        request_type='PUT',
                        url=f'{_config.api_host}/model/content',
                        **{
                            'params': {'type':'standardize', 'model_id': model_id},
                            'headers': {'Authorization': f'Bearer {_auth.get_access_token()}'},
                            'json': training_data
                        }
                    )
        else:
            raise ValueError('Either a name or a model id must be provided')

        # If a new standardize model was created, try to log its model id
        try:
            if name and response is not None and response.ok:
                _json = response.json()
                modelid = (
                    _json.get('model_id') or _json.get('id') or _json.get('modelId') or _json.get('model')
                )
                if modelid:
                    _logging.info(f": New standardize model created :: {modelid}")
                else:
                    _logging.info(f": Standardize model created. Response: {response.text}")
        except Exception:
            _logging.info(": Standardize model created (could not parse model id from response)")

        return response
