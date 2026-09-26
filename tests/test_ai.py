"""Offline contracts for the shared structured AI answers runtime."""
import copy
import os
import traceback

import pytest
import yaml

from wrangles import ai, ai_cache, ai_config
from wrangles.clients import typesafe


SCORE = {"severity": {"instructions": "How severe?", "criteria": ["Cosmetic", "Workaround", "Blocking"]}}
CHOICE = {"team": {"instructions": "Which team?", "criteria": {"Support": None, "Billing": "Payments"}}}
NOUL = {"repeat": {"instructions": "Has this happened before?"}}


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    for name in list(os.environ):
        if name.startswith(("WRANGLES_AI_CACHE_", "WRANGLES_EXTRACT_AI_CACHE_")):
            monkeypatch.delenv(name)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("WRANGLES_AI_CONFIG", raising=False)
    ai_config.clear_cache()
    ai_cache.clear()
    yield
    ai_config.clear_cache()
    ai_cache.clear()


@pytest.fixture
def transport(monkeypatch):
    calls = []

    def call(**kwargs):
        calls.append(copy.deepcopy(kwargs))
        answers = {}
        # Deliberately return a different question ordering than the request.
        for label, question in reversed(list(kwargs["questions"].items())):
            kind = question["type"]
            if kind == "score":
                answers[label] = {"type": kind, "score": 1.42, "confidence": 0.37,
                                  "probabilities": {"2": 0.42, "0": 0.0, "1": 0.58},
                                  "legend": dict(enumerate(question["criteria"]))}
            elif kind == "choice":
                options = list(question["criteria"])
                answers[label] = {"type": kind, "choice": options[0], "confidence": 0.0,
                                  "probabilities": {option: 1.0 / len(options) for option in options}}
            else:
                answers[label] = {"type": kind, "noul": 0.0 if kwargs["state"] == "zero" else 0.94}
        return {"model": kwargs["model"], "answers": answers, "usage": {"input_tokens": 10}}

    monkeypatch.setattr(typesafe, "call_systemone", call)
    return calls


def save_config(config, monkeypatch, tmp_path):
    path = tmp_path / "catalog.yml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setenv("WRANGLES_AI_CONFIG", str(path))
    ai_config.clear_cache()


def test_named_mixed_questions_share_one_request_and_preserve_native_values(transport):
    questions = {
        **{key: {**value, "type": "score"} for key, value in SCORE.items()},
        **{key: {**value, "type": "choose"} for key, value in CHOICE.items()},
        **{key: {**value, "type": "true_false"} for key, value in NOUL.items()},
    }
    questions["severity"]["output"] = ["Result", "Certainty", "Distribution"]
    original = copy.deepcopy(questions)
    result = ai.answers({"Description": "broken"}, questions, api_key="synthetic-key")
    assert len(transport) == 1
    assert list(result) == ["severity", "team", "repeat"]
    assert result["severity"] == {
        "score": 1.42, "confidence": 0.37,
        "probabilities": {"Cosmetic": 0.0, "Workaround": 0.58, "Blocking": 0.42},
    }
    assert result["team"] == {"choice": "Support", "confidence": 0.0,
                              "probabilities": {"Support": 0.5, "Billing": 0.5}}
    assert result["repeat"] == {"probability_true": 0.94, "true_criteria": ""}
    assert questions == original
    assert transport[0]["questions"]["team"]["type"] == "choice"
    assert transport[0]["questions"]["repeat"]["type"] == "noul"
    assert all("output" not in q for q in transport[0]["questions"].values())


@pytest.mark.parametrize("method,definitions", [("choose", CHOICE), ("score", SCORE), ("true_false", NOUL)])
def test_individual_wrangles_support_multiple_questions_in_one_request(transport, method, definitions):
    questions = {"first": copy.deepcopy(next(iter(definitions.values()))),
                 "second": copy.deepcopy(next(iter(definitions.values())))}
    result = getattr(ai, method)("state", questions, api_key="synthetic-key")
    assert list(result) == ["first", "second"]
    assert len(transport) == 1
    assert len(transport[0]["questions"]) == 2


def test_batch_shape_order_duplicate_suppression_and_independent_results(transport):
    result = ai.true_false(["zero", "positive", "zero"], NOUL, api_key="synthetic-key")
    assert [row["repeat"]["probability_true"] for row in result] == [0.0, 0.94, 0.0]
    assert len(transport) == 2
    result[0]["repeat"]["probability_true"] = 1
    assert result[2]["repeat"]["probability_true"] == 0
    assert ai.true_false("zero", NOUL, api_key="synthetic-key")["repeat"]["probability_true"] == 0
    assert len(transport) == 2


