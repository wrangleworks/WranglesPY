# JSON and YAML recipe conversions

Use `structure.*` to convert between JSON/YAML text and Python objects in recipe
columns. The `structure` namespace also contains the existing split and tokenize
operations.

| Canonical recipe | Compatible recipe |
| --- | --- |
| `structure.to_json` | `convert.to_json` |
| `structure.from_json` | `convert.from_json` |
| `structure.to_yaml` | `convert.to_yaml` |
| `structure.from_yaml` | `convert.from_yaml` |

The implementations live in `wrangles.recipe_wrangles.structure`. The four
`convert.*` functions re-export those same objects, preserving their parameters,
defaults, supported options, and behavior. The proposed `standardize.*`
serialization names are not registered; the callable model-backed `standardize`
and its `clean`, `custom`, and `replace` operations remain available.

Given `JSONText` containing `{"name":"Київ","count":2}`, this recipe exercises
all four conversions:

```yaml
wrangles:
  - structure.from_json:
      input: JSONText
      output: Object
      default: {}
  - structure.to_yaml:
      input: Object
      output: YAMLText
  - structure.from_yaml:
      input: YAMLText
      output: ObjectAgain
      default: {}
  - structure.to_json:
      input: ObjectAgain
      output: JSONAgain
```

`Object` and `ObjectAgain` contain the dictionary, and `JSONAgain` is
`{"name": "Київ", "count": 2}`. In Excel, serialize dictionaries and lists to
text before writing them into cells. Omitting `output` overwrites the input
column. Multiple inputs can map to corresponding output columns.

DataFrame calls use the same namespace and leave the source frame unchanged:

```python
import wrangles

source = wrangles.DataFrame({'JSONText': ['{"a":1}']})
decoded = source.wrangles.structure.from_json(input='JSONText', output='Object')
encoded = decoded.wrangles.structure.to_yaml(input='Object', output='YAMLText')
```

All four recipes support `where`, bound `where_params`, and conditional `if`.
They retain the existing element-wise merge-back behavior. For example:

```yaml
wrangles:
  - structure.from_json:
      input: JSONText
      output: Object
      default: {}
      where: Apply = :enabled
      where_params: {enabled: 1}
      if: row_count > 0
```

Serialization options such as `ensure_ascii`, `sort_keys`, `indent`, and YAML
`allow_unicode` retain their existing meanings. JSON serialization wraps scalar
values in a single-item array: a scalar `7` becomes `[7]`. Decoders preserve their
existing empty/null/falsy and fallback rules; YAML uses the safe loader, including
its existing scalar resolution. `convert.parse` keeps its separate tolerant
JSON-like parsing policy and is not added to `structure`.
