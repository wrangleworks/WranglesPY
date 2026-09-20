"""Compare deterministic AI Mode parsing with a downstream extract.ai step.

In VS Code, select this repository's .venv interpreter and Run Python File.
Set SERPAPI_API_KEY and OPENAI_API_KEY in the environment or ignored .env file
(loading .env requires python-dotenv). Each successful search is extracted once.
Set REPLAY_FILE to a saved JSON snapshot to retry extraction without searching.
"""

from datetime import datetime
import json
from pathlib import Path
from pprint import pprint
import re

import pandas as pd


# ---- Editable run defaults -------------------------------------------------
REPOSITORY = Path(__file__).resolve().parent
RECIPE_FILE = REPOSITORY / "search_ai_mode_test.recipe"
REPLAY_FILE = None  # A prior JSON snapshot; relative paths start at REPOSITORY.
OUTPUT_DIRECTORY = REPOSITORY / ".data"
WRITE_OUTPUTS = True  # Unique Excel/JSON filenames preserve earlier trial evidence.
PRETTY_PRINT = False
NROWS = None  # None = all input rows; 1 = a one-row trial.
THREADS = 1
EXTRACT_ENABLED = True
EXTRACT_MODEL = None  # None uses the configured extract.ai default.
EXTRACT_THREADS = 1
EXTRACT_TIMEOUT = 60
EXTRACT_RETRIES = 1
DESCRIPTION_HEADING = "Product Description"
SPECIFICATIONS_HEADING = "Technical Specifications"
PRICING_HEADING = "Pricing & Sources"
AI_MODE_QUERY = [
    {"base_query": "Provide the following product information:"},
    {DESCRIPTION_HEADING: "1-3 sentences including the product name and key features."},
    {SPECIFICATIONS_HEADING: "List confirmed technical specifications."},
    {PRICING_HEADING: "List suppliers and available pricing with source links."},
    {"query_suffix": (
        "Use the exact information labels as headings. "
        "Include only the requested sections; no follow-up questions."
    )},
]

# User-supplied examples, 2026-09-17; JSON-style records, without generated data.
INPUT_ROWS = [
    {
        "ID": 1,
        "Description": (
            "INA NATV6-PP-A YOKE TYPE TRACK ROLLERS NATV..-PP FULL COMPLEMENT NEEDL"
        ),
        "Mfr": "INA",
        "MPN": "NATV6-PP-A",
        "part_codes": ["NATV6-PP-A", "NATV6"],
        "query": "INA NATV6-PP-A YOKE TYPE TRACK ROLLERS NATV..-PP FULL COMPLEMENT NEEDL 40OZ",
    },
    {
        "ID": 2,
        "Description": "RENOLD SYNERGY GY08B2S26I DUPLEX CONN LINK",
        "Mfr": "RENOLD",
        "MPN": "GY08B2S26I",
        "part_codes": ["GY08B2S26I"],
        "query": "RENOLD SYNERGY GY08B2S26I DUPLEX CONN LINK",
    },
]
# ---------------------------------------------------------------------------


def clean_ai_mode_links(df, input, output=None):
    """Remove Google's viewer instruction from link labels for this trial."""
    from wrangles._text_cleanup import map_markdown_prose

    viewer_label = re.compile(
        r'(\[(?:\\.|[^\]\\\n])*?)\s*'
        r'Go to product viewer dialog for this item\.(?=\]\()'
    )

    def clean(value):
        if not isinstance(value, str):
            return value
        return map_markdown_prose(
            value, lambda prose: viewer_label.sub(lambda match: match[1].rstrip(), prose)
        )

    df[output or input] = df[input].map(clean)
    return df


def prepare_search_evidence(df, input, output, enabled=True):
    """Adapt the complete result to the shared answer-content boundary."""
    from wrangles._search_ai_extraction import prepare_evidence

    df[output] = df[input].map(prepare_evidence)
    df["__search_ai_ready"] = [
        bool(enabled and answer.get("meta_data", {}).get("status") == "Success"
             and any(captured["content"].values()))
        for answer, captured in zip(df[input], df[output])
    ]
    # Keep this column present even when all searches failed or extraction is off.
    df["search_ai_extracted"] = None
    return df