def test_true_criterion_is_supplied_context_and_not_a_generated_explanation(transport):
    definitions = {"repeat": {**NOUL["repeat"], "criteria": {
        "true": {"description": "Prior contact", "examples": ["Called twice"]},
        "false": "First contact",
    }}}
    result = ai.true_false("positive", definitions, api_key="synthetic-key")
    assert result["repeat"] == {"probability_true": 0.94, "true_criteria": definitions["repeat"]["criteria"]["true"]}
    result["repeat"]["true_criteria"]["examples"].append("mutation")
    assert definitions["repeat"]["criteria"]["true"]["examples"] == ["Called twice"]


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_default_names_and_empty_output_forms(blank):
    assert ai._output_columns({"severity": {**SCORE["severity"], "output": blank}}, "score") == [
        "severity", "severity_confidence", "severity_probabilities"]
    assert ai._output_columns({"repeat": {**NOUL["repeat"], "output": blank}}, "true_false") == [
        "repeat", "repeat_true_criteria"]


def test_explicit_output_names_and_projection_validation():
    assert ai._output_columns({"severity": {**SCORE["severity"], "output": ["A", "B", "C"]}}, "score") == ["A", "B", "C"]
    assert ai._output_columns({"repeat": {**NOUL["repeat"], "output": ["A", "B"]}}, "true_false") == ["A", "B"]


@pytest.mark.parametrize("output", [["one"], ["a", "b"], ["a", "b", ""], ["a", "a", "c"], [], "name", ["a", "b", "c", "d"]])
def test_invalid_positional_outputs_fail_before_calls(transport, output):
    with pytest.raises(ValueError):
        ai.score("state", {"severity": {**SCORE["severity"], "output": output}})
    assert transport == []


def test_generated_and_explicit_names_must_not_collide():
    definitions = {"q": NOUL["repeat"], "q_true_criteria": NOUL["repeat"]}
    with pytest.raises(ValueError, match="unique"):
        ai._prepare_questions(definitions, "true_false")


@pytest.mark.parametrize("definitions,kind", [
    ({}, "score"),
    ({"q": {"instructions": "score", "criteria": ["same", "same"]}}, "score"),
    ({"q": {"instructions": "score", "criteria": ["only"]}}, "score"),
    ({"q": {"instructions": "score", "criteria": list(map(str, range(11)))}}, "score"),
    ({"q": {"instructions": "score", "criteria": ["low", {"high": "very"}]}}, "score"),
    ({"q": {"instructions": "choose", "criteria": {}}}, "choose"),
    ({"q": {"instructions": "choose", "criteria": {str(i): None for i in range(256)}}}, "choose"),
    ({"q": {"instructions": "choose", "criteria": {True: None}}}, "choose"),
    ({"q": {"instructions": "noul", "criteria": {True: "yes"}}}, "true_false"),
    ({"q": {"instructions": "noul", "criteria": {"other": "yes"}}}, "true_false"),
    ({"q": {"instructions": "noul", "criteria": None}}, "true_false"),
    ({"q": {"instructions": "noul", "type": "score"}}, "true_false"),
    ({"q": {"instructions": "question"}}, None),
    ({"q": {"instructions": "question", "type": "noul"}}, None),
    ({"q": {"instructions": "question", "type": [], "criteria": []}}, None),
    ({"": {"instructions": "question"}}, "true_false"),
    ({"q": {"instructions": "  "}}, "true_false"),
    ({"q": {"instructions": "question", "scale": 100}}, "true_false"),
    ({"q": {"instructions": {"value": float("nan")}}}, "true_false"),
])
def test_invalid_questions_fail_before_credentials_or_provider(transport, definitions, kind):
    function = getattr(ai, kind or "answers")
    with pytest.raises(ValueError):
        function("state", definitions)
    assert transport == []


def test_json_descriptions_and_boundary_criteria_are_preserved():
    definitions = {"q": {"instructions": {"question": "Choose", "context": [1, None]},
                          "criteria": {str(i): None for i in range(255)}}}
    prepared = ai._prepare_questions(definitions, "choose")
    assert len(prepared["q"]["criteria"]) == 255
    assert prepared["q"]["instructions"] == definitions["q"]["instructions"]
    assert len(ai._prepare_questions({"q": {"instructions": "Score", "criteria": list(map(str, range(10)))}}, "score")["q"]["criteria"]) == 10


@pytest.mark.parametrize("row", [42, None, {"value": float("nan")}, {1: "non-string-key"}, {"value": object()}])
def test_all_rows_validated_before_sending_any(transport, row):
    with pytest.raises(ValueError):
        ai.true_false(["valid first", row], NOUL, api_key="synthetic-key")
    assert transport == []


def test_empty_batch_needs_no_credentials_or_catalog(transport, monkeypatch):
    monkeypatch.setattr(ai_config, "resolve", lambda *a, **kw: pytest.fail("No work needs no config"))
    assert ai.score([], SCORE) == []
    assert transport == []


