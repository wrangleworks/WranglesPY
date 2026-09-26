# AI model configuration

`wrangles/ai_defaults.yml` is the packaged catalog for AI model selection and
defaults. Set `WRANGLES_AI_CONFIG` to a versioned replacement YAML file to use
your own catalog. Start from a copy of the packaged file. Configuration is
loaded locally and cached; call `wrangles.ai_config.clear_cache()` after changing
an already-loaded file.

## Providers, models, and operations

Version 2 groups models under their providers. Model entries describe lifecycle,
default roles, model-specific defaults, and known supported parameter values.
Operation settings hold concurrency, timeouts, caching, and extraction prompts.

This is an excerpt; a replacement file should contain the complete catalog:

```yaml
version: 2
providers:
  openai:
    endpoints:
      responses: https://api.openai.com/v1/responses
    models:
      gpt-6-luna:
        status: active
        default_for: [global, test, extract.ai, generate.ai]
        defaults:
          reasoning:
            effort: none
          text:
            verbosity: low
        supported_values:
          reasoning.effort: [none, low, medium, high, xhigh, max]
          text.verbosity: [low, medium, high]
operations:
  extract.ai:
    provider: openai
    protocol: responses
    defaults:
      default_concurrency: 32
      request_timeout_seconds: 12
      retries: 1
```

`status` is `active`, `deprecated`, or `retired`. It describes the model's status
in this catalog, not a live availability check against the provider. A model
can serve several roles through `default_for`; each role has one default within
a provider. Deprecated and retired entries cannot hold default roles. Explicit
model selection remains available for compatibility, including unlisted custom
models and dated snapshots. Provider errors still determine actual availability.

The `global` role is a fallback for text extraction and generation. Embeddings
and URL retrieval use their own roles and never inherit a text model. The `test`
role is selected explicitly by a test or trial runner; importing pytest does
not change production model selection.

`supported_values` contains lists of enum values, not flags for individual enum
members. It records capabilities for the models we configure; it is not an
automatically discovered inventory of every provider model. A provider entry
does not implement a new adapter. For example, the reserved Anthropic section
does not enable Anthropic extraction.

Use `protocol_defaults` for tuning that applies only to a specific protocol:

```yaml
gpt-4o-mini:
  status: active
  default_for: []
  protocol_defaults:
    chat_completions:
      temperature: 0.2
```

## Resolution and overrides

An operation selects its configured provider and protocol, then its model by
default role. Model defaults and protocol-specific defaults are combined with
operation defaults; operation defaults take precedence. Explicit caller
arguments take precedence over resolved defaults, including `False` and `0`.
Endpoint overrides remain available in APIs that already expose them.

All packaged operations default to one additional retry after the first attempt.
Set `retries: 0` to disable retries. Temperature is model-specific: modern OpenAI
models leave it unset, legacy GPT-4o Chat Completions keeps `0.2`, and the configured
Gemini URL-retrieval model keeps `0.1`. Unset temperature uses the provider's default.

For extraction, a saved definition's model retains its existing precedence over
the caller's `model`. Tuning defaults are resolved again for that selected model.
Explicit reasoning takes precedence over saved reasoning, which takes precedence
over configured reasoning. This change does not expand saved `ReasoningEffort`
values or alter the public parameter validation rules; those are separate from
validating the configuration itself.

The config loader rejects malformed declarations, conflicting default roles,
and configured enum defaults outside declared supported values. It does not
contact providers or validate credentials. Provider compatibility and extraction
quality still require live validation when adopting a new model.

Python callers can inspect the effective policy without making an AI request:

```python
from wrangles import ai_config

extraction = ai_config.resolve("extract.ai")
embeddings = ai_config.resolve("embeddings")
trial = ai_config.resolve("extract.ai", role="test")

# Existing helper remains available.
assert ai_config.extract_ai() == extraction
```

`load()` returns a defensive copy of the active YAML structure. `resolve()` and
`extract_ai()` return defensive copies of flat effective policies. Changing a
returned dictionary does not alter cached configuration.

## Integrated callers

| Operation | Callers | Configured settings |
| --- | --- | --- |
| `extract.ai` | Python and recipe extraction | Model, endpoints, model tuning, concurrency, timeout, retries, strictness, storage, cache, prompt |
| `embeddings` | `openai.embeddings` and recipe `create.embeddings` | Provider, model, endpoint, batch size, concurrency, timeout, retries, precision, optional dimensions/task |
| `search.retrieve_link_content` | Python, recipe, and Gemini URL-context client | Model, concurrency, timeout, retries, temperature |
| `generate.ai` | Python and recipe generation | Model, endpoint, reasoning/text tuning, concurrency, timeout, retries, strictness |

OpenAI embeddings retain `text-embedding-3-small` and their existing dimensions
unless explicitly configured otherwise. Jina requires an explicit model or a
Jina catalog model assigned the `embeddings` role; the package does not invent a
Jina model default. Explicit Jina URLs retain their existing provider inference.

Gemini URL retrieval retains its existing model and Google URL-context tools.
`search.ai_mode` delegates its underlying model to SerpAPI/Google and has no
selectable LLM model in this API.

The low-level `openai.chatGPT` transport takes an explicit request settings
dictionary. It preserves those settings and resolves omitted endpoint, timeout,
and retry values from the extraction operation's Chat Completions configuration.

Generation remains unreleased. Its operation keeps `low` reasoning; extraction
keeps `none` where supported. Its existing direct-Python and recipe strictness
defaults are represented by `strict` and `recipe_strict`, respectively.

## Version-1 overrides

Existing `version: 1` files with an `extract_ai` section remain supported with
their original replacement semantics. Existing `model_capabilities` flags
remain accepted on that compatibility path and retain packaged capability
inheritance. Generation still follows a version-1 extraction model override;
other operations use packaged defaults because version 1 did not configure them.

For new files, copy version 2 and edit the provider/model catalog and operation
settings. The compatibility API `model_capabilities()` remains available for
existing extraction internals; new configuration should use `supported_values`.
