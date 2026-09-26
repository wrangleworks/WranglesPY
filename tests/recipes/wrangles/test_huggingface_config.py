"""Offline contracts for the generic Hugging Face task caller."""
from unittest.mock import Mock

import pandas as pd
import pytest
import requests
import yaml

from wrangles import ai_config
from wrangles.recipe_wrangles import main


@pytest.fixture(autouse=True)
def configured_huggingface(monkeypatch, tmp_path):
    monkeypatch.delenv("WRANGLES_AI_CONFIG", raising=False)
    ai_config.clear_cache()
    config = ai_config.load()
    provider = config["providers"]["huggingface"]
    provider["endpoints"]["hf_inference"] = "https://hf.example/models/"
    provider["models"]["org/task-model"] = {
        "status": "deprecated",
        "defaults": {"parameters": {"max_length": 20, "do_sample": True}},
    }
    config["operations"]["huggingface"]["defaults"]["request_timeout_seconds"] = 17
    path = tmp_path / "ai.yml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setenv("WRANGLES_AI_CONFIG", str(path))
    ai_config.clear_cache()
    monkeypatch.setattr(main._time, "sleep", Mock())
    yield
    ai_config.clear_cache()


def response(status=200, body=None, headers=None):
    return Mock(status_code=status, headers=headers or {}, json=Mock(return_value=body if body is not None else {"result": "ok"}))


def run(**kwargs):
    return main.huggingface(
        pd.DataFrame({"text": ["one", "two"]}), input="text", output="result",
        api_token="offline-test-token", model="Org/task-model", **kwargs,
    )


def test_model_defaults_and_explicit_options_reach_request(monkeypatch, caplog):
    post = Mock(return_value=response())
    monkeypatch.setattr(main._requests, "post", post)
    result = run(parameters={"do_sample": False}, timeout=9, retries=0)
    assert result["result"].tolist() == [{"result": "ok"}, {"result": "ok"}]
    assert result["text"].tolist() == ["one", "two"]
    assert post.call_count == 2
    for call in post.call_args_list:
        assert call.args == ("https://hf.example/models/Org/task-model",)
        assert call.kwargs["timeout"] == 9
        assert call.kwargs["json"]["parameters"] == {"max_length": 20, "do_sample": False}
        assert set(call.kwargs["json"]) == {"inputs", "parameters"}
    deprecated = [r for r in caplog.records if "deprecated" in r.getMessage()]
    assert len(deprecated) == 1
    assert "huggingface" in deprecated[0].getMessage()
    assert "Org/task-model" in deprecated[0].getMessage()


@pytest.mark.parametrize("failure", [requests.Timeout(), requests.ConnectionError(), response(503), response(429)])
def test_configured_retry_and_timeout_are_used(monkeypatch, failure):
    post = Mock(side_effect=[failure, response(), response()])
    monkeypatch.setattr(main._requests, "post", post)
    assert len(run()) == 2
    assert post.call_count == 3
    assert all(call.kwargs["timeout"] == 17 for call in post.call_args_list)
    main._time.sleep.assert_called_once_with(1)


def test_explicit_zero_disables_transport_retries(monkeypatch):
    post = Mock(side_effect=requests.Timeout())
    monkeypatch.setattr(main._requests, "post", post)
    with pytest.raises(requests.Timeout):
        run(retries=0)
    assert post.call_count == 1


def test_transport_retry_budget_is_bounded(monkeypatch):
    post = Mock(side_effect=requests.ConnectionError())
    monkeypatch.setattr(main._requests, "post", post)
    with pytest.raises(requests.ConnectionError):
        run()
    assert post.call_count == 2


@pytest.mark.parametrize("header,delay", [("30", 30), ("invalid", 1)])
def test_provider_retry_after_is_respected(monkeypatch, header, delay):
    post = Mock(side_effect=[response(429, headers={"Retry-After": header}), response(), response()])
    monkeypatch.setattr(main._requests, "post", post)
    run()
    main._time.sleep.assert_called_once_with(delay)


@pytest.mark.parametrize("status,attempts", [(401, 2), (503, 4)])
def test_terminal_provider_json_is_preserved(monkeypatch, status, attempts):
    body = {"error": "offline provider error"}
    post = Mock(return_value=response(status, body))
    monkeypatch.setattr(main._requests, "post", post)
    assert run()["result"].tolist() == [body, body]
    assert post.call_count == attempts


@pytest.mark.parametrize("option", [{"retries": -1}, {"retries": True}, {"timeout": 0}, {"timeout": float("inf")}])
def test_invalid_transport_options_fail_before_requests(monkeypatch, option):
    post = Mock()
    monkeypatch.setattr(main._requests, "post", post)
    with pytest.raises(ValueError):
        run(**option)
    post.assert_not_called()
