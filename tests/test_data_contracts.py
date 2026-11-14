"""Offline contracts for shared adapters, including pandas' future string mode."""

from dataclasses import FrozenInstanceError
import inspect

import numpy as np
import pandas as pd
import pytest

from wrangles._data_contracts import (
    DataContract,
    assign_result,
    data_contract,
    is_empty_scalar,
    is_missing_scalar,
    joined_text_rows,
    normalize_missing_values,
    structured_values,
    text_matrix,
    text_values,
)


@pytest.fixture(params=[False, True], ids=["legacy-pandas", "future-strings-and-cow"])
def pandas_mode(request):
    with pd.option_context(
        "future.infer_string", request.param,
        "mode.copy_on_write", request.param,
    ):
        yield


@pytest.mark.parametrize("value", [None, np.nan, pd.NA, pd.NaT, np.datetime64("NaT")])
def test_missing_sentinels_are_scalar_missing_values(value):
    assert is_missing_scalar(value) is True
    assert is_empty_scalar(value) is True


@pytest.mark.parametrize("value", ["", " ", "nan", "None", "null", "<NA>", 0, False, [], {}, [pd.NA], np.array([np.nan])])
def test_missing_detection_preserves_real_values_and_containers(value):
    assert is_missing_scalar(value) is False


def test_empty_text_policy_does_not_discard_falsy_values_or_containers():
    assert is_empty_scalar("") is True
    assert is_empty_scalar(" \t") is False
    assert is_empty_scalar(" \t", whitespace=True) is True
    for value in (0, False, [], {}, [None], np.array([]), "nan", "None"):
        assert is_empty_scalar(value, whitespace=True) is False


def test_text_conversion_preserves_distinct_legacy_sentinel_spellings(pandas_mode):
    values = [None, np.nan, pd.NA, pd.NaT, "", " ", "nan", 0, False, [1], {"a": 1}]
    assert text_values(values, missing="stringify", non_text="stringify") == [
        "None", "nan", "<NA>", "NaT", "", " ", "nan", "0", "False", "[1]", "{'a': 1}",
    ]


@pytest.mark.parametrize("values,expected", [
    (pd.Series([1.23456789, np.nan], dtype="float32"), ["1.2345679", "nan"]),
    (pd.Series([1.234, np.nan], dtype="float16"), ["1.234", "nan"]),
    (pd.Series(pd.to_datetime(["2026-01-01", None])), ["2026-01-01", "NaT"]),
    (pd.Series(pd.to_timedelta(["1 day", None])), ["1 days", "NaT"]),
])
def test_series_text_retains_dtype_aware_formatting(values, expected, pandas_mode):
    assert text_values(values, missing="stringify", non_text="stringify") == expected
    assert text_values(values, missing="empty", non_text="stringify") == [expected[0], ""]
    assert text_values(values, missing="none", non_text="stringify") == [expected[0], "None"]


def test_series_formatting_does_not_override_non_text_policies(pandas_mode):
    values = pd.Series([1.23456789, np.nan], dtype="float32")
    preserved = text_values(values, missing="empty", non_text="preserve")
    assert preserved[0] == values.iloc[0]
    assert not isinstance(preserved[0], str)
    assert preserved[1] == ""
    with pytest.raises(TypeError, match="Non-text value"):
        text_values(values, non_text="raise")
    with pytest.raises(ValueError, match="Missing values"):
        text_values(values, missing="raise")


@pytest.mark.parametrize("values", [
    pd.Series([], dtype="float32"), pd.Series([], dtype="datetime64[ns]"),
    pd.Series([], dtype="object"), pd.Series([], dtype="string"),
])
def test_empty_series_adaptation_is_empty(values, pandas_mode):
    assert text_values(values) == []


@pytest.mark.parametrize("values", [
    pd.Series([np.nan, np.nan], dtype="float32"),
    pd.Series([pd.NaT, pd.NaT], dtype="datetime64[ns]"),
    pd.Series([pd.NA, pd.NA], dtype="string"),
])
def test_all_missing_series_obey_explicit_missing_policy(values, pandas_mode):
    assert text_values(values, missing="none") == ["None", "None"]
    assert text_values(values, missing="empty") == ["", ""]
    assert all(is_missing_scalar(value) for value in text_values(values, missing="preserve"))


@pytest.mark.parametrize("policy, expected", [("empty", ""), ("none", "None")])
def test_missing_text_policies_do_not_rewrite_literal_strings(policy, expected):
    assert text_values([None, np.nan, pd.NA, pd.NaT, "nan", "None"], missing=policy) == [
        expected, expected, expected, expected, "nan", "None",
    ]


