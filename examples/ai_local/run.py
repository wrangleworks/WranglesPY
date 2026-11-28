"""Explicit live OpenAI BYOK smoke test: python examples/ai_local/run.py."""

import argparse
import json
from pathlib import Path
from time import perf_counter

import pandas as pd
import wrangles


# User-editable defaults for this three-row live example.
PACKAGE = Path(__file__).resolve().parent
MODEL = "gpt-5-mini"
TIMEOUT = 120
STEPS = ("ai.agent", "ai.skill")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", choices=STEPS)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--timeout", type=float, default=TIMEOUT)
    args = parser.parse_args()
    source = pd.DataFrame({"Description": ["PUMP seal", "valve kit", "pump SEAL"],
                           "Unrelated": [10, 20, 30]}, index=[9, 4, 2])
    for entry in (args.step,) if args.step else STEPS:
        params = {"input": "Description", "output": {
            "Name": {"type": "string"}, "Count": {"type": "integer"}},
            "skill_package": str(PACKAGE), "model": args.model, "timeout": args.timeout}
        if entry == "ai.agent":
            params.update(instructions="Apply our product naming Skill.", skills=[{"model_id": "normalize-products"}])
        else:
            params["skill"] = "normalize-products"
        started = perf_counter()
        result = wrangles.recipe.run({"wrangles": [{entry: params}]}, dataframe=source)
        assert result["Name"].tolist() == ["Pump Seal", "Valve Kit", "Pump Seal"]
        assert result["Count"].tolist() == [2, 1, 2]
        pd.testing.assert_frame_equal(result[source.columns], source)
        report = result.attrs["wrangles_ai_runtime"]
        assert report["tools"].index("convert_case") < report["tools"].index("count_values")
        assert report["tools"][-1] == "submit_results"
        assert set(report["committed_columns"]) == {"Name", "Count"}
        assert report["skill"]["name"] == "normalize-products"
        print(f"{entry} passed in {perf_counter() - started:.2f}s")
        print(result.to_string())
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
