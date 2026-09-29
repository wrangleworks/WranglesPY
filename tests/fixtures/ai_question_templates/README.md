# Per-product category questions

This small synthetic fixture demonstrates `ai.score` question templates and
existing split wrangles. No customer data or live responses are committed.

`products.json` contains three deliberately authored records with this schema:

| Field | Type | Purpose |
| --- | --- | --- |
| `Description` | string | Shared input sent to the model. |
| `Manufacturer Name` | string | Substituted as `{{ Manufacturer_Name }}`. |
| `CandidateCategories` | dictionary of string keys to category strings | Produces a dictionary of answers with the same semantic keys, such as `category_1`. |
| `CandidateList` | list of category strings | Alternate source shape for testing list answers; not used by the active recipe. |

The first record has three candidates. The second has two different candidates
and an empty-string placeholder at `category_3`; its list also ends with an
empty-string placeholder. The third has empty collections. All manufacturer
names are fictional. This file is the deterministic source fixture; there is
no sampling or external export to regenerate.

`ai_category_judge.recipe` renders the `category_fit` questions from each product's
`CandidateCategories` dictionary and sends them together in one Typesafe request
per product with nonblank candidates. The row with no candidates needs no
request and returns `{}`. The same detailed four-level rubric applies to every
nonblank candidate.
The resulting `category_fit` dictionary retains the original candidate keys;
each answer contains its `value`, score, confidence, and criterion-labelled
probabilities. An empty or whitespace-only string produces `{}` at its original
key without sending a question to Typesafe, so the second product retains
`category_3: {}`. With a list source, the same placeholder rule preserves the
list position. Missing keys or positions are not added automatically; supply
blank-string slots in the input when needed. Other JSON values are not skipped.

The active `split.dictionary` step expands `category_fit` directly into columns
such as `category_1`, each containing the complete answer dictionary. Candidate
keys determine these columns regardless of input order, and supplied placeholder
keys retain `{}`. The recipe has just two steps: `ai.score` and
`split.dictionary`. A further `split.dictionary` step can expose individual
answer fields if needed.

## Run from the repository's VS Code terminal

Use the existing virtual environment with WranglesPY and its dependencies
installed. `TYPESAFE_API_KEY` must already be available in that terminal's
environment. The runner does not load, print, or save credential values.

```powershell
.\.venv\Scripts\python.exe tests\fixtures\ai_question_templates\run.py
```

The default run submits only the first two synthetic products and prints their
`Description` and full `category_fit` dictionaries. It uses the model
catalog, disables the in-process AI cache, uses one thread, and retries zero
times. This command makes live Typesafe calls; results are not deterministic.

To include the empty-candidate record and print every result column, including
the candidate columns created by `split.dictionary`:

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
