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


def expanded_question(kind="score", **overrides):
    source = {"choose": CHOICE["team"], "score": SCORE["severity"], "true_false": NOUL["repeat"]}[kind]
    return {**copy.deepcopy(source), "instructions": "Evaluate {{ category }} for {{ Product_Description }}.",
            "for_each": {"values": "Candidate Categories", "variable": "category"}, **overrides}


@pytest.mark.parametrize("method", ["choose", "score", "true_false", "answers"])
def test_templates_expand_each_row_into_one_request_and_preserve_candidate_values(method, transport):
    kind = "score" if method == "answers" else method
    definition = expanded_question(kind)
    if method == "answers":
        definition["type"] = kind
    definitions = {"fits": definition}
    row = {"Product Description": "Metal container", "Candidate Categories": ["Containers", "Shelves"]}
    original = copy.deepcopy((row, definitions))

    result = getattr(ai, method)(row, definitions, api_key="synthetic-key")

    assert len(transport) == 1
    assert transport[0]["state"] == row
    wire = list(transport[0]["questions"].values())
    assert [q["instructions"] for q in wire] == [
        "Evaluate Containers for Metal container.", "Evaluate Shelves for Metal container."]
    assert all("for_each" not in q and "output" not in q for q in wire)
    assert [item["value"] for item in result["fits"]] == ["Containers", "Shelves"]
    fields = {"choose": {"choice", "confidence", "probabilities"},
              "score": {"score", "confidence", "probabilities"},
              "true_false": {"probability_true", "true_criteria"}}[kind]
    assert all(set(item) == {"value", *fields} for item in result["fits"])
    assert (row, definitions) == original


def test_varying_candidates_keep_list_shape_dictionary_keys_and_fixed_answers(transport):
    definitions = {
        "fits": expanded_question(type="score"),
        "repeat": {**NOUL["repeat"], "type": "true_false"},
    }
    rows = [
        {"Product Description": "first", "Candidate Categories": ["Containers", "Containers", "Shelves"]},
        {"Product Description": "second", "Candidate Categories": {"category_7": "Shelves", "category_2": "Storage"}},
        {"Product Description": "third", "Candidate Categories": []},
        {"Product Description": "fourth", "Candidate Categories": {}},
    ]
    result = ai.answers(rows, definitions, api_key="synthetic-key", threads=1)

    assert [list(row) for row in result] == [["fits", "repeat"]] * 4
    assert [len(row["fits"]) for row in result] == [3, 2, 0, 0]
    assert [item["value"] for item in result[0]["fits"]] == ["Containers", "Containers", "Shelves"]
    assert [list(item) for item in result[1]["fits"]] == [["category_7"], ["category_2"]]
    assert result[1]["fits"][0]["category_7"]["value"] == "Shelves"
    assert result[1]["fits"][1]["category_2"]["value"] == "Storage"
    assert [len(call["questions"]) for call in transport] == [4, 3, 1, 1]
    assert all(row["repeat"]["probability_true"] == 0.94 for row in result)
    result[0]["fits"][0]["probabilities"]["Cosmetic"] = 1
    assert result[0]["fits"][1]["probabilities"]["Cosmetic"] == 0.0


@pytest.mark.parametrize("candidates", [[], {}])
def test_empty_expansion_needs_no_credentials_or_catalog(candidates, transport, monkeypatch):
    monkeypatch.setattr(ai_config, "resolve", lambda *a, **kw: pytest.fail("Empty expansion needs no config"))
    result = ai.score({"Candidate Categories": candidates}, {"fits": expanded_question()})
    assert result == {"fits": []}
    assert transport == []


@pytest.mark.parametrize("output,expected", [(None, "fits"), ("", "fits"), ("  ", "fits"),
                                              ("Category Fits", "Category Fits"), (["Category Fits"], "Category Fits")])
def test_expanded_output_has_one_stable_destination(output, expected):
    assert ai._output_columns({"fits": expanded_question(output=output)}, "score") == [expected]


@pytest.mark.parametrize("output", [[], ["one", "two"], ["one", "two", "three"], [""], [4], 4])
def test_expanded_output_rejects_invalid_projection(transport, output):
    with pytest.raises(ValueError):
        ai.score({"Candidate Categories": []}, {"fits": expanded_question(output=output)})
    assert transport == []


def test_expanded_and_ordinary_destinations_cannot_collide(transport):
    with pytest.raises(ValueError, match="unique"):
        ai.score({}, {"ordinary": SCORE["severity"], "fits": expanded_question(output="ordinary_confidence")})
    assert transport == []


