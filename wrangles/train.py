"""
Train new models
"""
from typing import Union as _Union
import requests as _requests
from . import config as _config
from . import auth as _auth


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
            response = _requests.post(f'{_config.api_host}/model/content', params={'type':'classify', 'name': name}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=training_data)
        elif model_id:
            response = _requests.put(f'{_config.api_host}/model/content', params={'type':'classify', 'model_id': model_id}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=training_data)
        else:
            raise ValueError('Either a name or a model id must be provided')

        return response

    def extract(training_data: list, name: str = None, model_id: str = None):
        """
        Train an extraction model. This can extract custom entities from the input.
        Requires WrangleWorks Account and Subscription.
        
        :param training_data: paired list of entities to find and optional standard representation of that entitiy.
        :param name: If provided, will create a new model with this name.
        :param model_id: If provided, will update this model.
        """
        # If input is a list, check to make sure that all sublists are length of 2
        # Must have both values filled ('' counts as filled, None does not count)
        if isinstance(training_data, list):
            check_index = [training_data.index(x) for x in training_data if len(x) != 3]
            if len(check_index) != 0: # If an index does not have len() of 2 then raise error
                raise ValueError(f"Training_data list must contain a list of two elements, plus optional Notes. Check element(s) {check_index} in training_list.\nFormat:\nFirst element is 'Entity to Find'\nSecond Element is 'Variation', If no variation, use \'\'\n"
                "Example:[['Television', 'TV', '']]")
            # checking the first element in training list
            if training_data[0] != ['Entity to Find', 'Variation (Optional)', 'Notes']:
                training_data = [['Entity to Find', 'Variation (Optional)', 'Notes']] + training_data
        
        if name:
            response = _requests.post(f'{_config.api_host}/model/content', params={'type':'extract', 'name': name}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=training_data)
        elif model_id:
            response = _requests.put(f'{_config.api_host}/model/content', params={'type':'extract', 'model_id': model_id}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=training_data)
        else:
            raise ValueError('Either a name or a model id must be provided')

        return response

    def lookup(
        data: _Union[dict, list],
        name: str = None,
        model_id: str = None,
        settings: dict = {}
    ):
        """
        Train a lookup model. This can be used as reference data to look values up from.

        Requires WrangleWorks Account and Subscription.
        
        :param training_data: 2D array of training data. Must contain the column Key as the first column.
        :param name: If provided, will create a new model with this name.
        :param model_id: If provided, will update this model.
        :param settings: Specific settings to apply to the lookup wrangle.
        """
        # Validate input
        if isinstance(data, list):
            if len(data) < 2:
                raise ValueError("Lookup: The data must contain at least 1 header row and 1 row of contents")
            
            if not isinstance(data[0], list):
                raise ValueError("Lookup: The data must be a 2D array.")

            if not data[0][0] == "Key":
                raise ValueError("Lookup: Column 1 must be named Key")
            
        elif isinstance(data, dict):
            if not "Columns" in data or not "Data" in data:
                raise ValueError(
                    "Lookup: The data must be a dictionary of the format {'Data': [[]], 'Columns': [], 'Settings': {}}"
                )
            
        if name is not None and settings.get("variant", "") not in ["key", "embedding", "fuzzy", "recipe"]:
            raise ValueError(
                "A new lookup must contain a value for setting/variant."
            )

        if name:
            response = _requests.post(
                f'{_config.api_host}/model/content',
                params={'type':'lookup', 'name': name, **settings},
                headers={'Authorization': f'Bearer {_auth.get_access_token()}'},
                json=data
            )
        elif model_id:
            response = _requests.put(
                f'{_config.api_host}/model/content',
                params={'type':'lookup', 'model_id': model_id, **settings},
                headers={'Authorization': f'Bearer {_auth.get_access_token()}'},
                json=data
            )
        else:
            raise ValueError('Either a name or a model id must be provided')

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
            response = _requests.post(f'{_config.api_host}/model/content', params={'type':'standardize', 'name': name}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=training_data)
        elif model_id:
            response = _requests.put(f'{_config.api_host}/model/content', params={'type':'standardize', 'model_id': model_id}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=training_data)
        else:
            raise ValueError('Either a name or a model id must be provided')

        return response
