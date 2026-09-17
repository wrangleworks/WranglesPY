"""Run the two product examples through search.ai_mode and pretty-print them.

In VS Code, select this repository's .venv interpreter and Run Python File.
Set SERPAPI_API_KEY in the environment or the ignored repository .env file
(loading .env requires python-dotenv). Each input row makes one search.
"""

from pathlib import Path
from pprint import pprint
import re

import pandas as pd


# ---- Editable run defaults -------------------------------------------------
REPOSITORY = Path(__file__).resolve().parent
RECIPE_FILE = REPOSITORY / "search_ai_mode_test.recipe"
NROWS = None  # None = all input rows; 1 = a one-row trial.
THREADS = 1
COUNTRY = "us"
LANGUAGE = "en"
AI_MODE_QUERY = [
    {"base_query": "Provide the following product information:"},
    {"Product Description": "1-3 sentences including the product name and key features."},
    {"Technical Specifications": "List confirmed technical specifications."},
    {"Sources & Pricing": "List suppliers and available pricing with source links."},
    {"query_suffix": (
        "Use the requested headings exactly as written. "
        "Include only the requested sections, and do not include follow-up questions."
    )},
]

# User-supplied examples, 2026-09-17; JSON-style records, without generated data.
INPUT_ROWS = [
    {
        "ID": 1,
        "Description": (
            "INA NATV6-PP-A YOKE TYPE TRACK ROLLERS NATV..-PP FULL COMPLEMENT NEEDL\n"
            "40OZ"
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

    input_df = pd.DataFrame(INPUT_ROWS)
    if NROWS is not None:
        input_df = input_df.head(NROWS)

    results_df = wrangles.recipe.run(
        str(RECIPE_FILE),
        dataframe=input_df,
        functions=[clean_ai_mode_links],
        variables={
            "AI_MODE_QUERY": AI_MODE_QUERY,
            "THREADS": THREADS,
            "COUNTRY": COUNTRY,
            "LANGUAGE": LANGUAGE,
        },
    )

    pprint(results_df.to_dict(orient="records"), sort_dicts=False, width=120)
    return results_df


if __name__ == "__main__":
    results_df = main()  # Also available for inspection in the VS Code debugger.
