"""
Train new models
"""

import requests as _requests
from . import config as _config
from . import auth as _auth

class train():
    """
    Train new models
    """

    def classify(training_data: list, name: str):
        """
        Train a classification model. This can predict the category of a text input.
        Requires WrangleWorks Account and Subscription.
        
        :param training_data: paired list of examples and labels.
        :param name: The name of the new model.
        """
        # If input is a list, check to make sure that all sublists are length of 2
        if isinstance(training_data, list):
            check_index = [training_data.index(x) for x in training_data if len(x) != 2 or '' in x]
            if len(check_index) != 0:
                raise ValueError(f'Training_data list must contain a list of two non-empty elements. Check element(s) {check_index} in training_list.\nFormat:\nFirst element is "Example"\nSecond Element is "Category" -- \'\' is not valid.\n'
                "Example:[['Rice', 'Grain']]")
            # checking the first element in training list
            if training_data[0] != ['Example', 'Category']:
                training_data = [['Example', 'Category']] + training_data
        # Validate input here
        response = _requests.post(f'{_config.api_host}/data/user/model/train', params={'type':'classify', 'name': name}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=training_data)
        return response

    def extract(training_data: list, name: str):
        """
        Train an extraction model. This can extract custom entities from the input.
        Requires WrangleWorks Account and Subscription.
        
        :param training_data: paired list of entities to find and optional standard representation of that entitiy.
        :param name: The name of the new model.
        """
        # If input is a list, check to make sure that all sublists are length of 2
        # Must have both values filled ('' counts as filled, None does not count)
        if isinstance(training_data, list):
            check_index = [training_data.index(x) for x in training_data if len(x) != 2]
            if len(check_index) != 0: # If an index does not have len() of 2 then raise error
                raise ValueError(f"Training_data list must contain a list of two elements. Check element(s) {check_index} in training_list.\nFormat:\nFirst element is 'Entity to Find'\nSecond Element is 'Variation', If no variation, use \'\'\n"
                "Example:[['Television', 'TV']]")
            # checking the first element in training list
            if training_data[0] != ['Entity to Find', 'Variation (Optional)']:
                training_data = [['Entity to Find', 'Variation (Optional)']] + training_data
        
        # Validate input here
        response = _requests.post(f'{_config.api_host}/data/user/model/train', params={'type':'extract', 'name': name}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=training_data)
        return response

    def standardize(training_data: list, name: str):
        """
        Train a standardize model. This can standardize text to a desired format.
        Requires WrangleWorks Account and Subscription.
        
        :param training_data: paired list of entities to find and replace.
        :param name: The name of the new model.
        """
        # If input is a list, check to make sure that all sublists are length of 2
        if isinstance(training_data, list):
            check_index = [training_data.index(x) for x in training_data if len(x) != 2]
            if len(check_index) != 0:
                raise ValueError(f'Training_data list must contain a list of two elements. Check element(s) {check_index} in training_list.\nFormat:\nFirst element is "Entity to Find"\nSecond Element is "Variation", If no variation, use \'\'\n'
                "Example:[['USA', 'United States of America']]")
                
            # checking the first element in training list
            if training_data[0] != ['Find', 'Replace']:
                training_data = [['Find', 'Replace']] + training_data
        else:
            raise ValueError('A list is expected for training_data')
        
        # Validate input here
        response = _requests.post(f'{_config.api_host}/data/user/model/train', params={'type':'standardize', 'name': name}, headers={'Authorization': f'Bearer {_auth.get_access_token()}'}, json=training_data)
        return response