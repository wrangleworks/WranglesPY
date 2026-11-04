import pytest

from wrangles import data
from scripts import check_model_registry_access as checker


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300

    def json(self):
        return {"id": "some-model"}


def _mock_status(monkeypatch, model_id_to_status: dict):
    def request_retries(**kwargs):
        model_id = kwargs["params"]["id"]
        return FakeResponse(model_id_to_status[model_id])

    monkeypatch.setattr(data._auth, "get_access_token", lambda: "token")
    monkeypatch.setattr(data._utils, "request_retries", request_retries)


def test_check_all_categorizes_accessible_not_found_and_denied(monkeypatch):
    registry = {
        "aaaaaaaa-0000-0000": "accessible model",
        "bbbbbbbb-0000-0000": "deleted model",
        "cccccccc-0000-0000": "forbidden model",
    }
    _mock_status(monkeypatch, {
        "aaaaaaaa-0000-0000": 200,
        "bbbbbbbb-0000-0000": 404,
        "cccccccc-0000-0000": 403,
    })

    accessible, not_found, denied_or_errored = checker.check_all(registry)

    assert [m for m, _, _ in accessible] == ["aaaaaaaa-0000-0000"]
    assert [m for m, _, _ in not_found] == ["bbbbbbbb-0000-0000"]
    assert [m for m, _, _ in denied_or_errored] == ["cccccccc-0000-0000"]


def test_check_all_empty_registry_returns_empty_results():
    accessible, not_found, denied_or_errored = checker.check_all({})
    assert accessible == []
    assert not_found == []
    assert denied_or_errored == []


def test_main_returns_zero_when_all_accessible(monkeypatch):
    _mock_status(monkeypatch, {"aaaaaaaa-0000-0000": 200})
    monkeypatch.setattr(checker, "MODEL_REGISTRY", {"aaaaaaaa-0000-0000": "note"})

    assert checker.main() == 0


def test_main_returns_nonzero_when_any_model_inaccessible(monkeypatch):
    _mock_status(monkeypatch, {
        "aaaaaaaa-0000-0000": 200,
        "bbbbbbbb-0000-0000": 404,
    })
    monkeypatch.setattr(checker, "MODEL_REGISTRY", {
        "aaaaaaaa-0000-0000": "note",
        "bbbbbbbb-0000-0000": "note",
    })

    assert checker.main() == 1
