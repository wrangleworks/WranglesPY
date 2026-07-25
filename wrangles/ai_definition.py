"""
Compile recipe and saved-model extract.ai definitions into one canonical form.

The compiler is provider-neutral. Provider adapters may further restrict the
resulting JSON Schema for their own structured-output implementation.
"""
import copy as _copy
import json as _json
import logging as _logging
import re as _re
from dataclasses import dataclass as _dataclass
from typing import Any as _Any


_LOG = _logging.getLogger(__name__)

_DEFAULT_SCALAR_TYPES = ["string", "number", "boolean"]
_TYPE_ALIASES = {
    "str": "string",
    "text": "string",
    "float": "number",
    "decimal": "number",
    "int": "integer",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
    "map": "object",
}
_JSON_TYPES = {
    "array",
    "boolean",
    "integer",
    "null",
    "number",
    "object",
    "string",
}
_SUPPORTED_SCHEMA_KEYS = {
    "additionalProperties",
    "anyOf",
    "const",
    "default",
    "description",
    "enum",
    "examples",
    "exclusiveMaximum",
    "exclusiveMinimum",
    "items",
    "maximum",
    "maxItems",
    "maxLength",
    "minimum",
    "minItems",
    "minLength",
    "multipleOf",
    "nullable",
    "properties",
    "required",
    "title",
    "type",
}
_INCOMPATIBLE_SCHEMA_KEYS = {
    "$defs",
    "$ref",
    "allOf",
    "definitions",
    "else",
    "if",
    "not",
    "oneOf",
    "patternProperties",
    "then",
}
_SAVED_SCHEMA_COLUMNS = {
    "additionalproperties": "additionalProperties",
    "default": "default",
    "description": "description",
    "enum": "enum",
    "examples": "examples",
    "items": "items",
    "properties": "properties",
    "required": "required",
    "type": "type",
}


@_dataclass(frozen=True)
class CompiledAIDefinition:
    """Canonical extract.ai definition consumed by provider transports."""

    output: dict
    root_schema: dict
    model: str
    messages: list
    strict: bool
    strict_requested: bool
    dynamic_paths: tuple
    key_to_original: dict
    output_generic_key: bool
    diagnostics: tuple

    @property
    def needs_remap(self) -> bool:
        return any(
            sanitized != original
            for sanitized, original in self.key_to_original.items()
        )


