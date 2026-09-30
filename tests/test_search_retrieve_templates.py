"""Credential-free contracts for recipe URL retrieval prompt variables."""

import json
import threading
from types import SimpleNamespace

import jsonschema
import pandas as pd
import pytest
import yaml

import wrangles
from wrangles import ai_config, search
from wrangles.clients import gemini
from wrangles.recipe_wrangles import search as recipe_search


@pytest.fixture(autouse=True)
def retrieval_configuration(monkeypatch, tmp_path):
    monkeypatch.delenv("WRANGLES_AI_CONFIG", raising=False)
    ai_config.clear_cache()
    config = ai_config.load()
    config["operations"]["search.retrieve_link_content"]["defaults"].update({
        "default_concurrency": 2,
        "request_timeout_seconds": 3.25,
        "retries": 0,
        "temperature": 0.17,
    })
    config["providers"]["google"]["endpoints"]["base_url"] = "https://google.example/gemini"
    path = tmp_path / "ai.yml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setenv("WRANGLES_AI_CONFIG", str(path))
    ai_config.clear_cache()
    yield
    ai_config.clear_cache()


def _run(dataframe, **options):
    return wrangles.recipe.run({"wrangles": [{"search.retrieve_link_content": {
        "input": "URL", "output": "results", "api_key": "fake-key", **options,
    }}]}, dataframe=dataframe)


def _response(url, prompt):
    return {
        "retrieved_url": url,
        "status": "Success",
        "error": None,
        "extracted_content": {"prompt": prompt},
    }


@pytest.fixture
def retrieval_calls(monkeypatch):
    calls = {"clients": [], "requests": []}

    def retrieve(**kwargs):
        calls["requests"].append(kwargs)
        return _response(kwargs["url"], kwargs["prompt"])

    def get_client(client, config):
        calls["clients"].append((client, config))
        return SimpleNamespace(retrieve=retrieve)

    monkeypatch.setattr(search, "_get_client", get_client)
    return calls


def test_recipe_prompt_uses_full_original_row(retrieval_calls):
    frame = pd.DataFrame({
        "URL": ["https://product.example/one", "https://product.example/two"],
        "Item Details": ["Brass fitting", "Steel bearing"],
        "product_attribute_dictionary": [{"diameter": [1, 2]}, {"material": "steel"}],
    }, index=[17, 4])
    result = _run(frame, prompt="For {{ Item_Details }} verify {{ product_attribute_dictionary }}")
    assert [cell[0]["extracted_content"]["prompt"] for cell in result["results"]] == [
        'For Brass fitting verify {"diameter":[1,2]}',
        'For Steel bearing verify {"material":"steel"}',
    ]
    assert result.index.tolist() == [17, 4]
    assert result["Item Details"].tolist() == ["Brass fitting", "Steel bearing"]
    assert len(retrieval_calls["clients"]) == 1


@pytest.mark.parametrize("value", [
    {"{{ missing }}": ["{{ missing }}", {"Unicode": "café", "enabled": True, "empty": None}]},
    ["α", 2, 1.25, False, None, {"nested": ["value"]}],
    {}, [], 42, 1.25, True, None,
])
def test_exact_variable_serializes_finite_json_without_templating_data(retrieval_calls, value):
    _run(pd.DataFrame({"URL": ["https://product.example/one"], "attributes": [value]}),
         prompt="{{ attributes }}")
    assert json.loads(retrieval_calls["requests"][0]["prompt"]) == value


@pytest.mark.parametrize("missing", [False, True])
def test_nullable_dataframe_scalars_render_as_json_values(retrieval_calls, missing):
    frame = pd.DataFrame({
        "URL": ["https://product.example/one", "https://product.example/two"],
        "count": pd.Series([4, pd.NA if missing else 5], dtype="Int64"),
        "length": pd.Series([1.25, pd.NA if missing else 2.5], dtype="Float64"),
        "available": pd.Series([True, pd.NA if missing else False], dtype="boolean"),
    })
    if missing:
        # The recipe engine's unrelated final fillna('') does not support
        # nullable numerical columns, so check missing values at the adapter.
        result = recipe_search.retrieve_link_content(
            frame, input="URL", output="results", prompt="[{{count}},{{length}},{{available}}]",
        )
    else:
        result = _run(frame, prompt="[{{count}},{{length}},{{available}}]")
    assert [json.loads(cell[0]["extracted_content"]["prompt"]) for cell in result["results"]] == [
        [4, 1.25, True], [None, None, None] if missing else [5, 2.5, False],
    ]


