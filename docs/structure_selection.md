# Selecting columns, elements, and rows

Use these `structure.*` recipe operations to select or aggregate data. Their
implementations live in `wrangles.recipe_wrangles.structure`; the existing
`select.*` recipe names and imports remain supported aliases of the same functions.

| Canonical recipe | Compatible recipe | Parameters |
| --- | --- | --- |
| `structure.select_columns` | `select.columns` | `input`: column names, wildcards, or exclusions such as `-Internal` |
| `structure.dictionary_elements` | `select.dictionary_element` | `input`, `element`, optional `output` and `default` (default `''`) |
| `structure.element` | `select.element` | `input`: literal paths such as `Data['key'][0]`, optional `output` and `default` |
| `structure.group_by` | `select.group_by` | Optional `by`, aggregation names mapped to columns, `auto_rename_columns` (default `true`) |
| `structure.head` | `select.head` | `n`: positive integer |
| `structure.list_elements` | `select.list_element` | `input`, optional `output`, `element` (default `0`), and `default` (default `''`) |
| `structure.sample` | `select.sample` | `rows`: count or fraction between 0 and 1; pandas sampling options such as `random_state` |
| `structure.tail` | `select.tail` | `n`: positive integer |

For example, given `Category`, `Attributes` (dictionaries with `material` and
`dimensions` keys), and `Tags` (lists), this recipe uses all eight operations:

```yaml
wrangles:
  - structure.dictionary_elements:
      input: Attributes
      element: material
      output: Material
      default: unknown
  - structure.list_elements:
      input: Tags
      element: 0
      output: FirstTag
      default: untagged
  - structure.element:
      input: Attributes['dimensions'][0]
      output: Width
      default: 0
  - structure.select_columns:
      input: [Category, Material, FirstTag, Width]
  - structure.group_by:
      by: Category
      sum: Width
  - structure.head:
      n: 10
  - structure.tail:
      n: 5
  - structure.sample:
      rows: 3
      random_state: 7
```

`group_by` preserves the first-seen group order and names aggregated columns such
as `Width.sum`. With `auto_rename_columns: false`, provide unique output names
when aggregating a column more than once:

```yaml
wrangles:
  - structure.group_by:
      by: Category
      auto_rename_columns: false
      min: [{Width: Minimum}]
      max: [{Width: Maximum}]
```

`structure.group_by` retains the existing selection aggregation contract; it is
separate from the proposed `structure.pandas_group_by` adapter.

All eight operations support `if`, `where`, and bound `where_params`. For example:

```yaml
wrangles:
  - structure.head:
      n: 2
      where: Width >= :minimum
      where_params: {minimum: 10}
      if: row_count > 0
```

For `select_columns`, `group_by`, `head`, `tail`, and `sample`, a matching `where`
replaces the result with the transformed subset. For the three element helpers,
it merges the selected outputs back into the original rows. As with the legacy
names, a `where` matching no rows skips execution and retains the original frame,
adding explicitly declared output columns with empty strings if needed.

`head`, `tail`, and column selection preserve row indices. `sample` resets the
index; a count larger than the available rows samples all rows. Dictionary/list
extraction overwrites its input when `output` is omitted. The general `element`
helper also strips the path from that default output name, so `Data['key'][0]`
overwrites `Data`. Its input is a literal path, even when a key contains `*`.

The existing `structure.split_dictionary`, `structure.split_list`,
`structure.split_text`, and `structure.tokenize` recipes are unchanged. Core
`wrangles.select` functions and the existing `df.wrangles.select` accessor retain
their existing APIs.
