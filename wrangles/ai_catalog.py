"""Public extraction and embedding metadata from the packaged configuration.

The public catalog is deliberately smaller than runtime configuration: it does
not expose endpoints, prompts, credentials, or arbitrary provider parameters.
Deployment exports always use the packaged YAML, never WRANGLES_AI_CONFIG.
"""
import copy as _copy
import math as _math

from . import ai_config as _ai_config


_EMBEDDING_COMMON_FIELDS = (
    "batch_size", "default_concurrency", "request_timeout_seconds", "retries",
    "precision", "dimensions",
)
_EMBEDDING_PROVIDER_FIELDS = {
    "openai": _EMBEDDING_COMMON_FIELDS,
    "jina": (*_EMBEDDING_COMMON_FIELDS, "task", "normalized", "truncate", "late_chunking"),
}


def _is_embedding_model(entry: dict) -> bool:
    return ("embeddings" in entry.get("applications", [])
            or "embeddings" in entry.get("default_for", []))


def _embedding_default(key: str, value, model: str):
    """Reject structured/private values masquerading as public scalar options."""
    if key in {"precision", "task"}:
        valid = isinstance(value, str) and bool(value.strip())
    elif key in {"normalized", "truncate", "late_chunking"}:
        valid = isinstance(value, bool)
    elif key == "request_timeout_seconds":
        valid = type(value) in {int, float} and _math.isfinite(value) and value > 0
    else:
        valid = type(value) is int and value >= (0 if key == "retries" else 1)
    if not valid:
        raise ValueError(f"Embedding model {model!r} has an invalid public default for {key!r}.")
    return value


def _embedding_catalog(config: dict) -> dict:
    operation = "embeddings"
    policy = _ai_config._resolve_v2(config, operation)
    if policy["protocol"] != "embeddings":
        raise ValueError("The public embedding catalog requires the embeddings protocol.")
    providers = {}
    for provider, fields in sorted(_EMBEDDING_PROVIDER_FIELDS.items()):
        if provider not in config["providers"]:
            continue
        entries = config["providers"][provider]["models"]
        models = []
        for model_id, raw_entry in sorted(entries.items()):
            entry = _ai_config._model_entry(config, provider, model_id)
            if not _is_embedding_model(entry):
                continue
            resolved = _ai_config._resolve_v2(config, operation, model=model_id, provider=provider)
            defaults = {key: _embedding_default(key, resolved[key], model_id)
                        for key in fields if key in resolved}
            supported = entry.get("supported_values", {})
            supported_values = {key: _copy.deepcopy(supported[key])
                                for key in fields if key in supported}
            _ai_config._validate_defaults(defaults, supported_values, f"embeddings.{provider}.{model_id}")
            models.append({
                "id": model_id,
                "status": entry["status"],
                # Default roles belong to explicit catalog entries, not their
                # snapshots: runtime selection does not inherit these roles.
                "default_for": list(raw_entry.get("default_for", [])),
                "defaults": defaults,
                "supported_values": supported_values,
            })
        assigned_default = next((model["id"] for model in models
                                 if operation in model["default_for"]), None)
        providers[provider] = {"default_model": assigned_default, "models": models}

    selected = providers.get(policy["provider"])
    if selected is None or selected["default_model"] != policy["model"]:
        raise ValueError("The embeddings default must select an eligible model from a supported provider.")
    return {
        "operation": operation,
        "provider": policy["provider"],
        "protocol": policy["protocol"],
        "default_model": policy["model"],
        "providers": providers,
    }


def extract_ai_catalog(package_version: str) -> dict:
    """Return extraction choices with a separate, additive embeddings catalog.

    OpenAI extraction entries exclude models whose applications or default roles
    identify embeddings. Entries without annotations remain eligible so
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
        if _is_embedding_model(entry):
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
        "embeddings": _embedding_catalog(config),
    }