def test_string_substitution_is_literal_single_pass(retrieval_calls):
    value = '{{ missing }} \\1 $1 "quoted"\nsecond line'
    _run(pd.DataFrame({"URL": ["https://product.example/one"], "details": [value]}),
         prompt="{{details}} / {{ details }}")
    assert retrieval_calls["requests"][0]["prompt"] == f"{value} / {value}"


def test_alias_normalization_replaces_each_non_ascii_character(retrieval_calls):
    _run(pd.DataFrame({
        "URL": ["https://product.example/one"],
        "Item / Details": ["brass"], "café": ["Unicode"], "_size2": ["small"],
    }), prompt="{{ Item___Details }} {{ caf_ }} {{_size2}}")
    assert retrieval_calls["requests"][0]["prompt"] == "brass Unicode small"


@pytest.mark.parametrize("placeholder", [
    "missing", "details.upper()", "details | upper", "details[0]", "1details", "café", "",
])
def test_bad_references_fail_before_creating_provider(retrieval_calls, placeholder):
    frame = pd.DataFrame({"URL": ["https://product.example/one"], "details": ["brass"]})
    with pytest.raises(ValueError):
        _run(frame, prompt="{{ " + placeholder + " }}")
    assert retrieval_calls == {"clients": [], "requests": []}


def test_referenced_ambiguous_alias_fails_before_provider(retrieval_calls):
    frame = pd.DataFrame({
        "URL": ["https://product.example/one"], "Item Details": ["one"], "Item-Details": ["two"],
    })
    with pytest.raises(ValueError, match="ambiguous"):
        _run(frame, prompt="{{ Item_Details }}")
    assert retrieval_calls == {"clients": [], "requests": []}


def test_exact_duplicate_source_column_name_is_ambiguous(retrieval_calls):
    frame = pd.DataFrame([["https://product.example/one", "first", "second"]],
                         columns=["URL", "details", "details"])
    with pytest.raises(ValueError, match="ambiguous"):
        recipe_search.retrieve_link_content(frame, input="URL", output="results", prompt="{{ details }}")
    assert retrieval_calls == {"clients": [], "requests": []}


def test_unreferenced_ambiguous_and_invalid_columns_do_not_break_prompt(retrieval_calls):
    _run(pd.DataFrame({
        "URL": ["https://product.example/one"], "Item Details": ["one"],
        "Item-Details": ["two"], "1leading": [object()], "details": ["wanted"],
    }), prompt="{{ details }}")
    assert retrieval_calls["requests"][0]["prompt"] == "wanted"


@pytest.mark.parametrize("invalid", [
    float("nan"), float("inf"), {"nested": [float("-inf")]},
    {1: "integer key"}, {"nested": {1: "integer key"}}, ("tuple",), {"set"},
])
def test_invalid_value_in_later_row_fails_before_any_provider_call(retrieval_calls, invalid):
    frame = pd.DataFrame({
        "URL": ["https://product.example/one", "https://product.example/two"],
        "details": ["valid", invalid],
    })
    with pytest.raises(ValueError, match="JSON"):
        _run(frame, prompt="{{ details }}")
    assert retrieval_calls == {"clients": [], "requests": []}


def test_circular_value_fails_before_provider(retrieval_calls):
    value = []
    value.append(value)
    with pytest.raises(ValueError, match="JSON"):
        _run(pd.DataFrame({"URL": ["https://product.example/one"], "details": [value]}),
             prompt="{{ details }}")
    assert retrieval_calls == {"clients": [], "requests": []}