class _Compiler:
    def __init__(self, source: str):
        self.source = source
        self.diagnostics = []
        self.dynamic_paths = []

    def migration(self, message: str) -> None:
        diagnostic = f"{self.source}: {message}"
        self.diagnostics.append(diagnostic)
        _LOG.warning("extract.ai definition migration: %s", diagnostic)

    def error(self, path: str, message: str) -> None:
        raise ValueError(f"Invalid extract.ai definition at {path}: {message}")

    @staticmethod
    def _parse_json_value(value: _Any) -> _Any:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped.startswith(("{", "[")):
            return value
        try:
            return _json.loads(stripped)
        except (TypeError, ValueError):
            return value

    def normalize_schema(self, value: _Any, path: str) -> dict:
        if value is None:
            value = {}
        if not isinstance(value, dict):
            self.error(path, f"expected an object, received {type(value).__name__}.")

        node = {
            key: self._parse_json_value(item)
            for key, item in _copy.deepcopy(value).items()
        }

        incompatible = sorted(_INCOMPATIBLE_SCHEMA_KEYS.intersection(node))
        if incompatible:
            self.error(
                path,
                "unsupported structured-output keyword(s): "
                f"{', '.join(incompatible)}. Rewrite this field using properties, "
                "items, enum, or anyOf.",
            )
        unknown = sorted(set(node) - _SUPPORTED_SCHEMA_KEYS - _INCOMPATIBLE_SCHEMA_KEYS)
        if unknown:
            self.error(
                path,
                "unsupported structured-output keyword(s): "
                f"{', '.join(unknown)}. Remove or explicitly migrate these fields.",
            )

        if "const" in node:
            if "enum" in node:
                self.error(path, "cannot define both const and enum.")
            node["enum"] = [node.pop("const")]
            self.migration(f"{path} mapped const to a single-value enum.")

        if "nullable" in node:
            nullable = node.pop("nullable")
            if not isinstance(nullable, bool):
                self.error(path, "nullable must be true or false.")
            if nullable:
                schema_type = node.get("type") or _DEFAULT_SCALAR_TYPES
                schema_types = list(schema_type) if isinstance(schema_type, list) else [schema_type]
                if "null" not in schema_types:
                    schema_types.append("null")
                node["type"] = schema_types
                self.migration(f"{path} mapped nullable: true to a null type union.")

        schema_type = node.get("type")
        if isinstance(schema_type, str):
            normalized_type = _TYPE_ALIASES.get(schema_type.strip().lower(), schema_type)
            if normalized_type != schema_type:
                self.migration(
                    f"{path} mapped legacy type {schema_type!r} to {normalized_type!r}."
                )
            node["type"] = normalized_type
        elif isinstance(schema_type, list):
            normalized_types = [
                _TYPE_ALIASES.get(str(item).strip().lower(), item)
                for item in schema_type
            ]
            if normalized_types != schema_type:
                mappings = [
                    f"{old!r} to {new!r}"
                    for old, new in zip(schema_type, normalized_types)
                    if old != new
                ]
                self.migration(
                    f"{path} mapped legacy type {', '.join(mappings)}."
                )
            node["type"] = normalized_types
        elif schema_type not in (None, ""):
            self.error(path, "type must be a string or array of strings.")

        if not node.get("type") and (
            "properties" in node or "additionalProperties" in node
        ):
            node["type"] = "object"
            self.migration(f"{path} inferred type 'object' from object keywords.")
        elif not node.get("type") and "items" in node:
            node["type"] = "array"
            self.migration(f"{path} inferred type 'array' from items.")
        if not node.get("type") and not node.get("anyOf"):
            node["type"] = list(_DEFAULT_SCALAR_TYPES)

        declared_types = (
            node.get("type")
            if isinstance(node.get("type"), list)
            else [node.get("type")]
        )
        invalid_types = sorted({
            str(item)
            for item in declared_types
            if item is not None and item not in _JSON_TYPES
        })
        if invalid_types:
            self.error(
                path,
                f"unsupported JSON type(s): {', '.join(invalid_types)}.",
            )

        for label in ("enum", "properties", "required"):
            if isinstance(node.get(label), str):
                node[label] = [
                    item.strip()
                    for item in node[label].split(",")
                    if item.strip()
                ]
                self.migration(f"{path}.{label} converted a comma-separated string to a list.")

        if "enum" in node and not isinstance(node["enum"], list):
            self.error(path, "enum must be an array or comma-separated string.")
        if "required" in node and not isinstance(node["required"], list):
            self.error(path, "required must be an array or comma-separated string.")
        if "examples" in node and not isinstance(node["examples"], list):
            if node["examples"] not in ("", None):
                node["examples"] = [node["examples"]]
                self.migration(f"{path}.examples wrapped a scalar value in a list.")

        properties = node.get("properties")
        if isinstance(properties, list):
            node["properties"] = {str(name): {} for name in properties}
            properties = node["properties"]
            self.migration(f"{path}.properties expanded a property-name list.")
        if properties is not None and not isinstance(properties, dict):
            self.error(path, "properties must be an object, list, or comma-separated string.")
        if isinstance(properties, dict):
            node["properties"] = {
                str(name): self.normalize_schema(child, f"{path}.properties.{name}")
                for name, child in properties.items()
            }

        is_object = (
            node.get("type") == "object"
            or (
                isinstance(node.get("type"), list)
                and "object" in node["type"]
            )
        )
        if is_object:
            additional = node.get("additionalProperties")
            if isinstance(additional, dict):
                node["additionalProperties"] = self.normalize_schema(
                    additional,
                    f"{path}.additionalProperties",
                )
                self.dynamic_paths.append(path)
            elif additional is True:
                self.dynamic_paths.append(path)
            elif additional not in (None, False):
                self.error(path, "additionalProperties must be true, false, or a schema object.")
            elif properties is None and "additionalProperties" not in node:
                node["additionalProperties"] = True
                self.dynamic_paths.append(path)
                self.migration(
                    f"{path} treats an object without named properties as a dynamic dictionary."
                )
            else:
                node["additionalProperties"] = False
        elif "properties" in node or "additionalProperties" in node:
            self.error(path, "object keywords require type 'object'.")

        is_array = (
            node.get("type") == "array"
            or (
                isinstance(node.get("type"), list)
                and "array" in node["type"]
            )
        )
        if is_array:
            if "items" not in node:
                node["items"] = {}
            if not isinstance(node["items"], dict):
                self.error(path, "items must be a schema object.")
            node["items"] = self.normalize_schema(node["items"], f"{path}.items")
        elif "items" in node:
            self.error(path, "items requires type 'array'.")

        if "anyOf" in node and not isinstance(node["anyOf"], list):
            self.error(path, "anyOf must be an array of schema objects.")
        if isinstance(node.get("anyOf"), list):
            node["anyOf"] = [
                self.normalize_schema(option, f"{path}.anyOf[{index}]")
                for index, option in enumerate(node["anyOf"])
            ]

        return node

    def saved_model(self, content: dict) -> tuple:
        if not isinstance(content, dict):
            self.error("model_id", "saved model content must be an object.")

        top_level = {str(key).lower(): value for key, value in content.items()}
        columns = top_level.get("columns")
        rows = top_level.get("data")
        settings = top_level.get("settings") or {}
        if not isinstance(columns, list) or not isinstance(rows, list):
            self.error("model_id", "saved model must contain Columns and Data arrays.")
        if not isinstance(settings, dict):
            self.error("model_id.settings", "Settings must be an object.")

        normalized_columns = [
            _re.sub(r"[^a-z0-9]", "", str(column).lower())
            for column in columns
        ]
        if "find" not in normalized_columns:
            self.error("model_id.columns", "saved model must contain a Find column.")

        output = {}
        for row_number, row in enumerate(rows, start=1):
            if isinstance(row, dict):
                row_values = {
                    _re.sub(r"[^a-z0-9]", "", str(key).lower()): value
                    for key, value in row.items()
                }
            elif isinstance(row, (list, tuple)):
                if len(row) > len(normalized_columns):
                    self.error(
                        f"model_id.data[{row_number}]",
                        "contains more values than the Columns array.",
                    )
                row_values = dict(zip(normalized_columns, row))
            else:
                self.error(
                    f"model_id.data[{row_number}]",
                    "must be an array or object.",
                )

            field_name = row_values.get("find")
            if field_name in (None, ""):
                self.error(f"model_id.data[{row_number}].Find", "must not be blank.")
            field_name = str(field_name)
            if field_name in output:
                self.error(
                    f"model_id.data[{row_number}].Find",
                    f"duplicates field {field_name!r}.",
                )

            schema = {}
            for column, value in row_values.items():
                if column in {"find", "notes"} or value in ("", None):
                    continue
                schema_key = _SAVED_SCHEMA_COLUMNS.get(column)
                if schema_key is None:
                    self.error(
                        f"model_id.data[{row_number}]",
                        f"unsupported saved-model column {column!r}.",
                    )
                schema[schema_key] = value
            output[field_name] = schema

        normalized_settings = {
            _re.sub(r"[^a-z0-9]", "", str(key).lower()): value
            for key, value in settings.items()
        }
        saved_model = None
        saved_messages = []
        for key in ("gptmodel", "aimodel", "model"):
            if normalized_settings.get(key) not in (None, ""):
                saved_model = normalized_settings[key]
                if key != "model":
                    self.migration(f"model_id.settings.{key} mapped to model.")
                break
        for key in ("additionalmessages", "generalinstructions", "instructions", "messages"):
            if normalized_settings.get(key) not in (None, ""):
                saved_messages = normalized_settings[key]
                if key != "messages":
                    self.migration(f"model_id.settings.{key} mapped to messages.")
                break

        known_settings = {
            "additionalmessages",
            "aimodel",
            "generalinstructions",
            "gptmodel",
            "instructions",
            "messages",
            "model",
        }
        unknown_settings = sorted(set(normalized_settings) - known_settings)
        for key in unknown_settings:
            self.migration(f"model_id.settings.{key} is not used by extract.ai.")

        return output, saved_model, saved_messages


