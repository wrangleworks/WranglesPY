"""Offline configuration contracts; no provider requests or credentials."""
import copy

import pytest
import yaml

from wrangles import ai_config


@pytest.fixture(autouse=True)
def isolate_config(monkeypatch):
    monkeypatch.delenv("WRANGLES_AI_CONFIG", raising=False)
    ai_config.clear_cache()
    yield
    ai_config.clear_cache()


def use_config(config, monkeypatch, tmp_path):
    path = tmp_path / "ai.yml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setenv("WRANGLES_AI_CONFIG", str(path))
    ai_config.clear_cache()
    return path


def test_packaged_operation_defaults_and_model_lifecycle():
    config = ai_config.load()
    assert config["version"] == 2
    luna = config["providers"]["openai"]["models"]["gpt-6-luna"]
    assert luna["status"] == "active"
    assert luna["supported_values"]["reasoning.effort"] == ["none", "low", "medium", "high", "xhigh", "max"]
    extraction = ai_config.resolve("extract.ai")
    generation = ai_config.resolve("generate.ai")
    assert extraction["model"] == generation["model"] == "gpt-6-luna"
    assert extraction["reasoning"] == {"effort": "none"}
    assert generation["reasoning"] == {"effort": "low"}
    assert generation["strict"] is True
    assert generation["recipe_strict"] is False
    assert extraction["request_timeout_seconds"] == 12
    assert extraction["cache"]["ttl_seconds"] == 3600
    assert ai_config.resolve("embeddings")["model"] == "text-embedding-3-small"
    assert ai_config.resolve("search.retrieve_link_content")["model"] == "gemini-3.8-flash"
    for operation in config["operations"]:
        explicit_model = "org/task-model" if config["operations"][operation].get("requires_model") else None
        assert ai_config.resolve(operation, model=explicit_model)["retries"] == 1
    assert config["providers"]["anthropic"]["models"] == {}


def test_catalog_metadata_is_separate_from_request_defaults():
    config = ai_config.load()
    provider = config["providers"]["openai"]
    assert provider["models"]["gpt-6-luna"]["applications"] == ["data_extraction", "description_writing"]
    assert provider["models"]["gpt-6-sol"]["applications"] == ["reasoning", "agents"]
    assert provider["models"]["text-embedding-3-large"]["default_for"] == []
    assert provider["documentation"]["model_cards"].startswith("https://")
    policy = ai_config.resolve("extract.ai")
    assert "model_cards" not in policy["endpoints"]
    assert "applications" not in policy
    assert "documentation" not in policy


def test_generic_task_operation_requires_explicit_model():
    with pytest.raises(ValueError, match="requires an explicit model"):
        ai_config.resolve("huggingface")
    policy = ai_config.resolve("huggingface", model="Org/task-model")
    assert policy["model"] == "Org/task-model"
    assert policy["endpoints"]["hf_inference"] == "https://router.huggingface.co/hf-inference/models"


@pytest.mark.parametrize("catalog_prefix", ["", "models/"])
@pytest.mark.parametrize("caller_prefix", ["", "models/"])
def test_google_model_spellings_share_defaults_and_preserve_explicit_model(
    monkeypatch, tmp_path, catalog_prefix, caller_prefix,
):
    config = ai_config.load()
    config["providers"]["google"]["models"] = {
        catalog_prefix + "gemini-alias-test": {
            "status": "active", "default_for": ["search.retrieve_link_content"],
            "defaults": {"temperature": 0.17},
        },
    }
    use_config(config, monkeypatch, tmp_path)
    requested_model = caller_prefix + "gemini-alias-test"
    resolved = ai_config.resolve("search.retrieve_link_content", model=requested_model)
    assert resolved["model"] == requested_model
    assert resolved["temperature"] == 0.17
    assert ai_config.model_defaults(requested_model, provider="google") == {"temperature": 0.17}


def test_google_duplicate_catalog_spellings_are_rejected(monkeypatch, tmp_path):
    config = ai_config.load()
    models = config["providers"]["google"]["models"]
    models["gemini-alias-test"] = {"status": "active", "defaults": {"temperature": 0.17}}
    models["models/gemini-alias-test"] = {"status": "active", "defaults": {"temperature": 0.8}}
    use_config(config, monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="Duplicate Google model aliases"):
        ai_config.load()


