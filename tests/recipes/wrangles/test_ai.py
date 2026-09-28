"""Offline recipe integration for structured Typesafe answers."""

import copy
import inspect
import json
import os
from pathlib import Path
import runpy
import sys

import jsonschema
import pandas as pd
import pytest
import yaml

import wrangles
from wrangles.recipe_wrangles import ai as recipe_ai
from wrangles.clients import typesafe


@pytest.fixture(autouse=True)
def no_live_auth(monkeypatch):
    monkeypatch.setattr(wrangles.recipe._auth, "get_applied_permission_group", lambda: None)


def question(kind, **overrides):
    result = {"instructions": "Evaluate the supplied product."}
    if kind == "choose":
        result["criteria"] = {"bearing": "A bearing", "belt": "A belt"}
    elif kind == "score":
        result["criteria"] = ["Low", "Medium", "High"]
    else:
        result["criteria"] = {"true": "Suitable outdoors", "false": "Indoor use only"}
    return {**result, **overrides}


@pytest.fixture
def core_calls(monkeypatch):
    """Mock only the network-facing core entry points, retaining real validation."""
    calls = []

    def execute(data, questions, kind, **settings):
        calls.append({"kind": kind, "data": data, "questions": questions, "settings": settings})
        prepared = wrangles.ai._prepare_questions(questions, kind=kind)
        results = []
        for row in data:
            response = {}
            for label, definition in prepared.items():
                if definition["type"] == "choose":
                    response[label] = {
                        "choice": "bearing", "confidence": 0.8,
                        "probabilities": {"bearing": 0.8, "belt": 0.2},
                    }
                elif definition["type"] == "score":
                    response[label] = {
                        "score": 1.42, "confidence": 0.7,
                        "probabilities": {"Low": 0.0, "Medium": 0.58, "High": 0.42},
                    }
                else:
                    response[label] = {
                        "probability_true": 0.75,
                        "true_criteria": definition.get("criteria", {}).get("true", ""),
                    }
            results.append(response)
        return results
    monkeypatch.setattr(wrangles.ai, "_run", execute)
    return calls


def run(kind, definitions, dataframe=None, **options):
    if dataframe is None:
        dataframe = pd.DataFrame({"Description": ["first", "second"], "Ignore": [1, 2]})
    return wrangles.recipe.run(
        {"wrangles": [{f"ai.{kind}": {"input": "Description", "questions": definitions, **options}}]},
        dataframe=dataframe,
    )


@pytest.mark.parametrize("kind", ["choose", "score", "true_false"])
def test_homogeneous_named_questions_share_row_records_and_defaults(kind, core_calls):
    source = pd.DataFrame({"Description": ["first", "second"], "Ignore": [1, 2]}, index=[8, 3])
    result = run(kind, {"First": question(kind), "Second": question(kind)}, dataframe=source,
                 api_key="test-key", threads=3, cache=False)

    assert result.index.tolist() == [8, 3]
    assert len(core_calls) == 1
    assert core_calls[0]["data"] == [{"Description": "first"}, {"Description": "second"}]
    assert core_calls[0]["settings"]["threads"] == 3
    assert core_calls[0]["settings"]["cache"] is False
    if kind == "true_false":
        assert result.columns.tolist() == ["Description", "Ignore", "First", "First_true_criteria",
                                           "Second", "Second_true_criteria"]
        assert result["First"].tolist() == [0.75, 0.75]
        assert result["First_true_criteria"].tolist() == ["Suitable outdoors"] * 2
    else:
        assert result.columns.tolist() == ["Description", "Ignore", "First", "First_confidence",
                                           "First_probabilities", "Second", "Second_confidence",
                                           "Second_probabilities"]
        assert result["First"].tolist() == (["bearing"] * 2 if kind == "choose" else [1.42] * 2)
        assert isinstance(result["First_probabilities"].iloc[0], dict)


@pytest.mark.parametrize("blank", [None, "", "  "])
def test_whole_blank_output_uses_default_columns(blank, core_calls):
    result = run("choose", {"Category": question("choose", output=blank)})
    assert result["Category"].tolist() == ["bearing", "bearing"]
    assert "Category_probabilities" in result


