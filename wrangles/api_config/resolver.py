"""Resolve a caller's selection against one validated file snapshot."""

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from urllib.parse import urlsplit

from .. import ai_config
from .parameters import RESERVED, check_schema, validate_parameters


class _Default(Enum):
    INHERIT = "inherit"


INHERIT = _Default.INHERIT
ACTION = "wrangle.execute"
DECISIONS = "ai.decisions"
SEARCH = "search.ai_mode"
# Adapter capabilities, independent of which models or callers select them.
ADAPTERS = {DECISIONS: {("typesafe", "systemone"), ("openrouter", "decisions")},
            SEARCH: {("serpapi", "google_ai_mode")}}
CONTROLS = {
    DECISIONS: {"default_concurrency", "request_timeout_seconds", "retries", "cache", "decimals"},
    SEARCH: {"default_concurrency", "include_raw_response"},
}


@dataclass(frozen=True)
class Snapshot:
    _config: dict
    source: str
    revision: str
    version: int
    _legacy_config: dict | None = None

    @property
    def config(self):
        """A copy for inspection or authoring a new replacement file."""
        return deepcopy(self._config)


@dataclass
class Choice:
    provider: str
    api: str
    transport: str
    model: str | None = None
    request_model: str | None = None
    status: str | None = None

    def selection(self):
        result = {"provider": self.provider, "api": self.api}
        if self.model is not None:
            result["model"] = self.model
        if self.provider != self.transport:
            result["routed_via"] = {"provider": self.transport, "api": self.api}
        return result


@dataclass
class Resolution:
    choice: Choice
    endpoint: str
    fixed_query: dict
    defaults: dict
    parameters: dict
    provenance: dict
    schemas: list
    api_config: dict


def load_snapshot(path=None):
    from .legacy import from_legacy
    path = Path(path if path is not None else ai_config.config_path()).resolve()
    config, digest = ai_config._read_config(str(path))
    packaged = path == ai_config._PACKAGED_CONFIG.resolve()
    version = config["version"]
    legacy = config if version == 2 else None
    if version < 3:
        standard, _ = ai_config._read_config(str(ai_config._PACKAGED_CONFIG.resolve()))
        config = from_legacy(config, standard)
    return Snapshot(config, "packaged" if packaged else "replacement", digest, version, legacy)


def _members(config, operation, caller, action):
    if operation not in config["operations"]:
        raise ValueError(f"No AI operation {operation!r} is configured.")
    try:
        cell = config["callers"][caller]["operations"][operation]["actions"][action]
        policy = config["operations"][operation]["actions"][action]
    except KeyError:
        raise ValueError(f"No API selection for {caller}/{operation}/{action}.") from None
    return cell, policy


def choices(config, operation, policy):
    result = []
    for reference in policy["compatible_apis"]:
        transport, api = reference["provider"], reference["api"]
        if (transport, api) not in ADAPTERS[operation]:
            raise ValueError(f"Unsupported {operation} interface {transport}/{api}.")
        if api not in config["providers"].get(transport, {}).get("apis", {}):
            raise ValueError(f"Missing API interface {transport}/{api}.")
        if operation == SEARCH:
            result.append(Choice(transport, api, transport))
            continue
        for owner, provider in config["providers"].items():
            for model, entry in provider.get("models", {}).items():
                route = entry.get("routed_via", {})
                if (route.get("provider"), route.get("api")) == (transport, api):
                    result.append(Choice(owner, api, transport, model, route["request_model"], entry["status"]))
                if owner == transport and api in entry.get("apis", []):
                    result.append(Choice(owner, api, owner, model, model, entry["status"]))
    return result


def _default(options, selection):
    matches = [choice for choice in options if choice.model == selection.get("model")
               and all(choice.selection().get(k) == value for k, value in selection.items())
               and choice.status != "retired"]
    if len(matches) != 1:
        raise ValueError("default_selection must identify one available API choice.")
    return matches[0]