def test_row_templates_without_for_each_render_recursive_descriptions_and_score_probability_labels(transport):
    questions = {
        "score": {"type": "score", "instructions": {"question": ["Fit for {{ Proposed_Category }}?", {"detail": "{{ Detail }}"}]},
                  "criteria": ["No {{ Proposed_Category }} fit", "Partial {{ Proposed_Category }} fit", "Full {{ Proposed_Category }} fit"]},
        "choice": {"type": "choose", "instructions": "Choose for {{ Proposed_Category }}", "criteria": {
            "first": {"description": ["Suitable for {{ Proposed_Category }}"]}, "second": None}},
        "true_false": {"type": "true_false", "instructions": "Fit for {{ Proposed_Category }}?", "criteria": {
            "true": {"description": "Fits {{ Proposed_Category }}", "examples": ["{{ Detail }}"]}, "false": "Does not fit {{ Proposed_Category }}"}},
    }
    original = copy.deepcopy(questions)
    result = ai.answers({"Proposed Category": "Storage", "Detail": "Stackable"}, questions, api_key="synthetic-key")
    wire = transport[0]["questions"]

    assert wire["score"]["instructions"] == {"question": ["Fit for Storage?", {"detail": "Stackable"}]}
    assert list(result["score"]["probabilities"]) == ["No Storage fit", "Partial Storage fit", "Full Storage fit"]
    assert wire["choice"]["criteria"] == {"first": {"description": ["Suitable for Storage"]}, "second": None}
    assert result["true_false"]["true_criteria"] == {"description": "Fits Storage", "examples": ["Stackable"]}
    assert wire["true_false"]["criteria"]["false"] == "Does not fit Storage"
    assert questions == original


def test_substitution_is_single_pass_and_local_variable_takes_precedence(transport):
    row = {"Product Description": "{{ Missing }}", "category": "not the candidate",
           "Candidate Categories": ["{{ Other_Missing }}"]}
    result = ai.score(row, {"fits": expanded_question()}, api_key="synthetic-key")
    wire = next(iter(transport[0]["questions"].values()))
    assert wire["instructions"] == "Evaluate {{ Other_Missing }} for {{ Missing }}."
    assert result["fits"][0]["value"] == "{{ Other_Missing }}"


def test_structured_candidate_values_are_preserved_and_rendered_as_json(transport):
    row = {"Candidate Categories": [{"name": "Containers", "levels": [1, 2]}, None, 7]}
    definition = expanded_question(instructions="Candidate {{ category }}")
    result = ai.score(row, {"fits": definition}, api_key="synthetic-key")
    assert [item["value"] for item in result["fits"]] == row["Candidate Categories"]
    assert [q["instructions"] for q in transport[0]["questions"].values()] == [
        'Candidate {"name":"Containers","levels":[1,2]}', "Candidate null", "Candidate 7"]
    result["fits"][0]["value"]["levels"].append(3)
    assert row["Candidate Categories"][0]["levels"] == [1, 2]


@pytest.mark.parametrize("for_each", [None, [], {}, {"values": "Candidates"}, {"variable": "category"},
    {"values": ["Containers"], "variable": "category"}, {"values": {"first": "Containers"}, "variable": "category"},
    {"values": "", "variable": "category"}, {"values": "Candidates", "variable": ""},
    {"values": "Candidates", "variable": "1category"}, {"values": "Candidates", "variable": "Category Name"},
    {"values": "Candidates", "variable": "category", "unknown": True}])
def test_invalid_expansion_definitions_fail_before_credentials_or_requests(for_each, transport):
    with pytest.raises(ValueError):
        ai.score({}, {"fits": expanded_question(for_each=for_each)})
    assert transport == []


@pytest.mark.parametrize("bad_row", [
    {"Product Description": "missing candidates"},
    {"Product Description": "string candidates", "Candidate Categories": '["Containers"]'},
    {"Product Description": "null candidates", "Candidate Categories": None},
    {"Product Description": "number candidates", "Candidate Categories": 4},
    {"Product Description": "invalid key", "Candidate Categories": {1: "Containers"}},
    {"Product Description": "nonfinite candidate", "Candidate Categories": [float("nan")]},
    {"Candidate Categories": ["Containers"]},
    {"Product Description": "first alias", "Product_Description": "second alias", "Candidate Categories": ["Containers"]},
])
def test_all_expanded_rows_are_validated_before_any_provider_call(bad_row, transport):
    valid = {"Product Description": "valid first", "Candidate Categories": ["Containers"]}
    with pytest.raises(ValueError):
        ai.score([valid, bad_row], {"fits": expanded_question()}, api_key="synthetic-key")
    assert transport == []