def test_mixed_questions_project_explicit_columns_and_native_values(core_calls):
    result = run("answers", {
        "Category": question("choose", type="choose", output=["Category Name", "Certainty", "Distribution"]),
        "Severity": question("score", type="score"),
        "Outdoor": question("true_false", type="true_false", output=["Outdoor Probability", "Criterion"]),
    })

    assert core_calls[0]["kind"] is None
    assert list(core_calls[0]["questions"]) == ["Category", "Severity", "Outdoor"]
    assert result["Category Name"].tolist() == ["bearing"] * 2
    assert result["Certainty"].tolist() == [0.8] * 2
    assert result["Severity"].tolist() == [1.42] * 2
    assert result["Severity_probabilities"].iloc[0] == {"Low": 0.0, "Medium": 0.58, "High": 0.42}
    assert result["Outdoor Probability"].tolist() == [0.75] * 2
    assert result["Criterion"].tolist() == ["Suitable outdoors"] * 2
    assert "Outdoor" not in result


def test_true_false_without_criteria_has_blank_criteria_output(core_calls):
    result = run("true_false", {"Outdoor": {"instructions": "Can it be used outdoors?"}})
    assert result["Outdoor"].tolist() == [0.75, 0.75]
    assert result["Outdoor_true_criteria"].tolist() == ["", ""]


def test_structured_true_criteria_stays_structured(core_calls):
    criteria = {"requirements": ["water resistant", "UV resistant"]}
    result = run("true_false", {"Outdoor": question("true_false", criteria={"true": criteria})})
    assert result["Outdoor_true_criteria"].tolist() == [criteria, criteria]


def test_where_preserves_untouched_rows_and_overwrites_nested_destinations(core_calls):
    source = pd.DataFrame({"Description": ["first", "second"], "Category": ["old1", "old2"]}, index=[5, 9])
    result = run("answers", {
        "Category": question("choose", type="choose"),
        "Outdoor": question("true_false", type="true_false"),
    }, dataframe=source, where="Description = 'second'")

    assert core_calls[0]["data"] == [{"Description": "second"}]
    assert result.index.tolist() == [5, 9]
    assert result["Category"].tolist() == ["old1", "bearing"]
    assert result["Category_confidence"].tolist() == ["", 0.8]
    assert result["Outdoor"].tolist() == ["", 0.75]
    assert result["Outdoor_true_criteria"].tolist() == ["", "Suitable outdoors"]


def test_where_no_rows_creates_all_nested_destinations_without_calling_core(core_calls):
    source = pd.DataFrame({"Description": ["first"], "Category": ["kept"]})
    result = run("answers", {
        "Category": question("choose", type="choose"),
        "Outdoor": question("true_false", type="true_false", output=["Probability", "Rule"]),
    }, dataframe=source, where="Description = 'missing'")

    assert core_calls == []
    assert result.columns.tolist() == ["Description", "Category", "Category_confidence",
                                       "Category_probabilities", "Probability", "Rule"]
    assert result["Category"].tolist() == ["kept"]
    assert result["Probability"].tolist() == [""]


def test_empty_dataframe_has_declared_schema_without_calling_core(core_calls):
    result = run("score", {"Severity": question("score")}, dataframe=pd.DataFrame({"Description": []}))
    assert core_calls == []
    assert result.empty
    assert result.columns.tolist() == ["Description", "Severity", "Severity_confidence", "Severity_probabilities"]


@pytest.mark.parametrize("where", ["Description = 'second'", "Description = 'missing'"])
def test_nested_output_names_are_literal_even_when_they_contain_wildcards(where, core_calls):
    source = pd.DataFrame({"Description": ["first", "second"], "OutdoorElse": ["kept1", "kept2"]})
    result = run("true_false", {"Outdoor*": question("true_false")}, dataframe=source, where=where)
    assert "Outdoor*" in result
    assert "Outdoor*_true_criteria" in result
    assert result["Outdoor*"].tolist() == (["", 0.75] if core_calls else ["", ""])
    assert result["OutdoorElse"].tolist() == ["kept1", "kept2"]


