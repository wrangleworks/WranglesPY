"""
Checks access to every model in tests/model_registry.py before the
credentialed test suite runs.

Run this as step one of a live/credentialed test session (it needs
WRANGLES_USER/WRANGLES_PASSWORD or another valid auth path - do not run it
under pytest-local.ini's offline config, which deliberately has no
credentials). Exits non-zero if any model is missing or inaccessible, so a
broken model fixture fails fast with a clear report instead of surfacing as
scattered individual test failures deep into a run.

    python scripts/check_model_registry_access.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wrangles import data as _data
from tests.model_registry import MODEL_REGISTRY


def check_all(registry: dict) -> tuple[list, list, list]:
    """
    Check access to every model in the registry.

    :return: (accessible, not_found, denied_or_errored) - each a list of
        (model_id, note, detail) tuples.
    """
    accessible = []
    not_found = []
    denied_or_errored = []

    for model_id, note in sorted(registry.items()):
        try:
            _data.model(model_id)
            accessible.append((model_id, note, None))
        except _data.ModelNotFoundError as e:
            not_found.append((model_id, note, str(e)))
        except Exception as e:
            denied_or_errored.append((model_id, note, str(e)))

    return accessible, not_found, denied_or_errored


def main() -> int:
    print(f"Checking access to {len(MODEL_REGISTRY)} registered models...\n")

    accessible, not_found, denied_or_errored = check_all(MODEL_REGISTRY)

    print(f"Accessible: {len(accessible)}/{len(MODEL_REGISTRY)}")

    if not_found:
        print(f"\nNOT FOUND ({len(not_found)}) - model no longer exists, "
              "tests referencing it need a replacement model or removal:")
        for model_id, note, detail in not_found:
            print(f"  - {model_id}  ({note})\n    {detail}")

    if denied_or_errored:
        print(f"\nACCESS DENIED / ERROR ({len(denied_or_errored)}) - the "
              "test-runner account needs access granted, or this ID is "
              "stale/mocked-only and should be removed from the registry:")
        for model_id, note, detail in denied_or_errored:
            print(f"  - {model_id}  ({note})\n    {detail}")

    if not_found or denied_or_errored:
        print(
            "\nFix these before running the credentialed test suite - each "
            "one will otherwise surface as a confusing failure inside "
            "whichever test happens to hit it first, instead of here."
        )
        return 1

    print("\nAll registered models are accessible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