def test_url_lists_dictionaries_blanks_and_dual_outputs_remain_aligned(retrieval_calls):
    first, second, third = [f"https://product.example/{number}" for number in (1, 2, 3)]
    result = _run(pd.DataFrame({
        "URL": [
            [None, "", {"summary": {"link": first}}, {"url": second}],
            None,
            ({"link": third}, "  "),
            "",
        ],
        "details": ["first", "blank", "third", "empty"],
    }), prompt="{{ details }}", output=["results", "text"])
    assert [[item["retrieved_url"] for item in cell] for cell in result["results"]] == [
        [first, second], [], [third], [],
    ]
    assert [[item["extracted_content"]["prompt"] for item in cell] for cell in result["results"]] == [
        ["first", "first"], [], ["third"], [],
    ]
    assert result["text"].iloc[0].index(first) < result["text"].iloc[0].index(second)
    assert "prompt: first" in result["text"].iloc[0]
    assert "prompt: third" in result["text"].iloc[2]
    assert result["text"].iloc[1] == result["text"].iloc[3] == ""
    assert len(retrieval_calls["requests"]) == 3


def test_multiple_inputs_use_prompts_from_before_output_assignment(retrieval_calls):
    result = _run(pd.DataFrame({
        "URL": ["https://product.example/a", None],
        "other_url": ["https://product.example/b", "https://product.example/c"],
        "details": ["original one", "original two"],
    }), input=["URL", "other_url"], output=["details", "other_results"], prompt="{{ details }}")
    assert result["details"].iloc[0][0]["extracted_content"]["prompt"] == "original one"
    assert result["details"].iloc[1] == []
    assert [cell[0]["extracted_content"]["prompt"] for cell in result["other_results"]] == [
        "original one", "original two",
    ]


def test_output_overwriting_later_input_keeps_original_urls_and_prompts(retrieval_calls):
    first, second = "https://product.example/first", "https://product.example/second"
    result = _run(pd.DataFrame({"URL": [first], "second_url": [second]}),
                  input=["URL", "second_url"], output=["second_url", "results"],
                  prompt="Verify {{ second_url }}")
    assert result["second_url"].iloc[0][0]["retrieved_url"] == first
    assert result["results"].iloc[0][0]["retrieved_url"] == second
    assert all(call["prompt"] == f"Verify {second}" for call in retrieval_calls["requests"])


def test_all_blank_urls_skip_provider_and_preserve_output_shape(retrieval_calls):
    result = _run(pd.DataFrame({"URL": [None, "", [], ()], "details": ["x"] * 4}),
                  prompt="{{ details }}", output=["results", "text"])
    assert result["results"].tolist() == [[], [], [], []]
    assert result["text"].tolist() == ["", "", "", ""]
    assert retrieval_calls == {"clients": [], "requests": []}


@pytest.mark.parametrize("prompt", [None, "", "Retrieve the specs; use JSON {\"key\": \"value\"}."])
def test_unchanged_recipe_prompts_reach_client_unchanged(retrieval_calls, prompt):
    _run(pd.DataFrame({"URL": ["https://product.example/one"]}), prompt=prompt)
    assert retrieval_calls["requests"][0]["prompt"] == prompt


@pytest.mark.parametrize("urls", ["https://product.example/one", ["https://product.example/one"]])
def test_direct_python_retrieval_preserves_literal_prompt_and_return_shape(retrieval_calls, urls):
    prompt = "Keep {{ missing }} literal for direct Python callers."
    result = search.retrieve_link_content(urls, prompt=prompt, model_id="custom-model", threads=1,
                                          output_format="markdown", client_config={"api_key": "fake-key"})
    scalar = isinstance(urls, str)
    assert isinstance(result, dict if scalar else list)
    assert retrieval_calls["requests"] == [{
        "url": urls if scalar else urls[0], "prompt": prompt,
        "model_id": "custom-model", "output_format": "markdown",
    }]


