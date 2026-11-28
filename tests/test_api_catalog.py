"""Credential-free catalog, resolution and HTTP contracts for the Python pilot."""

from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit

import pandas as pd
import pytest
import requests
import yaml

import wrangles
from wrangles import ai_cache, ai_config, api_config
from wrangles.api_config.catalog import main as generate


DECISIONS = "ai.decisions"
SEARCH = "search.ai_mode"
ACTION = "wrangle.execute"
MICROSOFT = {"provider": "microsoft", "api": "decisions", "model": "microsoft-decision-1"}
JEV = {"provider": "typesafe", "api": "systemone", "model": "jev-1.13.0"}
AI_MODE = {"provider": "serpapi", "api": "google_ai_mode"}
QUESTIONS = {"fit": {"type": "choose", "instructions": "Which part?",
                     "criteria": {"belt": "A belt", "pump": "A pump"}}}


def action(config, operation):
    return config["callers"]["wranglespy"]["operations"][operation]["actions"][ACTION]


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    monkeypatch.delenv("WRANGLES_AI_CONFIG", raising=False)
    for key in os.environ.copy():
        if key.startswith("WRANGLES_AI_CACHE_"):
            monkeypatch.delenv(key)
    monkeypatch.setattr(wrangles.auth, "get_applied_permission_group", lambda: None)
    monkeypatch.setattr("socket.socket.connect", lambda *args: pytest.fail("Unexpected network request"))
    for provider in ("TYPESAFE", "OPENROUTER", "SERPAPI"):
        monkeypatch.setenv(provider + "_API_KEY", "offline-" + provider.lower())
    ai_config.clear_cache()
    ai_cache.clear()
    yield
    ai_config.clear_cache()
    ai_cache.clear()


@pytest.fixture
def replace(tmp_path, monkeypatch):
    def install(config):
        path = tmp_path / "internal-deployment-name.yml"
        path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        monkeypatch.setenv("WRANGLES_AI_CONFIG", str(path))
        ai_config.clear_cache()
        return path
    return install


@pytest.fixture
def network(monkeypatch):
    calls = []

    def send(session, request, **kwargs):
        url = urlsplit(request.url)
        response = requests.Response()
        response.status_code, response.encoding = 200, "utf-8"
        if request.method == "POST":
            body = json.loads(request.body)
            calls.append((url.netloc + url.path, body, request.headers["Authorization"], kwargs["timeout"]))
            response.headers["Content-Type"] = "application/json"
            answer = {"type": "choice", "choice": "belt", "confidence": 0.763,
                      "probabilities": {"belt": 0.812, "pump": 0.188}}
            response._content = json.dumps({"model": body["model"], "answers": {"fit": answer},
                                            "usage": {"input_tokens": 12}}).encode()
        else:
            assert request.method == "GET"
            params = {k: values[0] for k, values in parse_qs(url.query).items()}
            assert params.pop("api_key") == "offline-serpapi"
            calls.append((url.netloc + url.path, params))
            response.headers["Content-Type"] = "text/markdown"
            response._content = b"---\nsearch_metadata:\n  status: Success\n---\nAnswer"
        return response

    monkeypatch.setattr(requests.Session, "send", send)
    return calls


def test_packaged_decision_choices_match_post_and_output(network):
    catalog = api_config.export_catalog()
    cell = action(catalog, DECISIONS)
    assert cell["default_selection"] == JEV
    assert [c["provider"] for c in cell["choices"]] == ["typesafe", "microsoft"]
    assert cell["choices"][1]["routed_via"] == {"provider": "openrouter", "api": "decisions"}
    assert all(c["defaults"]["cache"] == {"enabled": False} for c in cell["choices"])
    direct = wrangles.ai.decisions("part", QUESTIONS)
    frame = wrangles.recipe.run({"wrangles": [{DECISIONS: {
        "input": "part", "questions": QUESTIONS, "provider": "microsoft", "decimals": 0,
    }}]}, dataframe=pd.DataFrame({"part": ["item"]}))
    assert direct["fit"] == {"choice": "belt", "confidence": 0.76, "probabilities": {"belt": 0.81, "pump": 0.19}}
    assert frame["fit_confidence"].tolist() == [1.0]
    assert frame.at[0, "fit_probabilities"] == {"belt": 1.0, "pump": 0.0}
    assert [(url, body["model"], key, timeout) for url, body, key, timeout in network] == [
        ("api.typesafe.ai/v1/systemone", JEV["model"], "Bearer offline-typesafe", 30),
        ("openrouter.ai/api/alpha/decisions", "microsoft/microsoft-decision-1", "Bearer offline-openrouter", 30),
    ]
    assert all(set(body) == {"state", "questions", "model"} for _, body, _, _ in network)
    assert all(body["questions"]["fit"]["type"] == "choice" for _, body, _, _ in network)


