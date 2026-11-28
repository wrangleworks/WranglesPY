"""Private defaults and safe YAML codec selection shared by recipe wrappers."""

try:
    from yaml import CSafeLoader as _YAMLLoader, CSafeDumper as _YAMLDumper
except ImportError:
    from yaml import SafeLoader as _YAMLLoader, SafeDumper as _YAMLDumper


def _normalize_default_list(default, input: list, func_name: str) -> list:
    """
    Normalize a default value/list into a per-column list of defaults.

    A scalar (or a single-element list) is broadcast to all columns.
    A list with the same length as input is used as-is, one default per column.
    An empty list (`[]`) is treated as the default value itself, not a per-column list.
    """
    if isinstance(default, list) and len(default) > 0:
        if len(default) == 1:
            return [default[0]] * len(input)
        elif len(default) != len(input):
            raise ValueError(
                f'The list of default values must be a single value or the same length as input/output for {func_name}'
            )
        else:
            return default
    else:
        return [default] * len(input)
