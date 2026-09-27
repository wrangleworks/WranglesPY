"""Generate public extraction and embedding metadata from packaged configuration."""
import argparse
import ast
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = Path(__file__).resolve().with_name("ai-models-v1.json")
sys.path.insert(0, str(REPOSITORY_ROOT))

from wrangles.ai_catalog import extract_ai_catalog


def package_version_from_setup(path: Path) -> str:
    """Read setup(version='...') statically; never execute packaging code."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "setup"):
            for keyword in node.keywords:
                if keyword.arg == "version":
                    if (isinstance(keyword.value, ast.Constant)
                            and isinstance(keyword.value.value, str)
                            and keyword.value.value.strip()):
                        return keyword.value.value.strip()
                    raise ValueError("setup.py version must be a literal non-empty string.")
    raise ValueError("setup.py must contain setup(version='...').")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Output JSON path (default: schema/ai-models-v1.json).")
    parser.add_argument("--package-version",
                        help="Published package/RC version; otherwise read setup.py statically.")
    args = parser.parse_args(argv)
    version = args.package_version
    if version is None:
        version = package_version_from_setup(REPOSITORY_ROOT / "setup.py")
    catalog = extract_ai_catalog(version)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8", newline="\n")
    print(f"Generated AI catalog: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