@pytest.mark.parametrize("applications", ["embeddings", False, None, ["embeddings", ""], ["embeddings", 3]])
def test_invalid_applications_metadata_is_rejected(monkeypatch, tmp_path, applications):
    config = ai_config.load()
    config["providers"]["jina"]["models"]["jina-embeddings-v5-omni-small"]["applications"] = applications
    use_config(config, monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="applications"):
        ai_config.load()


def test_singular_application_metadata_has_migration_error(monkeypatch, tmp_path):
    config = ai_config.load()
    config["providers"]["openai"]["models"]["gpt-6-luna"]["application"] = "extraction"
    use_config(config, monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="renamed to applications"):
        ai_config.load()


@pytest.mark.parametrize("applications", [[], ["data_extraction", "description writing"]])
def test_applications_accepts_lists_including_spaces(monkeypatch, tmp_path, applications):
    config = ai_config.load()
    config["providers"]["openai"]["models"]["gpt-6-luna"]["applications"] = applications
    use_config(config, monkeypatch, tmp_path)
    assert ai_config.load()["providers"]["openai"]["models"]["gpt-6-luna"]["applications"] == applications


@pytest.mark.parametrize("provider,model", [
    ("openai", "gpt-4o"),
    ("openai", "gpt-4o-2024-08-06"),
    ("google", "models/deprecated-gemini"),
])
def test_deprecated_catalog_models_warn_only_when_called(monkeypatch, tmp_path, caplog, provider, model):
    config = ai_config.load()
    config["providers"]["google"]["models"]["deprecated-gemini"] = {"status": "deprecated"}
    use_config(config, monkeypatch, tmp_path)
    operation = "extract.ai" if provider == "openai" else "search.retrieve_link_content"
    assert ai_config.resolve(operation, model=model)["model"] == model
    assert not caplog.records
    ai_config.warn_if_deprecated(model, provider)
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert "deprecated" in caplog.text
    assert provider in caplog.text and model in caplog.text


def test_active_snapshot_override_and_unlisted_models_do_not_warn(monkeypatch, tmp_path, caplog):
    config = ai_config.load()
    config["providers"]["openai"]["models"]["gpt-4o-2024-08-06"] = {"status": "active"}
    use_config(config, monkeypatch, tmp_path)
    for model in ("gpt-6-luna", "gpt-4o-2024-08-06", "unlisted-model"):
        ai_config.warn_if_deprecated(model)
    assert not caplog.records


def test_legacy_configuration_uses_packaged_deprecation_status(monkeypatch, tmp_path, caplog):
    use_config({"version": 1, "extract_ai": {"model": "gpt-4o"}}, monkeypatch, tmp_path)
    ai_config.warn_if_deprecated("gpt-4o")
    assert "deprecated" in caplog.text


def test_custom_catalog_is_authoritative_for_deprecation(monkeypatch, tmp_path, caplog):
    config = ai_config.load()
    del config["providers"]["openai"]["models"]["gpt-4o"]
    use_config(config, monkeypatch, tmp_path)
    ai_config.warn_if_deprecated("gpt-4o")
    assert not caplog.records


def test_deprecated_default_roles_remain_usable(monkeypatch, tmp_path, caplog):
    config = ai_config.load()
    config["providers"]["openai"]["models"]["gpt-6-luna"]["status"] = "deprecated"
    use_config(config, monkeypatch, tmp_path)
    for operation, role in (("extract.ai", None), ("generate.ai", None), ("extract.ai", "test")):
        assert ai_config.resolve(operation, role=role)["model"] == "gpt-6-luna"
    assert not caplog.records  # Only execution emits the warning.


@pytest.mark.parametrize("documentation", [[], {"model_cards": ""}, {"model_cards": False}])
def test_invalid_documentation_metadata_is_rejected(monkeypatch, tmp_path, documentation):
    config = ai_config.load()
    config["providers"]["google"]["documentation"] = documentation
    use_config(config, monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="documentation"):
        ai_config.load()


