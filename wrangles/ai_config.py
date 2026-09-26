"""Load and resolve the provider/model catalog in WRANGLES_AI_CONFIG.

Version 2 files replace the packaged catalog completely. Resolution combines
the selected model's defaults, its protocol defaults, and then operation
defaults. Callers apply explicit per-call options last. Version 1 replacement
files retain their original extraction policy and capability-override behavior.
"""
import copy as _copy
import functools as _functools
import logging as _logging
import math as _math
import os as _os
import re as _re
from pathlib import Path as _Path

import yaml as _yaml


_PACKAGED_CONFIG = _Path(__file__).with_name("ai_defaults.yml")
_CONFIG_ENV = "WRANGLES_AI_CONFIG"
_STATUSES = {"active", "deprecated", "retired"}
_LEGACY_FLAGS = {"reasoning", "reasoning_none", "low_verbosity"}


def _merge(base: dict, override: dict) -> dict:
    result = _copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = _copy.deepcopy(value)
    return result


def _object(value, location: str) -> dict:
    if not isinstance(value, dict) or any(not isinstance(key, str) or not key.strip() for key in value):
        raise ValueError(f"{location} must be an object with non-empty string keys.")
    return value


def _string(value, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location} must be a non-empty string.")
    return value


def _validate_defaults(defaults: dict, supported: dict, location: str) -> None:
    for path, allowed in supported.items():
        value = defaults
        for key in path.split("."):
            if not isinstance(value, dict):
                raise ValueError(f"{location}.{path} requires nested objects.")
            if key not in value:
                break
            value = value[key]
        else:
            if value not in allowed or type(value) not in {type(item) for item in allowed}:
                raise ValueError(f"{location}.{path} must be one of {allowed!r}.")


def _validate_settings(settings: dict, location: str) -> None:
    """Check shared runtime setting types without restricting provider options."""
    _object(settings, location)
    for key in ("reasoning", "text", "cache", "prompt", "parameters"):
        if key in settings:
            _object(settings[key], f"{location}.{key}")
    for key in ("strict", "recipe_strict", "store"):
        if key in settings and not isinstance(settings[key], bool):
            raise ValueError(f"{location}.{key} must be true or false.")
    for key, minimum in (("default_concurrency", 1), ("batch_size", 1), ("retries", 0)):
        if key in settings and (type(settings[key]) is not int or settings[key] < minimum):
            raise ValueError(f"{location}.{key} must be an integer >= {minimum}.")
    if "request_timeout_seconds" in settings:
        value = settings["request_timeout_seconds"]
        if type(value) not in {int, float} or not _math.isfinite(value) or value <= 0:
            raise ValueError(f"{location}.request_timeout_seconds must be a positive finite number.")
    cache = settings.get("cache", {})
    for key in ("enabled", "single_flight"):
        if key in cache and not isinstance(cache[key], bool):
            raise ValueError(f"{location}.cache.{key} must be true or false.")
    for key in ("max_entries", "max_value_bytes", "log_every"):
        if key in cache and (type(cache[key]) is not int or cache[key] < 0):
            raise ValueError(f"{location}.cache.{key} must be a non-negative integer.")
    if "ttl_seconds" in cache:
        value = cache["ttl_seconds"]
        if type(value) not in {int, float} or not _math.isfinite(value) or value < 0:
            raise ValueError(f"{location}.cache.ttl_seconds must be a non-negative finite number.")


def _model_entry(config: dict, provider: str, model: str) -> dict:
    models = config.get("providers", {}).get(provider, {}).get("models", {})
    name = model.strip().lower()
    if provider == "google":
        # The Gemini SDK accepts both spellings for the same model. Normalize
        # catalog lookup only; preserve the caller's model in the request.
        name = name.removeprefix("models/")
        models = {key.removeprefix("models/"): value for key, value in models.items()}
    base = _re.sub(r"-\d{4}-\d{2}-\d{2}$", "", name)
    return _merge(models.get(base, {}), models.get(name, {}))


def _model_policy(config: dict, provider: str, model: str, protocol: str = None) -> dict:
    entry = _model_entry(config, provider, model)
    return _merge(entry.get("defaults", {}), entry.get("protocol_defaults", {}).get(protocol, {}))


