# Missing values across Python, pandas, and JSON

[Overview](../README.md) · [Wrangles data contracts](data-contracts.md)

This guide explains the behavior behind the operation-policy review. It does
not choose new Wrangles defaults. Examples distinguish an actual missing value
from text that merely looks like one.

The pandas comparison is **2.3.3 versus 3.1.1**. Unless a version is stated,
the examples describe behavior shared by both. A Python example and a JSON
example may use different spellings for the same value.

## 1. The states we need to distinguish

| State | Python example | JSON example | Meaning |
| --- | --- | --- | --- |
| Field absent | `{}` | `{}` | No `description` member was supplied. |
| Field present with a null | `{"description": None}` | `{"description": null}` | The member exists, with an explicit null value. The business meaning needs a contract. |
| Empty text | `{"description": ""}` | `{"description": ""}` | A string was supplied, with zero characters. |
| Whitespace text | `{"description": "  "}` | `{"description": "  "}` | Two characters were supplied. Calling this empty requires an additional rule. |
| Literal text | `{"description": "None"}` | `{"description": "None"}` | The four letters `None`, not a null. |
| Valid falsy value | `{"quantity": 0, "active": False}` | `{"quantity": 0, "active": false}` | Real numeric and Boolean values. |
| Empty collection | `{"items": []}` | `{"items": []}` | A collection with no members. Whether this differs from an unknown collection is a business decision. |

**Missing** describes a condition; it is not one universal Python value.
An absent field, an unknown measurement, a failed calculation, and an explicit
request to clear a value can all be described as missing, but they need not
mean the same thing. Neither `None` nor JSON `null` records *why* a value is
missing.

## 2. Python: `None`, NaN, and truthiness

The examples below start with these imports:

```pycon
>>> import json
>>> import math
>>> import numpy as np
>>> import pandas as pd
```

### `None` is a distinct value

Python has the singleton `None`. Check for it with `is None`. The names `null`
and `nan` are not built-in Python constants; use `None`, `float("nan")`, or
`np.nan` as appropriate.

```pycon
>>> value = None
>>> value is None
True
>>> value == "None"
False
>>> str(value)
'None'
```

That last conversion changes the type and loses a distinction: `str(None)` and
the original text `"None"` now have the same value.

### An absent dictionary key is different from a `None` value

```pycon
>>> absent = {}
>>> explicit_null = {"value": None}
>>> "value" in absent, "value" in explicit_null
(False, True)
>>> absent.get("value"), explicit_null.get("value")
(None, None)
```

