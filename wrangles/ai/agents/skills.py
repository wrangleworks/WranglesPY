"""Load the text Skills selected for one Copilot session from an Agent Plugins bundle."""

from dataclasses import dataclass
import hashlib
import json
import logging
import os
from pathlib import Path
import re

import yaml


_LOG = logging.getLogger("wrangles.agent_skills")
_MANIFEST_ID = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
_TEXT = {"type": "string"}
_MANIFEST_FIELDS = {
    "$schema": {"const": _MANIFEST_ID},
    "name": {"type": "string", "minLength": 1, "maxLength": 64,
             "pattern": r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\Z"},
    **dict.fromkeys(("version", "description", "homepage", "repository", "license"), _TEXT),
    "author": {"type": "object", "properties": dict.fromkeys(("name", "email", "url"), _TEXT),
               "additionalProperties": False},
    "keywords": {"type": "array", "items": _TEXT},
    "extensions": {"type": "object", "additionalProperties": {"type": "object"}},
}


@dataclass(frozen=True)
class LocalSkill:
    package: str
    name: str
    path: Path
    description: str
    text: str
    sha256: str

    def report(self):
        return {"package": self.package, "name": self.name, "path": str(self.path), "sha256": self.sha256}


class SelectedSkills:
    """Copilot's SkillProvider for the explicitly selected, already-read files."""

    def __init__(self, selected):
        self.selected = selected

    def list_skills(self):
        from copilot import SkillProviderDescriptor
        return [SkillProviderDescriptor(name=s.name, description=s.description) for s in self.selected.values()]

    def read_skill(self, name):
        skill = self.selected.get(name)
        return skill.text if skill else None


def _package_name(root):
    from jsonschema import Draft202012Validator

    path = (root / "plugin.json").resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError("plugin.json must resolve inside the configured package")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    schema = {"type": "object", "required": ["$schema", "name"], "properties": _MANIFEST_FIELDS}
    if not Draft202012Validator(schema).is_valid(manifest):
        raise ValueError("Invalid Agent Plugins 1.0 manifest: check plugin.json $schema, name and metadata")
    if set(manifest) - _MANIFEST_FIELDS.keys():
        _LOG.warning("Ignoring unrecognized top-level fields in plugin.json")
    return manifest["name"]


def load_skills(package, skill, skills):
    if skills is not None:
        if skill is not None or not isinstance(skills, list) or not skills:
            raise ValueError("Use skill or a nonempty skills list of model_id references")
        if any(not isinstance(ref, dict) or set(ref) != {"model_id"} for ref in skills):
            raise ValueError("Each skills entry requires a local model_id")
        names = [ref["model_id"] for ref in skills]
    else:
        names = [skill] if skill is not None else []
    if not names:
        if package is not None:
            raise ValueError("skill_package requires a named Skill")
        return {}
    for name in names:
        if not isinstance(name, str) or len(name) > 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise ValueError("Use a portable lowercase Skill name")
    if len(set(names)) != len(names):
        raise ValueError("Duplicate Skill reference")
    package = package or os.getenv("WRANGLES_AGENT_PLUGIN")
    if not package:
        raise ValueError("Set skill_package or WRANGLES_AGENT_PLUGIN when selecting a Skill")
    root = Path(package).resolve(strict=True)
    package_name = _package_name(root)
    selected = {}
    for name in names:
        folder = (root / "skills" / name).resolve(strict=True)
        path = (folder / "SKILL.md").resolve(strict=True)
        if not folder.is_relative_to(root) or not path.is_relative_to(folder):
            raise ValueError("Skill must resolve inside the configured package")
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        lines = text.splitlines()
        if not lines or lines[0] != "---" or "---" not in lines[1:]:
            raise ValueError("Missing SKILL.md frontmatter")
        end = lines.index("---", 1)
        metadata = yaml.safe_load("\n".join(lines[1:end]))
        description = metadata.get("description") if isinstance(metadata, dict) else None
        if (not isinstance(description, str) or not description.strip() or len(description) > 1024
                or metadata.get("name") != name or not "\n".join(lines[end + 1:]).strip()):
            raise ValueError("SKILL.md requires matching name, description and instructions")
        selected[name] = LocalSkill(package_name, name, path, description, text, hashlib.sha256(raw).hexdigest())
    return selected
