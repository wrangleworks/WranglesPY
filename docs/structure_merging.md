# Structural merge recipes

Use these `structure.*` recipes to combine columns, dictionaries, lists, and
key/value pairs. Their implementations live in
`wrangles.recipe_wrangles.structure`; the existing `merge.*` recipe names and
imports re-export the same functions.

| Canonical recipe | Compatible recipe | Behavior |
| --- | --- | --- |
| `structure.coalesce` | `merge.coalesce` | Select the first non-empty value from columns or a list |
| `structure.concatenate` | `merge.concatenate` | Join columns or list elements using `char` |
| `structure.merge_dictionaries` | `merge.dictionaries` | Merge dictionaries, with later conflicting values taking precedence |
| `structure.key_value_pairs` | `merge.key_value_pairs` | Build a dictionary from paired key and value columns |
| `structure.merge_lists` | `merge.lists` | Combine list values, with optional duplicate removal |
| `structure.to_list` | `merge.to_list` | Collect column values into a list |
| `structure.to_dictionary` | `merge.to_dict` | Collect column headers and values into a dictionary |

For a frame with the columns referenced below, this recipe uses all seven
operations independently:

```yaml
wrangles:
  - structure.coalesce:
      input: [Primary, Backup]
      output: Label
  - structure.concatenate:
      input: [First, Last]
      output: FullName
      char: ' '
      skip_empty: true
  - structure.merge_dictionaries:
      input: [Base, Overrides]
      output: Attributes
      skip_empty: true
  - structure.key_value_pairs:
      input:
        AttributeKey*: AttributeValue*
      output: Properties
      skip_empty: true
  - structure.merge_lists:
      input: [Tags1, Tags2]
      output: Tags
      remove_duplicates: true
      ignore_case: true
  - structure.to_list:
      input: [First, Last]
      output: Parts
      include_empty: false
  - structure.to_dictionary:
      input: [First, Last]
      output: Record
      include_empty: false
```

`Base` and `Overrides` contain dictionaries; `Tags1` and `Tags2` contain lists.
For example, `Base: {color: red, size: M}` and `Overrides: {color: blue}` produce
`Attributes: {color: blue, size: M}`. List duplicate removal preserves the
first-seen order. Dictionary keys also retain insertion order when a later value
overwrites an existing key.

`key_value_pairs.input` is a mapping of key-column names to value-column names.
The function expands paired wildcard patterns itself, in source-column order;
the recipe dispatcher passes the mapping unchanged. Explicit names such as
`{'Attribute Key [1]': 'Attribute Value [1]'}` work too.

All seven recipes support `where`, bound `where_params`, and conditional `if`:

```yaml
wrangles:
  - structure.concatenate:
      input: [First, Last]
      output: FullName
      char: ' '
      where: Apply = :enabled
      where_params: {enabled: 1}
      if: row_count > 0
```

Matching rows are transformed and merged back into the original frame. Other
rows keep their existing output values; a new output column is blank on those
rows. With no matches, execution is skipped and the original rows are retained.
`coalesce` can overwrite a single input when `output` is omitted; multiple input
columns require an output. The other operations require an explicit output.

Parameters, defaults, empty/falsy handling, scalar stringification, boolean
source-column coercions in dictionary conversion/pairing, and meaningful errors
retain their existing `merge.*` behavior. Existing `df.wrangles.merge` calls and
core Python APIs remain supported. The existing structure split/tokenize
exports are unchanged.

When writing a dictionary or list into an Excel cell, serialize the output to
text first, for example with `convert.to_json`.