def test_preserve_policies_keep_original_structured_cells_and_missing_objects():
    container = [None, False]
    values = [container, {"a": None}, pd.NA, None, 0, False]
    result = text_values(values, missing="preserve", non_text="preserve")
    assert all(actual is original for actual, original in zip(result, values))


def test_reject_policies_are_explicit():
    with pytest.raises(ValueError, match="Missing values"):
        text_values([pd.NA], missing="raise")
    with pytest.raises(TypeError, match="Non-text value"):
        text_values([["a"]], non_text="raise")
    with pytest.raises(ValueError, match="missing must"):
        text_values([], missing="null")
    with pytest.raises(ValueError, match="non_text must"):
        text_matrix(pd.DataFrame(), non_text="guess")


@pytest.mark.parametrize("scalar", ["abc", None, 3, {"a": 1}])
def test_cell_iterables_cannot_accidentally_be_scalar_or_mapping(scalar):
    with pytest.raises(TypeError, match="iterable of cells"):
        text_values(scalar)


def test_matrix_and_join_preserve_row_order_and_integer_precision(pandas_mode):
    frame = pd.DataFrame({"integer": [2**60 + 1, 0], "decimal": [0.5, 1.5]})
    assert text_matrix(frame) == [[str(2**60 + 1), "0.5"], ["0", "1.5"]]
    assert joined_text_rows(frame, separator="|") == [f"{2**60 + 1}|0.5", "0|1.5"]
    assert text_matrix(pd.DataFrame(index=[9, 9])) == [[], []]
    assert joined_text_rows(pd.DataFrame(index=[9, 9])) == ["", ""]


def test_matrix_keeps_each_columns_native_formatting_including_duplicate_labels(pandas_mode):
    frame = pd.concat([
        pd.Series([1.23456789, np.nan], dtype="float32"),
        pd.Series(pd.to_datetime(["2026-01-01", None])),
        pd.Series(pd.to_timedelta(["1 day", None])),
    ], axis=1)
    frame.columns = ["same", "same", "duration"]
    assert text_matrix(frame, missing="empty") == [
        ["1.2345679", "2026-01-01", "1 days"], ["", "", ""],
    ]
    assert joined_text_rows(frame, separator="|", missing="none") == [
        "1.2345679|2026-01-01|1 days", "None|None|None",
    ]


@pytest.mark.parametrize("frame,expected_first_row", [
    (
        pd.DataFrame({
            "a": pd.to_datetime(["2026-01-01", None]),
            "b": pd.to_datetime(["2026-01-01 12:00:00", None]),
        }),
        ["2026-01-01 00:00:00", "2026-01-01 12:00:00"],
    ),
    (
        pd.DataFrame({
            "a": pd.to_timedelta(["1 day", None]),
            "b": pd.to_timedelta(["1 day 12:30:00", None]),
        }),
        ["1 days 00:00:00", "1 days 12:30:00"],
    ),
])
def test_matrix_retains_frame_wide_datetime_and_timedelta_block_formatting(frame, expected_first_row, pandas_mode):
    frame = frame.copy()
    frame.index = [4, 4]
    frame.columns = ["same", "same"]
    with pd.option_context("future.infer_string", False):
        assert frame.astype(str).values.tolist()[0] == expected_first_row
    # Preserve the native cast of the active pandas mode. Future inference
    # itself changes datetime-block formatting; the adapter must not add drift.
    active_first_row = frame.astype(str).values.tolist()[0]
    assert text_matrix(frame, missing="stringify") == [active_first_row, ["NaT", "NaT"]]
    assert text_matrix(frame, missing="empty") == [active_first_row, ["", ""]]
    assert joined_text_rows(frame, separator="|", missing="none") == [
        "|".join(active_first_row), "None|None",
    ]
    preserved = text_matrix(frame, missing="preserve", non_text="preserve")
    assert preserved[0][0] == frame.iloc[0, 0]
    assert not isinstance(preserved[0][0], str)
    with pytest.raises(TypeError, match="Non-text value"):
        text_matrix(frame, non_text="raise")


def test_join_requires_explicit_missing_to_text_policy(pandas_mode):
    frame = pd.DataFrame({"a": ["steel"], "b": [None]})
    assert joined_text_rows(frame, missing="none") == ["steel None"]
    with pytest.raises(TypeError):
        joined_text_rows(frame, missing="preserve")


