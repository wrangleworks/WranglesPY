# Local runtime validation

## Python-computed columns

On 2026-11-26, `python examples/ai_local/run.py` exercised both entry points
with OpenAI BYOK, model `gpt-5-mini`, Microsoft Copilot SDK 2.0.3 and its
matching runtime v1.0.116 on Windows x64 with Python 3.13.1. Both loaded the
local `wrangles-local-example/normalize-products` Skill.

| Entry point | Observed tool calls in order | Counts in input order | Elapsed |
| --- | --- | --- | --- |
| `ai.agent` with the named Skill | `convert_case`, `count_values`, `submit_results` | 2, 1, 2 | 18.79 s |
| `ai.skill` | `convert_case`, `count_values`, `submit_results` | 2, 1, 2 | 12.58 s |

Python wrote both `Name` and `Count`. The script checked `Pump Seal`, `Valve Kit`,
and `Pump Seal` in order and verified the original index and unrelated column.
Both runs completed using column names and tool receipts without calling
`read_dataframe`. The separate credential-free regression test for each entry
point submits conflicting counts of 3 and checks that the dataframe retains
Python's counts of 2, 1, 2 alongside a valid model-judged output.

## Original local runtime

Executed 2026-11-26 on Windows x64, Python 3.12.0, using
`microsoft-copilot-sdk==2.0.2` and its pinned Copilot runtime v1.0.115.
The OpenAI key was loaded into the smoke-test process from the developer's
local environment file. Credentials and provider payloads were not recorded.

The reproducible script is `examples/ai_local/run.py`. Both recipe entry points
ran against OpenAI BYOK using `gpt-5-mini`, separately from the offline suite.
Each resolved the package `wrangles-local-example`, Skill `normalize-products`,
at `examples/ai_local/skills/normalize-products/SKILL.md`.

| Entry point | Observed tool calls | Names in input order | Counts |
| --- | --- | --- | --- |
| `ai.agent` with inline instructions and attached Skill | `read_dataframe`, `submit_results` | Pump Seal, Valve Kit, Pump Seal | 2, 1, 2 |
| `ai.skill` | `read_dataframe`, `submit_results` | Pump Seal, Valve Kit, Pump Seal | 2, 1, 2 |

Both runs asserted that the original index `[9, 4, 2]`, Description, and
Unrelated columns were preserved. Both exited successfully. The first run took
about 18 seconds and the second about 9 seconds, including runtime startup and
cleanup; these are observations, not performance guarantees.

The credential-free tests in `tests/recipes/wrangles/test_ai_runtime.py` replace
the SDK boundary and retain actual recipe dispatch, local Skill resolution,
tool handlers, result validation, row assembly, and cleanup control flow. They
cover duplicate input index labels and reordered output rows as well as
malformed/incomplete results and runtime failures. These tests do not claim to
prove model behavior; the two live runs above supply that separate evidence.