def test_duplicate_destinations_rejected_even_when_where_matches_no_rows(core_calls):
    with pytest.raises(ValueError, match="(?i)(duplicate|unique|collision|already)"):
        run("choose", {"First": question("choose", output=["Same", "Certainty1", "Probs1"]),
                       "Second": question("choose", output=["Same", "Certainty2", "Probs2"])},
            where="Description = 'missing'")
    assert core_calls == []


def test_concurrent_collects_nested_outputs_and_ordinary_wrangle_output(core_calls):
    source = pd.DataFrame({"Description": ["first", "second"], "Severity": [99, 99]})
    result = wrangles.recipe.run({"wrangles": [{"concurrent": {"wrangles": [
        {"ai.choose": {"input": "Description", "questions": {"Category": question("choose")}}},
        {"ai.answers": {"input": "Description", "questions": {
            "Severity": question("score", type="score"),
            "Outdoor": question("true_false", type="true_false"),
        }}},
        {"copy": {"input": "Description", "output": "Copied"}},
    ]}}]}, dataframe=source)

    assert len(core_calls) == 2
    assert result["Category"].tolist() == ["bearing"] * 2
    assert result["Severity"].tolist() == [1.42] * 2
    assert result["Outdoor"].tolist() == [0.75] * 2
    assert result["Copied"].tolist() == ["first", "second"]
    assert set(result) == {"Description", "Severity", "Category", "Category_confidence",
                           "Category_probabilities", "Severity_confidence", "Severity_probabilities",
                           "Outdoor", "Outdoor_true_criteria", "Copied"}


def test_dataframe_accessor_uses_recipe_wrapper_without_mutating_source(core_calls):
    source = wrangles.DataFrame({"Description": ["first"]})
    result = source.wrangles.ai.answers(input="Description", questions={
        "Severity": question("score", type="score"),
        "Outdoor": question("true_false", type="true_false"),
    })
    assert result["Severity"].tolist() == [1.42]
    assert result["Outdoor"].tolist() == [0.75]
    assert source.columns.tolist() == ["Description"]


def test_clean_answers_namespace_has_no_legacy_alias_or_schema_entry():
    accessor = wrangles.DataFrame({"Description": []}).wrangles.ai
    for namespace in (wrangles.ai, recipe_ai, accessor):
        assert callable(namespace.answers)
        assert not hasattr(namespace, "questions")

    schemas = {
        f"ai.{name}": yaml.safe_load(function.__doc__)
        for name, function in inspect.getmembers(recipe_ai, inspect.isfunction)
        if not name.startswith("_")
    }
    assert set(schemas) == {"ai.choose", "ai.score", "ai.true_false", "ai.answers"}
    assert schemas["ai.answers"]["required"] == ["questions"]


def test_wrapper_rejects_response_count_mismatch(monkeypatch):
    monkeypatch.setattr(wrangles.ai, "_run", lambda *args, **kwargs: [])
    with pytest.raises(RuntimeError, match="response count"):
        run("choose", {"Category": question("choose")})


@pytest.mark.parametrize("kind", ["choose", "score", "true_false", "answers"])
def test_schema_exposes_public_parameters_and_accepts_named_questions(kind):
    function = getattr(recipe_ai, kind)
    schema = yaml.safe_load(function.__doc__)
    jsonschema.Draft202012Validator.check_schema(schema)
    assert set(inspect.signature(function).parameters) - {"df"} == set(schema["properties"])
    definition = question("choose" if kind == "answers" else kind)
    if kind == "answers":
        definition["type"] = "choose"
    jsonschema.validate({"questions": {"Question": definition}}, schema)
    definition["output"] = ["wrong length"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"questions": {"Question": definition}}, schema)