Using `.get()` without a distinct default hides that difference. Use membership
testing when presence matters, or use an internal sentinel as described below.
[Python dictionary behavior](https://docs.python.org/3/library/stdtypes.html#mapping-types-dict)

### NaN is a floating-point value with special comparison rules

NaN means “not a number.” It can arise from numerical work; pandas also uses it
to represent missing data. Its presence alone does not explain the cause.

```pycon
>>> number = float("nan")
>>> math.isnan(number)
True
>>> number == number
False
>>> number is None
False
>>> str(number)
'nan'
```

Use `math.isnan()` for an appropriate numeric scalar, or pandas' missing-value
detection for pandas data. Equality with NaN is not a missing-value test.
[Python floating-point helpers](https://docs.python.org/3/library/math.html#math.isnan)

### Falsy does not mean missing

Python's `if value` and `value or fallback` use truthiness. They do not ask
whether the value is missing.

```pycon
>>> [bool(x) for x in [None, "", 0, False, [], {}, "  ", "nan", float("nan")]]
[False, False, False, False, False, False, True, True, True]
>>> 0 or "fallback"
'fallback'
>>> float("nan") or "fallback"
nan
```

The same fallback expression discards a valid zero and retains a missing NaN.
Also, `False == 0` is `True` in Python. A deduplication or filtering rule may
need to distinguish their types explicitly.
[Python truth-value rules](https://docs.python.org/3/library/stdtypes.html#truth-value-testing)

## 3. pandas: the column dtype determines the missing representation

pandas provides `pd.isna()` / `pd.notna()` to recognize supported null values.
`isnull()` / `notnull()` are aliases; the different names do not define
different kinds of missing data.

| Column or scalar context | Typical missing representation | Important consequence |
| --- | --- | --- |
| Python objects in an `object` column | `None`, `np.nan`, `pd.NA`, or `pd.NaT` can coexist | Original scalar forms can remain distinct even though pandas considers all missing. |
| Ordinary NumPy floating-point column | `np.nan`, displayed as `NaN` | An integer input with a missing value commonly becomes floating point. |
| Nullable integer, e.g. `Int64` | `pd.NA`, displayed as `<NA>` | Integers and missing values coexist without becoming floats. `Int64` and NumPy `int64` are different dtypes. |
| Nullable text, `dtype="string"` | `pd.NA` | Available in both pandas versions; distinct from the new default `str` dtype. |
| Default text in pandas 3.1.1, `dtype="str"` | NaN | Supported missing inputs such as `None` become NaN. Non-string assignments are restricted. |
| NumPy-backed datetime/timedelta column | `pd.NaT`, displayed as `NaT` | A missing timestamp or duration. Arrow-backed date/time dtypes can use `pd.NA` instead. |

These are dtype conventions, not separate business definitions of missingness.
[Pandas missing-data guide](https://pandas.pydata.org/docs/user_guide/missing_data.html)

```pycon
>>> ordinary = pd.Series([1, None])
>>> str(ordinary.dtype), ordinary.tolist()
('float64', [1.0, nan])
>>> nullable = pd.Series([1, None], dtype="Int64")
>>> str(nullable.dtype), nullable.tolist()
('Int64', [1, <NA>])
>>> objects = pd.Series([None, np.nan, pd.NA, pd.NaT], dtype=object)
>>> objects.isna().tolist()
[True, True, True, True]
```

For scalar cells, blank text and marker-looking text are not pandas nulls:

```pycon
>>> pd.isna([None, np.nan, pd.NA, pd.NaT, "", "  ", "nan", "None", "null", 0, False]).tolist()
[True, True, True, True, False, False, False, False, False, False, False]
>>> pd.isna([np.inf, -np.inf]).tolist()
[False, False]
```

Infinity is not considered missing by this check, even though standard JSON
cannot represent it as a number. Missing-value normalization and numeric
validity checking therefore answer different questions.

For a list or array, `pd.isna()` returns an array of answers. It is not a single
Boolean suitable for `if pd.isna(cell)` when a cell might itself contain a list.
A dictionary containing a missing value also does not automatically become a
missing dictionary. Scalar detection and recursive container handling are
separate operations.
[pandas.isna](https://pandas.pydata.org/docs/reference/api/pandas.isna.html)

### Missing comparisons and calculations have different rules

```pycon
>>> np.nan == np.nan
False
>>> pd.NaT == pd.NaT
False
>>> pd.NA == pd.NA
<NA>
>>> pd.NA + 1
<NA>
>>> bool(pd.NA)
Traceback (most recent call last):
    ...
TypeError: boolean value of NA is ambiguous
```

`pd.NA` often propagates “unknown” through expressions instead of returning a
definite answer. Use an explicit missing-value check before a scalar Boolean
decision. NaN and NaT, in contrast, are truthy scalars.

Reductions can intentionally skip missing values. Even an all-missing numeric sum
defaults to zero; `min_count` can require actual observations:

```pycon
>>> amounts = pd.Series([np.nan, np.nan], dtype="float64")
>>> float(amounts.sum())
0.0
>>> bool(pd.isna(amounts.sum(min_count=1)))
True
```

Consequently, “unknown total” and “known total of zero” can collapse unless the
operation specifies its rule.
[Series.sum](https://pandas.pydata.org/docs/reference/api/pandas.Series.sum.html)

### What changes for text between 2.3.3 and 3.1.1?

| Expression | pandas 2.3.3, ordinary defaults | pandas 3.1.1, ordinary defaults |
| --- | --- | --- |
| `pd.Series(["a", None])` | `object` dtype; second cell is `None` | `str` dtype; second cell is NaN |
| `pd.Series(["a", None], dtype="string")` | Nullable text; second cell is `pd.NA` | Nullable text; second cell is `pd.NA` |
| `pd.Series([1.5, np.nan]).astype(str).tolist()` | `["1.5", "nan"]` | `["1.5", np.nan]` |

The last row is a material migration change: pandas 3 preserves missingness
through this cast instead of converting every missing cell into text.
An extractor expecting every cell to be a Python string can therefore receive
a floating-point NaN.

Arrow can store the string data while recording nullness separately through a
validity bitmap. It does not require storing the letters `"nan"` or `"<NA>"` in
the string. Pandas' dtype determines the missing scalar exposed to Python.
[String migration guide](https://pandas.pydata.org/docs/user_guide/migration.html#the-new-string-data-type),
[Arrow validity bitmaps](https://arrow.apache.org/docs/format/Columnar.html#validity-bitmaps)

`fillna("")` deliberately merges missing cells with empty text. That may be a
useful boundary rule, but it loses information and is not valid for every
typed column. Likewise, converting a null to `"None"` creates ordinary text;
decoding every later `"None"` back to a null would corrupt genuine input text.
Preserving existing numeric/date text formatting is a separate concern from
choosing what to do with missing values.

## 4. JSON: `null` is its null value; absence is represented structurally

JSON has strings, numbers, Booleans, nulls, arrays, and objects. Its null literal
is lowercase `null`. It has no `None`, `pd.NA`, NaT, or numeric NaN literal.
Object member names must be strings. Names should be unique for interoperable
behavior. [JSON specification, sections 3–6](https://www.rfc-editor.org/rfc/rfc8259.html#section-3)

```json
{
  "missing_value": null,
  "empty_text": "",
  "literal_text": "null",
  "quantity": 0,
  "active": false,
  "items": []
}
```

Python's standard `json` module maps `None` to `null` and back:

```pycon
>>> json.dumps({"value": None, "literal": "None", "empty": "", "active": False})
'{"value": null, "literal": "None", "empty": "", "active": false}'
>>> json.loads('{"value": null}')
{'value': None}
>>> json.loads('{}')
{}
```

In JSON, `{}` and `{"value": null}` remain different. A particular API might
interpret omission as “leave unchanged” and null as “clear the value,” but that
meaning comes from the API contract, not JSON itself. Arrays have no absent
member syntax: removing an entry changes the array length and later positions.
[Python JSON conversion tables](https://docs.python.org/3/library/json.html#encoders-and-decoders)

### Python's default JSON encoder permits nonstandard NaN tokens

```pycon
>>> json.dumps({"value": float("nan")})
'{"value": NaN}'
>>> math.isnan(json.loads('NaN'))
True
```

That unquoted `NaN` is **not standard JSON**, even though Python accepts it.
The same issue applies to `Infinity` and `-Infinity`. Encoding with
`allow_nan=False` rejects these numeric values; it does not turn them into
nulls. If the intended output is null, conversion to Python `None` must happen
explicitly first.

```python
json.dumps({"value": float("nan")}, allow_nan=False)  # Raises ValueError
json.dumps({"value": None}, allow_nan=False)          # '{"value": null}'
```

On input, `parse_constant` can reject the three nonstandard tokens.
`strict=True` alone does not do this; that option governs control characters
inside strings. Extremely large numeric exponents can also overflow Python
floats, so rejecting those tokens alone is not complete numeric validation.
[Python JSON interoperability behavior](https://docs.python.org/3/library/json.html#standard-compliance-and-interoperability)

`pd.NA`, `pd.NaT`, and custom sentinel objects are not supported by the standard
encoder without an explicit conversion. Using `default=str` can hide this by
creating strings such as `"<NA>"`; it does not establish a null policy. Numeric
NaN is already handled by the encoder, so `default=str` does not fix its
nonstandard numeric output either.

### Keys need their own policy

Python dictionaries accept hashable keys. The standard JSON encoder accepts
certain non-string key types and converts them to strings. Distinct keys can
then collide:

```pycon
>>> payload = {None: "missing-key", "null": "text-key"}
>>> json.dumps(payload)
'{"null": "missing-key", "null": "text-key"}'
>>> json.loads(json.dumps(payload))
{'null': 'text-key'}
```

The first pair was lost on decoding. Replacing missing *values* with `None`
does not solve missing or colliding *keys*. A JSON-facing dictionary builder
needs a deliberate key contract as well as a value contract.

## 5. Round trips do not necessarily preserve the original distinctions

### JSON → Python → pandas → JSON

Consider two records: one omits `value`; the other explicitly supplies null.

```pycon
>>> rows = json.loads('[{}, {"value": null}]')
>>> ["value" in row for row in rows]
[False, True]
>>> frame = pd.DataFrame(rows)
>>> frame["value"].isna().tolist()
[True, True]
>>> frame.to_json(orient="records")
'[{"value":null},{"value":null}]'
```

The DataFrame normalizes records into columns and fills absent cells. This
round trip loses the original presence distinction. If presence matters,
capture it before constructing the DataFrame, for example in a separate
presence column or mask.
[DataFrame construction](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html)

### `to_dict()` and `to_json()` are different boundaries

```pycon
>>> frame = pd.DataFrame({"value": [1.0, np.nan]})
>>> records = frame.to_dict(orient="records")
>>> math.isnan(records[1]["value"])
True
>>> frame.to_json(orient="records")
'[{"value":1.0},{"value":null}]'
```

`to_dict()` creates Python containers; it does not promise that every leaf is
ready for strict JSON. Some dtype-specific nulls become `None`, but floating
NaN can remain, and nested container cells need separate attention.
`DataFrame.to_json()` has its own null conversion behavior. Therefore,
`json.dumps(frame.to_dict(...), allow_nan=False)` need not succeed where
`frame.to_json(...)` does.
[DataFrame.to_dict](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_dict.html),
[DataFrame.to_json](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_json.html)

### File readers can interpret text as missing

An in-memory string `"NA"` or `"null"` is real text. However, `read_csv()` has
default missing-token recognition, including several such strings and empty
fields. Options including `keep_default_na` and `na_values` control this.
That is a reader rule, not an inherent property of the text. Inspect the input
boundary when a legitimate code or label appears to disappear.
[CSV missing-value options](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html)

## 6. Custom sentinels distinguish internal states

Python 3.15 added `sentinel()`, which creates a unique object checked with `is`:

```python
# Python 3.15; illustrative API example, not a Wrangles policy change.
UNSET = sentinel("UNSET")

def transform(value=UNSET):
    if value is UNSET:
        return "argument omitted"
    if value is None:
        return "explicit null"
    return value

transform()        # "argument omitted"
transform(None)    # "explicit null"
transform("")      # ""
transform("None")  # "None"
```

This can distinguish an omitted argument from an explicit `None` without using
a magic string that might also occur in user data. The built-in preserves
identity through copying and supports pickling for appropriately importable
definitions. Sentinels are truthy; their display name does not make them null.
[Python sentinel documentation](https://docs.python.org/3.15/builtins/functions.html#sentinel)

The compatible `typing_extensions.sentinel` backport is available from
`typing_extensions` 4.16; older releases exposed an earlier `Sentinel` API.
This provides a path for supported Python versions before 3.15 if the project
chooses to use it. [Backport documentation](https://typing-extensions.readthedocs.io/en/latest/#sentinel-objects)

An application sentinel is not automatically recognized as a pandas missing
cell, an Arrow null, or JSON `null`. It needs an explicit translation at those
boundaries. Internal control state and stored data representation are separate
design decisions.

## 7. How this maps to the Wrangles policy review

In the workbook, **“markers” means legacy text representations of missing
values**, such as `"nan"` or `"None"`. It does not mean custom Python sentinel
objects. Preserving those strings, preserving actual nulls, and substituting
empty text are three different behaviors.

The [shared data-contract layer](data-contracts.md) separates scalar detection,
empty-text rules, text conversion, structured-value normalization, and result
assignment. Its structured normalizer handles list/dictionary *values*; it is
not a strict JSON validator or a dictionary-key sanitizer.

Current recipe execution attempts top-level `fillna("")` followed by
`fillna("0")` after ordinary wrangle steps. These are strings, including the
second pass's `"0"`; typed columns can reject such replacements. This cleanup
is not universally successful and does not recursively normalize list/dictionary
cells. Direct DataFrame accessors bypass the recipe-wide cleanup.
Consequently, a first step, a later step, and a direct accessor can see different
representations. File readers can also normalize values before the first step:
the CSV/JSON connector paths apply `fillna("")` after pandas reads the file.
These are existing behaviors to review, not newly agreed policies.
[Recipe execution](../wrangles/recipe.py), [DataFrame accessors](../wrangles/dataframe.py),
[file connector](../wrangles/connectors/file.py)

The guide leaves these decisions open:

| Decision | Distinctions to preserve or intentionally merge |
| --- | --- |
| Missing text input | Preserve a null, skip processing, substitute empty text, or retain a compatibility text spelling? |
| Empty handling | Are `""`, whitespace, empty lists, and empty dictionaries equivalent for this operation? |
| Valid falsy values | When, if ever, should zero or false be filtered? |
| Structured/API output | Does a missing result mean an absent member or a member with `null`? What may be used as a key? |
| Invalid numerical results | Reject NaN/infinity, report an error state, or deliberately map them to null? |
| Presence and provenance | Must “not supplied,” “unknown,” “not applicable,” and “failed” survive later transformations? If so, where is that state recorded? |

### Verification scope

The interactive examples were checked locally with Python 3.13.1, pandas 2.3.3,
NumPy 2.4.2, and PyArrow 24.0.0. The pandas 3.1.1 comparison and Python 3.15
sentinel API are documented behavior from the linked primary sources; they
were not executed as part of this documentation check. No live Wrangles
service calls are needed for these examples. Reference links were reviewed
on November 14, 2026.
