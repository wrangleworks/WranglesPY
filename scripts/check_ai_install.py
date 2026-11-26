"""Smoke-test the installed AI package with python -I scripts/check_ai_install.py."""

import sys
from importlib.metadata import distribution
from importlib.resources import files
from pathlib import Path

import wrangles
import wrangles.ai_cache as legacy_cache
from wrangles import recipe_wrangles
from wrangles.ai import cache


def main():
    installed_init = distribution("wrangles").locate_file("wrangles/__init__.py")
    assert Path(wrangles.__file__).resolve() == Path(installed_init).resolve()
    assert files("wrangles").joinpath("ai_defaults.yml").is_file()
    assert legacy_cache is cache

    frame = wrangles.DataFrame({"Text": []})
    accessor = frame.wrangles.ai
    names = ("choose", "score", "true_false", "decisions", "answers", "agent", "skill")
    for namespace in (wrangles.ai, recipe_wrangles.ai, accessor):
        for name in names:
            assert callable(getattr(namespace, name)), name

    result = accessor.agent(input="Text", instructions="Count occurrences.",
                            output={"Count": {"type": "integer"}})
    assert list(result.columns) == ["Text", "Count"]
    assert result["Count"].dtype == "int64"
    assert "copilot" not in sys.modules
    print(f"Verified seven AI entry points from {wrangles.__file__}")


if __name__ == "__main__":
    main()
