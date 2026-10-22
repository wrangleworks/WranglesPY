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
Optional `applications` metadata is a list of non-empty strings,
such as `[embeddings]` or `[data_extraction, description_writing]`. These labels help readers find
models; `default_for` selects defaults. Application labels are not sent to APIs.
Provider `documentation` links, including `model_cards`, are reference material
and are kept separate from request `endpoints`.

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
        applications: [data_extraction, description_writing]
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
a provider. Retired entries cannot hold default roles. Deprecated entries remain
usable, including through default roles. Explicit model selection remains available
for compatibility, including unlisted custom
models and dated snapshots. Provider errors still determine actual availability.
Selecting a deprecated model logs a warning naming its provider and model, then
continues normally. This also applies to configured defaults, saved definitions,
and tests. The warning is issued once per operation, outside row and retry loops;
reading or resolving the catalog does not emit warnings.

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

Packaged operations default to one additional retry after the first attempt,
except Gemini URL retrieval, which defaults to no retries. Set `retries: 0`
to disable retries. Temperature is model-specific: modern OpenAI
models and Gemini URL retrieval leave it unset, while legacy GPT-4o Chat Completions
keeps `0.2`. Unset temperature uses the provider's default (`1.0` for Gemini 3).

For extraction, a saved definition's model retains its existing precedence over
the caller's `model`. Both tuning and runtime defaults are resolved for that
selected model before applying explicit caller overrides.
Extraction accepts the simple recipe form `reasoning: none` and the equivalent
nested form `reasoning: {effort: none}`. Direct Python calls likewise accept
`reasoning="none"` or `reasoning={"effort": "none"}`. A scalar is normalized to
the object form before resolving overrides; nested objects retain their other
reasoning options.
Explicit reasoning takes precedence over saved reasoning, which takes precedence
over configured reasoning. Extraction defaults to `none` for every model,
including unlisted and future models. Reasoning is always sent to the provider;
unsupported settings produce a provider error instead of silently applying the
provider default. Declared verbosity enums are checked against the requested
value; unsupported verbosity values are warned about and omitted.
Recipe reasoning includes `max`. Saved `ReasoningEffort` remains `none|low` to
preserve compatibility with existing editors that use that narrower contract.

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
| `ai.choose`, `ai.score`, `ai.true_false`, `ai.answers` | Python and recipe structured answers | Provider, model, endpoint, concurrency, timeout, retries, cache |
| `extract.ai` | Python and recipe extraction | Model, endpoints, model tuning, concurrency, timeout, retries, strictness, storage, cache, prompt |
| `embeddings` | `openai.embeddings` and recipe `create.embeddings` | Provider, model, endpoint, batch size, concurrency, timeout, retries, precision, dimensions, Jina task/normalization/truncation |
| `search.retrieve_link_content` | Python, recipe, and Gemini URL-context client | Model, endpoint/API version, concurrency, per-URL deadline, retries, thinking level, temperature/top-p/top-k/token limits/stop sequences |
| `generate.ai` | Python and recipe generation | Model, endpoint, reasoning/text tuning, concurrency, timeout, retries, strictness |
| `huggingface` | Generic recipe task wrangle | Explicit model, endpoint, timeout, retries, task parameters |

Configured provider request options use explicit allowlists so runtime settings
and catalog metadata cannot leak into API payloads. Explicit request arguments
still override configured options. Gemini retrieval also accepts caller-supplied
`GenerateContentConfig` options through keyword arguments. Extraction retains
`messages`/`examples` aliases and recipe
output-shape controls because existing callers use them. Private transport
arguments and unused generation scaffolding have been removed where redundant.

This catalog governs WranglesPY callers. WranglesXL saved-model authoring and
WranglesJS note-generation calls still select models outside Python. Their model
defaults require a separate client integration. SerpAPI AI Mode and WrangleWorks
saved-model service endpoints own their server-side model selection.

## Provider settings

### OpenAI

OpenAI embeddings retain `text-embedding-3-small` and their existing dimensions
unless explicitly configured otherwise.

OpenAI uses complete request URLs in `endpoints`: `/v1/responses`,
`/v1/chat/completions`, and `/v1/embeddings` on `api.openai.com`.
Provider documentation links are not request endpoints.

The public `openai.chatGPT` wrapper has been removed. Legacy Chat Completions
remains available through `extract.ai(protocol="chat_completions")`. Extraction
resolves configuration once per operation and uses a private transport for its
individual rows.

The packaged OpenAI model reasoning defaults are `none`. Extraction and
generation inherit those model settings without an operation-level reasoning
override, so configured model defaults remain effective. Extraction also sends
`none` when an unlisted model has no configured effort. Explicit caller and
saved-definition settings retain their precedence.

Generation remains unreleased. Its existing direct-Python and recipe strictness
defaults are represented by `strict` and `recipe_strict`, respectively.

Extraction uses the operation's `defaults` directly. There is no profile registry
or caller-selectable preset behavior; the unused `profile` label has been removed.
A named preset system is outside the current configuration work.

### Jina

Jina requires an explicit model or a Jina catalog model assigned the `embeddings`
role; the package does not invent a Jina model default. Explicit Jina URLs retain
their existing provider inference. Jina uses the complete `/v1/embeddings`
request URL on `api.jina.ai` in `endpoints`.

