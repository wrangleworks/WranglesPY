import copy
import concurrent.futures
import json
import threading

import pandas as pd
import pytest
import requests

from wrangles import ai_cache, ai_config, config, extract, recipe


@pytest.fixture(autouse=True)
def _isolated_metadata_environment(monkeypatch):
    monkeypatch.delenv("WRANGLES_USER", raising=False)
    monkeypatch.delenv("WRANGLES_AI_CONFIG", raising=False)
    monkeypatch.setattr(config, "api_user", None)
    context_token = recipe._RECIPE_RUN_CONTEXT.set(None)
    ai_cache.clear()
    ai_config.clear_cache()

    def unexpected_network(*args, **kwargs):
        pytest.fail("Metadata attribution must not make an unexpected network or authentication call")

    monkeypatch.setattr(requests.sessions.Session, "request", unexpected_network)
    monkeypatch.setattr(recipe._auth, "get_access_token", unexpected_network)
    yield
    ai_cache.clear()
    ai_config.clear_cache()
    recipe._RECIPE_RUN_CONTEXT.reset(context_token)


@pytest.fixture
def calls(monkeypatch):
    captured = []

    def call_structured(data, api_key, payload, *args):
        captured.append({"data": copy.deepcopy(data), "payload": copy.deepcopy(payload)})
        return {"length": "25mm"}

    monkeypatch.setattr(extract._openai_responses, "call_structured", call_structured)
    return captured


def _step(**settings):
    return {"extract.ai": {
        "input": "Description",
        "api_key": "test-openai-key",
        "output": {"length": {"type": "string"}},
        "cache": False,
        **settings,
    }}


def _run_recipe(source=None, variables=None, functions=None):
    return recipe.run(
        source if source is not None else {"wrangles": [_step()]},
        dataframe=pd.DataFrame({"Description": ["wrench 25mm"]}),
        variables={"applied_permission_group": None, **(variables or {})},
        functions=functions,
    )


def test_direct_extract_uses_configured_wrangles_username(monkeypatch, calls):
    monkeypatch.setattr(config, "api_user", "local-user@example.test")

    result = extract.ai(
        "wrench 25mm", "test-openai-key", output={"length": {"type": "string"}}
    )

    assert result == {"length": "25mm"}
    assert calls[0]["payload"]["metadata"] == {"wrangles_user": "local-user@example.test"}


def test_xl_recipe_variables_supply_name_and_user_without_other_variables(calls):
    result = _run_recipe(variables={
        "recipe_name": "Supplier classification",
        "user_email": "xl-user@example.test",
        "OPENAI_API_KEY": "unrelated-secret-placeholder",
        "WRANGLES_PASSWORD": "unrelated-password-placeholder",
        "customer_notes": "not diagnostic metadata",
    })

    assert result["length"].tolist() == ["25mm"]
    assert calls[0]["payload"]["metadata"] == {
        "recipe_name": "Supplier classification",
        "wrangles_user": "xl-user@example.test",
    }


def test_wrangles_user_variable_takes_precedence_over_xl_email_and_config(monkeypatch, calls):
    monkeypatch.setattr(config, "api_user", "configured@example.test")
    _run_recipe(variables={
        "WRANGLES_USER": "runner@example.test",
        "user_email": "xl-user@example.test",
    })

    assert calls[0]["payload"]["metadata"] == {"wrangles_user": "runner@example.test"}


@pytest.mark.parametrize("metadata", [
    {"recipe_name": "Explicit name", "wrangles_user": "explicit@example.test", "job": "trial"},
    {},
])
def test_explicit_metadata_overrides_or_disables_automatic_labels(calls, metadata):
    original = copy.deepcopy(metadata)
    _run_recipe(
        {"wrangles": [_step(metadata=metadata)]},
        variables={"recipe_name": "Automatic name", "WRANGLES_USER": "automatic@example.test"},
    )

    assert calls[0]["payload"]["metadata"] == original
    assert metadata == original


@pytest.mark.parametrize("user_value", [None, "", "   ", "Missing", 123])
def test_unavailable_attribution_is_omitted(calls, user_value):
    _run_recipe(variables={"WRANGLES_USER": user_value, "user_email": user_value})

    assert "metadata" not in calls[0]["payload"]


