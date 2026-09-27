"""Public model metadata exported from the packaged extraction configuration.

The public catalog is deliberately smaller than runtime configuration: it does
not expose endpoints, prompts, credentials, or arbitrary provider parameters.
Deployment exports always use the packaged YAML, never WRANGLES_AI_CONFIG.
"""
from . import ai_config as _ai_config


def extract_ai_catalog(package_version: str) -> dict:
    """Return the versioned public catalog for the packaged extract.ai adapter.

    OpenAI catalog entries are eligible unless their applications include
    embeddings. Entries without application annotations remain eligible so
    older extraction models remain visible with their lifecycle status.
    Missing reasoning enums mean unknown; an explicit empty enum means the
    model does not support the option. No model capabilities are guessed.
    """
    if not isinstance(package_version, str) or not package_version.strip():
        raise ValueError("package_version must be a non-empty string.")
    config = _ai_config._load_config_file(str(_ai_config._PACKAGED_CONFIG.resolve()))
    if config["version"] != 2:
        raise ValueError("The public AI catalog requires packaged configuration version 2.")
    operation = "extract.ai"
    policy = _ai_config._resolve_v2(config, operation)
    provider = policy["provider"]
    if provider != "openai":
        raise ValueError("The public extract.ai catalog currently supports only OpenAI.")

    models = []
    for model_id in sorted(config["providers"][provider]["models"]):
        entry = _ai_config._model_entry(config, provider, model_id)
        if "embeddings" in entry.get("applications", []):
            continue
        resolved = _ai_config._resolve_v2(config, operation, model=model_id)
        defaults = {}
        reasoning = resolved.get("reasoning", {})
        if "effort" in reasoning:
            effort = reasoning["effort"]
            if not isinstance(effort, str):
                raise ValueError(f"Model {model_id!r} reasoning default must be a string.")
            defaults["reasoning_effort"] = effort
        supported_values = {}
        supported = entry.get("supported_values", {})
        if "reasoning.effort" in supported:
            efforts = supported["reasoning.effort"]
            if any(not isinstance(effort, str) for effort in efforts):
                raise ValueError(f"Model {model_id!r} reasoning enum must contain strings.")
            supported_values["reasoning_effort"] = list(efforts)
            # Runtime omits unsupported tuning, including an operation default
            # that applies to other models but not this model's declared enum.
            if defaults.get("reasoning_effort") not in efforts:
                defaults.pop("reasoning_effort", None)
        models.append({
            "id": model_id,
            "status": entry["status"],
            "defaults": defaults,
            "supported_values": supported_values,
        })

    if policy["model"] not in {model["id"] for model in models}:
        raise ValueError("The extract.ai default model is not eligible for the public catalog.")
    return {
        "schema_version": 1,
        "package_version": package_version.strip(),
        "operation": operation,
        "provider": provider,
        "protocol": policy["protocol"],
        "default_model": policy["model"],
        "models": models,
    }
