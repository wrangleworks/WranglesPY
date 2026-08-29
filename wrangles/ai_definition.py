"""
Compile recipe and saved-model extract.ai definitions into one canonical form.

The compiler is provider-neutral. Provider adapters may further restrict the
resulting JSON Schema for their own structured-output implementation.
"""
import copy as _copy
import json as _json
import logging as _logging
import math as _math
import re as _re
from dataclasses import dataclass as _dataclass
from typing import Any as _Any

import yaml as _yaml

try:
    from yaml import CSafeLoader as _SafeLoader
except ImportError:
    from yaml import SafeLoader as _SafeLoader


_LOG = _logging.getLogger(__name__)


class _JSONLikeLoader(_SafeLoader):
    """Restricted YAML loader whose implicit scalar rules match JSON."""

    def compose_node(self, parent, index):
        event = self.peek_event()
        if isinstance(event, _yaml.events.AliasEvent) or getattr(event, "anchor", None):
            raise _yaml.constructor.ConstructorError(
                None,
                None,
                "YAML anchors and aliases are not supported",
                event.start_mark,
            )
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, _yaml.nodes.MappingNode):
            raise _yaml.constructor.ConstructorError(
                None,
                None,
                f"expected a mapping node, received {node.id}",
                node.start_mark,
            )
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as exc:
                raise _yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable key",
                    key_node.start_mark,
                ) from exc
            if duplicate:
                raise _yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


_JSONLikeLoader.yaml_implicit_resolvers = _copy.deepcopy(
    _SafeLoader.yaml_implicit_resolvers
)
for _first_character, _resolvers in list(
    _JSONLikeLoader.yaml_implicit_resolvers.items()
):
    _JSONLikeLoader.yaml_implicit_resolvers[_first_character] = [
        resolver
        for resolver in _resolvers
        if resolver[0]
        not in {
            "tag:yaml.org,2002:bool",
            "tag:yaml.org,2002:float",
            "tag:yaml.org,2002:int",
            "tag:yaml.org,2002:null",
            "tag:yaml.org,2002:timestamp",
        }
    ]

_JSONLikeLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    _re.compile(r"^(?:true|false)$", _re.IGNORECASE),
    list("tTfF"),
)
_JSONLikeLoader.add_implicit_resolver(
    "tag:yaml.org,2002:null",
    _re.compile(r"^null$", _re.IGNORECASE),
    list("nN"),
)
_JSONLikeLoader.add_implicit_resolver(
    "tag:yaml.org,2002:int",
    _re.compile(r"^-?(?:0|[1-9][0-9]*)$"),
    list("-0123456789"),
)
_JSONLikeLoader.add_implicit_resolver(
    "tag:yaml.org,2002:float",
    _re.compile(
        r"^-?(?:(?:0|[1-9][0-9]*)\.[0-9]+(?:[eE][-+]?[0-9]+)?|"
        r"(?:0|[1-9][0-9]*)[eE][-+]?[0-9]+)$"
    ),
    list("-0123456789"),
)

_MAX_HUMAN_VALUE_LENGTH = 50_000
_MAX_HUMAN_VALUE_DEPTH = 20
_MAX_HUMAN_VALUE_NODES = 2_000