def test_replacement_changes_default_route_alternative_settings_and_alias_cache(replace, network):
    config = api_config.load_snapshot().config
    operation = config["operations"][DECISIONS]["actions"][ACTION]
    del operation["defaults"]["request_timeout_seconds"]
    config["providers"]["typesafe"]["apis"]["systemone"]["defaults"] = {"request_timeout_seconds": 12}
    router = config["providers"]["openrouter"]["apis"]["decisions"]
    router.update(endpoint="https://decisions.example/alpha", defaults={"request_timeout_seconds": 8})
    model = config["providers"]["microsoft"]["models"][MICROSOFT["model"]]
    model["routed_via"]["request_model"] = "microsoft/custom-deployment"
    model["defaults"] = {"request_timeout_seconds": 4}
    action(config, DECISIONS).update(default_selection=MICROSOFT, defaults={"cache": {"enabled": True}, "retries": 0})
    path = replace(config)
    catalog = api_config.export_catalog()
    assert catalog["configuration"] == {"version": 3, "source": "replacement", "revision": sha256(path.read_bytes()).hexdigest()}
    assert catalog["schema_version"] == 1 and catalog["package_version"] == version("wrangles")
    cell = action(catalog, DECISIONS)
    assert cell["default_selection"] == {**MICROSOFT, "routed_via": {"provider": "openrouter", "api": "decisions"}}
    assert [c["defaults"]["request_timeout_seconds"] for c in cell["choices"]] == [12, 4]
    choice = api_config.resolve(DECISIONS, overrides={"decimals": 0, "cache": {"enabled": False}})
    assert {k: choice.provenance[k] for k in ("selection", "request_timeout_seconds", "retries", "decimals", "cache.enabled")} == {
        "selection": "caller", "request_timeout_seconds": "model", "retries": "caller", "decimals": "explicit", "cache.enabled": "explicit",
    }
    wrangles.ai.answers("part", QUESTIONS)
    wrangles.ai.decisions("part", QUESTIONS, provider="openrouter", protocol="systemone", model="microsoft/custom-deployment")
    assert len(network) == 1
    url, body, key, timeout = network[0]
    assert (url, body["model"], key, timeout) == ("decisions.example/alpha", "microsoft/custom-deployment", "Bearer offline-openrouter", 4)
    wrangles.ai.decisions("part", QUESTIONS, cache=False, retries=0, decimals=0)
    assert len(network) == 2


@pytest.mark.parametrize("replacement", [False, True])
def test_search_cell_matches_direct_and_recipe_get(replacement, replace, network):
    if replacement:
        config = api_config.load_snapshot().config
        endpoint = config["providers"]["serpapi"]["apis"]["google_ai_mode"]
        endpoint.update(endpoint="https://search.example/custom", defaults={"parameters": {"language": "fr"}})
        action(config, SEARCH)["defaults"] = {"include_raw_response": True, "default_concurrency": 1}
        replace(config)
    cell = action(api_config.export_catalog(), SEARCH)
    assert cell["default_selection"] == AI_MODE
    item, = cell["choices"]
    assert "model" not in item
    assert item["defaults"].get("parameters", {}) == ({"hl": "fr"} if replacement else {})
    first = wrangles.search.ai_mode("part")
    assert ("raw_response" in first["ai_mode_metadata"]) is replacement
    recipe = {"wrangles": [{SEARCH: {"queries": "query", "id": "id", "output": ["answer", "meta"],
                                      "country": "us", "language": "de", "device": "desktop", "include_raw_response": False}}]}
    frame = wrangles.recipe.run(recipe, dataframe=pd.DataFrame({"query": ["belt"], "id": [7]}))
    assert frame.at[0, "answer"] == "Answer" and "raw_response" not in frame.at[0, "meta"]
    url = "search.example/custom" if replacement else "serpapi.com/search"
    fixed = {"engine": "google_ai_mode", "output": "md"}
    assert network == [(url, {**fixed, **item["defaults"].get("parameters", {}), "q": "part"}),
                       (url, {**fixed, "hl": "de", "gl": "us", "device": "desktop", "q": "belt"})]
    wrangles.search.ai_mode("actual", engine="google", q="discarded")
    assert network[-1][1]["engine"] == "google_ai_mode" and network[-1][1]["q"] == "actual"
    wrangles.search.ai_mode("part", language=None)
    assert "hl" not in network[-1][1]
    for invalid in ({"num": 5}, {"output": "json"}, {"caller": "wranglesxl"}, {"api_key": "wrong-place"},
                    {"request_timeout_seconds": 4}):
        with pytest.raises(ValueError):
            wrangles.search.ai_mode("unused", **invalid)
    assert len(network) == 4


