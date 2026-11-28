"""Translate the two pilot operations at the v1/v2 configuration boundary."""

from copy import deepcopy

from .. import ai_config
from .resolver import ACTION, DECISIONS, SEARCH, Choice, _default, choices


def as_v2(config):
    """Retain the existing wrangles.ai_config.load() editing and inspection contract."""
    operations = {key: deepcopy(value) for key, value in config["operations"].items()
                  if key not in (DECISIONS, SEARCH)}
    providers = {}
    for name, data in config["providers"].items():
        if name == "serpapi":
            continue
        item = deepcopy(data)
        declared = item.pop("apis", {})
        item.setdefault("models", {})
        if declared:
            item["endpoints"] = {key: api["endpoint"] for key, api in declared.items()}
        providers[name] = item
    for owner, data in config["providers"].items():
        for model, entry in data.get("models", {}).items():
            if "routed_via" not in entry:
                continue
            route = entry["routed_via"]
            legacy_model = providers[owner]["models"].pop(model)
            legacy_model.pop("routed_via")
            providers[route["provider"]]["models"][route["request_model"]] = legacy_model
    # Older consumers edit this v2 view and save it as a replacement. Retain
    # their original endpoint key; adapt it to 'decisions' at dispatch.
    router = providers.get("openrouter", {}).get("endpoints", {})
    if "decisions" in router:
        router["systemone"] = router.pop("decisions")
    operation = config["callers"].get("wranglespy", {}).get("operations", {}).get(DECISIONS, {})
    cell = operation.get("actions", {}).get(ACTION)
    if cell:
        policy = config["operations"][DECISIONS]["actions"][ACTION]
        options = choices(config, DECISIONS, policy)
        default = _default(options, cell["default_selection"])
        operations["ai.answers"] = {"provider": default.transport, "protocol": "systemone",
                                    "defaults": ai_config._merge(policy.get("defaults", {}), cell.get("defaults", {}))}
        for option in options:
            peers = [c for c in options if c.transport == option.transport and c.status != "retired"]
            if option == default or (len(peers) == 1 and option == peers[0]):
                providers[option.transport]["models"][option.request_model].setdefault("default_for", []).append("ai.answers")
    return {"version": 2, "providers": providers, "operations": operations}


def select_decision(config, options, provider, api, model):
    """Preserve v2 role selection, protocol defaults and unlisted or dated wire IDs."""
    if provider == "microsoft":
        provider = "openrouter"
        if model == "microsoft-decision-1":
            model = "microsoft/microsoft-decision-1"
    selected = ai_config._resolve_v2(config, "ai.answers", model, provider, api)
    transport, wire, protocol = selected["provider"], selected["model"], selected["protocol"]
    if transport == "openrouter" and protocol in ("decisions", "systemone"):
        canonical = "decisions"
    elif transport == "typesafe" and protocol == "systemone":
        canonical = "systemone"
    else:
        raise ValueError("AI decisions require TypeSafe System One or OpenRouter Decisions.")
    choice = next((c for c in options if c.transport == transport and c.request_model == wire),
                  Choice(transport, canonical, transport, wire, wire))
    defaults = ai_config._model_policy(config, transport, wire, protocol)
    return choice, defaults


def from_legacy(config, standard):
    if config["version"] == 1:
        return standard
    # AI Mode predated configuration. In v2 it always used the packaged
    # SerpAPI contract even when an AI-only replacement was installed.
    result = {"providers": {"serpapi": deepcopy(standard["providers"]["serpapi"])},
              "operations": {SEARCH: deepcopy(standard["operations"][SEARCH])},
              "callers": {"wranglespy": {"operations": {
                  SEARCH: deepcopy(standard["callers"]["wranglespy"]["operations"][SEARCH])}}}}
    if "ai.answers" not in config["operations"]:
        return result
    original = config["operations"]["ai.answers"]
    policy = deepcopy(standard["operations"][DECISIONS]["actions"][ACTION])
    policy["defaults"] = {"decimals": 2, **deepcopy(original.get("defaults", {}))}
    policy["defaults"].pop("parameters", None)
    policy["compatible_apis"] = []
    default = None
    for transport, api in (("typesafe", "systemone"), ("openrouter", "decisions")):
        source = config["providers"].get(transport)
        if source is None:
            continue
        endpoints = source.get("endpoints", {})
        endpoint = endpoints.get(api, endpoints.get("systemone"))
        target = result["providers"].setdefault(transport, {})
        target["apis"] = {api: {"endpoint": endpoint}}
        policy["compatible_apis"].append({"provider": transport, "api": api})
        for wire, entry in source.get("models", {}).items():
            owner, model = transport, wire
            if transport == "openrouter" and wire == "microsoft/microsoft-decision-1":
                owner, model = "microsoft", "microsoft-decision-1"
            defaults = ai_config._model_policy(config, transport, wire, original["protocol"])
            defaults.pop("parameters", None)
            adapted = {"status": entry["status"], "defaults": defaults}
            if owner == transport:
                adapted["apis"] = [api]
            else:
                adapted["routed_via"] = {"provider": transport, "api": api, "request_model": wire}
            result["providers"].setdefault(owner, {}).setdefault("models", {})[model] = adapted
            if transport == original["provider"] and "ai.answers" in entry.get("default_for", ()):
                default = {"provider": owner, "api": api, "model": model}
    result["operations"][DECISIONS] = {"actions": {ACTION: policy}}
    result["callers"]["wranglespy"]["operations"][DECISIONS] = {
        "actions": {ACTION: {"default_selection": default} if default and not original.get("requires_model") else {}}}
    return result
