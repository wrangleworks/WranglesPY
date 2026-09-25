"""
Load user-visible defaults for AI-backed wrangles.

Set WRANGLES_AI_CONFIG to a YAML file to override the packaged policy.
"""
import copy as _copy
import functools as _functools
import os as _os
import re as _re
from pathlib import Path as _Path

import yaml as _yaml


_PACKAGED_CONFIG = _Path(__file__).with_name("ai_defaults.yml")
_CONFIG_ENV = "WRANGLES_AI_CONFIG"


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

    if not isinstance(config, dict):
        raise ValueError(f"AI configuration '{config_path}' must contain a YAML object.")
    if config.get("version") != 1:
        raise ValueError(
            f"AI configuration '{config_path}' has unsupported version "
            f"{config.get('version')!r}; expected 1."
        )
    if not isinstance(config.get("extract_ai"), dict):
        raise ValueError(f"AI configuration '{config_path}' must define 'extract_ai'.")
    capabilities = config.get("model_capabilities", {})
    if not isinstance(capabilities, dict) or any(
        not isinstance(model, str)
        or not isinstance(flags, dict)
        or any(
            key not in {"reasoning", "reasoning_none", "low_verbosity"}
            or not isinstance(value, bool)
            for key, value in flags.items()
        )
        for model, flags in capabilities.items()
    ):
        raise ValueError(
            f"AI configuration '{config_path}' must define model_capabilities "
            "as model names mapped to boolean reasoning, reasoning_none, or low_verbosity flags."
        )
    return config


def config_path() -> _Path:
    """
    Return the active AI configuration path.
    """
    override = _os.getenv(_CONFIG_ENV)
    return _Path(override) if override else _PACKAGED_CONFIG


def load() -> dict:
    """
    Return a defensive copy of the active AI configuration.
    """
    return _copy.deepcopy(_load_config_file(str(config_path().resolve())))


def extract_ai() -> dict:
    """
    Return the configured extract.ai policy.
    """
    return load()["extract_ai"]


def model_capabilities(model: str) -> dict:
    """
    Return configured capability overrides, including dated model snapshots.
    """
    model = (model or "").strip().lower()
    base_model = _re.sub(r"-\d{4}-\d{2}-\d{2}$", "", model)
    packaged = _load_config_file(str(_PACKAGED_CONFIG.resolve()))
    active = load()
    flags = {}
    for config in (packaged, active):
        capabilities = config.get("model_capabilities", {})
        flags.update(capabilities.get(base_model, {}))
        flags.update(capabilities.get(model, {}))
    return flags


def clear_cache() -> None:
    """
    Clear cached configuration files, primarily for tests and long-lived hosts.
    """
    _load_config_file.cache_clear()