def _validate_json_tree(value: _Any) -> _Any:
    """Reject YAML-only values and unreasonably large nested input trees."""
    nodes = 0

    def visit(item: _Any, path: str, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > _MAX_HUMAN_VALUE_NODES:
            raise ValueError("contains too many nested values")
        if depth > _MAX_HUMAN_VALUE_DEPTH:
            raise ValueError("is nested too deeply")
        if item is None or isinstance(item, (str, bool, int)):
            return
        if isinstance(item, float):
            if not _math.isfinite(item):
                raise ValueError(f"{path} must be a finite number")
            return
        if isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{path}[{index}]", depth + 1)
            return
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ValueError(f"{path} contains a non-string object key")
                visit(child, f"{path}.{key}", depth + 1)
            return
        raise ValueError(f"{path} contains unsupported value type {type(item).__name__}")

    visit(value, "$", 0)
    return value


def _load_json_like(value: str) -> _Any:
    stripped = value.strip()
    if len(stripped) > _MAX_HUMAN_VALUE_LENGTH:
        raise ValueError(
            f"exceeds the {_MAX_HUMAN_VALUE_LENGTH:,}-character saved-cell limit"
        )
    for token in _yaml.scan(stripped):
        if isinstance(token, (_yaml.tokens.AnchorToken, _yaml.tokens.AliasToken)):
            raise ValueError("YAML anchors and aliases are not supported")
        if isinstance(token, _yaml.tokens.TagToken):
            raise ValueError("explicit YAML tags are not supported")
    try:
        parsed = _json.loads(stripped)
    except (TypeError, ValueError):
        parsed = _yaml.load(stripped, Loader=_JSONLikeLoader)
    return _validate_json_tree(parsed)


def _split_top_level(value: str, delimiter: str) -> list | None:
    """Split a human list without breaking quoted or nested values."""
    parts = []
    start = 0
    quote = None
    escaped = False
    depths = {"[": 0, "{": 0, "(": 0}
    closing = {"]": "[", "}": "{", ")": "("}

    for index, character in enumerate(value):
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
            continue
        if character in depths:
            depths[character] += 1
            continue
        if character in closing:
            opener = closing[character]
            depths[opener] = max(0, depths[opener] - 1)
            continue
        if character == delimiter and not any(depths.values()):
            parts.append(value[start:index].strip())
            start = index + 1

    if not parts:
        return None
    parts.append(value[start:].strip())
    return parts

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
    "exampleinput": "exampleInput",
    "exampleoutput": "exampleOutput",
    "examples": "examples",
    "items": "items",
    "nullable": "nullable",
    "properties": "properties",
    "required": "required",
    "type": "type",
}
_EXAMPLE_PAIR_KEYS = {"input", "name", "notes", "output"}
_MISSING = object()


@_dataclass(frozen=True)
class CompiledFieldExample:
    """A field-specific example with paired source input and expected value."""

    field: str
    input: _Any
    output: _Any
    name: str = None
    notes: str = None


@_dataclass(frozen=True)
class CompiledRecordExample:
    """A record-level example with paired source input and complete output."""

    name: str
    input: _Any
    output: dict
    notes: str = None


