"""
Functions for interacting with user and app data
"""
from . import config as _config
from . import auth as _auth
from . import utils as _utils


class AuthenticationError(RuntimeError):
    pass


class AuthorizationError(RuntimeError):
    pass


class ModelNotFoundError(RuntimeError):
    pass


def _raise_model_response_error(response, id: str, action: str) -> None:
    if response.status_code == 401:
        raise AuthenticationError(
            f'Authentication failed while accessing model {id}. '
            'The access token may have expired; refresh credentials and retry.'
        )
    if response.status_code == 403:
        raise AuthorizationError(
            f"Access denied to model {id}. Check the user's model permissions."
        )
    if response.status_code == 404:
        raise ModelNotFoundError(
            f"Model {id} was not found. Check the model id is correct."
        )
    raise RuntimeError(f'Something went wrong trying to {action} model {id}')


class user():
    """
    Get user data
    """

    def models(type: str = None) -> list:
        """
        Get a list of the user's models

        :param type: (Optional) Specify the type of models. 'classify' or 'extract'
        :returns: List of user's model, each a dict of properties.
        """
        params = {}
        if type: params['type'] = type
        response = _utils.request_retries(
                    request_type='GET',
                    url=f'{_config.api_host}/user/models',
                    **{
                        'params': params,
                        'headers': {'Authorization': f'Bearer {_auth.get_access_token()}'}
                    }
                )
        results = response.json()
        return results


def model(id: str):
    """
    Get a model definition
    :param id: model ID
    :returns: Dict of model properties
    """
    response = _utils.request_retries(
                request_type='GET',
                url=f'{_config.api_host}/model/metadata',
                **{
                    'params': {'id': id},
                    'headers': {'Authorization': f'Bearer {_auth.get_access_token()}'}
                }
            )
    if response.ok:
        return response.json()
    else:
        _raise_model_response_error(response, id, 'access')


def model_update(id: str, metadata: dict) -> None:
    """
    Update the metadata for a model

    :param id: Model ID
    :param metadata: Dict of metadata fields to update
    """
    response = _utils.request_retries(
                request_type='PATCH',
                url=f'{_config.api_host}/model/metadata',
                **{
                    'params': {'id': id},
                    'headers': {'Authorization': f'Bearer {_auth.get_access_token()}'},
                    'json': metadata
                }
            )
    if not response.ok:
        _raise_model_response_error(response, id, 'update')


def model_content(id: str, version_id: str = None) -> list:
    """
    Get the training data for a model

    :param id: Model ID
    :param version_id: (Optional) Version ID. If not provided, the latest version will be used.
    :return: Model data with Settings, Columns and Data as a 2D array
    """
    response = _utils.request_retries(
                request_type='GET',
                url=f'{_config.api_host}/model/content',
                **{
                    'params': {
                        **{'model_id': id},
                        **({'version_id': version_id} if version_id else {})
                    },
                    'headers': {'Authorization': f'Bearer {_auth.get_access_token()}'}
                }
            )
    if response.ok:
        return response.json()
    else:
        _raise_model_response_error(response, id, 'access')
