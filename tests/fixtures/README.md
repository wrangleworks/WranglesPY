# Test fixtures

Run Python tests from the repository root. Keep filenames and the relative
layout of recipes and custom functions together when moving these assets.
User-facing demos live in [examples/](../../examples/).

## Asset inventory and consumers

The following assets were consolidated here from the former sample directory.

| Assets | Consumers / purpose |
| --- | --- |
| `data.csv`, `data.json`, `data.jsonl`, `data.txt`, `data.xlsx`, `data2.xlsx` | File connector, read and recipe tests; CSV/JSON files also feed credentialed S3 tests. |
| `empty_cols.csv`, `empty_cols.xlsx`, `empty_df.json`, `empty_df.xlsx` | Empty-input file connector cases; retain the CSV companion to the workbook. |
| `write_data.jsonl`, `write_data.xlsx` | Retained file-format output samples. Tests write generated results under `tests/temp/`. |
| `test.db` | SQLite connector input database. |
| `matrix_dir/file1.csv`, `matrix_dir/file2.csv`, `matrix_dir/file3.json` | Matrix connector directory expansion tests. |
| `jinja_generic_template.jinja`, `jinjadescriptiontemplate.jinja` | Jinja connector and create-template tests. |
| `output_template.jinja` | Retained output-template companion fixture. |
| `recipe_sample.wrgl.yaml`, `recipe_sample.recipe` | Recipe and recipe-connector tests with an explicit `inputFile` variable. |
| `recipe_special_character.wrgl.yml`, `recipe_ception.wrgl.yaml` | Recipe parsing and nested matrix recipe tests. |
| `sub_rec_main.wrgl.yaml`, `sub_rec.wrgl.yaml` | Nested recipe connector tests; the parent references the child from the repository root. |
| `custom_functions.py` | Custom-function loading tests and CLI smoke checks. |
| `recipe-basic.wrgl.yml`, `recipe_custom_function.wrgl.yml` | Path-object recipe tests and local CLI smoke checks, including custom-function loading. |
| `generate-data.wrgl.yml` | CI, development deployment and tagged-publish workflow setup. |

The classification judge and web-search recipes had no tracked automated
callers and now live under `examples/extract_ai/` and `examples/search/`.
The extraction notebook lives under `examples/extract_ai/` too.

The existing [AI question template bundle](ai_question_templates/README.md) and
[AI Mode bundle](search_ai_mode/README.md) retain their runners, recipes and
data. Guides link to these maintained copies.

## Local verification

On Windows, run `scripts/test-local.ps1` from the repository root (use its
`-Python` parameter to select an existing interpreter).

CI runs the local CLI smoke checks from this directory:

```sh
cd tests/fixtures
wrangles.recipe recipe-basic.wrgl.yml
wrangles.recipe recipe_custom_function.wrgl.yml -f custom_functions.py
```

The container smoke check also uses `/workspace/tests/fixtures` as its working
directory. Workflow data setup runs from the repository root:

```sh
wrangles.recipe tests/fixtures/generate-data.wrgl.yml
```