def test_structured_normalization_is_explicit_recursive_and_preserves_keys():
    missing_key = np.nan
    source = [{missing_key: pd.NA, "values": [0, False, None, np.nan, pd.NaT, "nan", "None", ""]}]
    normalized = structured_values(source)
    assert next(iter(normalized[0])) is missing_key
    assert normalized[0][missing_key] is None
    assert normalized[0]["values"] == [0, False, None, None, None, "nan", "None", ""]
    assert source[0][missing_key] is pd.NA
    assert np.isnan(source[0]["values"][3])
    assert normalize_missing_values(float("inf")) == float("inf")
    untouched_tuple = (pd.NA,)
    assert normalize_missing_values(untouched_tuple) is untouched_tuple


def test_structured_normalization_rejects_cycles_but_allows_shared_containers():
    shared = [pd.NA]
    assert normalize_missing_values([shared, shared]) == [[None], [None]]
    recursive = []
    recursive.append(recursive)
    with pytest.raises(ValueError, match="Recursive containers"):
        normalize_missing_values(recursive)


def test_contract_decorator_preserves_callable_identity_signature_and_docstring():
    def operation(frame, input: str, *, output=None):
        """An unchanged schema-bearing docstring."""
        return frame

    signature = inspect.signature(operation)
    decorated = data_contract(
        "text_consumer", missing="none", non_text="stringify", output="text", notes="Legacy marker."
    )(operation)
    assert decorated is operation
    assert inspect.signature(decorated) == signature
    assert decorated.__doc__ == "An unchanged schema-bearing docstring."
    assert decorated.__data_contract__ == DataContract(
        "text_consumer", "none", "stringify", "text", "Legacy marker."
    )
    with pytest.raises(FrozenInstanceError):
        decorated.__data_contract__.missing = "empty"


@pytest.mark.parametrize("kwargs", [
    {"family": "guess"}, {"family": "typed", "missing": "guess"},
    {"family": "typed", "non_text": "guess"}, {"family": "typed", "output": "guess"},
])
def test_contract_metadata_rejects_unsupported_policies(kwargs):
    with pytest.raises(ValueError):
        data_contract(**kwargs)


def test_whole_assignment_is_positional_and_preserves_structured_cells(pandas_mode):
    frame = pd.DataFrame({"untouched": [1, 2]}, index=[9, 9])
    supplied = pd.Series([[1, 2], {"a": pd.NA}], index=[20, 21], dtype=object)
    assert assign_result(frame, "out", supplied, output_kind="structured") is frame
    assert frame.index.tolist() == [9, 9]
    assert frame["out"].iloc[0] == [1, 2]
    assert frame["out"].iloc[1]["a"] is pd.NA
    assert frame["out"].dtype == object
    assert frame["untouched"].tolist() == [1, 2]


def test_partial_structured_assignment_preserves_duplicate_row_positions(pandas_mode):
    frame = pd.DataFrame({"out": ["first", "second", "third"], "untouched": [1, 2, 3]}, index=[9, 9, 7])
    assign_result(frame, "out", [{"a": 0}, [False]], mask=[True, False, True], output_kind="structured")
    assert frame["out"].tolist() == [{"a": 0}, "second", [False]]
    assert frame["out"].dtype == object
    assert frame.index.tolist() == [9, 9, 7]
    assert frame["untouched"].tolist() == [1, 2, 3]


def test_partial_inference_keeps_compatible_storage_and_promotes_only_when_needed(pandas_mode):
    frame = pd.DataFrame({"out": [1, 2, 3], "other": ["a", "b", "c"]}, index=[8, 8, 4])
    other_dtype = frame["other"].dtype
    assign_result(frame, "out", [42], mask=pd.Series([False, True, False], index=frame.index))
    assert frame["out"].tolist() == [1, 42, 3]
    assert pd.api.types.is_integer_dtype(frame["out"].dtype)
    assign_result(frame, "out", ["changed"], mask=[True, False, False])
    assert frame["out"].tolist() == ["changed", 42, 3]
    assert frame["out"].dtype == object
    assert frame["other"].dtype == other_dtype


def test_partial_text_inference_keeps_string_storage(pandas_mode):
    frame = pd.DataFrame({"out": ["a", "b"]}, index=[4, 4])
    original_dtype = frame["out"].dtype
    assign_result(frame, "out", ["c"], mask=[True, False], output_kind="text")
    assert frame["out"].tolist() == ["c", "b"]
    assert frame["out"].dtype == original_dtype


