# Named Excel tables in recipes

`excel.table` reads and writes an existing structured table in the calling
WranglesXL workbook. This is spreadsheet write mode `table`, alongside `columns`
and `sheet`. A table name identifies a workbook-wide object, not a worksheet or
selected range; names are matched case-insensitively. This connector does not
open an `.xlsx` file or use the current selection. For files, use `file`.

```yaml
read:
  - excel.table:
      name: Products
wrangles:
  - math:
      input: Price * 2
      output: Price
write:
  - excel.table:
      name: Results
      action: replace
```

Read tables must already exist. A missing write table is created by WranglesXL
with the output headers on its destination worksheet. Missing read tables and
missing names fail explicitly; there is no fallback to the active selection.
Selection input retains its separate contract
(`grid.selected_data` / `excel.selected_data` when those companion connectors are
available). This feature does not expand #943 or implement `excel.sql`.

## Reads and writes

For a missing output table, specify its worksheet and top-left cell:

```yaml
write:
  - excel.table:
      name: Results
      sheet: Output
      cell: C3
      action: replace
```

`cell` defaults to `A1`. Omitted `sheet` uses the first 10 characters of
`<recipe_name>-<table_name>`, using the recipe variable `recipe_name` supplied by
XL (`Recipe` when unavailable). For example, `Clean` + `Results` gives
`Clean-Resu`. Invalid generated worksheet characters are replaced by `_`.
Explicit worksheet names are not truncated. Absolute cell references such as
`$C$3` are accepted and normalized to `C3`.

Existing workbook-wide tables retain their worksheet and location; `sheet` and
`cell` only select the location for a missing table. XL creates a missing worksheet,
but refuses occupied cells, table overlaps, invalid table names and out-of-bounds
results before any table mutation. Empty output creates a header-only table.
The 10-character prefix can collide for multiple output tables: provide distinct
`sheet`/`cell` destinations when needed. Batched outputs reuse the new table.

- Read headers and every body row, including filtered/hidden rows, excluding
  the totals row. A table with no body rows yields an empty dataframe with its
  headers. Ordinary recipe read options (`columns`, `where`, etc.) still apply.
- `replace` (default) clears/replaces the body, including empty results, and
  adjusts the table's row count. Existing table name, headers and table identity
  remain. It does not replace a worksheet.
- `append` adds rows; empty results add nothing. Existing and output column
  names must match exactly, but their order may differ: XL aligns values by name.
  Header names must be non-empty strings and unique ignoring case. New/missing
  columns fail; no columns are silently dropped or invented.
- Each write is an ordered operation. Repeated writes in a single request stay
  separate. For external selection batches, a `replace` becomes `append` after
  the first batch to retain every batch's rows.
- In this initial implementation, write targets with active filters or body
  formulas are rejected before mutation. Clear target filters first. Calculated
  columns are not replaced or silently converted to values. Incoming strings
  beginning with `=` are also rejected instead of being interpreted as formulas.

Read snapshots are captured before execution and stay unchanged for that run,
including when the same table is also a destination. A recipe may compose table
reads through `union`, `join` or `concatenate`. A table-only recipe runs once,
independently of the user's unrelated selection. If combined with selected-data
reads, each selected-data batch uses the same full table snapshot.

## Workbook transport

WranglesXL injects the reserved recipe variable `__excel_tables`:

```json
{"Products": {"columns": ["ID", "Price"], "data": [[1, 10], [2, 20]]}}
```

Python reads this mapping through its existing recipe-variable injection. Input
snapshots are never added to `memory.dataframes`, since the Lambda returns that
collection as write results. Python writes a split dataframe payload with
`connector: excel.table.write`, `name`, `action`, `sheet`, and `cell`. Missing
dataframe values introduced by `union`, join, or other reads are emitted as JSON
`null` in table output without changing the logical dataframe or input snapshots.
The existing Lambda variable
and output transport can carry this contract without a new top-level API field.
Do not set `__excel_tables` as a user runtime variable in XL; XL owns it.

XL routes table payloads separately from sheet/columns output and stages them
until recipe execution completes. It validates all staged table destinations
before starting table mutations. Excel writes are not a transaction: a later
Office API failure may still leave earlier changes applied. This staging does
not make unrelated sheet writes atomic or provide a rollback mechanism.

## Integration and verification

Python-only installation cannot read an open workbook. Deploy the matching
WranglesXL companion and publish the Python version and generated recipe schema
before enabling this feature. Saved child recipes whose reads are not visible to
XL planning cannot request additional workbook snapshots dynamically; keep table
reads in the effective top-level recipe (including supported compositions).
Workbook snapshots must fit the existing request-size limits; oversized requests
fail rather than silently truncating table data. This first version does not
introduce streaming table input.

Offline validation:

```sh
python -m pytest -c pytest-local.ini tests/connectors/test_excel.py -q
```

Before closing #1220, verify in live Excel with synthetic data: all-row reading
under filters, totals exclusion, empty tables, replacement growing/shrinking and
clearing rows, append/reordered columns, missing names, formula/filter rejection,
multiple writes, selection batches, cancellation/failure before table writes,
and preservation of table identity and surrounding cells. Record Python, XL,
JS and Lambda versions. Offline mocks do not establish deployed Office behavior.
