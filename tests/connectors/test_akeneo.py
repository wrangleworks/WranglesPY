import pytest
import pandas as pd
from unittest.mock import MagicMock
from wrangles.connectors.akeneo import read, write


_AUTH_RESPONSE = {"access_token": "test_token"}

_PRODUCTS_PAGE1 = {
    "_embedded": {
        "items": [
            {"identifier": "prod1", "family": "familyA"},
            {"identifier": "prod2", "family": "familyA"},
        ]
    },
    "_links": {
        "self": {"href": "https://akeneo.example.com/api/rest/v1/products?page=1"},
        "first": {"href": "https://akeneo.example.com/api/rest/v1/products?page=1"},
        "next": {"href": "https://akeneo.example.com/api/rest/v1/products?page=2"},
    },
}

_PRODUCTS_PAGE2 = {
    "_embedded": {
        "items": [
            {"identifier": "prod3", "family": "familyB"},
        ]
    },
    "_links": {
        "self": {"href": "https://github.com/wrangleworks/WranglesPY/issues/978/api/rest/v1/products?page=2"},
        "first": {"href": "https://akeneo.example.com/api/rest/v1/products?page=1"},
    },
}

_PRODUCTS_SINGLE_PAGE = {
    "_embedded": {
        "items": [
            {"identifier": "prod1", "family": "familyA"},
            {"identifier": "prod2", "family": "familyB"},
        ]
    },
    "_links": {
        "self": {"href": "https://akeneo.example.com/api/rest/v1/products"},
        "first": {"href": "https://akeneo.example.com/api/rest/v1/products"},
    },
}


def _mock_auth(mocker, status_code=200):
    auth_mock = MagicMock()
    auth_mock.ok = status_code < 400
    auth_mock.status_code = status_code
    auth_mock.json.return_value = _AUTH_RESPONSE if auth_mock.ok else {"message": "Unauthorized"}
    auth_mock.text = "Unauthorized"
    return auth_mock


def _mock_get(mocker, pages):
    get_mock = MagicMock()
    responses = []
    for page in pages:
        r = MagicMock()
        r.ok = True
        r.status_code = 200
        r.json.return_value = page
        responses.append(r)
    get_mock.side_effect = responses
    return get_mock


def test_read(mocker):
    mocker.patch("requests.post", return_value=_mock_auth(mocker))
    mocker.patch("requests.get", return_value=_make_get_response(_PRODUCTS_SINGLE_PAGE))

    df = read(
        host="https://akeneo.example.com",
        user="user",
        password="pass",
        client_id="client_id",
        client_secret="client_secret",
        source="products",
    )
    assert list(df["identifier"]) == ["prod1", "prod2"]


def test_read_columns(mocker):
    mocker.patch("requests.post", return_value=_mock_auth(mocker))
    mocker.patch("requests.get", return_value=_make_get_response(_PRODUCTS_SINGLE_PAGE))

    df = read(
        host="https://akeneo.example.com",
        user="user",
        password="pass",
        client_id="client_id",
        client_secret="client_secret",
        source="products",
        columns=["identifier"],
    )
    assert df.columns.tolist() == ["identifier"]
    assert len(df) == 2


def test_read_pagination(mocker):
    mocker.patch("requests.post", return_value=_mock_auth(mocker))
    get_mock = mocker.patch("requests.get")
    get_mock.side_effect = [
        _make_get_response(_PRODUCTS_PAGE1),
        _make_get_response(_PRODUCTS_PAGE2),
    ]

    df = read(
        host="https://akeneo.example.com",
        user="user",
        password="pass",
        client_id="client_id",
        client_secret="client_secret",
        source="products",
    )
    assert len(df) == 3
    assert list(df["identifier"]) == ["prod1", "prod2", "prod3"]


def test_read_auth_error(mocker):
    auth_mock = MagicMock()
    auth_mock.ok = False
    auth_mock.status_code = 401
    auth_mock.json.return_value = {"message": "Unauthorized"}
    auth_mock.text = "Unauthorized"
    mocker.patch("requests.post", return_value=auth_mock)

    with pytest.raises(ValueError, match="Akeneo authentication failed"):
        read(
            host="https://akeneo.example.com",
            user="bad_user",
            password="bad_pass",
            client_id="client_id",
            client_secret="client_secret",
            source="products",
        )


def test_read_api_error(mocker):
    mocker.patch("requests.post", return_value=_mock_auth(mocker))
    error_mock = MagicMock()
    error_mock.ok = False
    error_mock.status_code = 422
    error_mock.json.return_value = {"code": 422, "message": "Unprocessable Entity"}
    mocker.patch("requests.get", return_value=error_mock)

    with pytest.raises(ValueError, match="422"):
        read(
            host="https://akeneo.example.com",
            user="user",
            password="pass",
            client_id="client_id",
            client_secret="client_secret",
            source="products",
        )


def test_write(mocker):
    mocker.patch("requests.post", return_value=_mock_auth(mocker))
    patch_mock = MagicMock()
    patch_mock.ok = True
    patch_mock.status_code = 200
    patch_mock.text = '{"status_code": 204}\n{"status_code": 204}'
    mocker.patch("requests.patch", return_value=patch_mock)

    df = pd.DataFrame({"identifier": ["prod1", "prod2"], "family": ["familyA", "familyB"]})
    result = write(
        df=df,
        host="https://akeneo.example.com",
        user="user",
        password="pass",
        client_id="client_id",
        client_secret="client_secret",
        source="products",
    )
    assert result is None


def test_write_error(mocker):
    mocker.patch("requests.post", return_value=_mock_auth(mocker))
    patch_mock = MagicMock()
    patch_mock.status_code = 401
    patch_mock.text = '{"code": 401, "message": "Unauthorized"}'
    mocker.patch("requests.patch", return_value=patch_mock)

    df = pd.DataFrame({"identifier": ["prod1"]})
    with pytest.raises(ValueError, match="401"):
        write(
            df=df,
            host="https://akeneo.example.com",
            user="user",
            password="pass",
            client_id="client_id",
            client_secret="client_secret",
            source="products",
        )


def _make_get_response(data):
    r = MagicMock()
    r.ok = True
    r.status_code = 200
    r.json.return_value = data
    return r