def test_partial_numeric_widening_retains_native_pandas_storage(pandas_mode):
    frame = pd.DataFrame({"out": [1, 2], "untouched": [3, 4]}, index=[7, 7])
    expected = frame.copy()
    with pytest.warns(FutureWarning, match="incompatible dtype"):
        expected.loc[[True, False], "out"] = [1.5]
    assign_result(frame, "out", [1.5], mask=[True, False])
    pd.testing.assert_frame_equal(frame, expected)
    assert frame["out"].dtype == np.dtype("float64")
    assert frame["out"].tolist() == [1.5, 2.0]


@pytest.mark.parametrize("mask,values", [
    ([True, True], [1, 2]),
    ([True, False], [1]),
    ([False, True], [1.5]),
    ([True, False], [pd.Timestamp("2026-01-01")]),
    ([True, False], [pd.Timedelta("1 day")]),
    ([True, True], [1, "text"]),
])
def test_new_partial_inferred_output_retains_pandas_numeric_and_datetime_storage(mask, values, pandas_mode):
    expected = pd.DataFrame({"other": ["a", "b"]}, index=[7, 7])
    actual = expected.copy()
    # The baseline remains pandas 2.3's existing inference, including mixed
    # native scalars that future string inference otherwise rejects.
    with pd.option_context("future.infer_string", False):
        expected.loc[mask, "out"] = values
    assign_result(actual, "out", values, mask=mask)
    pd.testing.assert_frame_equal(actual, expected)


def test_new_numeric_matrix_lookup_retains_numeric_dtype_and_supports_next_math(monkeypatch):
    from wrangles.recipe_wrangles import main

    monkeypatch.setattr(main, "_model", lambda model_id: {
        "purpose": "lookup", "settings": {"columns": ["Value"]},
    })
    monkeypatch.setattr(main, "_lookup", lambda values, *args, **kwargs: [
        [{"a": 1, "b": 2}[value]] for value in values
    ])
    monkeypatch.setattr(main, "_define_permutations", lambda *args: [{"Region": "x"}])
    frame = pd.DataFrame({"Query": ["a", "b"], "Region": ["x", "x"]}, index=[7, 7])
    result = main.lookup(
        frame, input="Query", output="Value", model_id="synthetic",
        lookup_mode="by_matrix", matrix_variables=["Region"],
    )
    assert result["Value"].dtype == np.dtype("float64")
    assert result["Value"].tolist() == [1.0, 2.0]
    result = main.math(result, input="Value * 2", output="Doubled")
    assert result["Doubled"].tolist() == [2.0, 4.0]
    assert result.index.tolist() == [7, 7]


def test_output_writes_do_not_mutate_shared_parent_with_copy_on_write():
    with pd.option_context("mode.copy_on_write", True):
        parent = pd.DataFrame({"out": ["a", "b"]})
        child = parent.copy(deep=False)
        assign_result(child, "out", [{"value": False}], mask=[True, False], output_kind="mixed")
        assert parent["out"].tolist() == ["a", "b"]
        assert child["out"].tolist() == [{"value": False}, "b"]


@pytest.mark.parametrize("kwargs,values,error", [
    ({}, [1], ValueError),
    ({"mask": [True]}, [1], ValueError),
    ({"mask": [True, False]}, [1, 2], ValueError),
    ({"mask": [True, pd.NA]}, [1], TypeError),
    ({"mask": [1, 0]}, [1], TypeError),
    ({"mask": pd.Series([True, False], index=[1, 0])}, [1], ValueError),
    ({"output_kind": "text"}, ["a", False], TypeError),
    ({"output_kind": "guess"}, [1, 2], ValueError),
])
def test_invalid_output_contract_is_atomic(kwargs, values, error):
    frame = pd.DataFrame({"out": ["old", "same"]})
    before = frame.copy(deep=True)
    with pytest.raises(error):
        assign_result(frame, "out", values, **kwargs)
    pd.testing.assert_frame_equal(frame, before)


def test_empty_partial_selection_is_no_op_and_missing_cells_are_not_json_normalized(pandas_mode):
    frame = pd.DataFrame({"out": ["old", "same"]}, index=[5, 5])
    before = frame.copy(deep=True)
    assign_result(frame, "new", [], mask=[False, False], output_kind="structured")
    pd.testing.assert_frame_equal(frame, before)
    assign_result(frame, "out", [pd.NA, False], output_kind="mixed")
    assert frame["out"].iloc[0] is pd.NA
    assert frame["out"].iloc[1] is False
