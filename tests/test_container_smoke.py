from pathlib import Path

import pytest

from scripts import container_smoke


def test_runtime_versions_accept_migration_baseline():
    container_smoke.validate_runtime_versions(
        (3, 13, 9),
        container_smoke.EXPECTED_NUMPY,
        container_smoke.EXPECTED_PANDAS,
    )


@pytest.mark.parametrize(
    ("python_version", "numpy_version", "pandas_version"),
    [
        ((3, 12, 9), "2.4.6", "2.3.3"),
        ((3, 13, 9), "2.5.2", "2.3.3"),
        ((3, 13, 9), "2.4.6", "3.0.0"),
    ],
)
def test_runtime_versions_reject_unapproved_versions(
    python_version,
    numpy_version,
    pandas_version,
):
    with pytest.raises(RuntimeError):
        container_smoke.validate_runtime_versions(
            python_version,
            numpy_version,
            pandas_version,
        )


def test_wrangles_metadata_requires_pandas_below_three():
    container_smoke.validate_wrangles_pandas_requirement(
        [
            "numpy",
            "pandas[performance]<3.0,>=2.0; python_version >= '3.11'",
            "requests",
        ]
    )


@pytest.mark.parametrize(
    "requirement",
    ["pandas>=2.0", "pandas>=3.0,<4.0"],
)
def test_wrangles_metadata_rejects_pandas_three(requirement):
    with pytest.raises(RuntimeError):
        container_smoke.validate_wrangles_pandas_requirement([requirement])


def test_trimmed_package_data_accepts_only_s3(tmp_path):
    botocore_data = tmp_path / "botocore-data"
    botocore_data.mkdir()
    for name in container_smoke.RETAINED_BOTOCORE_DATA:
        path = botocore_data / name
        if name == "s3":
            path.mkdir()
        else:
            path.touch()

    pandas_package = tmp_path / "pandas"
    pandas_package.mkdir()

    container_smoke.validate_trimmed_package_data(botocore_data, pandas_package)


def test_trimmed_package_data_rejects_other_services(tmp_path):
    botocore_data = tmp_path / "botocore-data"
    botocore_data.mkdir()
    for name in container_smoke.RETAINED_BOTOCORE_DATA | {"ec2"}:
        path = botocore_data / name
        if "." in name:
            path.touch()
        else:
            path.mkdir()

    with pytest.raises(RuntimeError):
        container_smoke.validate_trimmed_package_data(botocore_data, tmp_path / "pandas")


def test_trimmed_package_data_rejects_missing_botocore_data(tmp_path):
    botocore_data = tmp_path / "missing-botocore-data"

    with pytest.raises(RuntimeError, match="Botocore data directory not found"):
        container_smoke.validate_trimmed_package_data(botocore_data, tmp_path / "pandas")


def test_runtime_toolchain_rejects_compiler():
    with pytest.raises(RuntimeError):
        container_smoke.validate_runtime_toolchain(
            lambda tool: Path("/usr/bin") / tool if tool == "gcc" else None
        )


def test_data_round_trip():
    container_smoke.validate_data_round_trip()


def test_data_round_trip_propagates_comparison_failure(mocker):
    comparison = mocker.patch(
        "pandas.testing.assert_frame_equal",
        side_effect=AssertionError("round trip changed the frame"),
    )

    with pytest.raises(AssertionError, match="round trip changed the frame"):
        container_smoke.validate_data_round_trip()

    comparison.assert_called_once()


def test_s3_model_loads_without_network(mocker):
    create_connection = mocker.patch(
        "socket.create_connection",
        side_effect=AssertionError("network access attempted"),
    )

    container_smoke.validate_s3_model()

    create_connection.assert_not_called()
