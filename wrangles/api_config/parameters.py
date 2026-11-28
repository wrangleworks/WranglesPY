"""Offline Draft 2020-12 parameter validation and public schema projection."""

from copy import deepcopy

from jsonschema import Draft202012Validator, validators
from jsonschema.exceptions import SchemaError, ValidationError
from referencing import Registry


# These names belong to authentication, transport, the operation, or run context.
# They may never arrive through free-form provider parameters or a public schema.
RESERVED = frozenset({
    "api_key", "apikey", "authorization", "headers", "auth", "credentials", "token",
    "caller", "context", "metadata", "correlation_id", "provider", "model", "routed_via",
    "client", "client_config", "endpoint", "url", "prompt", "instructions",
    "threads", "timeout", "retries", "cache", "include_raw_response", "search_mode",
    "access_token", "api_token", "password", "secret", "client_secret", "api", "protocol",
    "state", "questions", "engine", "q", "output", "decimals", "request_model",
    "default_concurrency", "request_timeout_seconds", "cache_ttl",
})


def _reference(schema, ref):
    if not isinstance(ref, str) or not ref.startswith("#/"):
        raise ValueError("API parameter schema references must be local JSON pointers.")
    node = schema
    try:
        for part in ref[2:].split("/"):
            key = part.replace("~1", "/").replace("~0", "~")
            node = node[int(key)] if isinstance(node, list) else node[key]
    except (KeyError, IndexError, TypeError, ValueError):
        raise ValueError("Unresolved local API parameter schema reference.") from None
    return node


def check_schema(schema):
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError:
        raise ValueError("Invalid Draft 2020-12 API parameter schema.") from None
    if schema.get("$schema", Draft202012Validator.META_SCHEMA["$id"]) != Draft202012Validator.META_SCHEMA["$id"]:
        raise ValueError("API parameter schemas must use Draft 2020-12.")
    # A local reference is always relative to this schema. Disallow identifiers
    # that rebase a reference and dynamic references in this offline pilot.
    def check(node):
        if isinstance(node, list):
            for item in node:
                check(item)
        elif isinstance(node, dict):
            if "$id" in node or "$dynamicRef" in node:
                raise ValueError("API parameter schemas support local static references only.")
            if "$ref" in node:
                _reference(schema, node["$ref"])
            for item in node.values():
                check(item)
    check(schema)


def _optional(validator, constraint, value, schema):
    return ()


def _partial_one_of(validator, branches, value, schema):
    # A mapping can acquire more fields. A scalar has its final value.
    keyword = "anyOf" if isinstance(value, dict) else "oneOf"
    yield from Draft202012Validator.VALIDATORS[keyword](validator, branches, value, schema)


def _partial_not(validator, excluded, value, schema):
    if isinstance(value, dict):
        if isinstance(excluded, dict) and set(excluded) == {"required"} and set(excluded["required"]) <= value.keys():
            yield ValidationError("Forbidden combination of fields.")
        return
    yield from Draft202012Validator.VALIDATORS["not"](validator, excluded, value, schema)


def _partial_if(validator, condition, value, schema):
    # Additional fields can change which branch applies to an object.
    if not isinstance(value, dict):
        yield from Draft202012Validator.VALIDATORS["if"](validator, condition, value, schema)


_DefaultsValidator = validators.extend(Draft202012Validator, {
    "required": _optional, "dependentRequired": _optional, "minProperties": _optional,
    "oneOf": _partial_one_of, "not": _partial_not, "if": _partial_if,
})


def validate_parameters(schema, values, *, partial=False):
    validator = (_DefaultsValidator if partial else Draft202012Validator)(schema, registry=Registry())
    for error in validator.iter_errors(values):
        path = ".".join(str(part) for part in error.absolute_path) or "parameters"
        raise ValueError(f"Invalid API parameters at {path} ({error.validator}).")


_SCALAR_CONSTRAINTS = {
    "type", "enum", "const", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "multipleOf", "pattern", "minLength", "maxLength",
}
_ANNOTATIONS = {"title", "description", "examples", "default", "$comment", "$schema", "$defs",
                "readOnly", "writeOnly", "deprecated"}


def _public_property(node, schema, allowed_defs, seen):
    """Inline opted-in local definitions. Omit fields we cannot safely describe."""
    if isinstance(node, bool):
        return node
    if node.get("writeOnly") or set(node) - _SCALAR_CONSTRAINTS - _ANNOTATIONS - {"$ref", "allOf", "anyOf", "oneOf", "not"}:
        return None
    if any(isinstance(value, (list, dict)) for value in [node.get("const"), *node.get("enum", [])]):
        return None
    result = {k: deepcopy(v) for k, v in node.items() if k in _SCALAR_CONSTRAINTS}
    if "$ref" in node:
        ref = node["$ref"]
        if ref in seen or ref not in allowed_defs:
            return None
        part = _public_property(_reference(schema, ref), schema, allowed_defs, seen | {ref})
        if part is None:
            return None
        result.setdefault("allOf", []).append(part)
    for key in ("allOf", "anyOf", "oneOf", "not"):
        if key in node:
            parts = [_public_property(part, schema, allowed_defs, seen)
                     for part in ([node[key]] if key == "not" else node[key])]
            if any(part is None for part in parts):
                return None
            if key == "not":
                result[key] = parts[0]
            else:
                result.setdefault(key, []).extend(parts)
    return result


def _clauses(schema):
    """Object constraints in an allOf also apply to every complete request."""
    if isinstance(schema, bool):
        yield schema
        return
    yield {key: value for key, value in schema.items() if key != "allOf"}
    for member in schema.get("allOf", []):
        yield from _clauses(member)


def public_schema(layers, public_names, public_defs):
    properties = {}
    required = set()
    clauses = [(root, clause) for root in layers for clause in _clauses(root)]
    for name in public_names:
        if name.lower() in RESERVED:
            raise ValueError("Reserved API parameters cannot be exported.")
        parts = []
        for root, schema in clauses:
            if schema is True:
                continue
            # A cross-property constraint cannot be projected onto one public
            # field independently. Keep it private rather than widen the schema.
            if schema is False or set(schema) - {"type", "properties", "required", "additionalProperties"} - _ANNOTATIONS:
                parts = []
                break
            value = schema.get("properties", {}).get(name, schema.get("additionalProperties", True))
            part = _public_property(value, root, public_defs, set())
            if part is None:
                parts = []
                break
            if part is not True:
                parts.append(part)
            if name in schema.get("required", []):
                required.add(name)
        if parts:
            properties[name] = parts[0] if len(parts) == 1 else {"allOf": parts}
    result = {"type": "object", "properties": properties, "additionalProperties": False}
    if required.intersection(properties):
        result["required"] = sorted(required.intersection(properties))
    return result
