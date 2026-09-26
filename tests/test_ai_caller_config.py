"""Offline contracts for configuration-backed embeddings and URL retrieval."""

import base64
import copy
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import requests
import yaml

import wrangles
from wrangles import ai_config, openai, search
from wrangles.clients import gemini


def _chat_settings():
    return {
        "model": "private-chat-model",
        "temperature": 0.7,
        "messages": [{"role": "system", "content": "Use the supplied input."}],
        "tools": [{"type": "function", "function": {
            "name": "parse_output", "parameters": {
                "type": "object", "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        }}],
    }


@pytest.fixture
def chat_transport(monkeypatch):
    calls = []

    def post(**kwargs):
        calls.append(copy.deepcopy(kwargs))
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({"choices": [{"message": {"tool_calls": [{
            "function": {"arguments": '{"value":"synthetic"}'},
        }]}}]}).encode("utf-8")
        return response

    monkeypatch.setattr(openai._requests, "post", post)
    return calls


@pytest.fixture
def configured_ai(monkeypatch, tmp_path):
    monkeypatch.delenv("WRANGLES_AI_CONFIG", raising=False)
    ai_config.clear_cache()
    config = ai_config.load()
    config["operations"]["embeddings"]["defaults"].update({
        "default_concurrency": 1,
        "request_timeout_seconds": 7.25,
        "retries": 2,
        "batch_size": 1,
        "precision": "float16",
    })
    config["operations"]["search.retrieve_link_content"]["defaults"].update({
        "default_concurrency": 1,
        "request_timeout_seconds": 3.25,
        "temperature": 0,
    })
    config["providers"]["openai"]["endpoints"]["embeddings"] = "https://openai.example/embeddings"
    config["providers"]["jina"]["endpoints"]["embeddings"] = "https://jina.example/embeddings"
    config["providers"]["google"]["endpoints"]["base_url"] = "https://google.example/gemini"
    path = tmp_path / "ai.yml"

    def save():
        path.write_text(yaml.safe_dump(config), encoding="utf-8")
        ai_config.clear_cache()

    save()
    monkeypatch.setenv("WRANGLES_AI_CONFIG", str(path))
    yield config, save
    ai_config.clear_cache()


def test_private_chat_transport_skips_resolution(chat_transport, monkeypatch):
    def unexpected_resolution(*args, **kwargs):
        raise AssertionError("Resolved options must not trigger another catalog lookup per row.")

    monkeypatch.setattr(ai_config, "resolve", unexpected_resolution)
    monkeypatch.setattr(ai_config, "model_defaults", unexpected_resolution)
    monkeypatch.setattr(ai_config, "warn_if_deprecated", unexpected_resolution)
    settings = _chat_settings()
    original = copy.deepcopy(settings)
    result = openai._chatGPT(
        "row input", "fake-key", settings,
        url="https://explicit.example/completions", timeout=8, retries=0,
    )
    assert result == {"value": "synthetic"}
    assert settings == original
    assert chat_transport[0]["url"] == "https://explicit.example/completions"
    assert chat_transport[0]["timeout"] == 8
    assert chat_transport[0]["json"]["model"] == original["model"]
    assert chat_transport[0]["json"]["temperature"] == original["temperature"]
    assert chat_transport[0]["json"]["messages"][:-1] == original["messages"]


@pytest.mark.parametrize("retries,expected_attempts", [(0, 1), (1, 2), (2, 3)])
def test_private_chat_transport_respects_http_retry_budget(monkeypatch, retries, expected_attempts):
    calls = []
    sleeps = []

    def post(**kwargs):
        calls.append(kwargs)
        response = requests.Response()
        response.status_code = 429
        response._content = b'{"error":{"message":"synthetic rate limit"}}'
        return response

    monkeypatch.setattr(openai._requests, "post", post)
    monkeypatch.setattr(openai._openai_responses, "_sleep_for_retry", lambda context, delay: sleeps.append(delay))
    result = openai._chatGPT(
        "row input", "fake-key", _chat_settings(),
        url="https://explicit.example/completions", timeout=3, retries=retries,
    )
    assert "value" in result
    assert len(calls) == expected_attempts
    assert sleeps == [1, 2][:retries]


@pytest.mark.parametrize("error_type", [requests.exceptions.Timeout, requests.exceptions.ConnectionError])
def test_chat_transport_retries_transient_failure_then_succeeds(chat_transport, monkeypatch, error_type):
    post = openai._requests.post
    attempts = []
    sleeps = []

    def fail_once(**kwargs):
        attempts.append(kwargs)
        if len(attempts) == 1:
            raise error_type("synthetic temporary failure")
        return post(**kwargs)

    monkeypatch.setattr(openai._requests, "post", fail_once)
    monkeypatch.setattr(openai._openai_responses, "_sleep_for_retry", lambda context, delay: sleeps.append(delay))
    result = openai._chatGPT(
        "row", "fake-key", _chat_settings(),
        url="https://explicit.example/completions", retries=1, timeout=3,
    )
    assert result == {"value": "synthetic"}
    assert len(attempts) == 2
    assert [attempt["timeout"] for attempt in attempts] == [3, 3]
    assert sleeps == [1]


@pytest.mark.parametrize("error_type", [requests.exceptions.Timeout, requests.exceptions.ConnectionError])
@pytest.mark.parametrize("retries", [0, 1, 2])
def test_chat_transport_respects_retry_budget_on_transport_failure(monkeypatch, error_type, retries):
    calls = []
    sleeps = []

    def post(**kwargs):
        calls.append(kwargs)
        raise error_type("synthetic temporary failure")

    monkeypatch.setattr(openai._requests, "post", post)
    monkeypatch.setattr(openai._openai_responses, "_sleep_for_retry", lambda context, delay: sleeps.append(delay))
    result = openai._chatGPT(
        "row", "fake-key", _chat_settings(),
        url="https://explicit.example/completions", timeout=3, retries=retries,
    )
    assert len(calls) == retries + 1
    assert sleeps == [1, 2][:retries]
    if error_type is requests.exceptions.Timeout:
        assert result == {"value": "Timed Out"}
    else:
        assert isinstance(result["value"], error_type)


def test_chat_transport_does_not_retry_invalid_request(monkeypatch):
    calls = []

    def post(**kwargs):
        calls.append(kwargs)
        raise requests.exceptions.InvalidURL("synthetic invalid URL")

    monkeypatch.setattr(openai._requests, "post", post)
    result = openai._chatGPT(
        "row", "fake-key", _chat_settings(),
        url="https://explicit.example/completions", timeout=3, retries=2,
    )
    assert len(calls) == 1
    assert isinstance(result["value"], requests.exceptions.InvalidURL)


@pytest.fixture
def embedding_transport(monkeypatch):
    calls = []

    def post(**kwargs):
        calls.append(copy.deepcopy(kwargs))
        rows = []
        for index, value in enumerate(kwargs["json"]["input"]):
            dimensions = kwargs["json"].get("dimensions", 2)
            vector = np.asarray([len(value)] + [1.25] * (dimensions - 1), dtype=np.float32)
            embedding = (
                base64.b64encode(vector.tobytes()).decode("ascii")
                if kwargs["json"].get("encoding_format") == "base64"
                else vector.tolist()
            )
            rows.append({"index": index, "embedding": embedding})
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({"data": rows}).encode("utf-8")
        return response

    monkeypatch.setattr(openai._requests, "post", post)
    return calls


@pytest.mark.parametrize("via_recipe", [False, True])
def test_embeddings_use_configured_defaults_at_request_time(configured_ai, embedding_transport, via_recipe):
    values = ["first", "second"]
    if via_recipe:
        result = wrangles.recipe.run(
            {"wrangles": [{"create.embeddings": {
                "input": "text", "output": "vector", "api_key": "fake-key",
            }}]},
            dataframe=pd.DataFrame({"text": values}),
        )["vector"].tolist()
    else:
        result = openai.embeddings(values, "fake-key")
        assert all(vector.dtype == np.float16 for vector in result)

    assert [list(vector) for vector in result] == [[5, 1.25], [6, 1.25]]
    assert len(embedding_transport) == 2  # Configured batch_size=1.
    assert all(call["timeout"] == 7.25 for call in embedding_transport)
    assert all(call["url"] == "https://openai.example/embeddings" for call in embedding_transport)
    assert all(call["json"]["model"] == ai_config.resolve("embeddings")["model"] for call in embedding_transport)
    assert all(call["json"]["encoding_format"] == "base64" for call in embedding_transport)


@pytest.mark.parametrize("via_recipe", [False, True])
def test_embeddings_explicit_options_override_config(configured_ai, embedding_transport, via_recipe):
    options = {
        "api_key": "fake-key", "model": "private-embedding-model",
        "url": "https://proxy.example/v1/embeddings", "provider": "openai",
        "batch_size": 2, "threads": 1, "timeout": 9, "retries": 0,
        "precision": "float32", "dimensions": 2,
    }
    if via_recipe:
        result = wrangles.recipe.run(
            {"wrangles": [{"create.embeddings": {"input": "text", "output": "vector", **options}}]},
            dataframe=pd.DataFrame({"text": ["a", "bb"]}),
        )["vector"].tolist()
    else:
        result = openai.embeddings(["a", "bb"], **options)
        assert all(vector.dtype == np.float32 for vector in result)
    assert [list(vector) for vector in result] == [[1, 1.25], [2, 1.25]]
    assert len(embedding_transport) == 1
    call = embedding_transport[0]
    assert call["timeout"] == 9
    assert call["url"] == options["url"]
    assert call["json"] == {
        "model": "private-embedding-model", "input": ["a", "bb"],
        "encoding_format": "base64", "dimensions": 2,
    }


@pytest.mark.parametrize("options, expected_url", [
    ({"url": "https://api.jina.ai/v1/embeddings"}, "https://api.jina.ai/v1/embeddings"),
    ({"provider": "jina"}, "https://jina.example/embeddings"),
    ({"provider": "jina", "url": openai.DEFAULT_EMBEDDING_URLS["openai"]}, "https://jina.example/embeddings"),
    ({"provider": "jina", "url": "https://proxy.example/embeddings"}, "https://proxy.example/embeddings"),
])
def test_embeddings_preserve_jina_inference_and_format(configured_ai, embedding_transport, options, expected_url):
    result = openai.embeddings(
        "hello", "fake-key", model="private-jina-model", task="retrieval.query",
        encoding_format="base64", **options,
    )
    assert isinstance(result, np.ndarray)
    assert result.tolist() == [5, 1.25]
    assert embedding_transport[0]["url"] == expected_url
    assert embedding_transport[0]["json"] == {
        "model": "private-jina-model", "input": ["hello"], "task": "retrieval.query",
    }


def test_embeddings_jina_requires_explicit_or_configured_model(configured_ai, embedding_transport):
    with pytest.raises(ValueError, match="(?i)(default|model)"):
        openai.embeddings("hello", "fake-key", provider="jina")
    assert embedding_transport == []


def test_embeddings_model_dimensions_default_and_explicit_override(configured_ai, embedding_transport):
    config, save = configured_ai
    model = ai_config.resolve("embeddings")["model"]
    config["providers"]["openai"]["models"][model].setdefault("defaults", {})["dimensions"] = 3
    save()
    configured_result = openai.embeddings("hello", "fake-key")
    explicit_result = openai.embeddings("hello", "fake-key", dimensions=4)
    assert configured_result.shape == (3,)
    assert explicit_result.shape == (4,)
    assert [call["json"]["dimensions"] for call in embedding_transport] == [3, 4]


def test_embeddings_selects_configured_jina_model_and_task(configured_ai, embedding_transport):
    config, save = configured_ai
    config["providers"]["jina"]["models"]["configured-jina-model"] = {
        "status": "active", "default_for": ["embeddings"],
        "defaults": {"task": "retrieval.passage", "dimensions": 3},
        "supported_values": {},
    }
    save()
    result = openai.embeddings("hello", "fake-key", provider="jina")
    assert result.shape == (3,)
    assert embedding_transport[0]["json"] == {
        "model": "configured-jina-model", "input": ["hello"],
        "task": "retrieval.passage", "dimensions": 3,
    }
    openai.embeddings("hello", "fake-key", provider="jina", task="retrieval.query")
    assert embedding_transport[1]["json"]["task"] == "retrieval.query"


@pytest.mark.parametrize("via_recipe", [False, True])
@pytest.mark.parametrize("task,expected_task", [(None, "text-matching"), ("clustering", "clustering")])
def test_embeddings_jina_v5_task_defaults_and_override(
    configured_ai, embedding_transport, via_recipe, task, expected_task,
):
    options = {
        "api_key": "fake-key", "provider": "jina", "model": "jina-embeddings-v5-omni-small",
    }
    if task is not None:
        options["task"] = task
    if via_recipe:
        result = wrangles.recipe.run(
            {"wrangles": [{"create.embeddings": {"input": "text", "output": "vector", **options}}]},
            dataframe=pd.DataFrame({"text": ["hello"]}),
        )["vector"].tolist()
    else:
        result = openai.embeddings(["hello"], **options)
    assert [list(vector) for vector in result] == [[5, 1.25]]
    assert embedding_transport[0]["json"]["task"] == expected_task


def test_embeddings_jina_v5_rejects_legacy_task(configured_ai, embedding_transport):
    with pytest.raises(ValueError, match="task must be one of.*jina-embeddings-v5-omni-small"):
        openai.embeddings(
            "hello", "fake-key", provider="jina", model="jina-embeddings-v5-omni-small", task="separation",
        )
    assert embedding_transport == []


def test_embeddings_uses_task_enum_from_override_catalog(configured_ai, embedding_transport):
    config, save = configured_ai
    model = config["providers"]["jina"]["models"]["jina-embeddings-v5-omni-small"]
    model["defaults"]["task"] = "custom-default"
    model["supported_values"]["task"] = ["custom-default", "custom-query"]
    save()
    options = {"provider": "jina", "model": "jina-embeddings-v5-omni-small"}
    openai.embeddings("hello", "fake-key", **options)
    openai.embeddings("hello", "fake-key", task="custom-query", **options)
    with pytest.raises(ValueError, match="task must be one of"):
        openai.embeddings("hello", "fake-key", task="retrieval.query", **options)
    assert [call["json"]["task"] for call in embedding_transport] == ["custom-default", "custom-query"]


@pytest.mark.parametrize("legacy_config", [False, True])
@pytest.mark.parametrize("task", [None, "separation"])
def test_embeddings_legacy_jina_task_compatibility(configured_ai, embedding_transport, legacy_config, task):
    config, save = configured_ai
    if legacy_config:
        config.clear()
        config.update({"version": 1, "extract_ai": {"model": "gpt-6-luna"}})
        save()
    openai.embeddings("hello", "fake-key", provider="jina", model="jina-embeddings-v3", task=task)
    body = embedding_transport[0]["json"]
    if task is None:
        assert "task" not in body
    else:
        assert body["task"] == "separation"


def test_embeddings_task_still_warns_for_non_jina(configured_ai, embedding_transport):
    with pytest.warns(UserWarning, match="task parameter is only supported for the Jina provider"):
        openai.embeddings("hello", "fake-key", task="clustering")
    assert "task" not in embedding_transport[0]["json"]


@pytest.mark.parametrize("provider,defaults,overrides", [
    ("openai", {"dimensions": 3, "user": "configured-user"}, {"user": "explicit-user"}),
    ("jina", {"normalized": False, "truncate": True, "late_chunking": True}, {"truncate": False}),
])
def test_embeddings_forward_supported_request_defaults(configured_ai, embedding_transport, provider, defaults, overrides):
    config, save = configured_ai
    model = "text-embedding-3-small" if provider == "openai" else "jina-embeddings-v5-omni-small"
    config["providers"][provider]["models"][model].setdefault("defaults", {}).update(defaults)
    save()
    openai.embeddings("hello", "fake-key", provider=provider, model=model, **overrides)
    body = embedding_transport[0]["json"]
    for key, value in {**defaults, **overrides}.items():
        assert body[key] == value
    assert "default_concurrency" not in body
    assert "request_timeout_seconds" not in body
    assert "retries" not in body


def test_embeddings_warns_once_per_operation_not_per_batch(configured_ai, embedding_transport, caplog):
    config, save = configured_ai
    config["providers"]["openai"]["models"]["old-embedding-model"] = {
        "status": "deprecated", "default_for": [],
    }
    save()
    for _ in range(2):
        openai.embeddings(["one", "two", "three"], "fake-key", model="old-embedding-model")
    assert len(embedding_transport) == 6
    warnings = [record for record in caplog.records if "deprecated status" in record.message]
    assert len(warnings) == 2


def test_embeddings_explicit_zero_retries_remains_zero(configured_ai, monkeypatch):
    calls = []

    def post(**kwargs):
        calls.append(kwargs)
        raise requests.exceptions.Timeout("synthetic timeout")

    monkeypatch.setattr(openai._requests, "post", post)
    with pytest.raises(RuntimeError, match="after 1 attempt"):
        openai.embeddings("hello", "fake-key", retries=0)
    assert len(calls) == 1


def test_embeddings_reads_changed_model_role_at_call_time(configured_ai, embedding_transport):
    config, save = configured_ai
    original = ai_config.resolve("embeddings")["model"]
    openai.embeddings("hello", "fake-key")
    models = config["providers"]["openai"]["models"]
    models["replacement-embedding-model"] = models.pop(original)
    save()
    openai.embeddings("hello", "fake-key")
    assert [call["json"]["model"] for call in embedding_transport] == [original, "replacement-embedding-model"]


def test_embeddings_rejects_unsupported_configured_provider(configured_ai, monkeypatch):
    monkeypatch.setattr(ai_config, "resolve", lambda *args, **kwargs: {"provider": "anthropic"})
    with pytest.raises(ValueError, match="Provider must be"):
        openai.embeddings("hello", "fake-key")


@pytest.fixture
def google_transport(monkeypatch):
    calls = {"clients": [], "requests": [], "closed": []}

    def generate_content(**kwargs):
        calls["requests"].append(kwargs)
        return SimpleNamespace(candidates=[SimpleNamespace(
            url_context_metadata=None,
            content=SimpleNamespace(parts=[SimpleNamespace(text='{"name":"Synthetic"}')]),
        )])

    def client(**kwargs):
        calls["clients"].append(kwargs)
        return SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content),
            close=lambda: calls["closed"].append(True),
        )

    types = SimpleNamespace(
        HttpOptions=lambda **kwargs: kwargs,
        HttpRetryOptions=lambda **kwargs: kwargs,
        GenerateContentConfig=lambda **kwargs: kwargs,
        Tool=lambda **kwargs: kwargs,
        UrlContext=lambda: {},
    )
    monkeypatch.setattr(gemini, "_get_genai", lambda: (
        SimpleNamespace(Client=client), types, SimpleNamespace(ClientError=type("ClientError", (Exception,), {})),
    ))
    return calls


@pytest.mark.parametrize("via_recipe", [False, True])
@pytest.mark.parametrize("model", [None, "models/private-google-model"])
def test_google_retrieval_uses_config_at_sdk_boundary(configured_ai, google_transport, via_recipe, model):
    options = {"prompt": "Use this custom instruction."}
    if model is not None:
        options["model_id"] = model
    if via_recipe:
        result = wrangles.recipe.run(
            {"wrangles": [{"search.retrieve_link_content": {
                "input": "url", "output": "page", "api_key": "fake-key", **options,
            }}]},
            dataframe=pd.DataFrame({"url": ["https://product.example/one"]}),
        )["page"].iloc[0][0]
    else:
        result = search.retrieve_link_content(
            "https://product.example/one", client_config={"api_key": "fake-key"}, **options,
        )
    assert result["extracted_content"] == {"name": "Synthetic"}
    assert google_transport["clients"][0]["http_options"]["timeout"] == 3250
    assert google_transport["clients"][0]["http_options"]["base_url"] == "https://google.example/gemini"
    assert google_transport["clients"][0]["http_options"]["api_version"] == "v1beta"
    assert google_transport["clients"][0]["http_options"]["retry_options"] == {
        "attempts": 2, "http_status_codes": [408, 429, 500, 502, 503, 504],
    }
    request = google_transport["requests"][0]
    assert request["model"] == (model or ai_config.resolve("search.retrieve_link_content")["model"])
    assert request["config"]["temperature"] == 0
    assert request["config"]["system_instruction"].startswith(options["prompt"])
    assert request["config"]["tools"] == [{"url_context": {}}]
    assert request["config"]["response_mime_type"] == "application/json"
    assert len(google_transport["closed"]) == 1


def test_google_direct_client_reads_changed_config_each_call(configured_ai, google_transport):
    config, save = configured_ai
    client = gemini.GeminiURLContextClient(api_key="fake-key")
    client.retrieve("https://product.example/one")
    config["operations"]["search.retrieve_link_content"]["defaults"].update({
        "temperature": 0.7, "request_timeout_seconds": 4, "retries": 0, "api_version": "v1",
    })
    config["providers"]["google"]["endpoints"]["base_url"] = "https://alternate.example/gemini"
    save()
    client.retrieve("https://product.example/two")
    assert [request["config"]["temperature"] for request in google_transport["requests"]] == [0, 0.7]
    assert [client["http_options"]["timeout"] for client in google_transport["clients"]] == [3250, 4000]
    assert [client["http_options"]["retry_options"]["attempts"] for client in google_transport["clients"]] == [2, 1]
    assert [client["http_options"]["base_url"] for client in google_transport["clients"]] == [
        "https://google.example/gemini", "https://alternate.example/gemini",
    ]
    assert [client["http_options"]["api_version"] for client in google_transport["clients"]] == ["v1beta", "v1"]


def test_google_forwards_model_tuning_defaults(configured_ai, google_transport):
    config, save = configured_ai
    model = ai_config.resolve("search.retrieve_link_content")["model"]
    tuning = {"top_p": 0.8, "top_k": 20, "max_output_tokens": 512, "stop_sequences": ["END"]}
    config["providers"]["google"]["models"][model]["defaults"].update(tuning)
    save()
    gemini.GeminiURLContextClient(api_key="fake-key").retrieve("https://product.example/one")
    request = google_transport["requests"][0]["config"]
    for key, value in tuning.items():
        assert request[key] == value
    assert "retries" not in request
    assert "api_version" not in request


def test_google_closes_client_when_request_fails(configured_ai, monkeypatch):
    closed = []

    def generate_content(**kwargs):
        raise RuntimeError("synthetic request failure")

    client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content),
        close=lambda: closed.append(True),
    )
    types = SimpleNamespace(
        HttpOptions=lambda **kwargs: kwargs, HttpRetryOptions=lambda **kwargs: kwargs,
        GenerateContentConfig=lambda **kwargs: kwargs, Tool=lambda **kwargs: kwargs, UrlContext=lambda: {},
    )
    monkeypatch.setattr(gemini, "_get_genai", lambda: (
        SimpleNamespace(Client=lambda **kwargs: client), types,
        SimpleNamespace(ClientError=type("ClientError", (Exception,), {})),
    ))
    result = gemini.GeminiURLContextClient(api_key="fake-key").retrieve("https://product.example/one")
    assert result["status"] == "Failure"
    assert "synthetic request failure" in result["error"]
    assert closed == [True]


