"""Credential-free tests for the public packaged AI model catalog."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from schema import generate_ai_catalog
from wrangles import ai_catalog, ai_config


@pytest.fixture(autouse=True)
def isolate_catalog(monkeypatch):
    monkeypatch.delenv("WRANGLES_AI_CONFIG", raising=False)
    ai_config.clear_cache()
    yield
    ai_config.clear_cache()


def use_packaged_config(config, monkeypatch, tmp_path):
    path = tmp_path / "packaged-ai.yml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(ai_config, "_PACKAGED_CONFIG", path)
    ai_config.clear_cache()


def test_catalog_exports_packaged_default_and_declared_model_options():
    config = ai_config.load()
    policy = ai_config.resolve("extract.ai")
    catalog = ai_catalog.extract_ai_catalog("1.20.4rc2")
    assert {key: value for key, value in catalog.items() if key != "models"} == {
        "schema_version": 1, "package_version": "1.20.4rc2", "operation": "extract.ai",
        "provider": policy["provider"], "protocol": policy["protocol"],
        "default_model": policy["model"],
    }
    entries = config["providers"][policy["provider"]]["models"]
    expected_models = sorted(model_id for model_id, entry in entries.items()
                             if "embeddings" not in entry.get("applications", []))
    assert [model["id"] for model in catalog["models"]] == expected_models
    for model in catalog["models"]:
        entry = entries[model["id"]]
        assert model["status"] == entry["status"]
        resolved = ai_config.resolve("extract.ai", model=model["id"])
        expected_defaults = ({"reasoning_effort": resolved["reasoning"]["effort"]}
                             if "effort" in resolved.get("reasoning", {}) else {})
        assert model["defaults"] == expected_defaults
    by_id = {model["id"]: model for model in catalog["models"]}
    assert by_id["gpt-6-luna"]["supported_values"]["reasoning_effort"] == [
        "none", "low", "medium", "high", "xhigh", "max",
    ]
    assert by_id["gpt-4o-mini"]["supported_values"] == {"reasoning_effort": []}
    assert by_id["gpt-5.4-mini"]["supported_values"] == {}
    assert "text-embedding-3-small" not in by_id
    assert "text-embedding-3-large" not in by_id


def test_catalog_ignores_hostile_runtime_override(monkeypatch, tmp_path):
    expected = ai_catalog.extract_ai_catalog("test-version")
    hostile = tmp_path / "hostile.yml"
    hostile.write_text("version: 999\nsecret: runtime-only-secret\n", encoding="utf-8")
    monkeypatch.setenv("WRANGLES_AI_CONFIG", str(hostile))
    ai_config.clear_cache()
    assert ai_catalog.extract_ai_catalog("test-version") == expected
    monkeypatch.setenv("WRANGLES_AI_CONFIG", str(tmp_path / "missing.yml"))
    assert ai_catalog.extract_ai_catalog("test-version") == expected


def test_catalog_whitelists_fields_and_does_not_mutate_packaged_config(monkeypatch, tmp_path):
    config = ai_config.load()
    provider = config["providers"]["openai"]
    provider["api_key"] = "private-provider-secret"
    provider["endpoints"]["responses"] = "https://private.example/secret-endpoint"
    provider["models"]["gpt-6-luna"]["defaults"]["api_key"] = "private-model-secret"
    config["operations"]["extract.ai"]["defaults"]["prompt"] = {
        "instructions": "private-operation-prompt",
    }
    use_packaged_config(config, monkeypatch, tmp_path)
    catalog = ai_catalog.extract_ai_catalog("test-version")
    assert set(catalog) == {
        "schema_version", "package_version", "operation", "provider", "protocol",
        "default_model", "models",
    }
    for model in catalog["models"]:
        assert set(model) == {"id", "status", "defaults", "supported_values"}
        assert set(model["defaults"]) <= {"reasoning_effort"}
        assert set(model["supported_values"]) <= {"reasoning_effort"}
    serialized = json.dumps(catalog)
    assert "private-" not in serialized
    assert "https://" not in serialized
    untouched = copy.deepcopy(catalog)
    catalog["models"][0]["supported_values"]["reasoning_effort"] = ["altered"]
    assert ai_catalog.extract_ai_catalog("test-version") == untouched


@pytest.mark.parametrize("operation_effort,expected", [(None, "low"), ("medium", "medium")])
def test_catalog_uses_runtime_protocol_operation_and_snapshot_precedence(
    monkeypatch, tmp_path, operation_effort, expected,
):
    config = ai_config.load()
    models = config["providers"]["openai"]["models"]
    for entry in models.values():
        entry["default_for"] = [role for role in entry.get("default_for", []) if role != "extract.ai"]
    models["catalog-test"] = {
        "status": "deprecated", "default_for": ["extract.ai"],
        "defaults": {"reasoning": {"effort": "none"}},
        "protocol_defaults": {"responses": {"reasoning": {"effort": "low"}}},
        "supported_values": {"reasoning.effort": ["none", "low", "medium"]},
    }
    models["catalog-test-2026-09-30"] = {"status": "retired", "default_for": []}
    if operation_effort is not None:
        config["operations"]["extract.ai"]["defaults"]["reasoning"] = {"effort": operation_effort}
    use_packaged_config(config, monkeypatch, tmp_path)
    catalog = ai_catalog.extract_ai_catalog("test-version")
    assert catalog["default_model"] == "catalog-test"
    by_id = {model["id"]: model for model in catalog["models"]}
    for model_id in ("catalog-test", "catalog-test-2026-09-30"):
        assert by_id[model_id]["defaults"] == {"reasoning_effort": expected}
        assert by_id[model_id]["supported_values"] == {"reasoning_effort": ["none", "low", "medium"]}
    assert by_id["catalog-test-2026-09-30"]["status"] == "retired"


@pytest.mark.parametrize("allowed", [[], ["none"]])
def test_catalog_omits_reasoning_defaults_outside_declared_enum(monkeypatch, tmp_path, allowed):
    config = ai_config.load()
    config["providers"]["openai"]["models"]["limited-model"] = {
        "status": "active", "default_for": [],
        "supported_values": {"reasoning.effort": allowed},
    }
    config["operations"]["extract.ai"]["defaults"]["reasoning"] = {"effort": "medium"}
    use_packaged_config(config, monkeypatch, tmp_path)
    assert ai_config.resolve("extract.ai", model="limited-model")["reasoning"] == {"effort": "medium"}
    model = next(model for model in ai_catalog.extract_ai_catalog("test-version")["models"]
                 if model["id"] == "limited-model")
    assert model["supported_values"] == {"reasoning_effort": allowed}
    assert model["defaults"] == {}


def test_generator_is_deterministic_outside_repository_and_supports_rc_version(monkeypatch, tmp_path):
    script = Path(generate_ai_catalog.__file__).resolve()
    output = tmp_path / "nested" / "ai-models-v1.json"
    monkeypatch.setenv("WRANGLES_AI_CONFIG", str(tmp_path / "missing-runtime-config.yml"))
    command = [sys.executable, str(script), "--output", str(output)]
    subprocess.run(command, cwd=tmp_path, check=True, capture_output=True, text=True)
    first = output.read_bytes()
    subprocess.run(command, cwd=tmp_path, check=True, capture_output=True, text=True)
    assert output.read_bytes() == first
    assert b"\r\n" not in first
    assert json.loads(first)["package_version"] == generate_ai_catalog.package_version_from_setup(
        generate_ai_catalog.REPOSITORY_ROOT / "setup.py",
    )
    subprocess.run(command + ["--package-version", "1.20.4rc7"], cwd=tmp_path,
                   check=True, capture_output=True, text=True)
    assert json.loads(output.read_text(encoding="utf-8"))["package_version"] == "1.20.4rc7"


def test_setup_version_is_read_without_executing_setup(tmp_path):
    setup = tmp_path / "setup.py"
    setup.write_text("raise RuntimeError('must not execute')\nsetup(version='2.0.0rc1')\n", encoding="utf-8")
    assert generate_ai_catalog.package_version_from_setup(setup) == "2.0.0rc1"
    setup.write_text("setup(version=compute_version())\n", encoding="utf-8")
    with pytest.raises(ValueError, match="literal"):
        generate_ai_catalog.package_version_from_setup(setup)


@pytest.mark.parametrize("version", [None, "", " ", 123])
def test_catalog_requires_a_package_version(version):
    with pytest.raises(ValueError, match="package_version"):
        ai_catalog.extract_ai_catalog(version)