def _message_list(value: _Any) -> list:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def compile_definition(
    output: _Any,
    *,
    model: str,
    messages: _Any = None,
    strict: bool = True,
    saved_model_content: dict = None,
    source: str = "recipe output",
) -> CompiledAIDefinition:
    """
    Compile a recipe/Python output and optional saved XL model definition.

    Direct keyed output overrides fields from the saved model. Saved model
    instructions run first, followed by call-level messages.
    """
    compiler = _Compiler(source)
    output_generic_key = False

    if isinstance(output, str):
        output_generic_key = True
        output = {"output": {"description": output}}
    elif (
        isinstance(output, dict)
        and "description" in output
        and not isinstance(output["description"], dict)
    ):
        output_generic_key = True
        output = {"output": output}
    elif output is not None and not isinstance(output, dict):
        compiler.error("output", "must be a string or object.")

    direct_output = {
        str(key): value if isinstance(value, dict) else {"description": str(value)}
        for key, value in (output or {}).items()
    }

    saved_output = {}
    saved_model = None
    saved_messages = []
    if saved_model_content is not None:
        if output_generic_key:
            compiler.error(
                "output",
                "must use named fields when combined with model_id.",
            )
        saved_output, saved_model, saved_messages = compiler.saved_model(saved_model_content)

    merged_output = {**saved_output, **direct_output}
    if not merged_output:
        compiler.error("output", "must define at least one field.")

    normalized_output = {
        field: compiler.normalize_schema(schema, f"output.{field}")
        for field, schema in merged_output.items()
    }

    key_to_original = {}
    sanitized_output = {}
    for original, schema in normalized_output.items():
        sanitized = _re.sub(r"[^a-zA-Z0-9_]", "_", original)
        base = sanitized
        suffix = 2
        while sanitized in key_to_original:
            sanitized = f"{base}_{suffix}"
            suffix += 1
        key_to_original[sanitized] = original
        sanitized_output[sanitized] = schema

    strict_requested = strict
    effective_strict = strict and not compiler.dynamic_paths
    if strict_requested and compiler.dynamic_paths:
        compiler.migration(
            "strict mode was disabled because dynamic dictionaries were found at "
            f"{', '.join(compiler.dynamic_paths)}. Fixed portions of the schema remain constrained."
        )

    compiled_model = saved_model or model
    if not isinstance(compiled_model, str) or not compiled_model.strip():
        compiler.error("model", "must be a non-empty string.")

    compiled_messages = _message_list(saved_messages) + _message_list(messages)
    root_schema = {
        "type": "object",
        "properties": sanitized_output,
        "required": list(sanitized_output),
        "additionalProperties": False,
    }

    return CompiledAIDefinition(
        output=sanitized_output,
        root_schema=root_schema,
        model=compiled_model,
        messages=compiled_messages,
        strict=effective_strict,
        strict_requested=strict_requested,
        dynamic_paths=tuple(compiler.dynamic_paths),
        key_to_original=key_to_original,
        output_generic_key=output_generic_key,
        diagnostics=tuple(compiler.diagnostics),
    )
