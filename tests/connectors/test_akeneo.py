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


@pytest.mark.skipif(not os.getenv('AKENEO_HOST'), reason="AKENEO_HOST not set")
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