def test_explicit_and_operation_defaults_have_documented_precedence(monkeypatch, tmp_path):
    config = ai_config.load()
    models = config["providers"]["openai"]["models"]
    models["gpt-6-luna"]["default_for"] = ["global", "generate.ai"]
    models["configured-extract"] = {
        "status": "active", "default_for": ["extract.ai"],
        "defaults": {"reasoning": {"effort": "high", "summary": "auto"}},
        "supported_values": {"reasoning.effort": ["high", "low"]},
    }
    models["configured-test"] = {"status": "active", "default_for": ["test"]}
    config["operations"]["extract.ai"]["defaults"]["reasoning"] = {"effort": "low"}
    use_config(config, monkeypatch, tmp_path)
    policy = ai_config.resolve("extract.ai")
    assert policy["model"] == "configured-extract"
    assert policy["reasoning"] == {"effort": "low", "summary": "auto"}
    assert ai_config.resolve("extract.ai", role="test")["model"] == "configured-test"
    assert ai_config.resolve("extract.ai", model="explicit-model", role="test")["model"] == "explicit-model"


def test_global_fallback_does_not_replace_embedding_or_retrieval_roles(monkeypatch, tmp_path):
    config = ai_config.load()
    config["providers"]["openai"]["models"]["gpt-6-luna"]["default_for"] = ["global", "test"]
    use_config(config, monkeypatch, tmp_path)
    assert ai_config.resolve("extract.ai")["model"] == "gpt-6-luna"
    for operation in ("embeddings", "search.retrieve_link_content"):
        for role in ("test", "global"):
            with pytest.raises(ValueError, match="cannot select"):
                ai_config.resolve(operation, role=role)
    with pytest.raises(ValueError, match="specify model explicitly"):
        ai_config.resolve("embeddings", provider="jina")


def test_provider_local_roles_support_a_configured_jina_default(monkeypatch, tmp_path):
    config = ai_config.load()
    config["providers"]["jina"]["models"]["custom-jina-model"] = {
        "status": "active", "default_for": ["embeddings"],
        "defaults": {"dimensions": 64},
    }
    use_config(config, monkeypatch, tmp_path)
    assert ai_config.resolve("embeddings")["model"] == "text-embedding-3-small"
    jina = ai_config.resolve("embeddings", provider="jina")
    assert jina["model"] == "custom-jina-model"
    assert jina["dimensions"] == 64
    assert jina["endpoints"]["embeddings"] == "https://api.jina.ai/v1/embeddings"


def test_custom_model_and_endpoint_are_preserved(monkeypatch, tmp_path):
    config = ai_config.load()
    config["providers"]["openai"]["endpoints"]["responses"] = "https://custom.example/responses"
    use_config(config, monkeypatch, tmp_path)
    policy = ai_config.resolve("extract.ai", model="unlisted-model")
    assert policy["model"] == "unlisted-model"
    assert policy["endpoints"]["responses"] == "https://custom.example/responses"
    assert policy["default_concurrency"] == 32
    assert "reasoning" not in policy
    assert "text" not in policy


def test_snapshot_inherits_model_options_with_exact_overrides(monkeypatch, tmp_path):
    config = ai_config.load()
    models = config["providers"]["openai"]["models"]
    models["gpt-6-luna-2026-09-25"] = {
        "status": "active", "default_for": [],
        "defaults": {"reasoning": {"effort": "high"}},
        "supported_values": {"reasoning.effort": ["low", "high"]},
    }
    use_config(config, monkeypatch, tmp_path)
    policy = ai_config.resolve("extract.ai", model="gpt-6-luna-2026-09-25")
    assert policy["reasoning"] == {"effort": "high"}
    assert policy["text"]["verbosity"] == "low"
    assert ai_config.model_capabilities(policy["model"])["reasoning_none"] is False
    assert ai_config.model_capabilities("gpt-6-luna-2026-09-26")["reasoning_none"] is True


def test_legacy_chat_defaults_do_not_leak_into_responses():
    assert ai_config.model_defaults("gpt-4o", protocol="chat_completions") == {"temperature": 0.2}
    assert ai_config.model_defaults("gpt-4o-mini-2024-07-18", protocol="chat_completions") == {"temperature": 0.2}
    assert ai_config.model_defaults("gpt-4o", protocol="responses") == {}
    assert "temperature" not in ai_config.resolve("extract.ai", model="gpt-4o")


def test_legacy_override_is_replacement_and_merges_capabilities(monkeypatch, tmp_path):
    legacy = {
        "version": 1,
        "extract_ai": {"model": "legacy-custom", "reasoning": {"effort": "high"}},
        "model_capabilities": {"gpt-6-luna": {"reasoning_none": False}},
    }
    use_config(legacy, monkeypatch, tmp_path)
    assert ai_config.load() == legacy
    assert ai_config.extract_ai() == legacy["extract_ai"]
    assert ai_config.resolve("extract.ai", model="explicit-custom") == {
        "model": "explicit-custom", "reasoning": {"effort": "high"},
    }
    assert ai_config.resolve("generate.ai")["model"] == "legacy-custom"
    assert ai_config.resolve("embeddings")["model"] == "text-embedding-3-small"
    assert ai_config.model_capabilities("gpt-6-luna") == {
        "reasoning": True, "reasoning_none": False, "low_verbosity": True,
    }