def test_declared_output_helper_preserves_ordinary_wrangle_shapes():
    helper = wrangles.recipe._declared_output_columns
    assert helper("copy", {"output": "Copied"}) == ["Copied"]
    assert helper("split.dictionary", {"output": [{"choice": "Category"}, "confidence"]}) == ["Category", "confidence"]
    assert helper("extract.ai", {"output": {"Field": {"type": "string"}}}) == ["Field"]
    assert helper("custom.dynamic", {}) is None


@pytest.fixture
def http_transport(monkeypatch):
    """Exercise the complete runtime, intercepting only the provider HTTP call."""
    for name in list(os.environ):
        if name.startswith(("WRANGLES_AI_CACHE_", "WRANGLES_EXTRACT_AI_CACHE_")):
            monkeypatch.delenv(name)
    monkeypatch.delenv("WRANGLES_AI_CONFIG", raising=False)
    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-recipe-integration-key")
    wrangles.ai_config.clear_cache()
    wrangles.ai_cache.clear()
    calls = []

    class Response:
        status_code = 200
        headers = {}

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

        def close(self):
            pass

    def post(url, **kwargs):
        calls.append({"url": url, **copy.deepcopy(kwargs)})
        request = kwargs["json"]
        first_row = request["state"]["Description"] == "first"
        answers = {}
        for label, definition in reversed(list(request["questions"].items())):
            kind = definition["type"]
            if kind == "choice":
                answers[label] = {
                    "type": "choice", "choice": "bearing" if first_row else "belt",
                    "confidence": 0.8 if first_row else 0.9,
                    "probabilities": {"belt": 0.2 if first_row else 0.85,
                                      "bearing": 0.8 if first_row else 0.15},
                }
            elif kind == "score":
                answers[label] = {
                    "type": "score", "score": 1.42 if first_row else 0.2,
                    "confidence": 0.7,
                    "legend": {"2": "High", "0": "Low", "1": "Medium"},
                    "probabilities": {"2": 0.42 if first_row else 0.0,
                                      "0": 0.0 if first_row else 0.8,
                                      "1": 0.58 if first_row else 0.2},
                }
                if len(definition["criteria"]) == 4:
                    answers[label].update(score=2.77, confidence=0.77,
                                          legend={str(i): criterion for i, criterion in enumerate(definition["criteria"])},
                                          probabilities={"0": 0.01, "1": 0.03, "2": 0.14, "3": 0.82})
            else:
                answers[label] = {"type": "noul", "noul": 0.0 if first_row else 0.6}
        return Response({"model": request["model"], "answers": answers,
                         "usage": {"input_tokens": 24, "output_tokens": 12}})

    monkeypatch.setattr(typesafe._requests, "post", post)
    yield calls
    wrangles.ai_config.clear_cache()
    wrangles.ai_cache.clear()


def test_mixed_recipe_through_http_preserves_native_columns_and_provider_payload(http_transport):
    definitions = {
        "Category": question("choose", type="choose", output=["Picked", "Certainty", "Distribution"]),
        "Severity": question("score", type="score"),
        "Outdoor": {"type": "true_false", "instructions": "Can it be used outdoors?"},
    }
    source = pd.DataFrame({"Description": ["first", "second"], "Excluded": [1, 2]}, index=[12, 4])
    result = run("answers", definitions, dataframe=source, cache=False, threads=1)

    assert result.index.tolist() == [12, 4]
    assert result["Picked"].tolist() == ["bearing", "belt"]
    assert result["Certainty"].tolist() == [0.8, 0.9]
    assert result["Distribution"].tolist() == [{"bearing": 0.8, "belt": 0.2},
                                               {"bearing": 0.15, "belt": 0.85}]
    assert result["Severity"].tolist() == [1.42, 0.2]
    assert result["Severity_probabilities"].tolist() == [
        {"Low": 0.0, "Medium": 0.58, "High": 0.42},
        {"Low": 0.8, "Medium": 0.2, "High": 0.0},
    ]
    assert result["Outdoor"].tolist() == [0.0, 0.6]
    assert result["Outdoor_true_criteria"].tolist() == ["", ""]
    assert len(http_transport) == 2
    assert [call["json"]["state"] for call in http_transport] == [
        {"Description": "first"}, {"Description": "second"},
    ]
    for call in http_transport:
        assert call["url"] == "https://api.typesafe.ai/v1/systemone"
        assert call["headers"]["Authorization"] == "Bearer synthetic-recipe-integration-key"
        assert set(call["json"]) == {"state", "model", "questions"}
        assert call["json"]["questions"] == {
            "Category": {"type": "choice", "instructions": definitions["Category"]["instructions"],
                         "criteria": {"bearing": "A bearing", "belt": "A belt"}},
            "Severity": {"type": "score", "instructions": definitions["Severity"]["instructions"],
                         "criteria": ["Low", "Medium", "High"]},
            "Outdoor": {"type": "noul", "instructions": "Can it be used outdoors?"},
        }


