import json
import logging

import pandas as pd
import pytest
import wrangles
from wrangles import ai_config, generate


def _run_generate(via_recipe, **settings):
    fields = {"length": {"type": "string"}}
    settings = {"api_key": "key", "threads": 1, **settings}
    if via_recipe:
        return wrangles.recipe.run(
            {"wrangles": [{"generate.ai": {**settings, "output": fields}}]},
            dataframe=pd.DataFrame({"data": ["wrench 25mm", "bolt 25mm"]}),
        )
    return generate.ai(
        ["wrench 25mm", "bolt 25mm"],
        output={"type": "object", "properties": fields}, **settings,
    )


@pytest.fixture
def generate_config(monkeypatch, tmp_path):
    monkeypatch.delenv("WRANGLES_AI_CONFIG", raising=False)
    ai_config.clear_cache()
    config = ai_config.load()

    def install():
        override = tmp_path / "generate-ai.yml"
        override.write_text(json.dumps(config), encoding="utf-8")
        monkeypatch.setenv("WRANGLES_AI_CONFIG", str(override))
        ai_config.clear_cache()

    yield config, install
    ai_config.clear_cache()


@pytest.fixture
def generation_calls(monkeypatch):
    calls = []

    def call_openai(api_key, payload, url, timeout, retries, previous_response_id=None):
        calls.append((payload, previous_response_id))
        return {"length": "25mm"}, f"response-{len(calls)}"

    monkeypatch.setattr(generate, "_call_openai", call_openai)
    return calls


@pytest.mark.parametrize("via_recipe", [False, True])
@pytest.mark.parametrize("explicit_model", [None, "explicit-model"])
@pytest.mark.parametrize("configured_model", [None, "configured-model"])
def test_generate_ai_resolves_model_at_call_time(
    monkeypatch, tmp_path, via_recipe, explicit_model, configured_model
):
    if configured_model:
        override = tmp_path / "ai.yml"
        override.write_text(json.dumps({
            "version": 1,
            "extract_ai": {"model": configured_model},
        }), encoding="utf-8")
        monkeypatch.setenv("WRANGLES_AI_CONFIG", str(override))
    else:
        monkeypatch.delenv("WRANGLES_AI_CONFIG", raising=False)
    ai_config.clear_cache()
    calls = []

    def call_openai(api_key, payload, url, timeout, retries):
        calls.append(payload)
        return {"length": "25mm"}, None

    monkeypatch.setattr(generate, "_call_openai", call_openai)
    settings = {
        "api_key": "key",
        "threads": 1,
        "reasoning": {"effort": "low"},
    }
    if explicit_model:
        settings["model"] = explicit_model
    fields = {"length": {"type": "string"}}
    try:
        if via_recipe:
            result = wrangles.recipe.run(
                {"wrangles": [{"generate.ai": {**settings, "output": fields}}]},
                dataframe=pd.DataFrame({"data": ["wrench 25mm"]}),
            )
            assert result["length"].tolist() == ["25mm"]
        else:
            result = generate.ai(
                "wrench 25mm", output={"type": "object", "properties": fields},
                **settings,
            )
            assert result["length"] == "25mm"
        assert len(calls) == 1
        assert calls[0]["model"] == (explicit_model or ai_config.extract_ai()["model"])
        assert calls[0]["reasoning"] == {"effort": "low"}
    finally:
        ai_config.clear_cache()