@pytest.mark.parametrize("direct_client", [False, True])
def test_google_deprecated_warning_per_operation(configured_ai, google_transport, caplog, direct_client):
    config, save = configured_ai
    config["providers"]["google"]["models"]["old-google-model"] = {"status": "deprecated", "default_for": []}
    save()
    urls = ["https://product.example/one", "https://product.example/two"]
    if direct_client:
        client = gemini.GeminiURLContextClient(api_key="fake-key")
        for url in urls:
            client.retrieve(url, model_id="old-google-model")
    else:
        search.retrieve_link_content(urls, model_id="old-google-model", client_config={"api_key": "fake-key"})
    warnings = [record for record in caplog.records if "deprecated status" in record.message]
    assert len(warnings) == (2 if direct_client else 1)
    assert len(google_transport["requests"]) == len(google_transport["closed"]) == 2


def test_retrieval_preserves_generic_client_interface(configured_ai, monkeypatch):
    calls = []
    client = SimpleNamespace(retrieve=lambda **kwargs: calls.append(kwargs) or {"url": kwargs["url"]})
    monkeypatch.setattr(search, "_get_client", lambda *args: client)
    result = search.retrieve_link_content("https://product.example/one", model_id="custom-model", prompt="custom-prompt")
    assert result == {"url": "https://product.example/one"}
    assert calls == [{
        "url": "https://product.example/one", "model_id": "custom-model", "prompt": "custom-prompt", "output_format": "json",
    }]


