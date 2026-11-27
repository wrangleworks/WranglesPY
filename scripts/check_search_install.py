"""Check installed search imports and offline behavior in Python isolated mode."""

from importlib import import_module
from importlib.metadata import distribution
from pathlib import Path

import wrangles
from wrangles.search import ai_mode


def main():
    installed = distribution("wrangles").locate_file("wrangles/search/__init__.py")
    assert Path(wrangles.search.__file__).resolve() == Path(installed).resolve()
    for old, new in (
        ("_ai_mode", "_ai_mode"),
        ("_search_ai_content", "_content"),
        ("_prompt_template", "_prompt_template"),
    ):
        assert import_module(f"wrangles.{old}") is import_module(f"wrangles.search.{new}")

    assert callable(ai_mode)
    assert wrangles.search.ai_mode is ai_mode
    skipped = ai_mode(" ")
    assert skipped == {
        "ai_mode_results": "",
        "ai_mode_metadata": {
            "query": "", "query_index": 1, "status": "Skipped",
            "error": None, "search_id": None,
        },
    }
    # Exercise the recipe entry point with a skipped query (no credentials).
    frame = wrangles.DataFrame({"query": [""], "ID": [1]})
    result = wrangles.recipe.run(
        {"wrangles": [{"search.ai_mode": {
            "queries": "query", "id": "ID", "output": ["body", "metadata"],
        }}]}, dataframe=frame,
    )
    assert result["body"].tolist() == [""]
    assert result["metadata"].iloc[0]["status"] == "Skipped"
    assert import_module("wrangles._text_cleanup").map_markdown_prose is import_module(
        "wrangles.search._content"
    ).map_markdown_prose
    print(f"Verified installed search package and legacy imports from {installed}")


if __name__ == "__main__":
    main()
