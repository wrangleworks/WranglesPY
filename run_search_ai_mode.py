"""Retrieve AI Mode Markdown, clean it, and structure it with extract.ai.

In VS Code, select this repository's .venv interpreter and Run Python File.
Set SERPAPI_API_KEY and OPENAI_API_KEY in the environment or ignored .env file
(loading .env requires python-dotenv). Each successful search is extracted once.
Set REPLAY_FILE to a saved JSON snapshot to retry extraction without searching.
"""

from datetime import datetime
import json
from pathlib import Path
from pprint import pprint

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
LOCATION = None  # Example: "Austin, Texas, United States"; None omits the override.
COUNTRY = None  # SerpAPI gl, e.g. "us" or "uk".
LANGUAGE = None  # SerpAPI hl, e.g. "en".
EXTRACT_ENABLED = True
EXTRACT_MODEL = None  # None uses the configured extract.ai default.
EXTRACT_REASONING = {"effort": "low"}  # Source/offer matching benefits from reasoning.
EXTRACT_THREADS = 1
EXTRACT_TIMEOUT = 60
EXTRACT_RETRIES = 1
DESCRIPTION_HEADING = "Product Description"
SPECIFICATIONS_HEADING = "Specifications"
PRICING_HEADING = "Pricing"
AI_MODE_QUERY = [
    {"base_query": "Summarize information in 3 sections:"},
    {DESCRIPTION_HEADING: ""},
    {SPECIFICATIONS_HEADING: "as name value pairs"},
    {PRICING_HEADING: "including the supplier name and source link"},
    {"query_suffix": "Summarize the information you found (e.g. matched the part number, "
                     "5 sources, 3 prices), but do not ask follow-on questions."},
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


def capture_search_response(df, input, metadata, prefix):
    """Save raw provider Markdown outside Excel, then remove it from metadata."""
    for index, value in enumerate(df[metadata], 1):
        raw = value.pop("raw_response", None)
        if isinstance(raw, str) and raw:
            path = Path(f"{prefix}_row{index:03d}.md")
            path.write_text(raw, encoding="utf-8")
            value["raw_response_file"] = str(path)
    return df


def prepare_search_extraction(df, input, metadata, enabled=True):
    """Only successful, nonempty Markdown answers enter the model call."""
    df["__search_ai_ready"] = [
        bool(enabled and meta.get("status") == "Success" and isinstance(body, str) and body.strip())
        for body, meta in zip(df[input], df[metadata])
    ]
    # Stable output columns also cover skipped rows and reset replayed results.
    for column, default in {
        "Product Description": "", "Match Confidence": "Uncertain",
        "Specifications": [], "references": [], "Pricing": [],
    }.items():
        df[column] = [default.copy() if isinstance(default, list) else default for _ in range(len(df))]
    return df


def validate_search_sources(df, input, references, pricing, diagnostics):
    """Check source URLs and IDs in place; leave the other AI outputs untouched."""
    from wrangles._search_ai_extraction import validate_sources

    sources, offers, metadata = [], [], []
    for refs, prices, body, ready in zip(df[references], df[pricing], df[input], df["__search_ai_ready"]):
        if ready:
            refs, prices, diagnostic = validate_sources(refs, prices, body)
        else:
            diagnostic = {"status": "skipped", "warnings": [], "rejected_references": []}
        sources.append(refs)
        offers.append(prices)
        metadata.append(diagnostic)
    df[references], df[pricing], df[diagnostics] = sources, offers, metadata
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
        input_df.drop(columns=["search_ai_extracted", "ai_mode_result_structured"], errors="ignore", inplace=True)
        required = {"ID", "Description", "Mfr", "MPN", "ai_mode_results", "ai_mode_metadata"}
        if missing := required - set(input_df.columns):
            raise ValueError(f"Replay snapshot is missing columns: {', '.join(sorted(missing))}")
        if "search_query" not in input_df:
            input_df["search_query"] = [metadata.get("query", "") for metadata in input_df["ai_mode_metadata"]]
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
        "LOCATION": LOCATION, "COUNTRY": COUNTRY, "LANGUAGE": LANGUAGE,
        "RAW_OUTPUT_PREFIX": str(output_stem),
        "RUN_SEARCH": REPLAY_FILE is None,
        "WRITE_OUTPUTS": WRITE_OUTPUTS,
        "XLSX_OUTPUT_FILE": str(output_stem.with_suffix(".xlsx")),
        "JSON_OUTPUT_FILE": str(output_stem.with_suffix(".json")),
        "EXTRACT_ENABLED": EXTRACT_ENABLED,
        "EXTRACT_MODEL": EXTRACT_MODEL,
        "EXTRACT_REASONING": EXTRACT_REASONING,
        "EXTRACT_THREADS": EXTRACT_THREADS,
        "EXTRACT_TIMEOUT": EXTRACT_TIMEOUT,
        "EXTRACT_RETRIES": EXTRACT_RETRIES,
    }
    if not EXTRACT_ENABLED:
        # Recipe variables resolve before step conditions. A skipped extraction
        # needs no credential; this placeholder does not change the environment.
        variables["OPENAI_API_KEY"] = ""

    results_df = wrangles.recipe.run(
        str(RECIPE_FILE),
        dataframe=input_df,
        functions=[capture_search_response, prepare_search_extraction, validate_search_sources],
        variables=variables,
    )

    if PRETTY_PRINT:
        pprint(results_df.to_dict(orient="records"), sort_dicts=False, width=120)
    return results_df


if __name__ == "__main__":
    results_df = main()  # Also available for inspection in the VS Code debugger.
