"""
Tests for wrangles.extract.dimensions.

All tests here are fully offline. Tier 1 and 2 need no nooa install at all
(pydantic is a base dependency; the wrangles.extract._nooa_client boundary is
mocked). Tier 3 exercises the real nooa package against its own FakeLLMClient
test double, and is skipped cleanly when nooa isn't installed.
"""
import builtins
import importlib
import importlib.util
import sys
import threading
import time

import pytest
from pydantic import ValidationError

import wrangles
from wrangles.nooa_client import DimensionsResult, Measurement


# ---------------------------------------------------------------------------
# Tier 1: Pydantic contract tests - no nooa needed at all.
# ---------------------------------------------------------------------------

def test_scalar_value_measurement():
    result = DimensionsResult.model_validate({
        "measurements": [
            {
                "kind": "diameter",
                "label": "outside diameter",
                "value": 3.2,
                "minimum": None,
                "maximum": None,
                "unit": "in",
                "qualifier": "outside",
                "source": "3.2 in OD",
            }
        ]
    })
    assert result.measurements[0].value == 3.2
    assert result.measurements[0].minimum is None
    assert result.measurements[0].maximum is None


def test_range_measurement():
    m = Measurement.model_validate({
        "kind": "width",
        "value": None,
        "minimum": 12,
        "maximum": 14,
        "unit": "in",
        "source": "12-14 in wide",
    })
    assert m.value is None
    assert m.minimum == 12
    assert m.maximum == 14


def test_compact_lwh_group_is_multiple_measurements():
    result = DimensionsResult.model_validate({
        "measurements": [
            {"kind": "length", "value": 18, "unit": "in", "source": "18 x 14 x 8 in"},
            {"kind": "width", "value": 14, "unit": "in", "source": "18 x 14 x 8 in"},
            {"kind": "height", "value": 8, "unit": "in", "source": "18 x 14 x 8 in"},
        ]
    })
    assert [m.kind for m in result.measurements] == ["length", "width", "height"]


def test_written_fraction_as_source_text():
    m = Measurement.model_validate({
        "kind": "misc",
        "label": "thickness",
        "value": 0.75,
        "unit": "in",
        "source": "3/4 in thick",
    })
    assert m.source == "3/4 in thick"


def test_shared_trailing_unit():
    # "9.7 in H x 3.2 in OD" - both measurements share the "in" unit even
    # though only stated once in some source phrasings; each measurement
    # still reports its own unit independently.
    result = DimensionsResult.model_validate({
        "measurements": [
            {"kind": "height", "value": 9.7, "unit": "in", "source": "9.7 in H"},
            {
                "kind": "diameter",
                "qualifier": "outside",
                "value": 3.2,
                "unit": "in",
                "source": "3.2 in OD",
            },
        ]
    })
    assert result.measurements[1].unit == "in"


def test_od_id_dia_notation():
    outside = Measurement.model_validate({
        "kind": "diameter", "qualifier": "outside", "value": 3.2, "unit": "in", "source": "3.2 in OD",
    })
    inside = Measurement.model_validate({
        "kind": "diameter", "qualifier": "inside", "value": 3.0, "unit": "in", "source": "3.0 in ID",
    })
    dia = Measurement.model_validate({
        "kind": "diameter", "value": 3.5, "unit": "in", "source": "DIA 3.5 in",
    })
    assert outside.qualifier == "outside"
    assert inside.qualifier == "inside"
    assert dia.kind == "diameter"


def test_misc_requires_label():
    Measurement.model_validate({
        "kind": "misc", "label": "bore diameter", "value": 1.25, "unit": "in", "source": "1.25 in bore",
    })
    with pytest.raises(ValidationError, match="descriptive label"):
        Measurement.model_validate({
            "kind": "misc", "value": 1.25, "unit": "in", "source": "1.25 in bore",
        })


def test_no_dimensional_fact_returns_empty_measurements():
    result = DimensionsResult.model_validate({"measurements": []})
    assert result.measurements == []


