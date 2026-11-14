"""Explicit data-boundary adapters shared by recipe wrangles.

These helpers do not change pandas defaults or normalize an entire recipe.
Callers choose how their own boundary handles missing and non-text values.
The decorator records that choice without wrapping or changing the function.
"""

from dataclasses import dataclass as _dataclass
import warnings as _warnings

import numpy as _np
import pandas as _pd


FAMILIES = frozenset({
    "text_transform", "text_consumer", "structured", "mixed_result", "typed",
    "orchestration", "passthrough",
})
MISSING_POLICIES = frozenset({"preserve", "stringify", "empty", "none", "raise"})
NON_TEXT_POLICIES = frozenset({"preserve", "stringify", "raise"})
OUTPUT_KINDS = frozenset({"infer", "mixed", "structured", "text"})


def _validate_choice(name, value, choices):
    if value not in choices:
        raise ValueError(f"{name} must be one of: {', '.join(sorted(choices))}")


@_dataclass(frozen=True)
class DataContract:
    """Review metadata; declarations do not imply runtime normalization."""

    family: str
    missing: str = "preserve"
    non_text: str = "preserve"
    output: str = "infer"
    notes: str = ""


def data_contract(family, *, missing="preserve", non_text="preserve", output="infer", notes=""):
    """Attach a frozen ``__data_contract__`` descriptor to the original callable."""
    _validate_choice("family", family, FAMILIES)
    _validate_choice("missing", missing, MISSING_POLICIES)
    _validate_choice("non_text", non_text, NON_TEXT_POLICIES)
    _validate_choice("output", output, OUTPUT_KINDS)
    if not isinstance(notes, str):
        raise TypeError("notes must be a string")
    descriptor = DataContract(family, missing, non_text, output, notes)

    def decorate(function):
        function.__data_contract__ = descriptor
        return function

    return decorate


def is_missing_scalar(value):
    """Return one Boolean without treating containers or falsy values as nulls."""
    if not _pd.api.types.is_scalar(value):
        return False
    return bool(_pd.isna(value))


def is_empty_scalar(value, *, whitespace=False):
    """Recognize missing scalars and empty text, optionally including whitespace."""
    if is_missing_scalar(value):
        return True
    if isinstance(value, str):
        return not value.strip() if whitespace else value == ""
    return False


def _iter_values(values):
    if isinstance(values, (str, bytes, dict, _pd.DataFrame)) or _pd.api.types.is_scalar(values):
        raise TypeError("values must be a one-dimensional iterable of cells")
    return iter(values)


def _text_value(value, missing, non_text):
    if is_missing_scalar(value):
        if missing == "raise":
            raise ValueError("Missing values are not allowed at this text boundary")
        if missing == "empty":
            return ""
        if missing == "none":
            return "None"
        if missing == "stringify":
            return str(value)
        return value
    if isinstance(value, str) or non_text == "preserve":
        return value
    if non_text == "raise":
        raise TypeError(f"Non-text value of type {type(value).__name__} is not allowed")
    return str(value)


def text_values(values, *, missing="stringify", non_text="stringify"):
    """Adapt cells to a list using explicit missing and non-text policies.

    A Series with ``non_text="stringify"`` retains pandas' dtype-aware text
    formatting for non-missing values, such as float32 precision and dates.
    Other iterables use Python's ``str``. The missing policy remains independent:
    ``stringify`` preserves Python's distinct ``None``, ``nan``, ``<NA>`` and
    ``NaT`` spellings; ``none`` uses literal ``"None"`` for every missing scalar.
    Containers remain whole cells; only ``non_text="stringify"`` stringifies them.
    """
    _validate_choice("missing", missing, MISSING_POLICIES)
    _validate_choice("non_text", non_text, NON_TEXT_POLICIES)
    if isinstance(values, _pd.Series) and non_text == "stringify":
        missing_positions = _np.flatnonzero(values.isna().to_numpy())
        if missing == "raise" and len(missing_positions):
            raise ValueError("Missing values are not allowed at this text boundary")
        result = values.astype(str).tolist()
        for position in missing_positions:
            result[position] = _text_value(values.iloc[position], missing, non_text)
        return result
    return [_text_value(value, missing, non_text) for value in _iter_values(values)]