def test_validation_and_offline_public_projection(replace):
    config = api_config.load_snapshot().config
    api = config["providers"]["serpapi"]["apis"]["google_ai_mode"]
    api.update(public_parameters=["hl", "device", "internal"], public_definitions=["Locale"], parameter_schema={
        "type": "object", "required": ["hl"], "additionalProperties": True,
        "$defs": {"Locale": {"type": "string", "enum": ["fr", "de"], "examples": ["private-example"]},
                  "Internal": {"const": "private-constant"}},
        "properties": {"hl": {"$ref": "#/$defs/Locale", "description": "private-description", "default": "fr"},
                       "device": {"type": "string"}, "internal": {"$ref": "#/$defs/Internal"}},
    })
    action(config, SEARCH)["parameter_schema"] = {"allOf": [
        {"properties": {"device": {"enum": ["mobile"]}}}, {"properties": {"hl": {"minLength": 2}}}]}
    replace(config)
    catalog = api_config.export_catalog()
    item, = action(catalog, SEARCH)["choices"]
    schema = item["parameter_schema"]
    assert set(schema["properties"]) == {"hl", "device"} and schema["additionalProperties"] is False
    assert schema["required"] == ["hl"] and "parameters" not in item["defaults"]
    encoded = json.dumps(catalog)
    for private in ("private-", "https://", "internal", "$ref", "$defs", "request_model", "ttl_seconds"):
        assert private not in encoded
    with pytest.raises(ValueError, match="required"):
        api_config.resolve(SEARCH)
    for params in ({"hl": False}, {"hl": "uk"}, {"hl": "fr", "device": "desktop"}):
        with pytest.raises(ValueError, match="Invalid API parameters"):
            api_config.resolve(SEARCH, parameters=params)
    params = {"language": "fr", "device": "mobile", "another_option": 0}
    resolved = api_config.resolve(SEARCH, parameters=params)
    assert resolved.parameters == {"hl": "fr", "device": "mobile", "another_option": 0}
    assert resolved.provenance["parameters.hl"] == "explicit"
    assert resolved.provenance["fixed_query.output"] == "operation"
    assert resolved.provenance["fixed_query.engine"] == "api"
    api["parameter_schema"]["properties"]["hl"] = {"$ref": "https://private.example/schema"}
    replace(config)
    with pytest.raises(ValueError, match="local JSON pointers"):
        api_config.export_catalog()


def test_legacy_roles_missing_cells_and_dated_models(replace, network):
    legacy = ai_config.load()
    models = legacy["providers"]["typesafe"]["models"]
    models[JEV["model"]]["default_for"].remove("ai.answers")
    models["jev-team"] = {"status": "active", "default_for": ["ai.answers"],
                          "protocol_defaults": {"systemone": {"request_timeout_seconds": 6}}}
    del legacy["operations"]["ai.answers"]["defaults"]["request_timeout_seconds"]
    replace(legacy)
    public = api_config.export_catalog()
    assert action(public, DECISIONS)["default_selection"]["model"] == "jev-team"
    assert action(public, SEARCH)["default_selection"] == AI_MODE
    wrangles.ai.decisions("part", QUESTIONS)
    wrangles.ai.answers("part", QUESTIONS, model="jev-team-2025-01-01")
    assert [(body["model"], timeout) for _, body, _, timeout in network] == [("jev-team", 6), ("jev-team-2025-01-01", 6)]
    del legacy["operations"]["ai.answers"]
    for provider in legacy["providers"].values():
        for entry in provider["models"].values():
            entry["default_for"] = [name for name in entry.get("default_for", []) if name != "ai.answers"]
    replace(legacy)
    assert list(api_config.export_catalog()["callers"]["wranglespy"]["operations"]) == [SEARCH]
    with pytest.raises(ValueError, match="No AI operation"):
        api_config.resolve("ai.answers")
    replace({"version": 1, "extract_ai": {"model": "legacy-extractor"}})
    assert action(api_config.export_catalog(), DECISIONS)["default_selection"] == JEV
    assert api_config.resolve(SEARCH).choice.selection() == AI_MODE