def _resolve_v2(config: dict, operation: str, model=None, provider=None, protocol=None, role=None) -> dict:
    operation_policy = config["operations"].get(operation)
    if operation_policy is None:
        raise ValueError(f"No AI operation {operation!r} is configured.")
    provider = provider if provider is not None else operation_policy["provider"]
    provider = _string(provider, "provider").strip().lower()
    provider_policy = config["providers"].get(provider)
    if provider_policy is None:
        raise ValueError(f"No AI provider {provider!r} is configured.")
    protocol = protocol if protocol is not None else operation_policy["protocol"]
    _string(protocol, "protocol")
    if model is None:
        if operation_policy.get("requires_model", False):
            raise ValueError(f"AI operation {operation!r} requires an explicit model.")
        wanted = role if role is not None else operation
        _string(wanted, "role")
        if wanted in {"global", "test"} and operation not in {"extract.ai", "generate.ai"}:
            raise ValueError(f"Role {wanted!r} cannot select a model for {operation!r}.")
        matches = [name for name, entry in provider_policy["models"].items()
                   if wanted in entry.get("default_for", [])]
        # A global language-model default must never replace an embedding or
        # provider-specific retrieval model.
        if not matches and role is None and operation in {"extract.ai", "generate.ai"}:
            matches = [name for name, entry in provider_policy["models"].items()
                       if "global" in entry.get("default_for", [])]
        if not matches:
            raise ValueError(f"No default model for {wanted!r} is configured for provider {provider!r}; specify model explicitly.")
        model = matches[0]
    model = _string(model, "model").strip()
    policy = _merge(_model_policy(config, provider, model, protocol), operation_policy.get("defaults", {}))
    policy.update(model=model, provider=provider, protocol=protocol,
                  endpoints=_copy.deepcopy(provider_policy.get("endpoints", {})))
    return policy