@pytest.mark.parametrize("via_recipe", [False, True])
@pytest.mark.parametrize("explicit_overrides", [False, True])
def test_generate_forwards_request_defaults_with_explicit_overrides(
    generate_config, generation_calls, via_recipe, explicit_overrides
):
    config, install = generate_config
    defaults = config["operations"]["generate.ai"]["defaults"]
    defaults.update(
        service_tier="flex", store=True, include=["reasoning.encrypted_content"],
        max_output_tokens=120, top_p=0.9, text={"verbosity": "low"},
    )
    install()
    settings = {}
    if explicit_overrides:
        settings.update(service_tier="default", store=False, max_output_tokens=40, text={"verbosity": "high"})
    _run_generate(via_recipe, **settings)
    for payload, _ in generation_calls:
        assert payload["service_tier"] == ("default" if explicit_overrides else "flex")
        assert payload["store"] is (not explicit_overrides)
        assert payload["max_output_tokens"] == (40 if explicit_overrides else 120)
        assert payload["include"] == ["reasoning.encrypted_content"]
        assert payload["top_p"] == 0.9
        assert payload["text"]["verbosity"] == ("high" if explicit_overrides else "low")
        assert payload["text"]["format"]["schema"]["properties"] == {"length": {"type": "string"}}
        assert payload["text"]["format"]["type"] == "json_schema"
        assert "default_concurrency" not in payload
        assert "provider" not in payload
        assert "recipe_strict" not in payload


@pytest.mark.parametrize("via_recipe", [False, True])
@pytest.mark.parametrize("configured_key,explicit_key", [
    ("max_tokens", "max_output_tokens"),
    ("max_output_tokens", "max_completion_tokens"),
])
def test_generate_token_alias_overrides_config_across_names(
    generate_config, generation_calls, via_recipe, configured_key, explicit_key
):
    config, install = generate_config
    config["operations"]["generate.ai"]["defaults"][configured_key] = 100
    install()
    _run_generate(via_recipe, **{explicit_key: 50})
    for payload, _ in generation_calls:
        assert payload["max_output_tokens"] == 50
        assert "max_tokens" not in payload
        assert "max_completion_tokens" not in payload


@pytest.mark.parametrize("via_recipe", [False, True])
@pytest.mark.parametrize("text", ["low", {"format": {"type": "text"}}])
def test_generate_rejects_invalid_text_or_schema_override(
    generate_config, generation_calls, via_recipe, text
):
    with pytest.raises(ValueError, match="generate.ai (text must|controls text.format)"):
        _run_generate(via_recipe, text=text)
    assert generation_calls == []


@pytest.mark.parametrize("via_recipe", [False, True])
@pytest.mark.parametrize("supported", [False, True])
def test_generate_uses_declared_reasoning_and_verbosity_enums(
    generate_config, generation_calls, via_recipe, supported, caplog
):
    config, install = generate_config
    model = ai_config.resolve("generate.ai")["model"]
    config["providers"]["openai"]["models"][model]["supported_values"].update({
        "reasoning.effort": ["none", "low"], "text.verbosity": ["low"],
    })
    install()
    with caplog.at_level(logging.WARNING):
        _run_generate(
            via_recipe, reasoning={"effort": "low" if supported else "high"},
            text={"verbosity": "low" if supported else "high"},
        )
    for payload, _ in generation_calls:
        if supported:
            assert payload["reasoning"] == {"effort": "low"}
            assert payload["text"]["verbosity"] == "low"
        else:
            assert "reasoning" not in payload
            assert "verbosity" not in payload["text"]
    assert sum("does not support" in record.message for record in caplog.records) == (0 if supported else 2)


@pytest.mark.parametrize("via_recipe", [False, True])
def test_generate_preserves_options_for_uncataloged_model(
    generate_config, generation_calls, via_recipe
):
    _run_generate(via_recipe, model="custom-model", reasoning={"effort": "medium"}, text={"verbosity": "high"})
    for payload, _ in generation_calls:
        assert payload["reasoning"] == {"effort": "medium"}
        assert payload["text"]["verbosity"] == "high"


@pytest.mark.parametrize("via_recipe", [False, True])
def test_generate_warns_once_for_deprecated_model(
    generate_config, generation_calls, via_recipe, caplog
):
    config, install = generate_config
    default_model = ai_config.resolve("generate.ai")["model"]
    model = "deprecated-generation-model"
    models = config["providers"]["openai"]["models"]
    models[model] = {**models[default_model], "status": "deprecated", "default_for": []}
    install()
    with caplog.at_level(logging.WARNING):
        _run_generate(via_recipe, model=model)
    assert len(generation_calls) == 2
    warnings = [record for record in caplog.records if "deprecated status" in record.message]
    assert len(warnings) == 1
    assert model in warnings[0].message


