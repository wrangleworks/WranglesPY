"""Structural schema for the v3 sections used by the Python pilot."""

from jsonschema import Draft202012Validator


_NAME = {"type": "string", "minLength": 1, "pattern": r"^\S+$"}
_NAMES = {"type": "array", "uniqueItems": True, "items": _NAME}


def _mapping(values):
    return {"type": "object", "propertyNames": _NAME, "additionalProperties": values}


def _object(properties, required=(), *, extras=False):
    return {"type": "object", "properties": properties, "required": list(required),
            "additionalProperties": extras}


_ROUTE = _object({"provider": _NAME, "api": _NAME}, ("provider", "api"))
_SETTINGS = {"defaults": {"type": "object"}, "parameter_schema": {"type": "object"}}
_API = _object({
    **_SETTINGS, "endpoint": _NAME, "fixed_query": _mapping({"type": "string"}),
    "public_parameters": _NAMES, "public_definitions": _NAMES,
}, ("endpoint",))
_MODEL = _object({
    **_SETTINGS, "apis": _NAMES,
    "status": {"enum": ["active", "deprecated", "retired"]},
    "routed_via": _object({"provider": _NAME, "api": _NAME, "request_model": _NAME},
                          ("provider", "api", "request_model")),
}, ("status",), extras=True)
_SELECTION = _object({"provider": _NAME, "api": _NAME, "model": _NAME, "routed_via": _ROUTE},
                     ("provider", "api"))
_CELL = _object({**_SETTINGS, "default_selection": _SELECTION}, ("default_selection",))
_POLICY = _object({**_SETTINGS, "compatible_apis": {"type": "array", "minItems": 1,
                   "uniqueItems": True, "items": _ROUTE}, "fixed_query": _mapping({"type": "string"})},
                  ("compatible_apis",))


def _actions(value):
    return _object({"actions": _object({"wrangle.execute": value})}, ("actions",))


_SCHEMA = _object({
    "version": {"const": 3},
    "providers": _mapping(_object({"apis": _mapping(_API), "models": _mapping(_MODEL)}, extras=True)),
    # Unmigrated operations retain the v2 structure validated by the existing loader.
    "operations": _object({"ai.decisions": _actions(_POLICY), "search.ai_mode": _actions(_POLICY)}, extras=True),
    "callers": _object({"wranglespy": _object({"operations": _object({
        "ai.decisions": _actions(_CELL), "search.ai_mode": _actions(_CELL)})}, ("operations",))}),
}, ("version", "providers", "operations", "callers"))


def validate_structure(config):
    error = next(Draft202012Validator(_SCHEMA).iter_errors(config), None)
    if error:
        location = ".".join(map(str, error.absolute_path)) or "configuration"
        raise ValueError(f"Invalid API configuration at {location} ({error.validator}).")
