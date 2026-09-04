import importlib.util
import json
from pathlib import Path

import jsonschema


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
GENERATOR_PATH = REPOSITORY_ROOT / "schema" / "generate_wrangle_manifest.py"
MANIFEST_SCHEMA_PATH = (
    REPOSITORY_ROOT / "schema" / "wrangles-runtime-manifest.schema.json"
)


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_wrangle_manifest", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


generator = _load_generator()


def _entry(manifest, runtime_key):
    return next(
        entry for entry in manifest["wrangles"] if entry["runtime_key"] == runtime_key
    )


def test_runtime_manifest_is_deterministic_and_schema_valid():
    first = generator.build_manifest(source_revision="test-revision")
    second = generator.build_manifest(source_revision="test-revision")

    assert generator.manifest_json(first) == generator.manifest_json(second)
    assert first["entry_count"] == len(first["wrangles"])
    assert [entry["runtime_key"] for entry in first["wrangles"]] == sorted(
        entry["runtime_key"] for entry in first["wrangles"]
    )

    schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(first)


def test_runtime_manifest_preserves_signature_and_embedded_schema_separately():
    manifest = generator.build_manifest(source_revision="test-revision")
    entry = _entry(manifest, "convert.case")
    parameters = {parameter["name"]: parameter for parameter in entry["parameters"]}

    assert entry["python_symbol"] == "wrangles.recipe_wrangles.convert.case"
    assert entry["internal_parameters"] == ["df"]
    assert parameters["input"]["required"] is True
    assert parameters["case"]["required"] is False
    assert parameters["case"]["default"] == "lower"
    assert entry["docstring_schema"]["required"] == ["input", "case"]
    assert entry["capabilities"] == {
        "if": True,
        "where": True,
        "where_params": True,
    }


def test_runtime_manifest_does_not_drop_callables_without_schema_docstrings():
    manifest = generator.build_manifest(source_revision="test-revision")

    price_breaks = _entry(manifest, "format.price_breaks")
    assert price_breaks["docstring_schema_status"] == "missing"
    assert price_breaks["plain_docstring"] == "Rearrange price breaks"

    maths = _entry(manifest, "maths")
    assert maths["docstring_schema_status"] == "missing"
    assert maths["plain_docstring"] == "Deprecated - use math"


def test_runtime_manifest_records_kwargs_without_treating_them_as_parameters():
    manifest = generator.build_manifest(source_revision="test-revision")
    entry = _entry(manifest, "convert.data_type")

    assert entry["variadic"]["keyword"] == "kwargs"
    assert "kwargs" not in {parameter["name"] for parameter in entry["parameters"]}


def test_runtime_manifest_separates_recipe_runner_injected_parameters():
    manifest = generator.build_manifest(source_revision="test-revision")

    batch = _entry(manifest, "batch")
    assert batch["internal_parameters"] == ["df", "functions", "variables"]
    assert "functions" not in {
        parameter["name"] for parameter in batch["parameters"]
    }
    assert "variables" not in {
        parameter["name"] for parameter in batch["parameters"]
    }

    log = _entry(manifest, "log")
    assert log["internal_parameters"] == ["df", "error"]
    assert "error" not in {parameter["name"] for parameter in log["parameters"]}

    recipe = _entry(manifest, "recipe")
    assert "variables" not in recipe["internal_parameters"]
    assert "variables" in {
        parameter["name"] for parameter in recipe["parameters"]
    }
