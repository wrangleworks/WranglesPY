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
    assert {key: value for key, value in catalog.items() if key not in {"models", "embeddings"}} == {
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
    provider["endpoints"]["embeddings"] = "https://private.example/embedding-endpoint"
    provider["models"]["text-embedding-3-small"]["defaults"] = {
        "api_key": "private-embedding-secret", "user": "private-user-identifier",
        "encoding_format": "private-format",
    }
    provider["models"]["text-embedding-3-small"]["supported_values"] = {
        "user": ["private-user-identifier"],
    }
    config["providers"]["jina"]["models"]["jina-embeddings-v5-omni-small"]["defaults"].update({
        "api_key": "private-jina-secret", "prompt": {"instructions": "private-jina-prompt"},
    })
    config["operations"]["extract.ai"]["defaults"]["prompt"] = {
        "instructions": "private-operation-prompt",
    }
    use_packaged_config(config, monkeypatch, tmp_path)
    catalog = ai_catalog.extract_ai_catalog("test-version")
    assert set(catalog) == {
        "schema_version", "package_version", "operation", "provider", "protocol",
        "default_model", "models", "embeddings",
    }
    for model in catalog["models"]:
        assert set(model) == {"id", "status", "defaults", "supported_values"}
        assert set(model["defaults"]) <= {"reasoning_effort"}
        assert set(model["supported_values"]) <= {"reasoning_effort"}
    assert set(catalog["embeddings"]) == {"operation", "provider", "protocol", "default_model", "providers"}
    for provider in catalog["embeddings"]["providers"].values():
        assert set(provider) == {"default_model", "models"}
        for model in provider["models"]:
            assert set(model) == {"id", "status", "default_for", "defaults", "supported_values"}
            assert set(model["defaults"]) <= {
                "batch_size", "default_concurrency", "request_timeout_seconds", "retries",
                "precision", "dimensions", "task", "normalized", "truncate", "late_chunking",
            }
    serialized = json.dumps(catalog)
    assert "private-" not in serialized
    assert "https://" not in serialized
    untouched = copy.deepcopy(catalog)
    catalog["models"][0]["supported_values"]["reasoning_effort"] = ["altered"]
    catalog["embeddings"]["providers"]["jina"]["models"][0]["supported_values"]["task"].append("altered")
    assert ai_catalog.extract_ai_catalog("test-version") == untouched


def test_catalog_includes_separate_packaged_embedding_providers_and_defaults():
    catalog = ai_catalog.extract_ai_catalog("test-version")
    embeddings = catalog["embeddings"]
    assert {key: value for key, value in embeddings.items() if key != "providers"} == {
        "operation": "embeddings", "provider": "openai", "protocol": "embeddings",
        "default_model": "text-embedding-3-small",
    }
    assert set(embeddings["providers"]) == {"openai", "jina"}
    openai = embeddings["providers"]["openai"]
    assert openai["default_model"] == "text-embedding-3-small"
    by_id = {model["id"]: model for model in openai["models"]}
    assert set(by_id) == {"text-embedding-3-small", "text-embedding-3-large"}
    assert by_id["text-embedding-3-small"]["default_for"] == ["embeddings"]
    assert by_id["text-embedding-3-large"]["default_for"] == []
    for model in openai["models"]:
        assert model["defaults"] == {
            "batch_size": 100, "default_concurrency": 10, "request_timeout_seconds": 30,
            "retries": 1, "precision": "float32",
        }
        assert model["supported_values"] == {}
    jina = embeddings["providers"]["jina"]
    assert jina["default_model"] is None
    assert len(jina["models"]) == 1
    model = jina["models"][0]
    assert model["id"] == "jina-embeddings-v5-omni-small"
    assert model["default_for"] == []
    assert model["defaults"] == {**openai["models"][0]["defaults"], "task": "text-matching"}
    assert model["supported_values"] == {"task": [
        "retrieval.query", "retrieval.passage", "text-matching", "clustering", "classification",
    ]}
    embedding_ids = {model["id"] for provider in embeddings["providers"].values()
                     for model in provider["models"]}
    assert not embedding_ids.intersection(model["id"] for model in catalog["models"])


def test_embedding_export_follows_provider_default_roles_and_runtime_precedence(monkeypatch, tmp_path):
    config = ai_config.load()
    openai_models = config["providers"]["openai"]["models"]
    openai_models["text-embedding-3-small"]["default_for"] = []
    openai_models["text-embedding-3-large"]["default_for"] = ["embeddings"]
    jina_models = config["providers"]["jina"]["models"]
    jina_models["catalog-vector"] = {
        "status": "deprecated", "default_for": ["embeddings"],
        "defaults": {"task": "retrieval.query", "dimensions": 128, "normalized": True, "truncate": False},
        "protocol_defaults": {"embeddings": {"dimensions": 256, "late_chunking": False}},
        "supported_values": {"dimensions": [128, 256], "task": ["retrieval.query", "retrieval.passage"]},
    }
    jina_models["catalog-vector-2026-09-30"] = {"status": "retired"}
    config["operations"]["embeddings"]["provider"] = "jina"
    config["operations"]["embeddings"]["defaults"].update({"task": "retrieval.passage", "retries": 0})
    use_packaged_config(config, monkeypatch, tmp_path)
    catalog = ai_catalog.extract_ai_catalog("test-version")
    embeddings = catalog["embeddings"]
    assert embeddings["provider"] == "jina"
    assert embeddings["default_model"] == "catalog-vector"
    assert embeddings["providers"]["openai"]["default_model"] == "text-embedding-3-large"
    jina = embeddings["providers"]["jina"]
    assert jina["default_model"] == "catalog-vector"
    by_id = {model["id"]: model for model in jina["models"]}
    for model_id in ("catalog-vector", "catalog-vector-2026-09-30"):
        assert by_id[model_id]["defaults"] == {
            "task": "retrieval.passage", "dimensions": 256, "normalized": True, "truncate": False,
            "late_chunking": False, "batch_size": 100, "default_concurrency": 10,
            "request_timeout_seconds": 30, "retries": 0, "precision": "float32",
        }
        assert by_id[model_id]["supported_values"] == {
            "dimensions": [128, 256], "task": ["retrieval.query", "retrieval.passage"],
        }
    assert by_id["catalog-vector-2026-09-30"]["default_for"] == []
    assert by_id["catalog-vector-2026-09-30"]["status"] == "retired"
    assert all("task" not in model["defaults"] for model in embeddings["providers"]["openai"]["models"])


def test_embedding_default_role_without_applications_stays_out_of_extraction(monkeypatch, tmp_path):
    config = ai_config.load()
    default_model = ai_config.resolve("embeddings")["model"]
    config["providers"]["openai"]["models"][default_model].pop("applications")
    use_packaged_config(config, monkeypatch, tmp_path)
    catalog = ai_catalog.extract_ai_catalog("test-version")
    assert default_model not in {model["id"] for model in catalog["models"]}
    assert default_model in {model["id"] for model in catalog["embeddings"]["providers"]["openai"]["models"]}


def test_embedding_catalog_does_not_fall_back_to_global_text_model(monkeypatch, tmp_path):
    config = ai_config.load()
    for model in config["providers"]["openai"]["models"].values():
        model["default_for"] = [role for role in model.get("default_for", []) if role != "embeddings"]
    use_packaged_config(config, monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="No default model for 'embeddings'"):
        ai_catalog.extract_ai_catalog("test-version")


def test_embedding_export_preserves_unknown_and_empty_enums(monkeypatch, tmp_path):
    config = ai_config.load()
    model = config["providers"]["jina"]["models"]["jina-embeddings-v5-omni-small"]
    model["defaults"].pop("task")
    model["supported_values"]["task"] = []
    use_packaged_config(config, monkeypatch, tmp_path)
    embeddings = ai_catalog.extract_ai_catalog("test-version")["embeddings"]
    exported = embeddings["providers"]["jina"]["models"][0]
    assert exported["supported_values"] == {"task": []}
    assert "task" not in exported["defaults"]
    assert "precision" not in exported["supported_values"]


@pytest.mark.parametrize("key,value", [("dimensions", {"secret": "private-value"}), ("precision", []), ("dimensions", True)])
def test_embedding_export_rejects_non_scalar_or_wrongly_typed_defaults(monkeypatch, tmp_path, key, value):
    config = ai_config.load()
    config["operations"]["embeddings"]["defaults"].pop(key, None)
    config["providers"]["openai"]["models"]["text-embedding-3-small"]["defaults"] = {key: value}
    use_packaged_config(config, monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="invalid public default"):
        ai_catalog.extract_ai_catalog("test-version")


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