def test_homogeneous_recipe_through_http_batches_both_named_questions_per_row(http_transport):
    definitions = {
        "Category": question("choose"),
        "Alternate": question("choose", output=["Alternative", "Alternative Confidence", "Alternative Probabilities"]),
    }
    result = run("choose", definitions, cache=False, threads=1)

    assert len(http_transport) == 2
    assert result["Category"].tolist() == ["bearing", "belt"]
    assert result["Alternative"].tolist() == ["bearing", "belt"]
    assert result["Category_probabilities"].tolist() == result["Alternative Probabilities"].tolist()
    assert result["Category_confidence"].tolist() == [0.8, 0.9]
    for call in http_transport:
        assert set(call["json"]) == {"state", "model", "questions"}
        assert set(call["json"]["questions"]) == {"Category", "Alternate"}
        for definition in call["json"]["questions"].values():
            assert definition == {
                "type": "choice", "instructions": "Evaluate the supplied product.",
                "criteria": {"bearing": "A bearing", "belt": "A belt"},
            }


def repeat_question(kind="score", **overrides):
    return question(kind, for_each={"values": "CandidateCategories", "variable": "category"},
                    instructions="Evaluate {{ category }} for {{ Manufacturer_Name }}.", **overrides)


@pytest.mark.parametrize("kind", ["choose", "score", "true_false", "answers"])
def test_recipe_templates_read_other_columns_and_return_one_grouped_output(kind, http_transport):
    question_kind = "score" if kind == "answers" else kind
    definition = repeat_question(question_kind)
    if kind == "answers":
        definition["type"] = question_kind
    source = pd.DataFrame({"Description": ["first", "second", "empty list", "empty dict"],
                           "Manufacturer Name": ["Acme", "Other", "Neither", "Neither"],
                           "CandidateCategories": [["Containers", "Shelves"], {"category_2": "Storage"}, [], {}]},
                          index=[12, 4, 19, 23])
    original = source.copy(deep=True)
    result = run(kind, {"fits": definition}, dataframe=source, cache=False, threads=1)

    assert result.index.tolist() == [12, 4, 19, 23]
    assert result.columns.tolist() == [*original.columns, "fits"]
    assert len(http_transport) == 2
    assert [call["json"]["state"] for call in http_transport] == [{"Description": "first"}, {"Description": "second"}]
    assert [q["instructions"] for q in http_transport[0]["json"]["questions"].values()] == [
        "Evaluate Containers for Acme.", "Evaluate Shelves for Acme."]
    assert [q["instructions"] for q in http_transport[1]["json"]["questions"].values()] == ["Evaluate Storage for Other."]
    assert [entry["value"] for entry in result["fits"].iloc[0]] == ["Containers", "Shelves"]
    assert list(result["fits"].iloc[1]) == ["category_2"]
    assert result["fits"].iloc[1]["category_2"]["value"] == "Storage"
    fields = {"choose": {"choice", "confidence", "probabilities"},
              "score": {"score", "confidence", "probabilities"},
              "true_false": {"probability_true", "true_criteria"}}[question_kind]
    assert set(result["fits"].iloc[1]["category_2"]) == {"value", *fields}
    assert result["fits"].iloc[2] == []
    assert result["fits"].iloc[3] == {}
    pd.testing.assert_frame_equal(source[original.columns], original)


