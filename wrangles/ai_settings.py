"""Shared saved-model General Instructions compatibility rules."""

import copy as _copy
import re as _re


_INSTRUCTION_KEYS = (
    "generalinstructions", "additionalmessages", "instructions", "messages",
)


def _key(value):
    return _re.sub(r"[^a-z0-9]", "", str(value).lower())


def find_general_instructions(settings: dict) -> tuple:
    """Return the first present alias, including an explicit empty value.

    GeneralInstructions takes precedence within one settings document. Presence
    matters: clearing it must not restore instructions from a stale legacy key.
    """
    normalized = {_key(key): value for key, value in settings.items()}
    for key in _INSTRUCTION_KEYS:
        if key in normalized:
            return key, normalized[key]
    return None, None


def merge_general_instructions(existing: dict | None = None, overrides: dict | None = None) -> dict:
    """Merge settings layers and mirror instructions for older readers.

    Resolve each layer before merging so an explicit legacy-key edit or clear
    overrides an existing GeneralInstructions value. Do not modify the inputs.
    """
    result = {}
    for settings in (existing, overrides):
        if settings is None:
            continue
        result.update(_copy.deepcopy(settings))
        key, value = find_general_instructions(settings)
        if key is not None:
            result = {
                name: setting for name, setting in result.items()
                if _key(name) not in _INSTRUCTION_KEYS
            }
            result["GeneralInstructions"] = _copy.deepcopy(value)
            # Keep this mirror until all supported readers understand the new key.
            result["AdditionalMessages"] = _copy.deepcopy(value)
    return result
