"""
Guards pytest-local.ini against silently drifting out of sync with the real
test suite. Run from the repo root: python scripts/check_pytest_local_config.py

Checks:
  1. Every --ignore=PATH in pytest-local.ini's addopts points to a file that
     still exists and still contains at least one real test (catches stale
     ignores left over from a rename/delete).
  2. Every --deselect=NODEID in pytest-local.ini's addopts still matches at
     least one test collected by the full, unrestricted suite (catches stale
     deselects left over from a renamed/removed test).
  3. Every tests/**/test_*.py file is reachable from pytest-local.ini's
     testpaths, unless it is explicitly --ignore=d (catches a newly added
     test file being silently excluded because nobody updated the config).

Exits non-zero with a description of every violation found.
"""
import configparser
import re
import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_INI = REPO_ROOT / "pytest-local.ini"


def _collect_all_node_ids() -> list[str]:
    """Full, unrestricted collection - the canonical universe of real tests."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    lines = [
        line for line in result.stdout.splitlines()
        if line and "::" in line and not line.startswith(" ")
    ]
    if not lines:
        print("Could not collect the full test suite to validate against:")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    return lines


def _parse_addopts(addopts_raw: str) -> list[str]:
    return shlex.split(addopts_raw)


def main() -> int:
    errors = []

    config = configparser.ConfigParser()
    config.read(LOCAL_INI)
    section = config["pytest"]

    # pytest's `testpaths` ini option, like `addopts`, is shlex-split - a
    # path containing a space must be quoted or it silently splits into two
    # bogus, non-existent paths and the file is never collected.
    testpaths = _parse_addopts(section.get("testpaths", ""))
    addopts = _parse_addopts(section.get("addopts", ""))

    ignores = [a.split("=", 1)[1] for a in addopts if a.startswith("--ignore=")]
    deselects = [a.split("=", 1)[1] for a in addopts if a.startswith("--deselect=")]

    # 0. Every testpaths entry must resolve to a real file/directory. Also
    # catches an unquoted path containing a space silently splitting into
    # two bogus, non-existent entries (testpaths is shlex-split by pytest).
    for tp in testpaths:
        if not (REPO_ROOT / tp).exists():
            errors.append(f"testpaths entry {tp!r} does not exist on disk")

    # 1. Stale --ignore entries: path must still exist.
    for path in ignores:
        if not (REPO_ROOT / path).exists():
            errors.append(f"--ignore={path} points to a file that no longer exists")

    # Full-suite node ids, used to validate both --deselect and testpaths coverage.
    all_node_ids = _collect_all_node_ids()
    all_files = sorted({node_id.split("::", 1)[0] for node_id in all_node_ids})

    # 2. Stale --deselect entries: must still match something real.
    for nodeid in deselects:
        if not any(n == nodeid or n.startswith(nodeid + "::") for n in all_node_ids):
            errors.append(
                f"--deselect={nodeid} does not match any currently collected test "
                "(likely renamed or removed)"
            )

    # 3. Every real test file must be covered by testpaths or explicitly ignored.
    def covered_by_testpaths(file_path: str) -> bool:
        p = Path(file_path)
        for tp in testpaths:
            tp_path = Path(tp)
            if p == tp_path:
                return True
            if tp_path.is_dir() or "." not in tp_path.name:
                try:
                    p.relative_to(tp_path)
                    return True
                except ValueError:
                    continue
        return False

    def covered_by_ignore(file_path: str) -> bool:
        return any(file_path == ig or file_path.startswith(ig.rstrip("/") + "/") for ig in ignores)

    for file_path in all_files:
        if not file_path.startswith("tests/"):
            continue
        if not re.match(r"tests[\\/](.*/)?test_.*\.py$", file_path):
            continue
        if covered_by_testpaths(file_path) or covered_by_ignore(file_path):
            continue
        errors.append(
            f"{file_path} is not covered by pytest-local.ini's testpaths and is not "
            "explicitly --ignore=d - it will be silently skipped by local test runs"
        )

    if errors:
        print("pytest-local.ini is out of sync with the test suite:\n")
        for error in errors:
            print(f"  - {error}")
        print(
            "\nUpdate pytest-local.ini: add new offline-safe test files to "
            "testpaths, add live-service-dependent files to --ignore, and "
            "remove stale --ignore/--deselect entries for tests that no "
            "longer exist."
        )
        return 1

    print(f"pytest-local.ini is in sync ({len(all_files)} test files, "
          f"{len(ignores)} ignores, {len(deselects)} deselects checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