@pytest.mark.parametrize("payload", [
    # Both value and range set
    {"kind": "length", "value": 5, "minimum": 4, "maximum": 6, "unit": "in", "source": "x"},
    # Neither value nor range set
    {"kind": "length", "unit": "in", "source": "x"},
    # Range missing one bound
    {"kind": "length", "minimum": 4, "unit": "in", "source": "x"},
])
def test_invalid_value_shapes_rejected(payload):
    with pytest.raises(ValidationError):
        Measurement.model_validate(payload)


def test_uncontracted_fields_rejected():
    with pytest.raises(ValidationError):
        Measurement.model_validate({
            "kind": "length", "value": 5, "unit": "in", "source": "x", "unexpected_field": "nope",
        })


# ---------------------------------------------------------------------------
# Tier 2: wrangles.extract.dimensions() plumbing, mocked at the nooa_client
# boundary. No nooa install needed.
# ---------------------------------------------------------------------------

def _mock_pipeline(monkeypatch, compute):
    """Patch wrangles.extract._nooa_client so dimensions() runs `compute` per row."""
    monkeypatch.setattr(wrangles.extract._nooa_client, "get_llm_client", lambda *a, **k: "fake-llm")
    monkeypatch.setattr(wrangles.extract._nooa_client, "build_agent_class", lambda llm: "fake-agent-cls")

    async def fake_extract_async(text, agent_cls):
        return compute(text)

    monkeypatch.setattr(wrangles.extract._nooa_client, "extract_async", fake_extract_async)


def test_scalar_input_returns_single_dict(monkeypatch):
    _mock_pipeline(monkeypatch, lambda text: DimensionsResult(measurements=[]))

    result = wrangles.extract.dimensions("some text", model="gpt-5-mini", api_key="key")

    assert result == {"measurements": []}


def test_list_input_returns_list_in_order(monkeypatch):
    def compute(text):
        return DimensionsResult(measurements=[
            Measurement(kind="length", value=float(text), unit="in", source=text)
        ])

    _mock_pipeline(monkeypatch, compute)

    results = wrangles.extract.dimensions(
        ["1", "2", "3", "4", "5"], model="gpt-5-mini", api_key="key", threads=3
    )

    assert [r["measurements"][0]["value"] for r in results] == [1.0, 2.0, 3.0, 4.0, 5.0]


def test_empty_list_input_short_circuits_without_nooa(monkeypatch):
    # Deliberately do NOT mock _nooa_client - proves the empty-input path
    # never touches it (and so never requires nooa to be installed).
    assert wrangles.extract.dimensions([], model="gpt-5-mini", api_key="key") == []


def test_bounded_concurrency(monkeypatch):
    max_workers = 2
    in_flight = {"current": 0, "max_seen": 0}
    lock = threading.Lock()

    def compute(text):
        with lock:
            in_flight["current"] += 1
            in_flight["max_seen"] = max(in_flight["max_seen"], in_flight["current"])
        time.sleep(0.05)
        with lock:
            in_flight["current"] -= 1
        return DimensionsResult(measurements=[])

    _mock_pipeline(monkeypatch, compute)

    wrangles.extract.dimensions(
        [str(i) for i in range(6)], model="gpt-5-mini", api_key="key", threads=max_workers
    )

    assert in_flight["max_seen"] <= max_workers


def test_kwargs_passthrough_to_get_llm_client(monkeypatch):
    captured = {}

    def fake_get_llm_client(model, api_key=None, api_base=None, **kwargs):
        captured["model"] = model
        captured["api_key"] = api_key
        captured["kwargs"] = kwargs
        return "fake-llm"

    monkeypatch.setattr(wrangles.extract._nooa_client, "get_llm_client", fake_get_llm_client)
    monkeypatch.setattr(wrangles.extract._nooa_client, "build_agent_class", lambda llm: "fake-agent-cls")

    async def fake_extract_async(text, agent_cls):
        return DimensionsResult(measurements=[])

    monkeypatch.setattr(wrangles.extract._nooa_client, "extract_async", fake_extract_async)

    wrangles.extract.dimensions(
        "text", model="gpt-5-mini", api_key="key", custom_kwarg="value"
    )

    assert captured["model"] == "gpt-5-mini"
    assert captured["api_key"] == "key"
    assert captured["kwargs"] == {"custom_kwarg": "value"}