def test_partial_object_constraints_and_complete_scalar_defaults(replace):
    config = api_config.load_snapshot().config
    cell = action(config, SEARCH)
    cell["parameter_schema"] = {
        "type": "object", "not": {"required": ["hl", "device"]},
        "properties": {"gl": {"oneOf": [{"type": "string"}, {"const": "xx"}]}},
    }
    replace(config)
    assert api_config.resolve(SEARCH, parameters={"hl": "en"}).parameters == {"hl": "en"}
    with pytest.raises(ValueError, match="Invalid API parameters"):
        api_config.resolve(SEARCH, parameters={"hl": "en", "device": "mobile"})
    cell["defaults"] = {"parameters": {"gl": "xx"}}
    replace(config)
    with pytest.raises(ValueError, match="oneOf"):
        api_config.load_snapshot()


def test_complete_replacement_and_cli_revision_paths(replace, tmp_path, monkeypatch, capsys):
    config = api_config.load_snapshot().config
    del config["callers"]["wranglespy"]["operations"][SEARCH]
    replacement = replace(config)
    output = tmp_path / "catalogs"
    for args in (["--packaged"], ["--config", str(replacement)], []):
        monkeypatch.setattr(sys, "argv", ["wrangles-api-catalog", "--output-dir", str(output), *args])
        generate()
        target = Path(capsys.readouterr().out.strip())
        payload = json.loads(target.read_text(encoding="utf-8"))
        assert payload["configuration"]["revision"] in target.name
        assert payload["configuration"]["source"] in target.name
        assert (SEARCH in payload["callers"]["wranglespy"]["operations"]) == (args == ["--packaged"])
    assert len(list(output.glob("*.json"))) == 2
    target.write_text("prior artifact", encoding="utf-8")
    with pytest.raises(SystemExit) as collision:
        generate()
    assert collision.value.code != 0 and target.read_text(encoding="utf-8") == "prior artifact"
    with pytest.raises(ValueError, match="No API selection"):
        wrangles.search.ai_mode("query")
    with pytest.raises(ValueError, match="No API selection"):
        api_config.resolve(DECISIONS, caller="wranglesxl")


def test_snapshot_cannot_be_changed_through_returned_values():
    snapshot = api_config.load_snapshot()
    baseline = api_config.export_catalog(snapshot)
    snapshot.config["callers"].clear()
    resolved = api_config.resolve(SEARCH, snapshot=snapshot)
    resolved.api_config["public_parameters"].clear()
    resolved.schemas[0]["properties"].clear()
    assert api_config.export_catalog(snapshot) == baseline
    assert api_config.export_catalog() == baseline
    with pytest.raises(ValueError, match="incompatible"):
        api_config.resolve(DECISIONS, provider="typesafe", model=MICROSOFT["model"])
    with pytest.raises(ValueError):
        api_config.resolve(DECISIONS, provider="microsoft", api="systemone")


def test_omitted_decision_action_is_unavailable_without_disabling_search(replace):
    config = api_config.load_snapshot().config
    config["callers"]["wranglespy"]["operations"][DECISIONS]["actions"].clear()
    replace(config)
    assert set(api_config.export_catalog()["callers"]["wranglespy"]["operations"]) == {SEARCH}
    assert api_config.resolve(SEARCH).choice.selection() == AI_MODE
    with pytest.raises(ValueError, match="No API selection"):
        api_config.resolve("ai.answers")


@pytest.mark.parametrize("change", ["route", "engine", "output", "selection", "setting", "unsupported_caller"])
def test_invalid_v3_fails_before_execution(change, replace):
    config = api_config.load_snapshot().config
    if change == "route":
        config["providers"]["microsoft"]["models"][MICROSOFT["model"]]["routed_via"]["api"] = "systemone"
    elif change == "engine":
        config["providers"]["serpapi"]["apis"]["google_ai_mode"]["fixed_query"]["engine"] = "google"
    elif change == "output":
        config["operations"][SEARCH]["actions"][ACTION]["fixed_query"] = {"output": "json"}
    elif change == "selection":
        del action(config, DECISIONS)["default_selection"]["model"]
    elif change == "setting":
        action(config, SEARCH)["defaults"] = {"retries": 2}
    else:
        config["callers"]["wranglesxl"] = config["callers"]["wranglespy"]
    replace(config)
    with pytest.raises(ValueError):
        api_config.export_catalog()
