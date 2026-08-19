import pytest

import wrangles.data as data


class FakeResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._body = body

    def json(self):
        return self._body


MODEL_ID = "93d92b4c-9f49-4ff5"


def _mock_model_response(monkeypatch, response):
    monkeypatch.setattr(data._auth, "get_access_token", lambda: "token")
    monkeypatch.setattr(data._utils, "request_retries", lambda **kwargs: response)


@pytest.mark.parametrize(
    "call_model_endpoint",
    [
        lambda: data.model(MODEL_ID),
        lambda: data.model_update(MODEL_ID, {"name": "Updated model"}),
        lambda: data.model_content(MODEL_ID),
    ],
)
def test_model_endpoints_raise_authentication_error_for_401(monkeypatch, call_model_endpoint):
    _mock_model_response(monkeypatch, FakeResponse(401))

    with pytest.raises(data.AuthenticationError) as info:
        call_model_endpoint()

    assert isinstance(info.value, RuntimeError)
    assert str(info.value) == (
        f"Authentication failed while accessing model {MODEL_ID}. "
        "The access token may have expired; refresh credentials and retry."
    )


@pytest.mark.parametrize(
    "call_model_endpoint",
    [
        lambda: data.model(MODEL_ID),
        lambda: data.model_update(MODEL_ID, {"name": "Updated model"}),
        lambda: data.model_content(MODEL_ID),
    ],
)
def test_model_endpoints_raise_authorization_error_for_403(monkeypatch, call_model_endpoint):
    _mock_model_response(monkeypatch, FakeResponse(403))

    with pytest.raises(data.AuthorizationError) as info:
        call_model_endpoint()

    assert isinstance(info.value, RuntimeError)
    assert str(info.value) == (
        f"Access denied to model {MODEL_ID}. Check the user's model permissions."
    )


def test_model_success_returns_metadata(monkeypatch):
    metadata = {"id": MODEL_ID, "name": "Model"}
    _mock_model_response(monkeypatch, FakeResponse(200, metadata))

    assert data.model(MODEL_ID) == metadata


def test_model_update_success_returns_none(monkeypatch):
    _mock_model_response(monkeypatch, FakeResponse(204))

    assert data.model_update(MODEL_ID, {"name": "Updated model"}) is None


def test_model_content_success_returns_content(monkeypatch):
    content = {"Settings": {}, "Columns": ["Key"], "Data": [["A"]]}
    _mock_model_response(monkeypatch, FakeResponse(200, content))

    assert data.model_content(MODEL_ID) == content