def test_invalid_threads_rejected():
    with pytest.raises(ValueError, match="threads"):
        wrangles.extract.dimensions("text", model="gpt-5-mini", api_key="key", threads=0)


# ---------------------------------------------------------------------------
# Missing-dependency and base-import checks - unconditional either way.
# ---------------------------------------------------------------------------

def test_base_import_does_not_import_nooa_or_litellm():
    assert "nooa" not in sys.modules
    assert "litellm" not in sys.modules


def test_clear_error_when_nooa_not_installed(monkeypatch):
    real_import = builtins.__import__

    def blocking_import(name, *args, **kwargs):
        if name == "nooa" or name.startswith("nooa."):
            raise ImportError("No module named 'nooa'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocking_import)
    # Force a fresh import attempt regardless of whether nooa is actually
    # installed in this environment.
    monkeypatch.setattr(wrangles.nooa_client, "_NOOA_NS", None)

    with pytest.raises(ImportError, match="nooa==0.0.10"):
        wrangles.extract.dimensions("text", model="gpt-5-mini", api_key="key")


# ---------------------------------------------------------------------------
# Tier 3: real nooa + its own FakeLLMClient. Skipped cleanly if nooa isn't
# installed.
# ---------------------------------------------------------------------------

pytestmark_nooa = pytest.mark.skipif(
    importlib.util.find_spec('nooa') is None,
    reason='nooa optional dependency is not installed'
)


@pytestmark_nooa
def test_real_nooa_happy_path():
    import asyncio
    from nooa.unifiedllm.fake import FakeLLMClient
    from nooa.unifiedllm.unifiedllm import LLMResponse

    valid_json = '{"measurements": [{"kind": "diameter", "label": null, "value": 3.2, "minimum": null, "maximum": null, "unit": "in", "qualifier": "outside", "source": "3.2 in OD"}]}'
    fake = FakeLLMClient(scripted_responses=[
        LLMResponse(
            raw_response=None,
            content=valid_json,
            tool_calls=[],
            finish_reason="stop",
            assistant_message={"role": "assistant", "content": valid_json},
            reasoning=None,
            usage=None,
        )
    ])

    agent_cls = wrangles.nooa_client.build_agent_class(fake)
    result = asyncio.run(wrangles.nooa_client.extract_async("3.2 in OD", agent_cls))

    assert isinstance(result, DimensionsResult)
    assert result.measurements[0].kind == "diameter"
    assert result.measurements[0].value == 3.2


@pytestmark_nooa
def test_real_nooa_validation_retry():
    import asyncio
    from nooa.unifiedllm.fake import FakeLLMClient
    from nooa.unifiedllm.unifiedllm import LLMResponse

    invalid_json = '{"measurements": [{"kind": "not-a-real-kind", "value": 1, "unit": "in", "source": "x"}]}'
    valid_json = '{"measurements": []}'

    def _response(content):
        return LLMResponse(
            raw_response=None,
            content=content,
            tool_calls=[],
            finish_reason="stop",
            assistant_message={"role": "assistant", "content": content},
            reasoning=None,
            usage=None,
        )

    fake = FakeLLMClient(scripted_responses=[_response(invalid_json), _response(valid_json)])

    agent_cls = wrangles.nooa_client.build_agent_class(fake)
    result = asyncio.run(wrangles.nooa_client.extract_async("no dimensions here", agent_cls))

    assert isinstance(result, DimensionsResult)
    assert result.measurements == []
    assert fake.call_count == 2