@pytest.mark.parametrize("kind", ["choose", "score", "true_false", "answers"])
def test_recipe_blank_candidate_slots_keep_collection_shape_and_skip_provider_questions(kind, http_transport):
    question_kind = "score" if kind == "answers" else kind
    definition = repeat_question(question_kind)
    if kind == "answers":
        definition["type"] = question_kind
    source = pd.DataFrame({
        "Description": ["first", "second", "blank list", "blank dict"],
        "Manufacturer Name": ["Acme", "Other", "Neither", "Neither"],
        "CandidateCategories": [
            ["", "Containers", " \t"],
            {"category_1": "", "category_2": "Storage", "category_3": "  "},
            ["", "\n"],
            {"category_1": "", "category_2": "  "},
        ],
    }, index=[12, 4, 19, 23])

    result = run(kind, {"fits": definition}, dataframe=source, cache=False, threads=1)

    assert result.index.tolist() == [12, 4, 19, 23]
    assert len(http_transport) == 2
    assert [len(call["json"]["questions"]) for call in http_transport] == [1, 1]
    assert [next(iter(call["json"]["questions"].values()))["instructions"] for call in http_transport] == [
        "Evaluate Containers for Acme.", "Evaluate Storage for Other."]
    assert result["fits"].iloc[0][0] == result["fits"].iloc[0][2] == {}
    assert result["fits"].iloc[0][1]["value"] == "Containers"
    assert list(result["fits"].iloc[1]) == ["category_1", "category_2", "category_3"]
    assert result["fits"].iloc[1]["category_1"] == result["fits"].iloc[1]["category_3"] == {}
    assert result["fits"].iloc[1]["category_2"]["value"] == "Storage"
    assert result["fits"].iloc[2] == [{}, {}]
    assert result["fits"].iloc[3] == {"category_1": {}, "category_2": {}}


def test_recipe_row_templates_without_loop_read_full_row_but_send_selected_input(http_transport):
    source = pd.DataFrame({"Description": ["first", "second"], "Proposed Category": ["Containers", "Shelves"]})
    result = run("score", {"fit": question("score", instructions="Fit for {{ Proposed_Category }}?")},
                 dataframe=source, cache=False, threads=1)
    assert result["fit"].tolist() == [1.42, 0.2]
    assert [call["json"]["questions"]["fit"]["instructions"] for call in http_transport] == [
        "Fit for Containers?", "Fit for Shelves?"]
    assert [call["json"]["state"] for call in http_transport] == [{"Description": "first"}, {"Description": "second"}]


def test_recipe_template_cache_includes_row_context_only_when_it_changes_questions(http_transport):
    source = pd.DataFrame({"Description": ["first"] * 3, "Manufacturer Name": ["Acme", "Other", "Acme"],
                           "CandidateCategories": [["Containers"], ["Shelves"], ["Containers"]],
                           "Unused": [1, 2, 3]})
    result = run("score", {"fits": repeat_question()}, dataframe=source, threads=1)
    assert len(http_transport) == 2
    assert [value[0]["value"] for value in result["fits"]] == ["Containers", "Shelves", "Containers"]
    assert all(call["json"]["state"] == {"Description": "first"} for call in http_transport)


def test_where_templates_resolve_only_selected_rows_and_preserve_other_values(http_transport):
    source = pd.DataFrame({"Description": ["first", "second"], "Manufacturer Name": [None, "Other"],
                           "CandidateCategories": [None, {"category_2": "Shelves"}], "Category Fits": ["keep", "replace"]},
                          index=[9, 3])
    result = run("score", {"fits": repeat_question(output="Category Fits")}, dataframe=source,
                 where="Description = 'second'", cache=False, threads=1)
    assert result.index.tolist() == [9, 3]
    assert result["Category Fits"].iloc[0] == "keep"
    assert result["Category Fits"].iloc[1]["category_2"]["value"] == "Shelves"
    assert len(http_transport) == 1
    assert http_transport[0]["json"]["state"] == {"Description": "second"}