@pytest.mark.parametrize("caller", ["python", "recipe"])
def test_retrieval_options_reach_google_with_aligned_url_prompts(monkeypatch, caller):
    calls = []

    def retrieve(self, url, prompt, output_format, policy, **kwargs):
        calls.append({"url": url, "prompt": prompt, "policy": policy, "options": kwargs})
        return _response(url, prompt)

    monkeypatch.setattr(gemini.GeminiURLContextClient, "_retrieve", retrieve)
    urls = [f"https://product.example/{number}" for number in range(3)]
    options = {
        "thinking_level": "low",
        "request_timeout_seconds": 1.5,
        "max_output_tokens": 256,
        "response_schema": {
            "type": "object", "properties": {"title": {"type": "string"}},
        },
    }
    if caller == "python":
        results = search.retrieve_link_content(
            urls, prompt="Keep {{ details }} literal", threads=1,
            client_config={"api_key": "fake-key"}, **options,
        )
        prompts = ["Keep {{ details }} literal"] * 3
    else:
        result = _run(pd.DataFrame({
            "URL": [urls[:2], [], urls[2:]],
            "details": ["first row", "blank row", "last row"],
        }), prompt="Verify {{ details }}", threads=1, **options)
        assert [len(cell) for cell in result["results"]] == [2, 0, 1]
        results = [item for cell in result["results"] for item in cell]
        prompts = ["Verify first row", "Verify first row", "Verify last row"]

    assert [item["retrieved_url"] for item in results] == urls
    assert [item["extracted_content"]["prompt"] for item in results] == prompts
    assert [call["url"] for call in calls] == urls
    assert [call["prompt"] for call in calls] == prompts
    for call in calls:
        assert call["policy"]["thinking_level"] == "low"
        assert call["policy"]["request_timeout_seconds"] == 1.5
        assert call["options"] == {
            "max_output_tokens": 256, "response_schema": options["response_schema"],
        }


@pytest.mark.parametrize("caller", ["python", "recipe"])
@pytest.mark.parametrize("options", [
    {},
    {"thinking_level": None, "request_timeout_seconds": None},
    {"thinking_level": "minimal"},
    {"request_timeout_seconds": 2.5},
    {"thinking_level": "low", "request_timeout_seconds": 4, "max_output_tokens": 128},
])
def test_custom_retrievers_receive_only_explicit_options(retrieval_calls, caller, options):
    url = "https://product.example/one"
    if caller == "python":
        result = search.retrieve_link_content(
            url, prompt="Page title", model_id="custom-model", **options,
        )
    else:
        result = _run(pd.DataFrame({"URL": [url]}),
                      prompt="Page title", model_id="custom-model", **options)["results"].iloc[0][0]
    assert result["extracted_content"] == {"prompt": "Page title"}
    assert retrieval_calls["requests"] == [{
        "url": url, "prompt": "Page title", "model_id": "custom-model", "output_format": "json",
        **{key: value for key, value in options.items() if value is not None},
    }]


def test_retrieval_schema_accepts_runtime_overrides_and_additional_sdk_options():
    schema = yaml.safe_load(recipe_search.retrieve_link_content.__doc__)
    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.validate({
        "input": "URL", "output": "results", "prompt": "Verify {{ details }}",
        "thinking_level": "minimal", "request_timeout_seconds": 10,
        "max_output_tokens": 256,
        "response_schema": {"type": "object", "properties": {"title": {"type": "string"}}},
    }, schema)
    assert {"thinking_level", "request_timeout_seconds"} <= schema["properties"].keys()


@pytest.mark.parametrize("threads", [None, 2])
def test_row_prompts_share_one_bounded_parallel_batch(monkeypatch, threads):
    calls = []
    policy_calls = []
    client_calls = []
    resolve = ai_config.resolve
    lock = threading.Lock()
    barrier = threading.Barrier(2)
    active = maximum = 0

    def resolve_once(*args, **kwargs):
        policy_calls.append(args)
        return resolve(*args, **kwargs)

    def retrieve(**kwargs):
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(maximum, active)
            calls.append(kwargs)
        try:
            barrier.wait(timeout=5)
            return _response(kwargs["url"], kwargs["prompt"])
        finally:
            with lock:
                active -= 1

    def get_client(client, config):
        client_calls.append((client, config))
        return SimpleNamespace(retrieve=retrieve)

    monkeypatch.setattr(search, "_get_client", get_client)
    monkeypatch.setattr(ai_config, "resolve", resolve_once)
    urls = [f"https://product.example/{i}" for i in range(4)]
    result = _run(pd.DataFrame({"URL": [urls[:2], urls[2:]], "details": ["first", "second"]}),
                  prompt="{{ details }}", threads=threads, model_id="custom-model", output_format="markdown")
    assert maximum == 2
    assert len(policy_calls) == len(client_calls) == 1
    assert client_calls == [("google_url_context", {"api_key": "fake-key"})]
    assert [item["retrieved_url"] for cell in result["results"] for item in cell] == urls
    assert [item["extracted_content"]["prompt"] for cell in result["results"] for item in cell] == [
        "first", "first", "second", "second",
    ]
    assert all(call["model_id"] == "custom-model" and call["output_format"] == "markdown" for call in calls)