def text_matrix(frame, *, missing="stringify", non_text="stringify"):
    """Adapt a frame while retaining pandas' context-aware text formatting.

    Stringification follows the original frame-wide cast, including datetime
    and timedelta blocks whose display precision depends on another column.
    Explicit missing policies are applied afterwards. Preserve/reject non-text
    policies avoid that cast and inspect each original column instead.
    """
    _validate_choice("missing", missing, MISSING_POLICIES)
    _validate_choice("non_text", non_text, NON_TEXT_POLICIES)
    if not isinstance(frame, _pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")
    if not len(frame.columns):
        return [[] for _ in range(len(frame))]
    if non_text == "stringify":
        missing_rows, missing_columns = _np.nonzero(frame.isna().to_numpy())
        if missing == "raise" and len(missing_rows):
            raise ValueError("Missing values are not allowed at this text boundary")
        result = frame.astype(str).to_numpy(dtype=object).tolist()
        for row, column in zip(missing_rows, missing_columns):
            result[row][column] = _text_value(frame.iloc[row, column], missing, non_text)
        return result
    columns = [
        text_values(frame.iloc[:, index], missing=missing, non_text=non_text)
        for index in range(len(frame.columns))
    ]
    return [list(row) for row in zip(*columns)]


def joined_text_rows(frame, separator=" ", *, missing="stringify", non_text="stringify"):
    """Join adapted row cells; preserved non-string cells remain an error."""
    if not isinstance(separator, str):
        raise TypeError("separator must be a string")
    return [separator.join(row) for row in text_matrix(frame, missing=missing, non_text=non_text)]


def normalize_missing_values(value):
    """Opt in to Python ``None`` for missing scalars in list/dict values.

    Dictionary keys are unchanged. Other containers and non-missing leaf values
    are preserved, including zero, false, literal marker strings and infinities.
    This is not JSON validation or serialization; strict JSON boundaries keep
    their separate rules. Input containers are not mutated.
    """
    def normalize(item, active_ids):
        if is_missing_scalar(item):
            return None
        if not isinstance(item, (list, dict)):
            return item
        item_id = id(item)
        if item_id in active_ids:
            raise ValueError("Recursive containers cannot be normalized")
        active_ids.add(item_id)
        try:
            if isinstance(item, list):
                return [normalize(child, active_ids) for child in item]
            return {key: normalize(child, active_ids) for key, child in item.items()}
        finally:
            active_ids.remove(item_id)

    return normalize(value, set())


def structured_values(values):
    """Normalize missing list/dict cells at an explicitly chosen boundary."""
    return [normalize_missing_values(value) for value in _iter_values(values)]


def _object_values(values):
    # Construct a one-dimensional array even when every cell is a same-size list.
    result = _np.empty(len(values), dtype=object)
    for index, value in enumerate(values):
        result[index] = value
    return result


def assign_result(df, column, values, *, mask=None, output_kind="infer"):
    """Assign one value per destination row and return the same frame.

    Values are positional, including when supplied as a Series. A Series mask
    must have exactly the frame's index and row order; other masks are positional
    Boolean iterables. Missing mask entries are rejected rather than guessed.

    Whole-column ``infer`` and ``text`` writes use ordinary pandas inference.
    ``text`` also validates that supplied cells are strings or missing scalars.
    Declared ``mixed``/``structured`` output uses object storage only for the
    destination. Partial inferred/text writes retain its dtype when possible,
    otherwise promoting that column to object without converting its cells.
    An empty partial selection is a no-op. All validation precedes frame mutation.
    """
    _validate_choice("output_kind", output_kind, OUTPUT_KINDS)
    if not isinstance(df, _pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if column in df.columns and not isinstance(df[column], _pd.Series):
        raise ValueError("The destination column label must be unique")
    supplied = list(_iter_values(values))
    if output_kind == "text" and any(
        not isinstance(value, str) and not is_missing_scalar(value)
        for value in supplied
    ):
        raise TypeError("Text output must contain only strings or missing scalars")

    if mask is None:
        if len(supplied) != len(df):
            raise ValueError("values must contain one cell per destination row")
        dtype = object if output_kind in {"mixed", "structured"} else None
        candidate = _pd.Series(supplied, index=df.index, dtype=dtype)
    else:
        if isinstance(mask, _pd.Series) and not mask.index.equals(df.index):
            raise ValueError("A Series mask must match the frame index and row order")
        selected = list(_iter_values(mask))
        if len(selected) != len(df):
            raise ValueError("mask must contain one Boolean per frame row")
        if any(not isinstance(value, (bool, _np.bool_)) for value in selected):
            raise TypeError("mask must contain only Booleans, without missing values")
        positions = [index for index, selected_row in enumerate(selected) if selected_row]
        if len(supplied) != len(positions):
            raise ValueError("values must contain one cell per selected row")
        if not positions:
            return df
        if column not in df.columns and output_kind in {"infer", "text"}:
            # A partial new column uses pandas' native missing representation
            # and inference (numeric/NaN, datetime/NaT, etc.). Initializing an
            # object column of None would prevent that inference permanently.
            # Keep this operation isolated until all writes have succeeded.
            temporary = _pd.DataFrame(index=df.index)
            replacement = (
                _object_values(supplied)
                if any(not _pd.api.types.is_scalar(value) for value in supplied)
                else supplied
            )
            try:
                temporary.loc[_np.asarray(selected, dtype=bool), column] = replacement
                candidate = temporary[column]
            except (TypeError, ValueError):
                # Future string inference can choose a string destination for
                # mixed scalar results. Keep those native cells as object data.
                candidate = _pd.Series(_np.nan, index=df.index, dtype=object)
                candidate.iloc[positions] = _object_values(supplied)
            df[column] = candidate
            return df
        base = (
            df[column] if column in df.columns
            else _pd.Series([None] * len(df), index=df.index, dtype=object)
        )
        candidate = (
            base.astype(object) if output_kind in {"mixed", "structured"}
            else base.copy()
        )
        object_replacement = _object_values(supplied)
        # Let pandas retain a numeric/extension dtype for compatible scalar
        # input. An object array would request object storage even for [42].
        # Object destinations and structured cells need the explicit 1-D array.
        replacement = (
            object_replacement
            if _pd.api.types.is_object_dtype(candidate.dtype)
            or any(not _pd.api.types.is_scalar(value) for value in supplied)
            else supplied
        )
        numeric_write = (
            _pd.api.types.is_numeric_dtype(base.dtype)
            and not _pd.api.types.is_bool_dtype(base.dtype)
            and all(
                isinstance(value, (int, float, complex, _np.number))
                and not isinstance(value, (bool, _np.bool_))
                for value in supplied
            )
        )
        try:
            with _warnings.catch_warnings():
                # Numeric widening (e.g. int64 to float64) is pandas 2.3's
                # existing behavior. Its warning is not evidence that the
                # destination needs object storage. Keep mixed-type warnings
                # as the signal to preserve those cells explicitly instead.
                _warnings.filterwarnings(
                    "ignore" if numeric_write else "error",
                    message="Setting an item of incompatible dtype", category=FutureWarning,
                )
                candidate.iloc[positions] = replacement
        except (TypeError, ValueError, FutureWarning):
            if _pd.api.types.is_object_dtype(candidate.dtype):
                raise
            candidate = base.astype(object)
            candidate.iloc[positions] = object_replacement

    df[column] = candidate
    return df