def test_v2_does_not_merge_packaged_models(monkeypatch, tmp_path):
    config = ai_config.load()
    models = config["providers"]["openai"]["models"]
    models["replacement"] = models.pop("gpt-6-luna")
    use_config(config, monkeypatch, tmp_path)
    assert ai_config.resolve("extract.ai")["model"] == "replacement"
    assert ai_config.model_capabilities("gpt-6-luna") == {}


def test_results_are_defensive_and_edits_reload_after_clear_cache(monkeypatch, tmp_path):
    config = ai_config.load()
    path = use_config(config, monkeypatch, tmp_path)
    policy = ai_config.extract_ai()
    policy["cache"]["enabled"] = False
    policy["endpoints"]["responses"] = "modified"
    assert ai_config.extract_ai()["cache"]["enabled"] is True
    config["operations"]["extract.ai"]["defaults"]["retries"] = 3
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    assert ai_config.extract_ai()["retries"] == 1
    ai_config.clear_cache()
    assert ai_config.extract_ai()["retries"] == 3


def test_inherited_snapshot_defaults_are_validated(monkeypatch, tmp_path):
    config = ai_config.load()
    config["providers"]["openai"]["models"]["gpt-6-luna-2026-09-25"] = {
        "status": "active", "defaults": {"reasoning": {"effort": "invalid"}},
    }
    use_config(config, monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="must be one of"):
        ai_config.load()


@pytest.mark.parametrize("mutation,match", [
    (lambda c: c.update(version=True), "unsupported version"),
    (lambda c: c.update(providers=[]), "providers must be an object"),
    (lambda c: c["providers"]["openai"].update(models=[]), "models must be an object"),
    (lambda c: c["providers"].update(OpenAI={"models": {}}), "Provider names must be lowercase"),
    (lambda c: c["providers"]["openai"]["models"]["gpt-6-luna"].update(status=[]), "status must"),
    (lambda c: c["providers"]["openai"]["models"]["gpt-6-luna"].update(status="retired"), "cannot hold default roles"),
    (lambda c: c["providers"]["openai"]["models"]["gpt-4o-mini"].update(default_for=["global"]), "Duplicate default role"),
    (lambda c: c["providers"]["openai"]["models"]["gpt-4o"].update(default_for="global"), "list of non-empty roles"),
    (lambda c: c["providers"]["openai"]["models"]["gpt-4o-mini"].update(default_for=["extrcat.ai"]), "unknown default role"),
    (lambda c: c["providers"]["openai"]["models"]["gpt-6-luna"]["supported_values"].update({"reasoning.effort": True}), "list of enum values"),
    (lambda c: c["providers"]["openai"]["models"]["gpt-6-luna"]["supported_values"].update({"reasoning.effort": [True]}), "list of enum values"),
    (lambda c: c["providers"]["openai"]["models"]["gpt-6-luna"]["defaults"]["reasoning"].update(effort="invalid"), "must be one of"),
    (lambda c: c["operations"]["generate.ai"]["defaults"]["reasoning"].update(effort="invalid"), "must be one of"),
    (lambda c: c["operations"]["generate.ai"]["defaults"].update(reasoning="low"), "reasoning must be an object"),
    (lambda c: c["operations"]["extract.ai"]["defaults"].update(default_concurrency=True), "must be an integer"),
    (lambda c: c["operations"]["extract.ai"]["defaults"].update(request_timeout_seconds=float("nan")), "positive finite"),
    (lambda c: c["operations"]["extract.ai"]["defaults"]["cache"].update(enabled="true"), "must be true or false"),
    (lambda c: c["operations"]["embeddings"].update(provider="missing"), "unconfigured provider"),
])
def test_invalid_v2_configs_fail_before_request_resolution(monkeypatch, tmp_path, mutation, match):
    config = copy.deepcopy(ai_config.load())
    mutation(config)
    use_config(config, monkeypatch, tmp_path)
    with pytest.raises(ValueError, match=match):
        ai_config.load()