def test_out_of_order_provider_completion_preserves_row_order(monkeypatch):
    second_finished = threading.Event()
    finished = []
    first, second = "https://product.example/first", "https://product.example/second"

    def retrieve(**kwargs):
        if kwargs["url"] == first:
            assert second_finished.wait(timeout=5), "The second URL was not processed concurrently."
            finished.append(first)
        else:
            finished.append(second)
            second_finished.set()
        return _response(kwargs["url"], kwargs["prompt"])

    monkeypatch.setattr(search, "_get_client", lambda *args: SimpleNamespace(retrieve=retrieve))
    result = _run(pd.DataFrame({"URL": [first, second], "details": ["first row", "second row"]}),
                  prompt="{{ details }}", threads=2)
    assert finished == [second, first]
    assert [cell[0]["retrieved_url"] for cell in result["results"]] == [first, second]
    assert [cell[0]["extracted_content"]["prompt"] for cell in result["results"]] == [
        "first row", "second row",
    ]


@pytest.mark.parametrize("output_format,mime_type", [("json", "application/json"), ("markdown", "text/plain")])
def test_row_prompts_and_options_reach_real_google_sdk_without_network(monkeypatch, output_format, mime_type):
    import httpx
    from google import genai
    from google.genai import _api_client, errors, types

    requests = []
    client_options = []
    clients = []

    async def send(client, request, **kwargs):
        requests.append(request)
        return httpx.Response(200, request=request, json={
            "candidates": [{"content": {"parts": [{"text": '{"name":"synthetic"}'}]}}],
        })

    def client(**kwargs):
        client_options.append(kwargs)
        instance = genai.Client(vertexai=False, **kwargs)
        clients.append(instance)
        return instance

    monkeypatch.setattr(_api_client, "has_aiohttp", False)
    monkeypatch.setattr(httpx.AsyncClient, "send", send)
    monkeypatch.setattr(gemini, "_get_genai", lambda: (SimpleNamespace(Client=client), types, errors))
    try:
        result = _run(pd.DataFrame({
            "URL": ["https://product.example/one", "https://product.example/two"],
            "details": ["brass fitting", "steel bearing"],
        }), prompt="Verify {{ details }}", output_format=output_format, threads=1,
                      model_id="models/private-google-model", thinking_level="low",
                      request_timeout_seconds=1.5, max_output_tokens=256, seed=17)
        bodies = [json.loads(request.content) for request in requests]
        assert len(bodies) == 2
        for request, body, details in zip(requests, bodies, ["brass fitting", "steel bearing"]):
            assert str(request.url) == "https://google.example/gemini/v1beta/models/private-google-model:generateContent"
            assert body["systemInstruction"]["parts"][0]["text"].startswith(f"Verify {details}\n\n")
            assert body["generationConfig"]["responseMimeType"] == mime_type
            assert body["generationConfig"]["temperature"] == 0.17
            thinking = body["generationConfig"]["thinkingConfig"]
            assert thinking.get("thinkingLevel", thinking.get("thinking_level")) == "LOW"
            assert body["generationConfig"]["maxOutputTokens"] == 256
            assert body["generationConfig"]["seed"] == 17
            assert body["tools"] == [{"urlContext": {}}]
        assert "https://product.example/one" in bodies[0]["contents"][0]["parts"][0]["text"]
        assert "https://product.example/two" in bodies[1]["contents"][0]["parts"][0]["text"]
        assert all(options["http_options"].timeout == 1500 for options in client_options)
        assert all(options["http_options"].retry_options.attempts == 1 for options in client_options)
        assert all(cell[0]["error"] is None for cell in result["results"])
    finally:
        for instance in clients:
            instance.close()