The catalog records Jina v5's `task` enum on the model: `retrieval.query`,
`retrieval.passage`, `text-matching`, `clustering`, and `classification`. Its
default is `text-matching`, matching the provider's documented default. Use
`retrieval.passage` for indexed documents and `retrieval.query` for search queries;
explicit caller `task` overrides the model default. Validation uses the selected
model's catalog enum. Uncataloged older Jina models retain their existing task
validation, including v3's `separation` value. See the
[Jina API schema](https://api.jina.ai/openapi.json) for model-specific values.

### Google Gemini

Gemini URL retrieval defaults to `gemini-3.5-flash` and uses Google's
URL-context tools. Its packaged settings explicitly select
`thinking_level: minimal`, `request_timeout_seconds: 10`, and `retries: 0`.
The Google SDK dependency requires version `1.64.0` or later for these controls.
Use `model_id` to select another model, such as `gemini-3.6-flash`, and
`thinking_level` to override the configured thinking level. The wrapper accepts
`minimal`, `low`, `medium`, and `high`; actual support depends on the model.
Explicit `request_timeout_seconds` overrides the configured deadline.

The deadline covers one URL's provider request, including all configured retries.
A timeout produces the existing per-URL `Failure` result and preserves output
ordering. Cancellation and client cleanup may take a little longer. Queued URLs
receive their own deadline when their worker starts, so a batch can exceed 10
seconds when it needs multiple waves of requests.

Additional caller keyword arguments are forwarded to the SDK's
`GenerateContentConfig` and override configured generation defaults, including
options such as `max_output_tokens`, `top_p`, and `temperature`. Retrieval's
prompt, URL-context tool, response format, and HTTP settings remain managed by
the wrapper. An explicit `thinking_config` replaces the thinking configuration
as a whole, including any selected `thinking_level`. See the
[retrieval guide](search_retrieve_link_content.md) for recipe and Python usage.
`search.ai_mode` delegates its underlying model to SerpAPI/Google and has no
selectable LLM model in this API.

For Google, `endpoints.base_url` is the SDK service root
`https://generativelanguage.googleapis.com`. The retrieval operation sets
`api_version: v1beta`; the SDK appends the model and method. With the default
`gemini-3.5-flash`, the complete request URL is
`https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent`.
Both the base URL and version are configurable. See the
[Google API reference](https://ai.google.dev/api/generate-content).
Google model names with or without the SDK's `models/` prefix share the same
catalog defaults. Declare only one spelling for each model in the catalog.

### Typesafe

The four answer wrangles provide structured answers to common types of
questions through [Typesafe](https://docs.typesafe.ai/introduction).
`ai.choose` selects the best-fitting option, `ai.score` locates the input along
ordered criteria, and `ai.true_false` returns the probability that a statement
is true. `ai.answers` answers any combination of these question types together.
They use Typesafe's `systemone` protocol at
`https://api.typesafe.ai/v1/systemone`, with `jev-1.13.0` as their pinned default
model. Each operation has its own default role; changing an extraction or global
model does not change these operations. Explicit unlisted Typesafe model names
remain available. This adapter supports only `provider: typesafe` and
`protocol: systemone`; adding another catalog provider alone does not implement
an adapter for it.

Their packaged runtime defaults are 10 concurrent requests, a 30-second timeout,
and one additional attempt after a transient failure. Caching is off by default
(`defaults.cache.enabled: false`). Set `cache: true` in a recipe or `cache=True`
in Python to enable a bounded in-memory cache with a one-hour TTL, at most 512
entries, and a maximum value size of 65,536 bytes. When enabled, duplicate
in-flight requests share their result. Periodic cache logging is disabled.
`WRANGLES_AI_CACHE_*` environment controls take precedence over caller and
catalog settings, independently of the existing `WRANGLES_EXTRACT_AI_CACHE_*`
controls. See [AI answers](ai_answers.md) for question schemas, examples, output
columns, and cache overrides.

Keep credentials outside the catalog. Supply `api_key` explicitly, use the local
`TYPESAFE_API_KEY` environment variable, or use `api_key: ${TYPESAFE_API_KEY}` in
a hosted recipe with that managed secret. Hosted secrets are supplied as recipe
variables; they are not placed in the worker's environment.

### Hugging Face

Hugging Face's generic task wrangle retains its required explicit `model`:
different tasks cannot share one model default. Its operation declares
`requires_model: true`, and model entries can supply task-specific `parameters`
and lifecycle status. Explicit parameters override configured values. Requests
use the configured HF Inference base plus the model ID, currently
`https://router.huggingface.co/hf-inference/models/{model}`. The wrangle preserves
raw JSON results and retries transient failures only. See the
[HF Inference reference](https://huggingface.co/docs/inference-providers/en/providers/hf-inference).

### Anthropic

The Anthropic provider entry is reserved for a future adapter. It does not
enable Anthropic extraction or other runtime support.

## Version-1 overrides

Existing `version: 1` files with an `extract_ai` section remain supported with
their original replacement semantics. Existing `model_capabilities` flags
remain accepted on that compatibility path and retain packaged capability
inheritance. Generation still follows a version-1 extraction model override;
other operations use packaged defaults because version 1 did not configure them.
This includes all four Typesafe answer wrangles.

A version-2 replacement remains authoritative: it must define any new operation
you intend to use, its provider, and a default model role (unless you supply the
model explicitly). An older version-2 file does not silently inherit the new
`ai.*` entries from the packaged catalog. Update it from the packaged catalog
before calling these operations.

For new files, copy version 2 and edit the provider/model catalog and operation
settings. The compatibility API `model_capabilities()` remains available for
existing extraction internals; new configuration should use `supported_values`.
