# Per-product category questions

This small synthetic fixture demonstrates `ai.score` question templates and
existing split wrangles. No customer data or live responses are committed.

`products.json` contains three deliberately authored records with this schema:

| Field | Type | Purpose |
| --- | --- | --- |
| `Description` | string | Shared input sent to the model. |
| `Manufacturer Name` | string | Substituted as `{{ Manufacturer_Name }}`. |
| `CandidateCategories` | dictionary of string keys to category strings | Preserves semantic keys such as `category_1` in each answer wrapper. |
| `CandidateList` | list of category strings | Produces answers without key wrappers. |

The first record has three candidates. The second has two different candidates,
ordered `category_3` then `category_1`, to verify that splitting follows keys
rather than positions. The third has empty collections. All manufacturer names
are fictional. This file is the deterministic source fixture; there is no
sampling or external export to regenerate.

`recipe.wrgl.yml` renders both sets of questions and sends them together in one
Typesafe request per product with candidates. The row with no candidates needs
no request. The same detailed four-level rubric applies to every candidate.
The resulting `category_fit` and `list_fit` cells retain all scores, confidence,
and criterion-labelled probabilities.

The final recipe steps use `split.list` followed by `split.dictionary` twice:
once to merge the keyed wrappers and once to expose the answer fields. This
produces `category_1_score`, `category_2_score`, and `category_3_score`, plus each
candidate's value, confidence, and complete probability dictionary. Existing
`create.column` coalescing fills padded slots with empty dictionaries. Absent
candidates have blank values, scores, and confidence, not fabricated answers.
The split steps are deliberately configured for this fixture's three semantic
keys; add matching steps if your own data uses other keys.

## Run from the repository's VS Code terminal

Use the existing virtual environment with WranglesPY and its dependencies
installed. `TYPESAFE_API_KEY` must already be available in that terminal's
environment. The runner does not load, print, or save credential values.

```powershell
.\.venv\Scripts\python.exe tests\fixtures\ai_question_templates\run.py
```

The default run submits only the first two synthetic products and prints a
compact table of candidate values, scores, and confidence. It uses the model
catalog, disables the in-process AI cache, uses one thread, and retries zero
times. This command makes live Typesafe calls; results are not deterministic.

To include the empty-candidate record and inspect full result dictionaries:

```powershell
.\.venv\Scripts\python.exe tests\fixtures\ai_question_templates\run.py --all-rows --full-results
```

Change the clearly labelled defaults at the top of `run.py`, or use its optional
`--input`, `--recipe`, `--nrows`, `--model`, `--cache` / `--no-cache`, `--threads`,
`--timeout`, and `--retries` overrides. Default paths are anchored to the runner.
The sample prints results only; it does not write an export or execution folder.

Automated recipe tests consume these files with a mocked provider. Those tests
validate template expansion, grouped outputs, and the semantic output columns
without API credentials or live requests. The exact live replay commands are
above; the authored JSON itself needs no regeneration command.