def test_config_resolves_once_with_explicit_zero_and_false_overrides(transport, monkeypatch, tmp_path):
    config = ai_config.load()
    config["operations"]["ai.true_false"]["defaults"].update(default_concurrency=2, request_timeout_seconds=7.5, retries=3)
    config["providers"]["typesafe"]["endpoints"]["systemone"] = "https://typesafe.example/evaluate"
    save_config(config, monkeypatch, tmp_path)
    original = ai_config.resolve
    resolutions = []
    def resolve(*args, **kwargs):
        resolutions.append((args, kwargs))
        return original(*args, **kwargs)
    monkeypatch.setattr(ai_config, "resolve", resolve)
    ai.true_false(["a", "a"], NOUL, api_key="synthetic-key", model="custom-jev", retries=0, cache=False, timeout=2.5, threads=1)
    assert len(resolutions) == 1
    assert len(transport) == 2
    assert all(call["model"] == "custom-jev" and call["retries"] == 0 and call["timeout"] == 2.5
               and call["url"] == "https://typesafe.example/evaluate" for call in transport)


def test_local_environment_key_and_explicit_key_precedence(transport, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "environment-test-key")
    ai.true_false("one", NOUL)
    ai.true_false("two", NOUL, api_key="explicit-test-key")
    assert [call["api_key"] for call in transport] == ["environment-test-key", "explicit-test-key"]
    with pytest.raises(ValueError, match="api_key"):
        ai.true_false("three", NOUL, api_key="")


@pytest.mark.parametrize("overrides", [
    {"threads": 0}, {"threads": True}, {"timeout": 0}, {"timeout": float("nan")},
    {"timeout": 10 ** 1000}, {"cache_ttl": 10 ** 1000},
    {"retries": -1}, {"retries": True}, {"cache": "yes"}, {"cache_ttl": float("inf")},
    {"provider": "openai"}, {"protocol": "responses"},
])
def test_invalid_runtime_settings_fail_before_requests(transport, overrides):
    with pytest.raises(ValueError):
        ai.true_false("state", NOUL, api_key="synthetic-key", **overrides)
    assert transport == []


def test_unusable_endpoint_error_does_not_disclose_credentials(transport, monkeypatch, tmp_path):
    config = ai_config.load()
    config["providers"]["typesafe"]["endpoints"]["systemone"] = "https://user:private-value@example.com"
    save_config(config, monkeypatch, tmp_path)
    with pytest.raises(ValueError) as exc:
        ai.true_false("private-state", NOUL, api_key="private-key")
    assert "private" not in str(exc.value)
    assert transport == []


def test_typesafe_cache_controls_are_independent_of_extraction(transport, monkeypatch):
    monkeypatch.setenv("WRANGLES_EXTRACT_AI_CACHE_ENABLED", "false")
    for _ in range(2):
        ai.true_false("state", NOUL, api_key="synthetic-key")
    assert len(transport) == 1
    monkeypatch.setenv("WRANGLES_AI_CACHE_ENABLED", "false")
    for _ in range(2):
        ai.true_false("state", NOUL, api_key="synthetic-key")
    assert len(transport) == 3
    monkeypatch.setenv("WRANGLES_EXTRACT_AI_CACHE_ENABLED", "true")
    assert ai_cache.resolve_policy({}).enabled is True


def test_invalid_cache_environment_value_is_not_exposed_in_traceback(transport, monkeypatch):
    monkeypatch.setenv("WRANGLES_AI_CACHE_TTL_SECONDS", "private-invalid-value")
    with pytest.raises(ValueError) as exc:
        ai.true_false("state", NOUL, api_key="synthetic-key")
    assert "private-invalid-value" not in "".join(traceback.format_exception(exc.value))
    assert transport == []


def test_cache_identity_includes_key_model_endpoint_state_and_questions(transport, monkeypatch, tmp_path):
    ai.true_false("a", NOUL, api_key="key-a")
    ai.true_false("b", NOUL, api_key="key-a")
    ai.true_false("a", NOUL, api_key="key-b")
    ai.true_false("a", NOUL, api_key="key-a", model="other-model")
    ai.true_false("a", {"repeat": {"instructions": "A different question?"}}, api_key="key-a")
    config = ai_config.load()
    config["providers"]["typesafe"]["endpoints"]["systemone"] = "https://other.example/systemone"
    save_config(config, monkeypatch, tmp_path)
    ai.true_false("a", NOUL, api_key="key-a")
    # Output names only affect local projection, so renaming may reuse the answer.
    ai.true_false("a", {"repeat": {**NOUL["repeat"], "output": ["new", "new_criteria"]}}, api_key="key-a")
    assert len(transport) == 6


def test_failures_are_not_cached(monkeypatch):
    attempts = []
    def fail(**kwargs):
        attempts.append(1)
        raise RuntimeError("synthetic transport failure")
    monkeypatch.setattr(typesafe, "call_systemone", fail)
    for _ in range(2):
        with pytest.raises(RuntimeError, match="synthetic"):
            ai.true_false("state", NOUL, api_key="synthetic-key")
    assert len(attempts) == 2
    assert ai_cache.stats()["entries"] == 0


def test_deprecated_model_warning_is_once_per_invocation(transport, monkeypatch, tmp_path, caplog):
    config = ai_config.load()
    config["providers"]["typesafe"]["models"]["jev-1.13.0"]["status"] = "deprecated"
    save_config(config, monkeypatch, tmp_path)
    ai.true_false(["a", "b", "c"], NOUL, api_key="synthetic-key")
    assert sum("deprecated status" in record.message for record in caplog.records) == 1
