"""Credential-free validation for the WranglesPY CI test image."""

from importlib import metadata
from pathlib import Path
import os
import shutil
import sys

from packaging.requirements import Requirement


EXPECTED_PYTHON = (3, 13)
TEST_CONTAINER_CONSTRAINTS = (
    Path(__file__).resolve().parents[1]
    / "constraints"
    / "test-container-python313.txt"
)
RETAINED_BOTOCORE_DATA = frozenset(
    {
        "s3",
        "_retry.json",
        "endpoints.json",
        "partitions.json",
        "sdk-default-configuration.json",
    }
)


def _require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_exact_constraints(path=TEST_CONTAINER_CONSTRAINTS):
    """Load exact package versions from the test-image constraint file."""
    path = Path(path)
    _require(path.is_file(), f"Test-container constraints not found: {path}")

    versions = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.partition("#")[0].strip()
        if not line:
            continue
        requirement = Requirement(line)
        specifiers = list(requirement.specifier)
        exact_versions = [
            specifier.version
            for specifier in specifiers
            if specifier.operator == "=="
        ]
        _require(
            len(specifiers) == 1 and len(exact_versions) == 1,
            f"Expected one exact version in test-container constraint: {line}",
        )
        name = requirement.name.lower()
        _require(name not in versions, f"Duplicate test-container constraint: {name}")
        versions[name] = exact_versions[0]

    for name in ("numpy", "pandas"):
        _require(name in versions, f"Missing test-container constraint: {name}")
    return versions


TEST_CONTAINER_VERSIONS = load_exact_constraints()
EXPECTED_NUMPY = TEST_CONTAINER_VERSIONS["numpy"]
EXPECTED_PANDAS = TEST_CONTAINER_VERSIONS["pandas"]


def validate_runtime_versions(python_version, numpy_version, pandas_version):
    """Validate the exact interpreter and constrained data-stack versions."""
    _require(
        tuple(python_version[:2]) == EXPECTED_PYTHON,
        f"Expected Python 3.13, found {python_version[0]}.{python_version[1]}",
    )
    _require(
        numpy_version == EXPECTED_NUMPY,
        f"Expected NumPy {EXPECTED_NUMPY}, found {numpy_version}",
    )
    _require(
        pandas_version == EXPECTED_PANDAS,
        f"Expected Pandas {EXPECTED_PANDAS}, found {pandas_version}",
    )
    _require(
        int(pandas_version.split(".", maxsplit=1)[0]) < 3,
        f"Pandas 3.x is not supported by this image: {pandas_version}",
    )


def validate_wrangles_pandas_requirement(requirements):
    """Prove the installed package metadata still excludes Pandas 3."""
    parsed_requirements = [Requirement(requirement) for requirement in requirements]
    pandas_requirements = [
        requirement
        for requirement in parsed_requirements
        if requirement.name.lower() == "pandas"
    ]
    _require(
        len(pandas_requirements) == 1,
        "Expected one Pandas package requirement, found "
        f"{[str(requirement) for requirement in pandas_requirements]}",
    )
    pandas_specifier = pandas_requirements[0].specifier
    _require(
        pandas_specifier.contains("2.999", prereleases=True)
        and not pandas_specifier.contains("3.0", prereleases=True),
        "Wrangles metadata must support Pandas 2.x and exclude Pandas 3: "
        f"{pandas_requirements[0]}",
    )


def validate_trimmed_package_data(botocore_data, pandas_package):
    """Validate the two package-data reductions used to control image size."""
    botocore_data = Path(botocore_data)
    _require(
        botocore_data.exists(),
        f"Botocore data directory not found: {botocore_data}",
    )
    actual_botocore_data = {path.name for path in botocore_data.iterdir()}
    _require(
        actual_botocore_data == RETAINED_BOTOCORE_DATA,
        "Unexpected Botocore data after trimming: "
        f"expected {sorted(RETAINED_BOTOCORE_DATA)}, "
        f"found {sorted(actual_botocore_data)}",
    )
    pandas_tests = Path(pandas_package) / "tests"
    _require(not pandas_tests.exists(), f"Pandas tests were not removed: {pandas_tests}")


def validate_runtime_toolchain(which=shutil.which):
    """Ensure compiler tools from the former source build are absent."""
    present = [tool for tool in ("gcc", "gfortran") if which(tool)]
    _require(not present, f"Build-only compiler tools found in runtime image: {present}")


def validate_data_round_trip():
    """Exercise NumPy, Pandas, and PyArrow together without external data."""
    import numpy
    import pandas
    import pyarrow

    original = pandas.DataFrame(
        {
            "id": numpy.array([1, 2], dtype=numpy.int64),
            "description": ["alpha", None],
        }
    )
    table = pyarrow.Table.from_pandas(original, preserve_index=False)
    restored = table.to_pandas()
    pandas.testing.assert_frame_equal(restored, original)


def validate_s3_model():
    """Load the retained S3 model without making a network request."""
    import boto3

    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="container-smoke-test",
        aws_secret_access_key="container-smoke-test",
        endpoint_url="https://example.invalid",
    )
    try:
        _require(
            client.meta.service_model.service_name == "s3",
            "The retained Botocore S3 service model did not load",
        )
    finally:
        client.close()


def main():
    import boto3
    import botocore
    import numexpr
    import numpy
    import pandas
    import polars
    import pyarrow
    import wrangles  # noqa: F401 - import itself is part of the smoke check

    validate_runtime_versions(sys.version_info, numpy.__version__, pandas.__version__)
    validate_wrangles_pandas_requirement(metadata.requires("wrangles") or ())
    validate_trimmed_package_data(
        Path(botocore.__file__).resolve().parent / "data",
        Path(pandas.__file__).resolve().parent,
    )
    validate_runtime_toolchain()
    validate_data_round_trip()
    validate_s3_model()

    versions = {
        "Python": sys.version.split()[0],
        "Wrangles": metadata.version("wrangles"),
        "NumPy": numpy.__version__,
        "Pandas": pandas.__version__,
        "PyArrow": pyarrow.__version__,
        "Polars": polars.__version__,
        "NumExpr": numexpr.__version__,
        "Boto3": boto3.__version__,
        "Botocore": botocore.__version__,
    }
    print("CI test-image smoke checks passed:")
    for name, version in versions.items():
        print(f"  {name}={version}")


if __name__ == "__main__":
    main()
