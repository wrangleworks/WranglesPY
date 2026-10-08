# Spreadsheet recipe inputs and writes

`excel.selected_data` reads the selected data supplied by WranglesXL for the
current recipe batch. It wraps `grid.selected_data`, which provides the same
options and behavior for grid hosts. Both support the usual read filters such
as `columns`, `not_columns`, and `where`.

```yaml
read:
  - join:
      how: left
      left_on: ID
      right_on: ID
      sources:
        - excel.selected_data: {}
        - file:
            name: products.csv
```

Excel batches only the selected rows. A batch size of 2 over five rows sends
2, 2, and 1 rows, with the matching selection headings, batch number, batch
total, and row count. External-only reads execute once, independently of the
selection's size. A mixed recipe executes its authored external reads for each
selected-data batch; scope ID-based queries to that batch's IDs when necessary.
An unfiltered external source can repeat rows across union batches.

Selected data must be present and nonempty. A missing or empty selected-data
operand in a join, union, or concatenate raises an error, including when its
read filters remove every row. Legacy `input` remains supported; a standalone
generic Python `input` can still represent an empty dataframe. Within a nested
recipe wrangle, these reads use the current parent dataframe, including earlier
transformations. They do not reread the original UI selection. The `read:
recipe` connector does not inherit that dataframe.

## Spreadsheet write modes

| Mode | Connector | Behavior |
| --- | --- | --- |
| `columns` | `excel.columns` | Insert new/changed output columns alongside the selected rows. |
| `sheet` | `excel.sheet` | Write all requested columns to the configured sheet/range. |

The complete calculation dataframe remains available. In columns mode, XL
compares the returned values with that batch's input and omits unchanged input
columns from the write. If everything is unchanged, nothing is inserted. The
number of output rows must equal the number of selected input rows; use sheet
mode for row-expanding or row-reducing results. Validation happens before
columns or headers are inserted for the batch.

```yaml
write:
  - excel.columns:
      columns: [Description, Category]
  - excel.sheet:
      name: Complete result
      action: overwrite
```

Each write respects its own column selection. Sheet mode retains unchanged
input columns and the existing `name`, `cell`, action, and formatting options.
Later API batches append to the same resolved target. `matrix` repeats its
configured child writes: a child `excel.sheet` still uses sheet mode. Matrix
is a separate connector and is not another spreadsheet write mode.

Columns appearing in later batches are appended in first-seen order, with
values aligned by column name. Their final order cannot be known in advance.
If an input column first changes in a later batch, XL fills its earlier output
cells from the original selected values; it also retains subsequent unchanged
values in that output column. It stores range coordinates rather than buffering
the complete selection.

## Compatibility and execution

- `dataframe` keeps its Python return-value and column-selection semantics.
  In XL columns mode, the runner translates a top-level legacy `dataframe`
  write to `excel.columns`, including when combined with sheet writes.
- Recipes using selected data default to columns mode. Existing external-only
  top-level reads retain their implicit sheet output. Legacy `output: range`
  and `output: sheet` select the default mode; explicit `excel.columns` and
  `excel.sheet` payloads select their own modes.
- An explicit columns write from an external-only read uses the selection only
  as an output target and checks row alignment. The external read executes once.
- Nested recipe wrangles suppress side-effecting writes, including both Excel
  writers. Use `dataframe` to shape a nested recipe's returned dataframe.
- Normal list runs use the Production version when present, otherwise latest.
  Development Editor runs use the loaded/current editor definition, including
  historical versions. The same snapshot controls planning and every batch.

The shared UI planning and dataframe projection helpers live in WranglesJS's
`recipe-execution` entry point. XL requests a full response with
`drop_unmodified_cols=false` and performs unchanged-column suppression at its
write boundary. Other API callers retain their existing default behavior.

The Python package containing these connectors must be promoted to the recipe
Lambda used by XL. A Python merge alone does not update that runtime. Likewise,
XL requires a WranglesJS package containing `recipe-execution`; publish/install
that companion package before integrating the XL change.
