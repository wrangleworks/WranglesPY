import os
import pytest
import pandas as pd
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
    df = read(
        host=_host,
        user=_user,
        password=_password,
        client_id=_client_id,
        client_secret=_client_secret,
        source="products",
    )
    assert isinstance(df, pd.DataFrame)


@_skip_no_creds
def test_read_auth_error():
    with pytest.raises(ValueError, match="Akeneo authentication failed"):
        read(
            host=_host,
            user="bad_user",
            password="bad_pass",
            client_id="bad_client_id",
            client_secret="bad_secret",
            source="products",
        )


@_skip_no_creds
def test_read_api_error():
    with pytest.raises(ValueError, match="Status Code:"):
        read(
            host=_host,
            user=_user,
            password=_password,
            client_id=_client_id,
            client_secret=_client_secret,
            source="invalid_source",
        )


@_skip_no_creds
def test_write_error():
    df = pd.DataFrame({"identifier": ["prod1"]})
    with pytest.raises(ValueError, match="Status Code:"):
        write(
            df=df,
            host=_host,
            user=_user,
            password=_password,
            client_id=_client_id,
            client_secret=_client_secret,
            source="invalid_source",
        )


@pytest.fixture
def akeneo_response(monkeypatch):
    """Mock Akeneo HTTP calls without credentials or a live PIM."""
    from unittest.mock import Mock

    auth = Mock(ok=True)
    auth.json.return_value = {"access_token": "test-token"}
    response = Mock(ok=True)
    response.json.return_value = {"_embedded": {"items": []}, "_links": {}}
    monkeypatch.setattr("wrangles.connectors.akeneo._requests.post", Mock(return_value=auth))
    monkeypatch.setattr("wrangles.connectors.akeneo._requests.get", Mock(return_value=response))
    return response


@pytest.fixture
def akeneo_settings():
    return {
        "host": "https://akeneo.example.com",
        "user": "test-user",
        "password": "test-password",
        "client_id": "test-client",
        "client_secret": "test-secret",
        "source": "products",
    }


def test_read_empty_response_preserves_columns(akeneo_response, akeneo_settings):
    columns = ["identifier", "family", "groups", "categories", "enabled", "values"]

    df = read(**akeneo_settings, columns=columns)

    pd.testing.assert_frame_equal(df, pd.DataFrame(columns=columns))


def test_read_empty_response_without_columns(akeneo_response, akeneo_settings):
    df = read(**akeneo_settings)

    pd.testing.assert_frame_equal(df, pd.json_normalize([], max_level=0))


def test_read_nonempty_response_rejects_missing_columns(akeneo_response, akeneo_settings):
    akeneo_response.json.return_value["_embedded"]["items"] = [{"identifier": "A"}]

    with pytest.raises(KeyError, match="missing_column"):
        read(**akeneo_settings, columns=["identifier", "missing_column"])


def test_left_join_empty_akeneo_response_preserves_rows(akeneo_response, akeneo_settings):
    from wrangles import recipe

    columns = ["identifier", "family", "groups", "categories", "enabled", "values"]
    selected = pd.DataFrame({"Item": ["B", "A", "B"]})

    df = recipe.run(
        {
            "read": [{"join": {
                "how": "left",
                "left_on": "Item",
                "right_on": "identifier",
                "validate": "many_to_one",
                "sources": [
                    {"excel.selected_data": {"columns": "Item"}},
                    {"akeneo": {**akeneo_settings, "columns": columns}},
                ],
            }}],
        },
        dataframe=selected,
    )

    assert df.columns.tolist() == ["Item", *columns]
    pd.testing.assert_series_equal(df["Item"], selected["Item"])
    assert df[columns].isna().all().all()


def test_read_nonempty_response_preserves_selected_data(akeneo_response, akeneo_settings):
    values = {"name": [{"locale": "en_US", "data": "Product A"}]}
    akeneo_response.json.return_value["_embedded"]["items"] = [
        {"identifier": "A", "family": "tools", "values": values}
    ]

    df = read(**akeneo_settings, columns=["values", "identifier"])

    pd.testing.assert_frame_equal(
        df, pd.DataFrame({"values": [values], "identifier": ["A"]})
    )