@pytest.mark.parametrize("empty", [False, True])
def test_no_selected_rows_discover_grouped_destinations_without_resolving_templates(empty, core_calls):
    source = pd.DataFrame({"Description": [] if empty else ["first"]})
    options = {} if empty else {"where": "Description = 'missing'"}
    result = run("answers", {"fits": repeat_question(type="score", output=["Category Fits"]),
                             "ordinary": question("true_false", type="true_false")},
                 dataframe=source, **options)
    assert core_calls == []
    assert result.columns.tolist() == ["Description", "Category Fits", "ordinary", "ordinary_true_criteria"]
    if not empty:
        assert result["Category Fits"].tolist() == [""]


def test_concurrent_collects_repeated_outputs_with_fixed_outputs(http_transport):
    source = pd.DataFrame({"Description": ["first"], "Manufacturer Name": ["Acme"],
                           "CandidateCategories": [{"category_1": "Containers"}]})
    recipe = {"wrangles": [{"concurrent": {"wrangles": [
        {"ai.score": {"input": "Description", "questions": {"fits": repeat_question(output="Category Fits")}, "cache": False}},
        {"ai.true_false": {"input": "Description", "questions": {"Outdoor": question("true_false")}, "cache": False}},
        {"copy": {"input": "Description", "output": "Copied"}},
    ]}}]}
    result = wrangles.recipe.run(recipe, dataframe=source)
    assert len(http_transport) == 2
    assert result["Category Fits"].iloc[0]["category_1"]["value"] == "Containers"
    assert result["Outdoor"].tolist() == [0.0]
    assert result["Copied"].tolist() == ["first"]


def test_template_destination_collision_is_rejected_for_no_match_recipe(core_calls):
    with pytest.raises(ValueError, match="(?i)(unique|duplicate|collision)"):
        run("score", {"fits": repeat_question(output="fixed_confidence"), "fixed": question("score")},
            where="Description = 'missing'")
    assert core_calls == []


@pytest.mark.parametrize("kind", ["choose", "score", "true_false", "answers"])
@pytest.mark.parametrize("output", [None, "", "Category Fits", ["Category Fits"]])
def test_schema_accepts_column_expansion_and_single_grouped_output(kind, output):
    definition = repeat_question("score" if kind == "answers" else kind, output=output)
    if kind == "answers":
        definition["type"] = "score"
    schema = yaml.safe_load(getattr(recipe_ai, kind).__doc__)
    jsonschema.validate({"input": "Description", "questions": {"fits": definition}}, schema)


@pytest.mark.parametrize("for_each", [None, {}, {"values": "CandidateCategories"},
    {"values": ["Containers"], "variable": "category"},
    {"values": {"category_1": "Containers"}, "variable": "category"},
    {"values": "CandidateCategories", "variable": "Category Name"},
    {"values": "CandidateCategories", "variable": "category", "extra": True}])
def test_schema_rejects_invalid_expansion_source_or_variable(for_each):
    schema = yaml.safe_load(recipe_ai.score.__doc__)
    definition = question("score", for_each=for_each)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"questions": {"fits": definition}}, schema)


@pytest.mark.parametrize("output", [[], ["one", "two"], ["one", "two", "three"], [""], 1])
def test_schema_rejects_multi_column_expanded_outputs(output):
    schema = yaml.safe_load(recipe_ai.score.__doc__)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"questions": {"fits": repeat_question(output=output)}}, schema)