def _validate_v2(config: dict) -> None:
    providers = _object(config.get("providers"), "providers")
    operations = _object(config.get("operations"), "operations")
    for provider, policy in providers.items():
        assigned_roles = {}
        if provider != provider.strip().lower():
            raise ValueError("Provider names must be lowercase without surrounding whitespace.")
        _object(policy, f"providers.{provider}")
        endpoints = _object(policy.get("endpoints", {}), f"providers.{provider}.endpoints")
        for protocol, url in endpoints.items():
            _string(url, f"providers.{provider}.endpoints.{protocol}")
        documentation = _object(policy.get("documentation", {}), f"providers.{provider}.documentation")
        for name, url in documentation.items():
            _string(url, f"providers.{provider}.documentation.{name}")
        models = _object(policy.get("models"), f"providers.{provider}.models")
        google_model_names = set()
        for name, entry in models.items():
            location = f"providers.{provider}.models.{name}"
            _object(entry, location)
            if name != name.strip().lower():
                raise ValueError(f"{location} model names must be lowercase without surrounding whitespace.")
            if provider == "google":
                google_name = name.removeprefix("models/")
                if google_name in google_model_names:
                    raise ValueError(f"Duplicate Google model aliases for {google_name!r}; configure only one spelling.")
                google_model_names.add(google_name)
            if not isinstance(entry.get("status"), str) or entry["status"] not in _STATUSES:
                raise ValueError(f"{location}.status must be active, deprecated, or retired.")
            if "application" in entry:
                raise ValueError(f"{location}.application has been renamed to applications; use a list of strings.")
            applications = entry.get("applications", [])
            if (not isinstance(applications, list)
                    or any(not isinstance(value, str) or not value.strip() for value in applications)):
                raise ValueError(f"{location}.applications must be a list of non-empty strings.")
            roles = entry.get("default_for", [])
            if not isinstance(roles, list) or any(not isinstance(role, str) or not role.strip() for role in roles):
                raise ValueError(f"{location}.default_for must be a list of non-empty roles.")
            if roles and entry["status"] == "retired":
                raise ValueError(f"{location}: retired models cannot hold default roles.")
            for role in roles:
                if role not in {"global", "test"} and role not in operations:
                    raise ValueError(f"{location}: unknown default role {role!r}.")
                if role in assigned_roles:
                    raise ValueError(f"Duplicate default role {role!r}: {assigned_roles[role]} and {location}.")
                assigned_roles[role] = location
            defaults = _object(entry.get("defaults", {}), f"{location}.defaults")
            _validate_settings(defaults, f"{location}.defaults")
            supported = _object(entry.get("supported_values", {}), f"{location}.supported_values")
            for path, values in supported.items():
                if (any(not key for key in path.split(".")) or not isinstance(values, list)
                        or any(type(value) not in {str, int, float} for value in values)):
                    raise ValueError(f"{location}.supported_values.{path} must be a list of enum values, not boolean flags.")
                if len(values) != len({(type(value), value) for value in values}):
                    raise ValueError(f"{location}.supported_values.{path} contains duplicate values.")
            protocol_defaults = _object(entry.get("protocol_defaults", {}), f"{location}.protocol_defaults")
            _validate_defaults(defaults, supported, location + ".defaults")
            for protocol, overrides in protocol_defaults.items():
                _validate_settings(overrides, f"{location}.protocol_defaults.{protocol}")
                _validate_defaults(_merge(defaults, overrides), supported, f"{location}.protocol_defaults.{protocol}")
    # Validate the effective snapshot as well as raw entries: a dated model can
    # inherit allowed values and must not override them with invalid defaults.
    for provider, policy in providers.items():
        for model in policy["models"]:
            entry = _model_entry(config, provider, model)
            defaults = entry.get("defaults", {})
            supported = entry.get("supported_values", {})
            location = f"providers.{provider}.models.{model}"
            _validate_defaults(defaults, supported, location + ".defaults")
            for protocol, overrides in entry.get("protocol_defaults", {}).items():
                _validate_defaults(_merge(defaults, overrides), supported, f"{location}.protocol_defaults.{protocol}")
    for operation, policy in operations.items():
        location = f"operations.{operation}"
        _object(policy, location)
        provider = _string(policy.get("provider"), location + ".provider")
        _string(policy.get("protocol"), location + ".protocol")
        if "requires_model" in policy and not isinstance(policy["requires_model"], bool):
            raise ValueError(f"{location}.requires_model must be true or false.")
        _validate_settings(policy.get("defaults", {}), location + ".defaults")
        if provider not in providers:
            raise ValueError(f"{location}.provider references an unconfigured provider {provider!r}.")
        # Generic task adapters can require a caller-supplied model because a
        # single default cannot serve their different tasks. Validate any
        # cataloged models without inventing a default selection for them.
        models = providers[provider]["models"] if policy.get("requires_model", False) else [None]
        for model in models:
            resolved = _resolve_v2(config, operation, model=model)
            supported = _model_entry(config, provider, resolved["model"]).get("supported_values", {})
            _validate_defaults(resolved, supported, location + ".defaults")


@_functools.lru_cache(maxsize=4)
def _load_config_file(path: str) -> dict:
    config_path = _Path(path)
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = _yaml.safe_load(config_file)
    except OSError as exc:
        raise ValueError(f"Unable to read AI configuration '{config_path}': {exc}") from exc
    except _yaml.YAMLError as exc:
        raise ValueError(f"AI configuration '{config_path}' is not valid YAML: {exc}") from exc
    _object(config, f"AI configuration '{config_path}'")
    version = config.get("version")
    if type(version) is not int or version not in {1, 2}:
        raise ValueError(f"AI configuration '{config_path}' has unsupported version {version!r}; expected 1 or 2.")
    if version == 2:
        _validate_v2(config)
    else:
        _object(config.get("extract_ai"), "extract_ai")
        capabilities = config.get("model_capabilities", {})
        if not isinstance(capabilities, dict) or any(
            not isinstance(model, str) or not isinstance(flags, dict)
            or any(key not in _LEGACY_FLAGS or not isinstance(value, bool) for key, value in flags.items())
            for model, flags in capabilities.items()
        ):
            raise ValueError("model_capabilities must map model names to boolean reasoning, reasoning_none, or low_verbosity flags.")
    return config


def config_path() -> _Path:
    """Return the active configuration path."""
    override = _os.getenv(_CONFIG_ENV)
    return _Path(override) if override else _PACKAGED_CONFIG


