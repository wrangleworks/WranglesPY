import json

import pandas as pd
import pytest
import wrangles
from wrangles import ai_config, generate


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

    def call_openai(input_data, api_key, payload, url, timeout, retries):
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
