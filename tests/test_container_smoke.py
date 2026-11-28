import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import container_smoke


def test_launcher_runs_process_recipe_once(tmp_path):
    recipe = tmp_path / "recipe.yml"
    recipe.write_text(
        """\
run:
  on_start:
    - custom.record: {stage: recipe-start}
    - concurrent:
        use_multiprocessing: true
        max_concurrency: 1
        run:
          - custom.record: {stage: worker}
""",
        encoding="utf-8",
    )
    functions = tmp_path / "user_hooks.py"
    functions.write_text(
        "def record(stage):\n"
        "    import multiprocessing\n"
        "    import os\n"
        "    print(stage, os.getpid(), multiprocessing.get_start_method(allow_none=True), flush=True)\n",
        encoding="utf-8",
    )

    # Pass only the OS environment needed to launch Python, even in credentialed CI.
    env = {
        key: os.environ[key]
        for key in ("PATH", "SYSTEMROOT", "LD_LIBRARY_PATH", "TEMP", "TMP", "TMPDIR")
        if key in os.environ
    }
    env["WRANGLES_RECIPE"] = str(recipe)
    env["WRANGLES_CUSTOM_FUNCTIONS"] = str(functions)
    launcher = Path(__file__).resolve().parents[1] / "main.py"
    result = subprocess.run(
        [sys.executable, str(launcher)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    events = [
        line.split() for line in result.stdout.splitlines()
        if line.startswith(("recipe-start ", "worker "))
    ]
    assert [event[0] for event in events] == ["recipe-start", "worker"]
    (_, launcher_pid, _), (_, worker_pid, start_method) = events
    assert launcher_pid != worker_pid
    assert start_method in {"forkserver", "spawn"}


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