@pytest.mark.parametrize("explicit_count", [15, 16])
def test_automatic_labels_respect_metadata_capacity(calls, explicit_count):
    explicit = {f"label_{index}": "value" for index in range(explicit_count)}
    _run_recipe(
        {"wrangles": [_step(metadata=explicit)]},
        variables={"recipe_name": "Recipe name", "WRANGLES_USER": "user@example.test"},
    )

    labels = calls[0]["payload"]["metadata"]
    assert len(labels) == 16
    assert all(labels[key] == value for key, value in explicit.items())
    assert len(explicit) == explicit_count
    if explicit_count == 15:
        assert labels["recipe_name"] == "Recipe name"
    assert "wrangles_user" not in labels


def test_automatic_labels_are_bounded_without_changing_source_variables(calls):
    variables = {"recipe_name": "r" * 600, "WRANGLES_USER": "u" * 600}
    _run_recipe(variables=variables)

    assert calls[0]["payload"]["metadata"] == {"recipe_name": "r" * 512, "wrangles_user": "u" * 512}
    assert variables == {"recipe_name": "r" * 600, "WRANGLES_USER": "u" * 600}


def test_saved_recipe_uses_existing_metadata_name(monkeypatch, calls):
    lookups = []

    def model(model_id):
        lookups.append(model_id)
        return {"purpose": "recipe", "name": "Saved supplier classifier"}

    monkeypatch.setattr(recipe._data, "model", model)
    monkeypatch.setattr(recipe._data, "model_content", lambda *args: {
        "recipe": "wrangles:\n  - extract.ai:\n      input: Description\n      api_key: test-openai-key\n      output:\n        length:\n          type: string\n"
    })
    _run_recipe("aaaaaaaa-bbbb-cccc", variables={"recipe_name": "Fallback name"})

    assert lookups == ["aaaaaaaa-bbbb-cccc"]
    assert calls[0]["payload"]["metadata"] == {"recipe_name": "Saved supplier classifier"}


def test_file_recipe_uses_basename_without_disclosing_directory(tmp_path, calls):
    source = tmp_path / "supplier-classifier.wrgl.yml"
    source.write_text(
        "wrangles:\n  - extract.ai:\n      input: Description\n      api_key: test-openai-key\n      output:\n        length:\n          type: string\n",
        encoding="utf-8",
    )
    _run_recipe(source)

    assert calls[0]["payload"]["metadata"] == {"recipe_name": source.name}


def test_nested_saved_recipe_restores_parent_and_inline_fragments_inherit(monkeypatch, calls):
    monkeypatch.setattr(recipe._data, "model", lambda model_id: {"purpose": "recipe", "name": "Child recipe"})
    monkeypatch.setattr(recipe._data, "model_content", lambda *args: {
        "recipe": "wrangles:\n  - extract.ai:\n      input: Description\n      api_key: test-openai-key\n      cache: false\n      output:\n        length:\n          type: string\n"
    })

    def run_children(df, variables):
        _run_recipe("aaaaaaaa-bbbb-cccc", variables={**variables, "WRANGLES_USER": "child@example.test"})
        return _run_recipe(variables=variables)

    _run_recipe(
        {"wrangles": [_step(), {"custom.run_children": {}}, _step()]},
        variables={"recipe_name": "Parent recipe", "WRANGLES_USER": "parent@example.test"},
        functions=[run_children],
    )

    assert [call["payload"]["metadata"] for call in calls] == [
        {"recipe_name": "Parent recipe", "wrangles_user": "parent@example.test"},
        {"recipe_name": "Child recipe", "wrangles_user": "child@example.test"},
        {"recipe_name": "Parent recipe", "wrangles_user": "parent@example.test"},
        {"recipe_name": "Parent recipe", "wrangles_user": "parent@example.test"},
    ]
    assert recipe._RECIPE_RUN_CONTEXT.get() is None


def test_named_inline_child_uses_its_name_and_restores_parent(calls):
    def run_child(df, variables):
        return _run_recipe(variables={
            **variables,
            "recipe_name": "Inline child",
            "WRANGLES_USER": "child@example.test",
        })

    _run_recipe(
        {"wrangles": [_step(), {"custom.run_child": {}}, _step()]},
        variables={"recipe_name": "Parent recipe", "WRANGLES_USER": "parent@example.test"},
        functions=[run_child],
    )

    assert [call["payload"]["metadata"] for call in calls] == [
        {"recipe_name": "Parent recipe", "wrangles_user": "parent@example.test"},
        {"recipe_name": "Inline child", "wrangles_user": "child@example.test"},
        {"recipe_name": "Parent recipe", "wrangles_user": "parent@example.test"},
    ]
    assert recipe._RECIPE_RUN_CONTEXT.get() is None