@_dataclass(frozen=True)
class CompiledAIDefinition:
    """Canonical extract.ai definition consumed by provider transports."""

    output: dict
    root_schema: dict
    model: str
    messages: list
    reasoning: dict | None
    field_examples: tuple
    record_examples: tuple
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
        if not (
            stripped.startswith(("{", "["))
            or stripped.startswith("- ")
        ):
            return value
        try:
            return _load_json_like(stripped)
        except (TypeError, ValueError, _yaml.YAMLError):
            return value

    @staticmethod
    def _parse_scalar_token(value: str) -> _Any:
        stripped = value.strip()
        if not stripped:
            return ""
        try:
            return _load_json_like(stripped)
        except (TypeError, ValueError, _yaml.YAMLError):
            return stripped

    @classmethod
    def _parse_list_value(cls, value: _Any) -> _Any:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            return value

        if stripped.startswith("[") or stripped.startswith("- "):
            try:
                parsed = _load_json_like(stripped)
            except (TypeError, ValueError, _yaml.YAMLError) as exc:
                raise ValueError(f"could not parse list value: {exc}") from exc
            if isinstance(parsed, list):
                return parsed

        parts = _split_top_level(stripped, "|")
        if parts is None:
            parts = _split_top_level(stripped, ",")
        if parts is None:
            return [cls._parse_scalar_token(stripped)]
        return [cls._parse_scalar_token(item) for item in parts if item.strip()]

    @classmethod
    def _parse_properties_value(cls, value: _Any) -> _Any:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            return value

        if stripped.startswith(("{", "[")) or stripped.startswith("- "):
            try:
                parsed = _load_json_like(stripped)
            except (TypeError, ValueError, _yaml.YAMLError) as exc:
                raise ValueError(f"could not parse properties value: {exc}") from exc
            if isinstance(parsed, (dict, list)):
                return parsed

        pipe_parts = _split_top_level(stripped, "|")
        comma_parts = _split_top_level(stripped, ",")
        parts = pipe_parts or comma_parts
        if parts and all(":" in item for item in parts):
            mapped = {}
            for item in parts:
                name, raw_schema = item.split(":", 1)
                name = name.strip()
                if not name or name in mapped:
                    return value
                mapped[name] = cls._parse_scalar_token(raw_schema)
            return mapped
        if ":" in stripped:
            try:
                parsed = _load_json_like(stripped)
            except (TypeError, ValueError, _yaml.YAMLError):
                return value
            if isinstance(parsed, dict):
                return parsed

        return cls._parse_list_value(value)

    @classmethod
    def _normalize_property_shorthand(cls, value: _Any) -> _Any:
        if not isinstance(value, dict):
            return value
        normalized = {}
        for name, schema in value.items():
            if schema in (None, ""):
                normalized[str(name)] = {}
                continue
            if isinstance(schema, str):
                schema_type = _TYPE_ALIASES.get(schema.strip().lower(), schema.strip().lower())
                if schema_type in _JSON_TYPES:
                    normalized[str(name)] = {"type": schema_type}
                    continue
            normalized[str(name)] = schema
        return normalized

    @classmethod
    def _parse_items_value(cls, value: _Any) -> _Any:
        if isinstance(value, str):
            stripped = value.strip()
            schema_type = _TYPE_ALIASES.get(stripped.lower(), stripped.lower())
            if schema_type in _JSON_TYPES:
                return {"type": schema_type}
            value = cls._parse_properties_value(value)

        if isinstance(value, list):
            return {
                "type": "object",
                "properties": {str(name): {} for name in value},
            }
        if isinstance(value, dict) and not set(value).intersection(_SUPPORTED_SCHEMA_KEYS):
            return {
                "type": "object",
                "properties": cls._normalize_property_shorthand(value),
            }
        return value

    @classmethod
    def _parse_additional_properties_value(cls, value: _Any) -> _Any:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.lower() in {"true", "false"}:
                return stripped.lower() == "true"
            schema_type = _TYPE_ALIASES.get(stripped.lower(), stripped.lower())
            if schema_type in _JSON_TYPES:
                return {"type": schema_type}
        return cls._parse_items_value(value)

    @classmethod
    def _parse_examples_value(cls, value: _Any) -> _Any:
        """
        Parse human-entered JSON/YAML-like examples into structured values.

        Examples cells conventionally contain one or more comma-separated
        values. Wrapping the cell as a YAML flow sequence supports unquoted
        object keys and values without requiring users to author strict JSON.
        """
        if not isinstance(value, str):
            return value

        stripped = value.strip()
        if stripped.startswith(("{", "[")) or stripped.startswith("- "):
            try:
                parsed = _load_json_like(stripped)
            except (TypeError, ValueError, _yaml.YAMLError) as exc:
                if _split_top_level(stripped, ",") is None:
                    raise ValueError(f"could not parse examples value: {exc}") from exc
                parsed = value
            if isinstance(parsed, (dict, list)):
                return parsed

        parts = _split_top_level(stripped, "|")
        if parts is None:
            parts = _split_top_level(stripped, ",")
        if parts is not None:
            return [cls._parse_scalar_token(item) for item in parts if item.strip()]
        return cls._parse_scalar_token(stripped)

    @staticmethod
    def _looks_like_example_pair(value: _Any) -> bool:
        return (
            isinstance(value, dict)
            and bool({"input", "output"}.intersection(value))
            and set(value).issubset(_EXAMPLE_PAIR_KEYS)
        )

    def split_field_examples(self, value: dict, path: str) -> tuple:
        """
        Separate schema value examples from field-level input/output pairs.

        `Examples` remains backward-compatible output-only guidance.
        `Example - Output` also remains output-only when no paired input exists.
        """
        schema = _copy.deepcopy(value)
        pairs = []

        example_input = schema.pop("exampleInput", _MISSING)
        example_output = schema.pop("exampleOutput", _MISSING)
        if example_input is not _MISSING:
            if example_input in ("", None):
                example_input = _MISSING
            else:
                example_input = self._parse_json_value(example_input)
        if example_output is not _MISSING:
            if example_output in ("", None):
                example_output = _MISSING
            elif example_input is _MISSING:
                example_output = self._parse_examples_value(example_output)
            else:
                example_output = self._parse_json_value(example_output)

        if example_input is not _MISSING and example_output is _MISSING:
            self.error(path, "Example - Input requires Example - Output.")
        if example_input is not _MISSING:
            pairs.append({
                "input": example_input,
                "output": example_output,
            })
        elif example_output is not _MISSING:
            existing = schema.get("examples", [])
            if existing in ("", None):
                existing = []
            elif not isinstance(existing, list):
                existing = [existing]
            output_values = (
                example_output
                if isinstance(example_output, list)
                else [example_output]
            )
            schema["examples"] = list(existing) + list(output_values)

        raw_examples = schema.get("examples", _MISSING)
        if raw_examples is _MISSING:
            return schema, pairs

        parsed_examples = self._parse_examples_value(raw_examples)
        example_items = (
            parsed_examples
            if isinstance(parsed_examples, list)
            else [parsed_examples]
        )
        value_examples = []
        for index, item in enumerate(example_items):
            if not self._looks_like_example_pair(item):
                value_examples.append(item)
                continue
            if item.get("input") in (None, ""):
                self.error(f"{path}.examples[{index}].input", "must not be blank.")
            if "output" not in item or item.get("output") == "":
                self.error(
                    f"{path}.examples[{index}].output",
                    "must be provided for a paired field example.",
                )
            pair = {
                "input": self._parse_json_value(item["input"]),
                "output": self._parse_json_value(item["output"]),
            }
            for metadata_key in ("name", "notes"):
                metadata_value = item.get(metadata_key)
                if metadata_value not in (None, ""):
                    pair[metadata_key] = str(metadata_value)
            pairs.append(pair)

        if value_examples:
            schema["examples"] = value_examples
        else:
            schema.pop("examples", None)
        return schema, pairs

    @staticmethod
    def _matches_json_type(value: _Any, schema_type: str) -> bool:
        if schema_type == "null":
            return value is None
        if schema_type == "boolean":
            return isinstance(value, bool)
        if schema_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if schema_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if schema_type == "string":
            return isinstance(value, str)
        if schema_type == "object":
            return isinstance(value, dict)
        if schema_type == "array":
            return isinstance(value, list)
        return False

    @staticmethod
    def _allows_null(schema: dict) -> bool:
        schema_type = schema.get("type")
        if schema_type == "null":
            return True
        if isinstance(schema_type, list) and "null" in schema_type:
            return True
        return any(
            isinstance(option, dict) and _Compiler._allows_null(option)
            for option in schema.get("anyOf", [])
        )

    def materialize_example(self, value: _Any, schema: dict, path: str) -> _Any:
        """Validate an expected example and null-fill nullable omissions."""
        if isinstance(schema.get("anyOf"), list):
            errors = []
            for option in schema["anyOf"]:
                try:
                    return self.materialize_example(value, option, path)
                except ValueError as exc:
                    errors.append(str(exc))
            self.error(path, "does not match any allowed schema.")

        if isinstance(value, str):
            declared = schema.get("type", _DEFAULT_SCALAR_TYPES)
            declared = declared if isinstance(declared, list) else [declared]
            non_null_types = [item for item in declared if item != "null"]
            if "string" not in non_null_types:
                if "object" in non_null_types:
                    candidate = self._parse_properties_value(value)
                elif "array" in non_null_types:
                    candidate = self._parse_list_value(value)
                else:
                    candidate = self._parse_scalar_token(value)
                if candidate != value:
                    value = candidate

        if "enum" in schema and value not in schema["enum"]:
            self.error(path, f"value {value!r} is not in the field enum.")

        schema_types = (
            schema.get("type", _DEFAULT_SCALAR_TYPES)
            if isinstance(schema.get("type", _DEFAULT_SCALAR_TYPES), list)
            else [schema.get("type")]
        )
        matching_types = [
            schema_type
            for schema_type in schema_types
            if self._matches_json_type(value, schema_type)
        ]
        if not matching_types:
            self.error(
                path,
                f"value {value!r} does not match type {schema.get('type')!r}.",
            )

        schema_type = matching_types[0]
        if schema_type == "object":
            properties = schema.get("properties", {})
            additional = schema.get("additionalProperties", False)
            unknown = [key for key in value if key not in properties]
            if unknown and additional is False:
                self.error(
                    path,
                    f"contains unknown field(s): {', '.join(map(str, unknown))}.",
                )
            materialized = {}
            for key, child_schema in properties.items():
                if key not in value:
                    if not self._allows_null(child_schema):
                        self.error(
                            f"{path}.{key}",
                            "must be provided because this property "
                            "does not allow null.",
                        )
                    materialized[key] = None
                    continue
                materialized[key] = self.materialize_example(
                    value[key],
                    child_schema,
                    f"{path}.{key}",
                )
            for key in unknown:
                materialized[key] = (
                    self.materialize_example(
                        value[key],
                        additional,
                        f"{path}.{key}",
                    )
                    if isinstance(additional, dict)
                    else value[key]
                )
            return materialized

        if schema_type == "array" and isinstance(schema.get("items"), dict):
            return [
                self.materialize_example(
                    item,
                    schema["items"],
                    f"{path}[{index}]",
                )
                for index, item in enumerate(value)
            ]
        return value

    def compile_record_examples(
        self,
        value: _Any,
        *,
        root_schema: dict,
        original_to_sanitized: dict,
        output_generic_key: bool,
        path: str,
    ) -> list:
        if value in (None, ""):
            return []
        raw_examples = value if isinstance(value, list) else [value]
        compiled = []
        for index, raw_example in enumerate(raw_examples):
            example_path = f"{path}[{index}]"
            if not isinstance(raw_example, dict):
                self.error(example_path, "must be an object with input and output.")
            if raw_example.get("input") in (None, ""):
                self.error(f"{example_path}.input", "must not be blank.")
            if "output" not in raw_example:
                self.error(f"{example_path}.output", "must be provided.")

            example_input = self._parse_json_value(raw_example["input"])
            example_output = raw_example["output"]
            if output_generic_key and not isinstance(example_output, dict):
                example_output = {"output": self._parse_examples_value(example_output)}
            elif isinstance(example_output, str):
                example_output = self._parse_json_value(example_output)
            if not isinstance(example_output, dict):
                self.error(f"{example_path}.output", "must be an object.")

            sanitized_output = {}
            for key, item in example_output.items():
                sanitized = original_to_sanitized.get(str(key), str(key))
                if sanitized not in root_schema["properties"]:
                    self.error(
                        f"{example_path}.output",
                        f"contains unknown output field {key!r}.",
                    )
                if sanitized in sanitized_output:
                    self.error(
                        f"{example_path}.output",
                        f"duplicates output field {key!r}.",
                    )
                sanitized_output[sanitized] = item

            complete_output = self.materialize_example(
                sanitized_output,
                root_schema,
                f"{example_path}.output",
            )
            name = raw_example.get("name")
            if name in (None, ""):
                name = f"example-{index + 1}"
            notes = raw_example.get("notes")
            if notes in (None, ""):
                notes = None
            compiled.append(
                CompiledRecordExample(
                    name=str(name),
                    input=example_input,
                    output=complete_output,
                    notes=str(notes) if notes is not None else None,
                )
            )
        return compiled

    def normalize_schema(
        self,
        value: _Any,
        path: str,
        *,
        nullable_default: bool = True,
    ) -> dict:
        if value is None:
            value = {}
        if not isinstance(value, dict):
            self.error(path, f"expected an object, received {type(value).__name__}.")

        node = {}
        for key, item in _copy.deepcopy(value).items():
            # YAML-like entries such as `{nullable}` are blank Excel values.
            # Omit only keywords whose documented behavior has a safe default.
            if (
                key in {"additionalProperties", "nullable", "required"}
                and isinstance(item, str)
                and not item.strip()
            ):
                continue
            parser = {
                "additionalProperties": self._parse_additional_properties_value,
                "anyOf": self._parse_list_value,
                "const": self._parse_json_value,
                "default": self._parse_json_value,
                "enum": self._parse_list_value,
                "examples": self._parse_examples_value,
                "items": self._parse_items_value,
                "properties": self._parse_properties_value,
                "required": self._parse_list_value,
            }.get(key)
            try:
                node[key] = parser(item) if parser else item
            except (TypeError, ValueError, _yaml.YAMLError) as exc:
                self.error(f"{path}.{key}", str(exc))
            if (
                key == "enum"
                and isinstance(item, str)
                and None in node[key]
                and any(
                    token.strip().lower() == "null"
                    for token in (_split_top_level(item, "|") or _split_top_level(item, ",") or [])
                )
            ):
                self.migration(
                    f"{path}.enum converted the string 'null' to JSON null."
                )

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

        nullable = node.pop("nullable", None)
        if isinstance(nullable, str):
            normalized_nullable = nullable.strip().lower()
            if normalized_nullable in {"true", "false"}:
                nullable = normalized_nullable == "true"
            else:
                self.error(path, "nullable must be true or false.")
        if nullable is not None:
            if not isinstance(nullable, bool):
                self.error(path, "nullable must be true or false.")
            if nullable:
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

        nullable_allowed = nullable if nullable is not None else nullable_default
        if nullable_allowed:
            if node.get("anyOf"):
                if not any(
                    isinstance(option, dict)
                    and (
                        option.get("type") == "null"
                        or (
                            isinstance(option.get("type"), list)
                            and "null" in option["type"]
                        )
                    )
                    for option in node["anyOf"]
                ):
                    node["anyOf"].append({"type": "null", "nullable": False})
            else:
                schema_type = node.get("type")
                schema_types = (
                    list(schema_type)
                    if isinstance(schema_type, list)
                    else [schema_type]
                )
                if "null" not in schema_types:
                    schema_types.append("null")
                node["type"] = schema_types
        elif isinstance(node.get("type"), list) and "null" in node["type"]:
            self.error(path, "nullable false conflicts with a type containing null.")
        elif isinstance(node.get("enum"), list) and None in node["enum"]:
            self.error(path, "nullable false conflicts with an enum containing null.")

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

        if isinstance(node.get("default"), str):
            non_null_types = [item for item in declared_types if item != "null"]
            if len(non_null_types) == 1 and non_null_types[0] != "string":
                parsed_default = self._parse_scalar_token(node["default"])
                if parsed_default != node["default"]:
                    node["default"] = parsed_default

        if "enum" in node and not isinstance(node["enum"], list):
            self.error(path, "enum must be an array or comma-separated string.")
        if "enum" in node and nullable_allowed:
            converted_string_null = False
            normalized_enum = []
            for item in node["enum"]:
                if isinstance(item, str) and item.strip().lower() == "null":
                    item = None
                    converted_string_null = True
                if item not in normalized_enum:
                    normalized_enum.append(item)
            if None not in normalized_enum:
                normalized_enum.append(None)
            node["enum"] = normalized_enum
            if converted_string_null:
                self.migration(
                    f"{path}.enum converted the string 'null' to JSON null."
                )
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
        elif isinstance(properties, dict):
            node["properties"] = self._normalize_property_shorthand(properties)
            properties = node["properties"]
        if properties is not None and not isinstance(properties, dict):
            self.error(path, "properties must be an object, list, or comma-separated string.")
        if isinstance(properties, dict):
            node["properties"] = {
                str(name): self.normalize_schema(
                    child,
                    f"{path}.properties.{name}",
                    nullable_default=False,
                )
                for name, child in properties.items()
            }
            if "required" not in node:
                node["required"] = list(node["properties"])

        if "required" in node:
            invalid_required = [
                item
                for item in node["required"]
                if not isinstance(item, str)
                or not isinstance(node.get("properties"), dict)
                or item not in node["properties"]
            ]
            if invalid_required:
                self.error(
                    path,
                    "required must contain only names defined in properties.",
                )

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
                    nullable_default=False,
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
            node["items"] = self.normalize_schema(
                node["items"],
                f"{path}.items",
                nullable_default=False,
            )
        elif "items" in node:
            self.error(path, "items requires type 'array'.")

        if "anyOf" in node and not isinstance(node["anyOf"], list):
            self.error(path, "anyOf must be an array of schema objects.")
        if isinstance(node.get("anyOf"), list):
            node["anyOf"] = [
                self.normalize_schema(
                    option,
                    f"{path}.anyOf[{index}]",
                    nullable_default=False,
                )
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
        saved_examples = top_level.get("examples")
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
        saved_reasoning = None
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

        reasoning_effort = normalized_settings.get("reasoningeffort")
        if reasoning_effort not in (None, ""):
            reasoning_effort = str(reasoning_effort).strip().lower()
            if reasoning_effort not in {"none", "low"}:
                self.error(
                    "model_id.settings.ReasoningEffort",
                    "must be 'none' or 'low'.",
                )
            saved_reasoning = {"effort": reasoning_effort}

        known_settings = {
            "additionalmessages",
            "aimodel",
            "generalinstructions",
            "gptmodel",
            "instructions",
            "messages",
            "model",
            "reasoningeffort",
        }
        unknown_settings = sorted(set(normalized_settings) - known_settings)
        for key in unknown_settings:
            self.migration(f"model_id.settings.{key} is not used by extract.ai.")

        return output, saved_model, saved_messages, saved_reasoning, saved_examples


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
    examples: _Any = None,
    strict: bool = True,
    saved_model_content: dict = None,
    source: str = "recipe output",
) -> CompiledAIDefinition:
    """
    Compile a recipe/Python output and optional saved XL model definition.

    Direct keyed output overrides fields from the saved model. Saved model
    instructions and record examples run first, followed by call-level
    messages and examples.
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
    saved_reasoning = None
    saved_examples = None
    if saved_model_content is not None:
        if output_generic_key:
            compiler.error(
                "output",
                "must use named fields when combined with model_id.",
            )
        (
            saved_output,
            saved_model,
            saved_messages,
            saved_reasoning,
            saved_examples,
        ) = compiler.saved_model(saved_model_content)

    merged_output = {**saved_output, **direct_output}
    if not merged_output:
        compiler.error("output", "must define at least one field.")

    raw_field_examples = []
    prepared_output = {}
    for field, schema in merged_output.items():
        clean_schema, pairs = compiler.split_field_examples(
            schema,
            f"output.{field}",
        )
        prepared_output[field] = clean_schema
        raw_field_examples.extend(
            (field, index, pair)
            for index, pair in enumerate(pairs)
        )

    normalized_output = {
        field: compiler.normalize_schema(schema, f"output.{field}")
        for field, schema in prepared_output.items()
    }

    key_to_original = {}
    original_to_sanitized = {}
    sanitized_output = {}
    for original, schema in normalized_output.items():
        sanitized = _re.sub(r"[^a-zA-Z0-9_]", "_", original)
        base = sanitized
        suffix = 2
        while sanitized in key_to_original:
            sanitized = f"{base}_{suffix}"
            suffix += 1
        key_to_original[sanitized] = original
        original_to_sanitized[original] = sanitized
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
    field_examples = []
    for original_field, index, pair in raw_field_examples:
        sanitized_field = original_to_sanitized[original_field]
        field_examples.append(
            CompiledFieldExample(
                field=sanitized_field,
                input=pair["input"],
                output=compiler.materialize_example(
                    pair["output"],
                    sanitized_output[sanitized_field],
                    f"output.{original_field}.examples[{index}].output",
                ),
                name=pair.get("name"),
                notes=pair.get("notes"),
            )
        )

    record_examples = []
    record_examples.extend(
        compiler.compile_record_examples(
            saved_examples,
            root_schema=root_schema,
            original_to_sanitized=original_to_sanitized,
            output_generic_key=output_generic_key,
            path="model_id.examples",
        )
    )
    record_examples.extend(
        compiler.compile_record_examples(
            examples,
            root_schema=root_schema,
            original_to_sanitized=original_to_sanitized,
            output_generic_key=output_generic_key,
            path="examples",
        )
    )

    return CompiledAIDefinition(
        output=sanitized_output,
        root_schema=root_schema,
        model=compiled_model,
        messages=compiled_messages,
        reasoning=saved_reasoning,
        field_examples=tuple(field_examples),
        record_examples=tuple(record_examples),
        strict=effective_strict,
        strict_requested=strict_requested,
        dynamic_paths=tuple(compiler.dynamic_paths),
        key_to_original=key_to_original,
        output_generic_key=output_generic_key,
        diagnostics=tuple(compiler.diagnostics),
    )


def render_example_guidance(compiled: CompiledAIDefinition) -> str:
    """Render canonical examples as stable, provider-neutral prompt content."""
    sections = []
    value_lines = []
    for field, schema in compiled.output.items():
        values = schema.get("examples")
        if values:
            value_lines.append(
                f"- {field}: examples are "
                f"{_json.dumps(values, ensure_ascii=False, default=str)}"
            )
    if value_lines:
        sections.append(
            "Use these field value examples as style guidance, not values to copy:\n"
            + "\n".join(value_lines)
        )

    if compiled.field_examples:
        blocks = []
        for example in compiled.field_examples:
            attributes = f" field={_json.dumps(example.field)}"
            if example.name:
                attributes += f" name={_json.dumps(example.name)}"
            lines = [
                f"<field_example{attributes}>",
            ]
            if example.notes:
                lines.append(
                    f"<notes>{_json.dumps(example.notes, ensure_ascii=False)}</notes>"
                )
            lines.extend([
                f"<input>{_json.dumps(example.input, ensure_ascii=False, default=str)}</input>",
                (
                    "<expected_value>"
                    f"{_json.dumps(example.output, ensure_ascii=False, default=str)}"
                    "</expected_value>"
                ),
                "</field_example>",
            ])
            blocks.append("\n".join(lines))
        sections.append(
            "Each field example below demonstrates only the named output field. "
            "Do not infer values for other fields from its expected value.\n"
            + "\n".join(blocks)
        )

    if compiled.record_examples:
        blocks = []
        for example in compiled.record_examples:
            lines = [
                f'<record_example name={_json.dumps(example.name)}>',
            ]
            if example.notes:
                lines.append(
                    f"<notes>{_json.dumps(example.notes, ensure_ascii=False)}</notes>"
                )
            lines.extend([
                f"<input>{_json.dumps(example.input, ensure_ascii=False, default=str)}</input>",
                (
                    "<expected_output>"
                    f"{_json.dumps(example.output, ensure_ascii=False, default=str)}"
                    "</expected_output>"
                ),
                "</record_example>",
            ])
            blocks.append("\n".join(lines))
        sections.append(
            "The record examples below demonstrate the complete expected output shape.\n"
            + "\n".join(blocks)
        )

    return "\n\n".join(sections)
