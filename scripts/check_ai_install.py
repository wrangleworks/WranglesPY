"""Smoke-test the installed AI and search packages with python -I scripts/check_ai_install.py."""

import sys
from importlib import import_module
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
    installed_search = distribution("wrangles").locate_file("wrangles/search/__init__.py")
    assert Path(wrangles.search.__file__).resolve() == Path(installed_search).resolve()
    for old, new in (
        ("_ai_mode", "_ai_mode"),
        ("_search_ai_content", "_content"),
        ("_prompt_template", "_prompt_template"),
    ):
        assert import_module(f"wrangles.{old}") is import_module(f"wrangles.search.{new}")
    assert wrangles.search.ai_mode(" ")["ai_mode_metadata"]["status"] == "Skipped"
    result = wrangles.recipe.run(
        {"wrangles": [{"search.ai_mode": {
            "queries": "query", "id": "ID", "output": ["body", "metadata"],
        }}]}, dataframe=wrangles.DataFrame({"query": [""], "ID": [1]}),
        variables={"applied_permission_group": None},
    )
    assert result["body"].tolist() == [""]
    assert result["metadata"].iloc[0]["status"] == "Skipped"
    print(f"Verified AI and search entry points from {wrangles.__file__}")


if __name__ == "__main__":
    main()
