# extract.ai OpenAI Best Practices

This note summarizes which 2026 OpenAI developer best practices were applied to `wrangles.extract.ai` in this branch, and which were intentionally not implemented.

## Implemented

- **Responses API by default**
  - `wrangles.extract.ai` now defaults to `https://api.openai.com/v1/responses`.
  - Chat Completions remains available only when a caller explicitly passes a `/chat/completions` URL.

- **Structured Outputs**
  - `extract.ai` now sends schemas through the Responses API `text.format` JSON Schema shape.
  - Output schemas are sanitized to the OpenAI-supported JSON Schema subset.
  - Object schemas are made strict with `required` fields and `additionalProperties: false`.
  - User-provided `examples` are removed from the submitted JSON Schema, because Structured Outputs does not support that schema keyword, and are instead added to the prompt as style guidance.

- **Dynamic Pydantic response validation**
  - `wrangles.openai_responses` dynamically builds Pydantic models from the sanitized JSON Schema.
  - Responses are parsed from JSON and validated locally before returning data to `extract.ai`.
  - This is an extra guard on top of OpenAI Structured Outputs, especially useful for tests, mocked responses, retries, and OpenAI-compatible providers.
  - The local validator supports scalar types, arrays, nested objects, enums, unions, and common constraints such as min/max values and string/list lengths.

- **Strict mode by default**
  - `strict` now defaults to `True` for `extract.ai`.
  - This improves reliability for extraction tasks that need predictable columns and types.

- **Reasoning controls**
  - `reasoning={"effort": "low"}` is sent by default only for models that support the Responses API reasoning parameter.
  - Non-reasoning models such as `gpt-4o-mini` omit the parameter to avoid unsupported-parameter API errors.
  - This is a practical extraction default: enough reasoning for simple normalization, without paying extra latency for high-effort reasoning.

- **Verbosity controls**
  - `text.verbosity` defaults to `low` only for models that support low verbosity.
  - Models such as `gpt-4o-mini` omit the field so the API can use its supported default.
  - Extraction should return concise structured data, not explanatory prose.

- **Prompt cache key**
  - A stable `prompt_cache_key` is generated from the namespace, model, and schema.
  - This follows the guidance to make repeated structured workloads more cache-friendly.

- **Static prompt, dynamic data**
  - The instructions and schema stay in the stable request body.
  - Row-specific data is sent separately as the user input for each request.

- **Unsupported Responses parameters are filtered**
  - Parameters such as `seed`, which were used by older tests and Chat Completions-style calls, are removed from Responses payloads.

- **Backwards-compatible Chat Completions path**
  - Existing OpenAI-compatible backends using the Chat Completions function-calling schema can still work by passing a Chat Completions URL.

- **Regression tests**
  - Added mocked tests for:
    - Responses payload structure.
    - Strict structured output behavior.
    - Dynamic Pydantic response validation.
    - Omitting default reasoning for non-reasoning models.
    - Scalar output compatibility.
    - Legacy Chat Completions URL override.

## Not Implemented

| Best practice | Status | Why it was not implemented | When to revisit |
| --- | --- | --- | --- |
| Latest production model default | Not implemented | The `extract.ai` default model is intentionally left as `gpt-4.1-mini` to preserve main-branch behavior and avoid changing cost, latency, or extraction results in an API migration PR. | Revisit in a separate model-upgrade PR with eval coverage comparing extraction quality, latency, and cost. |
| Agents SDK | Not implemented | `extract.ai` is a row-level extraction helper, not an agent workflow. It does not need handoffs, agent state, traces, long-running plans, or multi-agent orchestration. | Revisit if `extract.ai` becomes part of an agent that can plan, call tools, retry subtasks, or delegate work. |
| Hosted tools | Not implemented | Extraction should use only the provided row data. Web search, file search, code interpreter, image generation, or computer use would make results less deterministic and could introduce external context the user did not request. | Revisit only for a separate opt-in feature such as grounded extraction from files or web-backed enrichment. |
| Tool search | Not implemented | `extract.ai` does not expose a large tool catalog. There is nothing to defer or search for at runtime. | Revisit if the project adds many extraction tools or domain-specific tool plugins. |
| Custom function tools | Not implemented | The task is schema-based extraction, not an action-taking workflow. Adding function tools would complicate the API and increase side-effect risk. | Revisit if extraction needs controlled calls into internal services, such as unit normalization services or product catalogs. |
| Multi-turn state with `previous_response_id` | Not implemented | Each input row is processed independently. Chaining rows with `previous_response_id` could leak context between records and make batch results order-dependent. | Revisit for interactive extraction sessions, not batch row extraction. |
| Manual assistant-item replay and `phase` handling | Not implemented | The helper does not manually replay returned Responses output items between turns. It sends independent requests and parses final structured output. | Revisit if a future implementation adds manual conversation state instead of independent calls. |
| Conversation compaction | Not implemented | Extraction calls are short, stateless, and per-record. There is no long-running conversation to compact. | Revisit if extract workflows become multi-step conversations over large records. |
| Encrypted reasoning / ZDR state replay | Not implemented | This branch does not add stateful reasoning or manual encrypted reasoning-item replay. The current design avoids cross-call state. | Revisit if customers require stateless multi-turn reasoning with Zero Data Retention constraints. |
| High or xhigh reasoning by default | Not implemented | Extraction usually benefits more from strict schemas than high-effort reasoning. Higher effort can add latency and cost without guaranteed extraction gains. | Revisit only after evals show measurable quality improvement on hard extraction cases. |
| Automated eval suite | Partially implemented | Mocked unit tests verify request shape and compatibility, but they do not measure extraction quality against a labeled dataset. A real eval suite needs representative examples and expected outputs. | Revisit before changing prompts, default model, reasoning effort, or schema normalization behavior again. |
| Prompt optimization workflow | Not implemented | No automatic prompt optimizer, GEPA-style loop, or prompt A/B harness was added. The prompt was kept deliberately small and outcome-focused. | Revisit when there is an eval dataset that can score prompt candidates safely. |
| Streaming | Not implemented | `extract.ai` needs complete JSON objects. Streaming partial JSON would add parsing complexity without much benefit for batch extraction. | Revisit for interactive UX where users need progress updates. |
| Realtime API | Not implemented | Realtime speech/audio is unrelated to this text/data extraction helper. | Revisit only for a separate voice or live extraction product. |
| Vision/image input handling | Not implemented | Existing `extract.ai` accepts text-like Python values and dataframe rows. Image input would require a separate input contract and tests. | Revisit if users need extraction from images, screenshots, or PDFs rendered as images. |
| Safety identifier | Not implemented | This helper currently has no stable end-user identity parameter to hash and pass through. Adding one would be an API design change. | Revisit when the library defines a user/session identity field for abuse monitoring. |
| Full migration of all OpenAI usage in the repo | Not implemented | This branch targets `extract.ai` only. Migrating unrelated modules at the same time would increase behavior-change risk. | Revisit module by module, with focused tests for each API surface. |

## Current Verification

- `pytest tests\test_openai_extract_ai.py -q`
- `python -m compileall wrangles\extract.py wrangles\recipe_wrangles\extract.py wrangles\openai_responses.py tests\test_openai_extract_ai.py`
- `git diff --check`
