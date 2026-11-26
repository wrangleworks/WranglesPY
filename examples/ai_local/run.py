"""Explicit live OpenAI BYOK smoke test: python examples/ai_local/run.py."""

import json
from pathlib import Path

import pandas as pd
import wrangles


def main():
    package = str(Path(__file__).resolve().parent)
    source = pd.DataFrame({"Description": ["PUMP seal", "valve kit", "pump SEAL"],
                           "Unrelated": [10, 20, 30]}, index=[9, 4, 2])
    for entry in ("agent", "skill"):
        params = {"input": "Description", "output": {
            "Name": {"type": "string"}, "Count": {"type": "integer"}},
            "skill": "normalize-products", "skill_package": package, "model": "gpt-5-mini"}
        if entry == "agent":
            params["instructions"] = "Apply normalize-products to the complete dataframe."
        result = wrangles.recipe.run({"wrangles": [{"ai." + entry: params}]}, dataframe=source)
        assert result["Name"].tolist() == ["Pump Seal", "Valve Kit", "Pump Seal"]
        assert result["Count"].tolist() == [2, 1, 2]
        pd.testing.assert_frame_equal(result[source.columns], source)
        print(entry)
        print(result.to_string())
        print(json.dumps(result.attrs["wrangles_ai_runtime"], indent=2))


if __name__ == "__main__":
    main()