def _select(options, selection, operation, provider, model, api):
    default = _default(options, selection)
    if provider is not None:
        provider = ai_config._string(provider, "provider").strip().lower()
    if model is not None:
        model = ai_config._string(model, "model").strip()
    if provider is None and model is None and api is None:
        return default
    candidates = [c for c in options if provider is None or provider in (c.provider, c.transport)]
    if provider is not None and not candidates:
        raise ValueError(f"No AI provider {provider!r} for this operation; specify model explicitly on a configured route.")
    if api is not None:
        candidates = [c for c in candidates if c.api == api or
                      (c.transport == "openrouter" and provider in (None, "openrouter") and api == "systemone")]
    if model is not None:
        matches = [c for c in candidates if model in (c.model, c.request_model)]
        if matches:
            candidates = matches
        else:
            if any(model in (c.model, c.request_model) for c in options):
                raise ValueError(f"The selected model is incompatible with this provider/API for {operation}.")
            # Legacy decision calls allow an unlisted wire model on a supported
            # transport. It does not become a selectable catalog entry.
            base = default if default in candidates else next(iter(candidates), None)
            if operation != DECISIONS or base is None or provider not in (None, base.transport):
                raise ValueError(f"Unsupported model for {operation}.")
            return Choice(base.transport, base.api, base.transport, model, model)
    if default in candidates:
        return default
    if len(candidates) != 1:
        raise ValueError(f"No unique {operation} choice for this provider/API; specify model explicitly.")
    return candidates[0]


def _apply(result, values, provenance, source, prefix=""):
    for key, value in values.items():
        path = prefix + key
        if isinstance(value, dict):
            if not isinstance(result.get(key), dict):
                result[key] = {}
            _apply(result[key], value, provenance, source, path + ".")
        else:
            result[key] = deepcopy(value)
        provenance[path] = source


def _effective(config, choice, cell, policy, overrides, parameters, partial, legacy_model_defaults=None):
    provider = config["providers"][choice.transport]
    api = provider["apis"][choice.api]
    model = config["providers"].get(choice.provider, {}).get("models", {}).get(choice.model, {})
    if legacy_model_defaults is not None:
        model = {"defaults": legacy_model_defaults}
    settings, provenance, schemas = {}, {}, []
    for source, layer in (("api", api), ("model", model), ("operation", policy), ("caller", cell)):
        values = layer.get("defaults", {})
        if choice.transport == "serpapi" and "parameters" in values:
            from ..search._ai_mode import request_parameters
            values = {**values, "parameters": request_parameters(
                ai_config._object(values["parameters"], "defaults.parameters"), keep_omissions=True)}
        _apply(settings, values, provenance, source)
        if "parameter_schema" in layer:
            schemas.append(layer["parameter_schema"])
    _apply(settings, overrides, provenance, "explicit")
    params = ai_config._object(settings.pop("parameters", {}), "defaults.parameters")
    parameters = ai_config._object(parameters, "parameters")
    if choice.transport == "serpapi":
        from ..search._ai_mode import request_parameters
        _apply(params, request_parameters(parameters, keep_omissions=True), provenance, "explicit", "parameters.")
        params = request_parameters(params)
        # Preserve the adapter's fixed-field precedence for legacy kwargs.
        for key in ("engine", "q"):
            params.pop(key, None)
    elif parameters or (params and legacy_model_defaults is None):
        raise ValueError("Decision requests accept state, questions and the selected model only.")
    else:
        # Older decision models may carry unused parameter metadata.
        params = {}
    if RESERVED.intersection(k.lower() for k in params):
        raise ValueError("Reserved runtime, authentication or structural field in API parameters.")
    for schema in schemas:
        validate_parameters(schema, params, partial=partial)
    ai_config._validate_settings(settings, "resolved defaults")
    if settings.get("cache", {}).get("ttl_seconds") == 0:
        raise ValueError("cache_ttl must be a positive number of seconds.")
    if "decimals" in settings and (type(settings["decimals"]) is not int or settings["decimals"] < 0):
        raise ValueError("decimals must be a non-negative integer.")
    if "include_raw_response" in settings and type(settings["include_raw_response"]) is not bool:
        raise ValueError("include_raw_response must be true or false.")
    fixed = {**api.get("fixed_query", {}), **policy.get("fixed_query", {})}
    provenance["endpoint"] = "api"
    for key in fixed:
        provenance[f"fixed_query.{key}"] = "operation" if key in policy.get("fixed_query", {}) else "api"
    if choice.request_model:
        provenance["request_model"] = "routed_via" if choice.provider != choice.transport else "model"
    return Resolution(choice, api["endpoint"], fixed, settings, params, provenance, deepcopy(schemas), deepcopy(api))


