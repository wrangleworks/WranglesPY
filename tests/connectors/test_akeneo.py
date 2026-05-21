import os
import pytest
import pandas as pd
from unittest.mock import MagicMock
from wrangles.connectors.akeneo import read, write


_host = os.getenv('AKENEO_HOST', '...')
_user = os.getenv('AKENEO_USERNAME', '...')
_password = os.getenv('AKENEO_PASSWORD', '...')
_client_id = os.getenv('AKENEO_CLIENT_ID', '...')
_client_secret = os.getenv('AKENEO_SECRET', '...')

_has_credentials = all(
    os.getenv(v)
    for v in ('AKENEO_HOST', 'AKENEO_USERNAME', 'AKENEO_PASSWORD', 'AKENEO_CLIENT_ID', 'AKENEO_SECRET')
)

_skip_no_creds = pytest.mark.skipif(
    not _has_credentials,
    reason="Akeneo credentials not set in environment variables"
)


# ---------------------------------------------------------------------------
# Integration tests — require real credentials
# ---------------------------------------------------------------------------

@_skip_no_creds
def test_read():
    df = read(
        host=_host,
        user=_user,
        password=_password,
        client_id=_client_id,
        client_secret=_client_secret,
        source="products",
    )
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


@_skip_no_creds
def test_read_columns():
    df = read(
        host=_host,
        user=_user,
        password=_password,
        client_id=_client_id,
        client_secret=_client_secret,
        source="products",
        columns=["identifier"],
    )
    assert df.columns.tolist() == ["identifier"]
    assert len(df) > 0


@_skip_no_creds
def test_read_pagination():
    """Fetch enough records to exercise pagination (limit is set to 100)."""
    df = read(
        host=_host,
        user=_user,
        password=_password,
        client_id=_client_id,
        client_secret=_client_secret,
        source="products",
    )
    assert isinstance(df, pd.DataFrame)


# ---------------------------------------------------------------------------
# Error-condition tests — kept mocked (can't reproduce with a live instance)
# ---------------------------------------------------------------------------

def _mock_auth(mocker, status_code=200):
    auth_mock = MagicMock()
    auth_mock.ok = status_code < 400
    auth_mock.status_code = status_code
    auth_mock.json.return_value = (
        {"access_token": "test_token"} if auth_mock.ok else {"message": "Unauthorized"}
    )
    auth_mock.text = "Unauthorized"
    return auth_mock


def _make_get_response(data):
    r = MagicMock()
    r.ok = True
    r.status_code = 200
    r.json.return_value = data
    return r


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