def test_template_rendering_must_not_create_duplicate_score_probability_labels(transport):
    definitions = {"fit": {"instructions": "Evaluate fit", "criteria": ["{{ First }}", "{{ Second }}", "Other"]}}
    rows = [{"First": "Low", "Second": "High"}, {"First": "Same", "Second": "Same"}]
    with pytest.raises(ValueError):
        ai.score(rows, definitions, api_key="synthetic-key")
    assert transport == []


def test_cache_uses_rendered_questions_with_identical_provider_state_and_distinct_row_context(transport):
    definitions = {"fits": expanded_question(instructions="Evaluate {{ category }} for {{ Manufacturer }}")}
    contexts = [
        {"Manufacturer": "Acme", "Candidate Categories": ["Containers"]},
        {"Manufacturer": "Other", "Candidate Categories": ["Shelves", "Storage"]},
        {"Manufacturer": "Acme", "Candidate Categories": ["Containers"]},
    ]
    result = ai._run(["same product"] * 3, definitions, "score", contexts=contexts,
                     api_key="synthetic-key", model=None, provider=None, protocol=None, threads=1,
                     timeout=None, retries=None, cache=None, cache_ttl=None)
    assert len(transport) == 2
    assert all(call["state"] == "same product" for call in transport)
    assert [len(row["fits"]) for row in result] == [1, 2, 1]
    assert [q["instructions"] for q in transport[1]["questions"].values()] == [
        "Evaluate Shelves for Other", "Evaluate Storage for Other"]
    result[0]["fits"][0]["value"] = "mutated"
    assert result[2]["fits"][0]["value"] == "Containers"


def test_generated_question_identifiers_cannot_overwrite_user_questions(transport):
    definitions = {"fits": expanded_question(type="score"),
                   "_wrangles_question_0": {**NOUL["repeat"], "type": "true_false"},
                   "_wrangles_question_1": {**NOUL["repeat"], "type": "true_false"}}
    result = ai.answers({"Product Description": "product", "Candidate Categories": ["Containers", "Storage"]},
                        definitions, api_key="synthetic-key")
    assert list(result) == ["fits", "_wrangles_question_0", "_wrangles_question_1"]
    assert len(transport[0]["questions"]) == 4
    assert len(result["fits"]) == 2
    assert result["_wrangles_question_0"] == result["_wrangles_question_1"] == {"probability_true": 0.94, "true_criteria": ""}


def test_cached_wire_answers_are_projected_with_each_rows_own_candidate_value_and_key(transport):
    definitions = {"fits": expanded_question(instructions="Evaluate the input without a candidate reference")}
    contexts = [{"Candidate Categories": ["Containers"]},
                {"Candidate Categories": {"category_7": "Shelves"}},
                {"Candidate Categories": {"category_2": {"name": "Storage"}}}]
    result = ai._run(["same product"] * 3, definitions, "score", contexts=contexts,
                     api_key="synthetic-key", model=None, provider=None, protocol=None, threads=1,
                     timeout=None, retries=None, cache=None, cache_ttl=None)
    assert len(transport) == 1
    assert result[0]["fits"][0]["value"] == "Containers"
    assert result[1]["fits"][0]["category_7"]["value"] == "Shelves"
    assert result[2]["fits"][0]["category_2"]["value"] == {"name": "Storage"}
    result[1]["fits"][0]["category_7"]["probabilities"]["Cosmetic"] = 1
    assert result[2]["fits"][0]["category_2"]["probabilities"]["Cosmetic"] == 0.0


@pytest.mark.parametrize("row", [{}, {"Proposed Category": "First", "Proposed_Category": "Second"}])
def test_missing_or_ambiguous_plain_template_column_fails_before_requests(row, transport):
    with pytest.raises(ValueError, match="Proposed_Category"):
        ai.true_false(row, {"fit": {"instructions": "Fit for {{ Proposed_Category }}?"}})
    assert transport == []


def test_unreferenced_ambiguous_alias_does_not_reject_plain_questions(transport):
    result = ai.true_false({"Unused Field": "First", "Unused_Field": "Second"}, NOUL, api_key="synthetic-key")
    assert result["repeat"]["probability_true"] == 0.94
    assert len(transport) == 1