def format_search_extraction(df, input, evidence, output, diagnostics):
    """Build the trial view; source URLs always come from the captured catalog."""
    from wrangles._search_ai_extraction import format_product_result

    results, metadata = [], []
    for extracted, captured, ready in zip(df[input], df[evidence], df["__search_ai_ready"]):
        if ready:
            result, diagnostic = format_product_result(
                extracted, captured, description=DESCRIPTION_HEADING,
                specifications=SPECIFICATIONS_HEADING, pricing=PRICING_HEADING,
            )
        else:
            # Keep the display schema stable for skipped rows and all-empty runs.
            result = {DESCRIPTION_HEADING: "", SPECIFICATIONS_HEADING: [], PRICING_HEADING: [], "references": []}
            diagnostic = {"status": "skipped", "warnings": [], "source_matches": []}
        results.append(result)
        metadata.append(diagnostic)
    df[output], df[diagnostics] = results, metadata
    return df


def main():
    if NROWS is not None and NROWS < 1:
        raise ValueError("NROWS must be None for all rows, or a positive integer.")

    # Existing environment values take precedence; never put a key in the recipe.
    try:
        from dotenv import load_dotenv
    except ImportError:
        pass
    else:
        load_dotenv(REPOSITORY / ".env", override=False)

    import wrangles

    if REPLAY_FILE is None:
        input_df = pd.DataFrame(INPUT_ROWS)
    else:
        replay_path = Path(REPLAY_FILE)
        if not replay_path.is_absolute():
            replay_path = REPOSITORY / replay_path
        input_df = pd.DataFrame(json.loads(replay_path.read_text(encoding="utf-8")))
        required = {"ID", "Description", "Mfr", "MPN", "ai_mode_result", "ai_mode_result_complete", "ai_mode_markdown"}
        if missing := required - set(input_df.columns):
            raise ValueError(f"Replay snapshot is missing columns: {', '.join(sorted(missing))}")
    if NROWS is not None:
        input_df = input_df.head(NROWS)

    output_directory = Path(OUTPUT_DIRECTORY)
    if not output_directory.is_absolute():
        output_directory = REPOSITORY / output_directory
    output_stem = output_directory / f"ai_mode_results_{datetime.now():%y%m%d_%H%M%S_%f}"
    if WRITE_OUTPUTS:
        output_directory.mkdir(parents=True, exist_ok=True)
        print(f"Trial Excel: {output_stem.with_suffix('.xlsx')}")
        print(f"Trial JSON:  {output_stem.with_suffix('.json')}")

    variables = {
        "AI_MODE_QUERY": AI_MODE_QUERY,
        "THREADS": THREADS,
        "RUN_SEARCH": REPLAY_FILE is None,
        "WRITE_OUTPUTS": WRITE_OUTPUTS,
        "XLSX_OUTPUT_FILE": str(output_stem.with_suffix(".xlsx")),
        "JSON_OUTPUT_FILE": str(output_stem.with_suffix(".json")),
        "EXTRACT_ENABLED": EXTRACT_ENABLED,
        "EXTRACT_MODEL": EXTRACT_MODEL,
        "EXTRACT_THREADS": EXTRACT_THREADS,
        "EXTRACT_TIMEOUT": EXTRACT_TIMEOUT,
        "EXTRACT_RETRIES": EXTRACT_RETRIES,
        "DISPLAY_RESULT": "ai_mode_result_structured" if EXTRACT_ENABLED else "ai_mode_result",
    }
    if not EXTRACT_ENABLED:
        # Recipe variables resolve before step conditions. A skipped extraction
        # needs no credential; this placeholder does not change the environment.
        variables["OPENAI_API_KEY"] = ""

    results_df = wrangles.recipe.run(
        str(RECIPE_FILE),
        dataframe=input_df,
        functions=[clean_ai_mode_links, prepare_search_evidence, format_search_extraction],
        variables=variables,
    )

    if PRETTY_PRINT:
        pprint(results_df.to_dict(orient="records"), sort_dicts=False, width=120)
    return results_df


if __name__ == "__main__":
    results_df = main()  # Also available for inspection in the VS Code debugger.
