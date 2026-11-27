# External API configuration and caller catalogs

**Design target, November 27, 2026.** WranglesPY will resolve external API choices for recipes and direct Python calls and export the same choices for product editors. The [current AI configuration guide](ai_configuration.md) describes the shipped v1/v2 loader. [WranglesPY #1206](https://github.com/wrangleworks/WranglesPY/issues/1206) tracks delivery, open decisions and migration evidence.

## What the configuration owns

| Owner | Responsibility |
| --- | --- |
| Provider and API | Identify an implemented interface and its parameter schema. A model is optional. When models exist, record lifecycle, capabilities and tuning for each eligible choice. |
| Caller, operation and action | Select the default provider/API/model and apply operation-specific defaults. The target selection lives at `callers.<caller>.operations.<operation>.actions.<action>.default_selection`. Each alternative resolves its own defaults. |
| Shared WranglesPY resolver | Apply caller selection, saved settings and explicit arguments. Preserve which settings were inherited. Validate the effective values before the adapter builds a request. |
| Adapter and runtime | Translate provider parameters, inject credentials and enforce endpoint behavior. Wrangles owns concurrency, retries, deadlines, caching and output presentation. |
| Public catalog generator | Export a caller → operation → action view from the same validated snapshot and resolver. Include supported choices, lifecycle, filtered parameter schemas and resolved defaults. |

The executable Wrangles Registry owns operation identities and aliases. A product can use the operation binding to look up the corresponding API choices. System-Recipes owns provider cost facts and customer mappings. An OpenRouter model listing or an OpenAPI description can supply reviewed, versioned metadata. An entry becomes publicly selectable when its adapter and caller actually support it. Gateway routing and cost reconciliation are independent of local resolution. [Package ownership](https://github.com/wrangleworks/WranglesPY/issues/1284) · [Provider cost reporting](https://github.com/wrangleworks/System-Recipes/tree/main/recipes/provider_usage_costs)

## Resolution

1. Identify the origin product (`wranglespy`, `wranglesxl`, or `wranglesweb`), operation and action. An XL-authored recipe retains XL origin through Lambda, workers, batches and nested calls. Carry origin in bounded run context outside editable variables, saved Settings and provider kwargs. Exclude correlation IDs from result-cache keys, and retain cache isolation for settings that change results. Authentication establishes the principal separately.
2. Select the applicable provider, API and optional model. For extraction, explicit call settings take precedence over saved settings, followed by the resolved configuration and then provider behavior for omitted settings. Resolve tuning against the **selected** choice. Preserve explicit `false` and `0`, and leave the saved definition intact.
3. Separate `definition.save`, `index.build` and `wrangle.execute`. A delegated call such as Notes using extraction keeps the application's resolved policy. An independent step in a nested recipe resolves its own operation with the original caller.
4. Apply defaults explicitly. Define API/model parameter constraints with JSON Schema Draft 2020-12 in YAML and validate with Python `jsonschema`. Schema `default` is an annotation. Applicable constraints all hold, including when an adapter accepts extra kwargs. Validate partial defaults separately from complete invocation inputs. Preserve the adapter's existing error or warning behavior unless the operation's migration explicitly changes it.

### Worked cases

| Call | Expected behavior |
| --- | --- |
| Python recipe executes `ai.decisions` with packaged defaults | Select TypeSafe Jev (`jev-1.13.0` at the reviewed baseline). Selecting `openrouter` uses its Microsoft Decision-1 choice through the decisions API. Preserve the legacy `ai.answers` configuration role and cache identity for existing catalogs and recipes. Native probabilities and confidence remain part of the result contract. `decimals: 0` is applied to Wrangles output after validation. |
| The same recipe runs `search.ai_mode` | Select SerpAPI without synthesizing a model or exposing a model dropdown. The adapter fixes `engine=google_ai_mode` and `output=md`. Retain its option checks and handling of permitted extras. |
| XL executes a saved `extract.ai` definition | If the call omits a model, honor the saved model before the XL default. If the call explicitly supplies a different model, honor that choice and resolve its applicable tuning. Resaving, clearing and inheriting settings require distinct editor behavior. Keep the current extraction default of reasoning effort `none`, including for unlisted models, and honor explicit overrides. |
| A saved semantic index is queried | Reuse its persisted provider, API, model, dimensions and task contract. A change to the current embedding default is for new selections. Existing indexes with incomplete metadata need an explicit legacy policy. |

The XL saved-extraction editor offers supported `none` and `low` reasoning choices. Deprecated saved choices remain visible and executable with a warning, and resaving in that editor requires a current model. A user-authored recipe retains the execution contract. OpenAI small embeddings remain the general default and large an alternative. Local `ai.agent` and `ai.skill` are later inference consumers. Skills, tools and Copilot session configuration remain the Agent runtime's responsibility.

## Distribution and compatibility

- Keep the `wrangles.ai_config` import, packaged `wrangles/ai_defaults.yml` and `WRANGLES_AI_CONFIG` replacement path working during migration. Exercise v1 and v2 fixtures, including customized v2 decision roles. Introduce caller-owned selections for migrated operations and keep other operations on their existing behavior. Specify how legacy replacements handle a newly cataloged operation they never declared.
- Place shared selection and public projection under `wrangles/api_config/` as proposed in #1284, retain a generator entry point under `schema/`, and keep transports in `wrangles/clients/`. A native OpenRouter decisions call, an OpenAI Responses call and a SerpAPI search each retain their own wire contract.
- Export packaged and complete replacement configurations independently. Record package version, schema version and configuration revision/source using public-safe identifiers. Filter values, descriptions, annotations, examples and references. Bundle allowed references so consumers can read the catalog offline. Keep credentials, internal endpoints, prompts and unrestricted extra parameters out of public views.
- Publish an immutable artifact for the effective build/configuration pair. A DEV or PROD pointer should move only after the matching runtime deployment succeeds. A failed publish retains the prior artifact. Consumers must check revision agreement before presenting choices. A delayed publish must recheck the deployed revision. Rollback restores the matching pair.
- A per-attempt timeout and one additional retry, where configured, must fit the hosting request's remaining deadline. Local and hosted budgets can differ. Preserve existing operation-specific settings while the caller matrix is being agreed.

## Migration order and open decisions

First exercise the resolver and exporter together on decisions and SerpAPI AI Mode in Python. Compare actual requests and exported defaults for packaged and replacement configurations. Then bring saved and inline extraction onto that resolver and carry origin through JS, Core and Lambda for the XL save → reopen → execute trial. Web needs its own caller selections. Later adapters include DeepL at its translation service, semantic index build/query, classic search and local Agent inference.

Before the first implementation slice, settle the example source shape, missing origin/selection behavior, compatibility with older replacements, and handling of explicit unsupported parameters. Before the XL rollout, settle save/clear semantics, caller propagation, availability by environment, artifact naming and refresh behavior. Preserve protocol support in the integration baseline and reconcile changes separately with [the Responses-only proposal](https://github.com/wrangleworks/WranglesPY/pull/1251).
