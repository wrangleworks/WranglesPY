"""
Recipe-level wiring tests for extract.dimensions.

Fully offline: the plain wrangles.extract.dimensions() function is mocked,
so these tests exercise only the recipe wrangle's input/output column
handling - not the NOOA integration itself (see
tests/test_nooa_extract_dimensions.py for that).
"""
import pandas as pd
import pytest
import wrangles
from unittest.mock import patch


class TestExtractDimensions:
    @patch("wrangles.recipe_wrangles.extract._extract.dimensions")
    def test_single_input_column(self, dimensions):
        dimensions.return_value = [
            {"measurements": []},
            {"measurements": [{"kind": "length", "value": 6, "unit": "m", "source": "6m cable"}]},
        ]
        data = pd.DataFrame({"description": ["wrench 25mm", "6m cable"]})
        recipe = """
        wrangles:
          - extract.dimensions:
              input: description
              output: Dimensions
              model: gpt-5-mini
              api_key: test-key
        """

        result = wrangles.recipe.run(recipe, dataframe=data)

        # Single input column -> raw column values passed through, not records
        dimensions.assert_called_once()
        assert dimensions.call_args.args[0] == ["wrench 25mm", "6m cable"]
        assert result["Dimensions"].tolist() == [
            {"measurements": []},
            {"measurements": [{"kind": "length", "value": 6, "unit": "m", "source": "6m cable"}]},
        ]

    @patch("wrangles.recipe_wrangles.extract._extract.dimensions")
    def test_multiple_input_columns_combined_as_records(self, dimensions):
        dimensions.return_value = [{"measurements": []}]
        data = pd.DataFrame({
            "Description": ["Bottle"],
            "Size": ["750 mL"],
        })
        recipe = """
        wrangles:
          - extract.dimensions:
              input:
                - Description
                - Size
              output: Dimensions
              api_key: test-key
        """

        wrangles.recipe.run(recipe, dataframe=data)

        rows = dimensions.call_args.args[0]
        assert rows == [{"Description": "Bottle", "Size": "750 mL"}]

    @patch("wrangles.recipe_wrangles.extract._extract.dimensions")
    def test_omitted_input_uses_all_columns(self, dimensions):
        dimensions.return_value = [{"measurements": []}]
        data = pd.DataFrame({"Description": ["Bottle"], "Packaging": ["Boxed"]})
        recipe = """
        wrangles:
          - extract.dimensions:
              output: Dimensions
              api_key: test-key
        """

        wrangles.recipe.run(recipe, dataframe=data)

        rows = dimensions.call_args.args[0]
        assert rows == [{"Description": "Bottle", "Packaging": "Boxed"}]

    @patch("wrangles.recipe_wrangles.extract._extract.dimensions")
    def test_model_api_key_and_threads_forwarded(self, dimensions):
        dimensions.return_value = [{"measurements": []}]
        data = pd.DataFrame({"description": ["wrench 25mm"]})
        recipe = """
        wrangles:
          - extract.dimensions:
              input: description
              output: Dimensions
              model: gpt-5.4-mini
              api_key: ${API_KEY}
              threads: 4
        """

        wrangles.recipe.run(recipe, dataframe=data, variables={"API_KEY": "secret"})

        kwargs = dimensions.call_args.kwargs
        assert kwargs["model"] == "gpt-5.4-mini"
        assert kwargs["api_key"] == "secret"
        assert kwargs["threads"] == 4

    def test_missing_output_is_rejected(self):
        data = pd.DataFrame({"description": ["wrench 25mm"]})
        recipe = """
        wrangles:
          - extract.dimensions:
              input: description
              api_key: test-key
        """
        with pytest.raises(Exception):
            wrangles.recipe.run(recipe, dataframe=data)