def load() -> dict:
    """Return a defensive copy of the active, validated configuration."""
    return _copy.deepcopy(_load_config_file(str(config_path().resolve())))


def resolve(operation: str, model: str = None, provider: str = None,
            protocol: str = None, role: str = None) -> dict:
    """Resolve one operation without changing explicit per-call selections.

    Explicit model wins over the requested role, then the operation's default
    role, then (for extraction/generation only) the global role. A role such as
    'test' is opt-in. Defaults merge model -> protocol -> operation; callers
    apply explicit request options last. Unlisted explicit models are accepted.
    """
    config = load()
    if config["version"] == 2:
        return _resolve_v2(config, operation, model, provider, protocol, role)
    if operation == "extract.ai":
        policy = _copy.deepcopy(config["extract_ai"])
        for key, value in (("model", model), ("provider", provider), ("protocol", protocol)):
            if value is not None:
                policy[key] = value
        return policy
    packaged = _load_config_file(str(_PACKAGED_CONFIG.resolve()))
    # Version 1 shared its extraction model with generation, but no other
    # operation. Its missing extraction options must not inherit packaged ones.
    if operation == "generate.ai" and model is None and role is None:
        model = config["extract_ai"].get("model")
    return _resolve_v2(packaged, operation, model, provider, protocol, role)


def extract_ai() -> dict:
    """Return the flat extract.ai policy accepted by existing callers."""
    return resolve("extract.ai")


def model_defaults(model: str, provider: str = "openai", protocol: str = None) -> dict:
    """Return defaults for an explicit model, including dated snapshots."""
    config = load()
    if config["version"] == 1:
        config = _load_config_file(str(_PACKAGED_CONFIG.resolve()))
    return _model_policy(config, provider, model, protocol)


def model_supported_values(model: str, provider: str = "openai") -> dict:
    """Return declared model enums, including dated snapshots.

    Missing keys mean that the catalog does not specify an enum. Version 1
    files use the packaged model catalog, as they do for model defaults.
    """
    config = load()
    if config["version"] == 1:
        config = _load_config_file(str(_PACKAGED_CONFIG.resolve()))
    return _model_entry(config, provider, model).get("supported_values", {})


def warn_if_deprecated(model: str, provider: str = "openai") -> None:
    """Log catalog deprecation at a caller boundary without blocking execution.

    Call once after selecting the effective model, outside row/batch/retry loops.
    Reading or resolving configuration itself must not produce this warning.
    Version 1 files use the packaged catalog for lifecycle information.
    """
    config = load()
    if config["version"] == 1:
        config = _load_config_file(str(_PACKAGED_CONFIG.resolve()))
    provider = provider.strip().lower()
    if _model_entry(config, provider, model).get("status") == "deprecated":
        _logging.warning(
            "AI model has deprecated status in the configured catalog; continuing execution :: provider :: %s, model :: %s",
            provider, model,
        )


def _catalog_capabilities(config: dict, model: str) -> dict:
    supported = _model_entry(config, "openai", model).get("supported_values", {})
    flags = {}
    if "reasoning.effort" in supported:
        flags["reasoning"] = bool(supported["reasoning.effort"])
        flags["reasoning_none"] = "none" in supported["reasoning.effort"]
    if "text.verbosity" in supported:
        flags["low_verbosity"] = "low" in supported["text.verbosity"]
    return flags


def model_capabilities(model: str) -> dict:
    """Compatibility flags for the existing extract.ai parameter adapter.

    Version 2 stores enum values, not these legacy booleans. Version 1 files
    continue merging capability overrides over packaged capabilities.
    """
    model = (model or "").strip().lower()
    config = load()
    if config["version"] == 2:
        return _catalog_capabilities(config, model)
    packaged = _load_config_file(str(_PACKAGED_CONFIG.resolve()))
    flags = _catalog_capabilities(packaged, model)
    capabilities = config.get("model_capabilities", {})
    base = _re.sub(r"-\d{4}-\d{2}-\d{2}$", "", model)
    flags.update(capabilities.get(base, {}))
    flags.update(capabilities.get(model, {}))
    return flags


def clear_cache() -> None:
    """Reload configuration files on the next call after editing a policy."""
    _load_config_file.cache_clear()