@pytest.mark.parametrize("caller", ["client", "python", "recipe"])
def test_google_explicit_unlisted_model_does_not_require_model_defaults(google_transport, monkeypatch, caller):
    monkeypatch.delenv("WRANGLES_AI_CONFIG", raising=False)
    ai_config.clear_cache()
    model = "models/unlisted-google-model"
    try:
        if caller == "client":
            result = gemini.GeminiURLContextClient(api_key="fake-key").retrieve(
                "https://product.example/one", model_id=model, output_format="json",
            )
        elif caller == "python":
            result = search.retrieve_link_content(
                "https://product.example/one", model_id=model,
                client_config={"api_key": "fake-key"},
            )
        else:
            result = wrangles.recipe.run(
                {"wrangles": [{"search.retrieve_link_content": {
                    "input": "url", "output": "page", "api_key": "fake-key", "model_id": model,
                }}]},
                dataframe=pd.DataFrame({"url": ["https://product.example/one"]}),
            )["page"].iloc[0][0]
        assert result["error"] is None
        assert result["extracted_content"] == {"name": "Synthetic"}
        request = google_transport["requests"][0]
        assert request["model"] == model
        assert request["config"].get("temperature") is None
    finally:
        ai_config.clear_cache()


@pytest.mark.parametrize("model", ["gemini-3.8-flash", "models/gemini-3.8-flash"])
@pytest.mark.parametrize("custom_endpoint", [False, True])
def test_google_sdk_builds_configured_request_url(configured_ai, monkeypatch, model, custom_endpoint):
    """Exercise the installed SDK's URL construction without sending a request."""
    import httpx
    from google import genai
    from google.genai import errors, types

    config, save = configured_ai
    base_url = "https://proxy.example/google" if custom_endpoint else "https://generativelanguage.googleapis.com"
    version = "v1" if custom_endpoint else "v1beta"
    config["providers"]["google"]["endpoints"]["base_url"] = base_url
    config["operations"]["search.retrieve_link_content"]["defaults"]["api_version"] = version
    config["operations"]["search.retrieve_link_content"]["defaults"].pop("temperature")
    config["providers"]["google"]["models"]["gemini-3.8-flash"]["defaults"]["temperature"] = 0.17
    save()
    requests_sent = []
    clients = []

    def send(client, request, **kwargs):
        requests_sent.append(request)
        return httpx.Response(200, request=request, json={
            "candidates": [{"content": {"parts": [{"text": '{"name":"Synthetic"}'}]}}],
        })

    def client(**kwargs):
        result = genai.Client(vertexai=False, **kwargs)
        clients.append(result)
        return result

    monkeypatch.setattr(httpx.Client, "send", send)
    monkeypatch.setattr(gemini, "_get_genai", lambda: (SimpleNamespace(Client=client), types, errors))
    try:
        result = gemini.GeminiURLContextClient(api_key="fake-key").retrieve(
            "https://product.example/one", model_id=model, output_format="json",
        )
        assert result["error"] is None
        assert result["extracted_content"] == {"name": "Synthetic"}
        assert len(requests_sent) == 1
        assert requests_sent[0].method == "POST"
        assert str(requests_sent[0].url) == f"{base_url}/{version}/models/gemini-3.8-flash:generateContent"
        assert json.loads(requests_sent[0].content)["generationConfig"]["temperature"] == 0.17
    finally:
        for client in clients:
            client.close()


def test_google_retrieval_rejects_unsupported_provider(configured_ai, monkeypatch):
    monkeypatch.setattr(ai_config, "resolve", lambda *args, **kwargs: {"provider": "anthropic"})
    with pytest.raises(ValueError, match="only the 'google' provider"):
        search.retrieve_link_content("https://product.example/one")


@pytest.mark.parametrize("caller", ["embeddings", "retrieval"])
def test_callers_resolve_concurrency_and_preserve_explicit_threads(
    configured_ai, embedding_transport, google_transport, monkeypatch, caller,
):
    workers = []
    executor = openai._futures.ThreadPoolExecutor

    def record_executor(*args, **kwargs):
        workers.append(kwargs["max_workers"])
        return executor(*args, **kwargs)

    monkeypatch.setattr(openai._futures, "ThreadPoolExecutor", record_executor)
    for options in ({}, {"threads": 3}):
        if caller == "embeddings":
            openai.embeddings("hello", "fake-key", **options)
        else:
            search.retrieve_link_content(
                "https://product.example/one", client_config={"api_key": "fake-key"}, **options,
            )
    assert workers == [1, 3]
