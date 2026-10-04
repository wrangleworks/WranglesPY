"""Shared fixtures for integration tests."""
from copy import deepcopy

import pytest
from wrangles import data


@pytest.fixture
def saved_extract_schema_model(monkeypatch):
    """Fetch the real saved schema but select a compatible model locally.

    These tests exercise saved definitions and output shapes, not the legacy
    model choice stored in shared test data. Do not write back to that data.
    """
    fetch_model_content = data.model_content

    def model_content(*args, **kwargs):
        content = deepcopy(fetch_model_content(*args, **kwargs))
        settings = content.setdefault("Settings", {})
        # Remove legacy aliases so an old model cannot win during normalization.
        for key in list(settings):
            normalized = "".join(char.lower() for char in key if char.isalnum())
            if normalized in {"gptmodel", "aimodel", "model"}:
                del settings[key]
        settings["GPTModel"] = "gpt-5.4-mini"
        return content

    monkeypatch.setattr(data, "model_content", model_content)