@pytest.mark.parametrize("example_alias", ["Example", "Examples", "example", "examples"])
def test_generate_recipe_consumes_example_aliases(generate_config, generation_calls, example_alias):
    example = {"input": "sample 25mm", "output": {"length": "25mm"}, "notes": "Keep units"}
    _run_generate(True, **{example_alias: [example]})
    for payload, _ in generation_calls:
        assert json.loads(payload["input"][0]["content"]) == {"input": "sample 25mm", "notes": "Keep units"}
        assert json.loads(payload["input"][1]["content"]) == {"length": "25mm"}
        assert not {"Example", "Examples", "example", "examples"}.intersection(payload)


def test_generate_recipe_rejects_conflicting_example_aliases(generate_config, generation_calls):
    with pytest.raises(ValueError, match="one examples argument"):
        _run_generate(True, Example=[], examples=[])
    assert generation_calls == []


def test_generate_retains_instructions_summary_web_context_and_field_chaining(
    generate_config, generation_calls, monkeypatch
):
    monkeypatch.setattr(generate, "_perform_web_search", lambda query: "Known search context")
    result = generate.ai(
        "wrench", api_key="key", threads=1,
        output={"type": "object", "properties": {"length": {"type": "string"}, "width": {"type": "string"}}},
        messages=[{"role": "system", "content": "Use supplied dimensions"}],
        summary=True, web_search=True, previous_response=True,
    )
    assert result["source"] == "internet"
    assert len(generation_calls) == 2
    assert [previous for _, previous in generation_calls] == [None, "response-1"]
    for index, (payload, _) in enumerate(generation_calls):
        assert payload["instructions"] == "Use supplied dimensions"
        assert payload["reasoning"]["summary"] == "auto"
        assert "Known search context" in payload["input"][0]["content"]
        assert list(payload["text"]["format"]["schema"]["properties"]) == [["length"], ["width"]][index]


@pytest.mark.parametrize("via_recipe", [False, True])
@pytest.mark.parametrize("explicit_overrides", [False, True])
def test_generate_uses_operation_defaults_and_preserves_overrides(
    monkeypatch, tmp_path, via_recipe, explicit_overrides
):
    config = ai_config.load()
    defaults = config["operations"]["generate.ai"]["defaults"]
    defaults.update(
        default_concurrency=1, request_timeout_seconds=18, retries=2,
        strict=False, recipe_strict=True, reasoning={"effort": "medium"},
    )
    config["providers"]["openai"]["endpoints"]["responses"] = "https://configured.example/responses"
    override = tmp_path / "ai.yml"
    override.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setenv("WRANGLES_AI_CONFIG", str(override))
    ai_config.clear_cache()
    calls = []
    def call_openai(api_key, payload, url, timeout, retries):
        calls.append((payload, url, timeout, retries))
        return {"length": "25mm"}, None
    monkeypatch.setattr(generate, "_call_openai", call_openai)
    settings = {"api_key": "key"}
    if explicit_overrides:
        settings.update(
            timeout=22, retries=0, strict=False,
            reasoning={"effort": "low"}, url="https://explicit.example/responses",
        )
    fields = {"length": {"type": "string"}}
    try:
        if via_recipe:
            wrangles.recipe.run(
                {"wrangles": [{"generate.ai": {**settings, "output": fields}}]},
                dataframe=pd.DataFrame({"data": ["wrench 25mm"]}),
            )
        else:
            generate.ai("wrench 25mm", output={"type": "object", "properties": fields}, **settings)
        payload, url, timeout, retries = calls[0]
        assert payload["reasoning"] == {"effort": "low" if explicit_overrides else "medium"}
        assert payload["text"]["format"]["strict"] is (False if explicit_overrides else via_recipe)
        assert url == ("https://explicit.example/responses" if explicit_overrides else "https://configured.example/responses")
        assert timeout == (22 if explicit_overrides else 18)
        assert retries == (0 if explicit_overrides else 2)
    finally:
        ai_config.clear_cache()
