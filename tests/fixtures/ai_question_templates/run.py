"""Run the small category-scoring fixture using credentials from the environment."""

import argparse
import json
from pathlib import Path
from pprint import pprint
import sys


# User-editable run defaults. Paths are anchored to this file, not the terminal.
FIXTURE_DIR = Path(__file__).resolve().parent
REPOSITORY = FIXTURE_DIR.parents[2]
INPUT_PATH = FIXTURE_DIR / "products.json"
RECIPE_PATH = FIXTURE_DIR / "recipe.wrgl.yml"
NROWS = 2  # A bounded trial. Use None to include every record in the input file.
MODEL = None  # None uses the configured Typesafe model.
CACHE = False
THREADS = 1
TIMEOUT = 30
RETRIES = 0
FULL_RESULTS = False
DISPLAY_COLUMNS = [
    "Description",
    "category_1_value", "category_1_score", "category_1_confidence",
    "category_2_value", "category_2_score", "category_2_confidence",
    "category_3_value", "category_3_score", "category_3_confidence",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--recipe", type=Path, default=RECIPE_PATH)
    parser.add_argument("--nrows", type=int, default=NROWS,
                        help="Positive trial limit; use --all-rows for every record.")
    parser.add_argument("--all-rows", action="store_true")
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--cache", action=argparse.BooleanOptionalAction, default=CACHE)
    parser.add_argument("--threads", type=int, default=THREADS)
    parser.add_argument("--timeout", type=float, default=TIMEOUT)
    parser.add_argument("--retries", type=int, default=RETRIES)
    parser.add_argument("--full-results", action="store_true", default=FULL_RESULTS)
    args = parser.parse_args()
    if args.nrows is not None and args.nrows <= 0:
        parser.error("--nrows must be positive; use --all-rows for the complete input")
    if args.threads < 1 or args.timeout <= 0 or args.retries < 0:
        parser.error("threads and timeout must be positive; retries cannot be negative")

    # Run this checkout's implementation even if a released wheel is installed.
    sys.path.insert(0, str(REPOSITORY))
    import pandas as pd
    import yaml
    import wrangles

    records = json.loads(args.input.read_text(encoding="utf-8"))
    limit = None if args.all_rows else args.nrows
    records = records[:limit]
    recipe = yaml.safe_load(args.recipe.read_text(encoding="utf-8"))
    settings = recipe["wrangles"][0]["ai.score"]
    settings.update(cache=args.cache, threads=args.threads,
                    timeout=args.timeout, retries=args.retries)
    if args.model is not None:
        settings["model"] = args.model

    print(f"Scoring {len(records)} synthetic/input records using {args.recipe.name}.")
    result = wrangles.recipe.run(
        yaml.safe_dump(recipe, sort_keys=False),
        dataframe=pd.DataFrame(records),
    )
    if args.full_results:
        pprint(result.to_dict("records"), sort_dicts=False)
    else:
        print(result[DISPLAY_COLUMNS].to_string(index=False))


if __name__ == "__main__":
    main()