def test_saved_child_batch_inherits_name_without_rewriting_recipe_variables(monkeypatch, calls):
    snapshots = []

    def capture_snapshot(df, variables):
        snapshots.append((variables.get("recipe_name"), variables["recipe_variables"].get("recipe_name")))
        return df

    child = {"wrangles": [
        {"custom.capture_snapshot": {}},
        _step(),
        {"batch": {
            "batch_size": 1,
            "threads": 2,
            "wrangles": [{"custom.capture_snapshot": {}}, _step()],
        }},
    ]}
    monkeypatch.setattr(recipe._data, "model", lambda model_id: {
        "purpose": "recipe", "name": "Saved child",
    })
    monkeypatch.setattr(recipe._data, "model_content", lambda *args: {
        "recipe": json.dumps(child, indent=2),
    })

    def run_child(df, variables):
        return _run_recipe(
            "aaaaaaaa-bbbb-cccc",
            variables={**variables, "WRANGLES_USER": "child@example.test"},
            functions=[capture_snapshot],
        )

    caller_variables = {
        "applied_permission_group": None,
        "recipe_name": "Parent recipe",
        "WRANGLES_USER": "parent@example.test",
    }
    original_variables = caller_variables.copy()
    recipe.run(
        {"wrangles": [
            {"custom.capture_snapshot": {}},
            _step(),
            {"custom.run_child": {}},
            {"custom.capture_snapshot": {}},
            _step(),
        ]},
        dataframe=pd.DataFrame({"Description": ["wrench 25mm"]}),
        variables=caller_variables,
        functions=[capture_snapshot, run_child],
    )

    assert [call["payload"]["metadata"] for call in calls] == [
        {"recipe_name": "Parent recipe", "wrangles_user": "parent@example.test"},
        {"recipe_name": "Saved child", "wrangles_user": "child@example.test"},
        {"recipe_name": "Saved child", "wrangles_user": "child@example.test"},
        {"recipe_name": "Parent recipe", "wrangles_user": "parent@example.test"},
    ]
    # Attribution follows the saved source without changing executable recipe variables.
    assert snapshots == [("Parent recipe", "Parent recipe")] * 4
    assert caller_variables == original_variables
    assert recipe._RECIPE_RUN_CONTEXT.get() is None


def test_concurrent_recipes_keep_names_and_users_isolated(calls):
    barrier = threading.Barrier(2)

    def synchronize(df):
        barrier.wait(timeout=10)
        return df

    source = {"wrangles": [{"custom.synchronize": {}}, _step()]}

    def run_named(name):
        return _run_recipe(
            source,
            variables={"recipe_name": name, "WRANGLES_USER": f"{name}@example.test"},
            functions=[synchronize],
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(run_named, ["alpha", "beta"]))

    assert all(result["length"].tolist() == ["25mm"] for result in results)
    observed = sorted(
        (call["payload"]["metadata"]["recipe_name"], call["payload"]["metadata"]["wrangles_user"])
        for call in calls
    )
    assert observed == [
        ("alpha", "alpha@example.test"),
        ("beta", "beta@example.test"),
    ]
    assert recipe._RECIPE_RUN_CONTEXT.get() is None


def test_failed_nested_and_outer_recipes_restore_attribution(monkeypatch, calls):
    def fail(df):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(recipe._data, "model", lambda model_id: {
        "purpose": "recipe", "name": "Failing child",
    })
    monkeypatch.setattr(recipe._data, "model_content", lambda *args: {
        "recipe": json.dumps({"wrangles": [_step(), {"custom.fail": {}}]}, indent=2),
    })

    def recover_child(df, variables):
        with pytest.raises(RuntimeError, match="synthetic failure"):
            _run_recipe(
                "aaaaaaaa-bbbb-cccc",
                variables={**variables, "WRANGLES_USER": "child@example.test"},
                functions=[fail],
            )
        return df

    with pytest.raises(RuntimeError, match="synthetic failure"):
        _run_recipe(
            {"wrangles": [_step(), {"custom.recover_child": {}}, _step(), {"custom.fail": {}}]},
            variables={"recipe_name": "Failing parent", "WRANGLES_USER": "parent@example.test"},
            functions=[recover_child, fail],
        )

    assert [call["payload"]["metadata"] for call in calls] == [
        {"recipe_name": "Failing parent", "wrangles_user": "parent@example.test"},
        {"recipe_name": "Failing child", "wrangles_user": "child@example.test"},
        {"recipe_name": "Failing parent", "wrangles_user": "parent@example.test"},
    ]
    assert recipe._RECIPE_RUN_CONTEXT.get() is None

    extract.ai("independent input", "test-openai-key", output={"length": {"type": "string"}})

    assert "metadata" not in calls[-1]["payload"]
