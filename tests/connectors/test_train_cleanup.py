"""Offline regression checks for integration-test model cleanup."""
import importlib

import pytest
import requests

import wrangles
from tests.connectors.test_train import _delete_model


MODEL_ID = '12345678-1234-1234'
API_HOST = 'https://api.example.test'
train_module = importlib.import_module('wrangles.train')


@pytest.fixture(autouse=True)
def prevent_live_requests(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Cleanup regression tests must not contact live services')

    monkeypatch.setattr(requests.sessions.Session, 'request', blocked)


@pytest.fixture
def delete_request(mocker):
    mocker.patch.object(wrangles.config, 'api_host', API_HOST)
    mocker.patch.object(train_module._auth, 'get_access_token', return_value='test-token')
    request = mocker.patch.object(train_module._requests, 'delete')
    response = requests.Response()
    response.status_code = 200
    request.return_value = response
    return request


def test_cleanup_uses_checked_delete_client(mocker, delete_request):
    delete = mocker.patch.object(wrangles.train, 'delete')

    _delete_model(MODEL_ID)

    delete.assert_called_once_with(MODEL_ID)


def test_cleanup_sends_authenticated_delete(delete_request):
    _delete_model(MODEL_ID)

    delete_request.assert_called_once_with(
        f'{API_HOST}/model/delete',
        params={'model_id': MODEL_ID},
        headers={'Authorization': 'Bearer test-token'},
    )


def test_cleanup_propagates_http_error(delete_request):
    delete_request.return_value.status_code = 405
    delete_request.return_value._content = b'Method Not Allowed'

    with pytest.raises(RuntimeError, match='Delete model failed. 405 : Method Not Allowed'):
        _delete_model(MODEL_ID)

    delete_request.assert_called_once()


def test_cleanup_propagates_transport_error(delete_request):
    failure = requests.ConnectionError('cleanup connection failed')
    delete_request.side_effect = failure

    with pytest.raises(requests.ConnectionError) as error:
        _delete_model(MODEL_ID)

    assert error.value is failure
    delete_request.assert_called_once()