def test_category_template_example_splits_dictionary_answers_with_blank_placeholders(http_transport):
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "ai_question_templates"
    source = pd.DataFrame(json.loads((fixture / "products.json").read_text(encoding="utf-8")))
    recipe = yaml.safe_load((fixture / "ai_category_judge.recipe").read_text(encoding="utf-8"))
    assert [next(iter(step)) for step in recipe["wrangles"]] == ["ai.score", "split.dictionary"]
    assert list(recipe["wrangles"][0]["ai.score"]["questions"]) == ["category_fit"]
    recipe["wrangles"][0]["ai.score"].update(cache=False, threads=1)
    result = wrangles.recipe.run(recipe, dataframe=source)

    assert len(http_transport) == 2
    assert [len(call["json"]["questions"]) for call in http_transport] == [3, 2]
    assert [len(row) for row in result["category_fit"]] == [3, 3, 0]
    assert [list(row) for row in result["category_fit"]] == [
        ["category_1", "category_2", "category_3"], ["category_1", "category_2", "category_3"], []]
    assert all(isinstance(row, dict) for row in result["category_fit"])
    assert "list_fit" not in result
    assert "category_1_score" not in result
    assert [answer["value"] for answer in result["category_1"].iloc[:2]] == ["Containers", "Shelving Units"]
    assert [answer["score"] for answer in result["category_1"].iloc[:2]] == [2.77, 2.77]
    assert result["category_2"].iloc[0]["value"] == "Shelves"
    assert result["category_2"].iloc[1]["value"] == "Storage Cabinets"
    assert result["category_3"].iloc[0]["value"] == "Food Storage Containers"
    assert result["category_3"].iloc[1] == {}
    assert len(result["category_1"].iloc[0]["probabilities"]) == 4
    assert result["category_1"].iloc[2] == ""
    assert result["category_fit"].iloc[2] == {}
    for call in http_transport:
        assert list(call["json"]["state"]) == ["Description"]
        assert all("{{" not in definition["instructions"] for definition in call["json"]["questions"].values())


def test_unused_context_cells_need_not_be_json_when_provider_input_is_selected(http_transport):
    source = pd.DataFrame({"Description": ["first"], "Manufacturer Name": ["Acme"],
                           "CandidateCategories": [["Containers"]],
                           "Timestamp": [pd.Timestamp("2026-09-28")], "Missing": [float("nan")],
                           "Local Object": [object()]})
    result = run("score", {"fits": repeat_question()}, dataframe=source, cache=False)
    assert result["fits"].iloc[0][0]["value"] == "Containers"
    assert len(http_transport) == 1
    assert http_transport[0]["json"]["state"] == {"Description": "first"}


@pytest.mark.parametrize("row_index,expected_calls", [(1, 1), (2, 0)])
def test_category_template_example_handles_padded_and_empty_only_trial_slices(row_index, expected_calls, http_transport):
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "ai_question_templates"
    source = pd.DataFrame(json.loads((fixture / "products.json").read_text(encoding="utf-8")))[row_index:row_index + 1]
    recipe = yaml.safe_load((fixture / "ai_category_judge.recipe").read_text(encoding="utf-8"))
    recipe["wrangles"][0]["ai.score"].update(cache=False, threads=1)
    result = wrangles.recipe.run(recipe, dataframe=source)
    assert len(http_transport) == expected_calls
    assert "list_fit" not in result
    if row_index == 1:
        assert list(result["category_fit"].iloc[0]) == ["category_1", "category_2", "category_3"]
        assert result["category_1"].iloc[0]["value"] == "Shelving Units"
        assert result["category_2"].iloc[0]["value"] == "Storage Cabinets"
        assert result["category_3"].iloc[0] == {}
        assert len(http_transport[0]["json"]["questions"]) == 2
    else:
        assert result["category_fit"].tolist() == [{}]
        assert "category_1" not in result
        assert "category_2" not in result
        assert "category_3" not in result


@pytest.mark.parametrize("full_results", [False, True])
def test_category_template_runner_uses_anchored_paths_and_prints_nested_results(full_results, http_transport, monkeypatch, tmp_path, capsys):
    runner = Path(__file__).resolve().parents[2] / "fixtures" / "ai_question_templates" / "run.py"
    monkeypatch.chdir(tmp_path)
    args = [str(runner), "--all-rows"]
    if full_results:
        args.append("--full-results")
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.setattr(sys, "path", list(sys.path))
    runpy.run_path(str(runner), run_name="__main__")
    output = capsys.readouterr().out
    assert "Scoring 3" in output
    assert "category_fit" in output
    assert "category_1" in output
    assert "Containers" in output
    assert "probabilities" in output
    assert "list_fit" not in output
    assert ("CandidateCategories" in output) is full_results
    assert len(http_transport) == 2