def resolve(operation, *, caller="wranglespy", action=ACTION, provider=None, api=None,
            model=None, overrides=None, parameters=None, snapshot=None):
    """Resolve one invocation. Provider parameters and Wrangles controls stay separate."""
    operation = DECISIONS if operation == "ai.answers" else operation
    snap = snapshot if snapshot is not None else load_snapshot()
    config = snap._config
    cell, policy = _members(config, operation, caller, action)
    if set(overrides or {}) - CONTROLS[operation]:
        raise ValueError(f"Unsupported Wrangles override for {operation}.")
    options = choices(config, operation, policy)
    legacy_defaults = None
    if operation == DECISIONS and snap.version == 2:
        from .legacy import select_decision
        choice, legacy_defaults = select_decision(snap._legacy_config, options, provider, api, model)
    else:
        choice = _select(options, cell["default_selection"], operation, provider, model, api)
    resolved = _effective(config, choice, cell, policy, overrides or {}, parameters or {},
                          False, legacy_defaults)
    resolved.provenance["selection"] = "explicit" if any(x is not None for x in (provider, api, model)) else "caller"
    return resolved


def checked_endpoint(url, provider):
    try:
        parts = urlsplit(url)
        valid = parts.scheme == "https" and parts.hostname and not (parts.username or parts.password or parts.fragment)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise ValueError(f"The {provider} endpoint must be an HTTPS URL without embedded credentials or fragments.")
    return url


def validate_config(config):
    from .structure import validate_structure
    validate_structure(config)
    for name, provider in config["providers"].items():
        for api_name, api in provider.get("apis", {}).items():
            checked_endpoint(api["endpoint"], name)
            if name == "serpapi" and api.get("fixed_query", {}).get("engine") != api_name:
                raise ValueError("Each SerpAPI API must fix its own engine identifier.")
            if (name, api_name) in ADAPTERS[DECISIONS] and (api.get("public_parameters") or api.get("fixed_query")):
                raise ValueError("The Decisions adapter has no public provider parameters or fixed query.")
            if "parameter_schema" in api:
                check_schema(api["parameter_schema"])
            if not set(api.get("public_parameters", ())).issubset(api.get("parameter_schema", {}).get("properties", {})):
                raise ValueError("public_parameters must refer to declared API properties.")
            if RESERVED.intersection(key.lower() for key in api.get("public_parameters", ())):
                raise ValueError("Reserved API parameters cannot be public.")
        for model in provider.get("models", {}).values():
            route = model.get("routed_via")
            if route and model.get("apis"):
                raise ValueError("A routed model must identify its API through routed_via.")
            if route and route["api"] not in config["providers"].get(route["provider"], {}).get("apis", {}):
                raise ValueError("routed_via must identify a configured provider API.")
            if set(model.get("apis", ())) - set(provider.get("apis", ())):
                raise ValueError("Model references an unknown direct API.")
            if "parameter_schema" in model:
                check_schema(model["parameter_schema"])
    for caller, settings in config["callers"].items():
        for operation, definition in settings["operations"].items():
            for action in definition["actions"]:
                cell, policy = _members(config, operation, caller, action)
                options = choices(config, operation, policy)
                _default(options, cell["default_selection"])
                for layer in (policy, cell):
                    if "parameter_schema" in layer:
                        check_schema(layer["parameter_schema"])
                if operation == DECISIONS and policy.get("fixed_query"):
                    raise ValueError("The Decisions adapter does not accept fixed query fields.")
                for choice in options:
                    resolution = _effective(config, choice, cell, policy, {}, {}, True)
                    required = CONTROLS[operation]
                    if resolution.defaults.keys() - required:
                        raise ValueError(f"Unsupported runtime defaults for {operation}.")
                    if required - resolution.defaults.keys() or (operation == DECISIONS and
                            "enabled" not in resolution.defaults["cache"]):
                        raise ValueError(f"Incomplete runtime defaults for {operation}.")
                    if operation == SEARCH and resolution.fixed_query != {"engine": "google_ai_mode", "output": "md"}:
                        raise ValueError("search.ai_mode requires engine=google_ai_mode and output=md.")
