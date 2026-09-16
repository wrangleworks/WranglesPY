# WranglesPY Testing Strategy

## Goals

WranglesPY needs high-confidence tests without making local development or
AI-assisted coding slow, flaky, or dependent on live production state.

The default testing loop should be fast, deterministic, and credential-free.
Live-service tests still matter, but they should be explicit, opt-in, and
responsible for cleaning up anything they create.

## Test Categories

Use pytest markers to make test intent visible:

- `unit`: pure local tests with no network, credentials, or persistent service
  state.
- `contract`: mocked provider/API tests that verify request payloads, response
  parsing, retries, errors, caching, and schema contracts.
- `integration`: tests that exercise live services or deployed infrastructure.
- `live_ai`: tests that call a live AI provider.
- `live_wrangleworks`: tests that call live WrangleWorks services.
- `live_s3`: tests that call live AWS/S3 resources.
- `slow`: intentionally slow tests that should be excluded from tight local
  loops.

Unit and contract tests are the default for local development and AI-generated
test additions. Integration tests are opt-in.

## Default Local Workflow

Use:

```powershell
.\scripts\test-local.ps1
```

For focused iteration:

```powershell
python -m pytest -c pytest-local.ini <path-or-nodeid>
```

The local runner clears live credentials before running pytest. This prevents
local and AI-agent runs from accidentally calling OpenAI, WrangleWorks, AWS,
Gemini, SerpAPI, or other external providers.

Live integration tests are opt-in:

```powershell
python -m pytest -c pytest-integration.ini
```

Run them only in an environment that intentionally provides the required live
credentials and cleanup permissions.

Validate marker/config drift with:

```powershell
python scripts/check_pytest_markers.py
```

## AI-Generated Test Standard

AI-generated tests should follow the same bar as human-authored tests:

- Prefer unit or contract coverage.
- Mock provider transports and WrangleWorks APIs.
- Assert behavior and externally visible contracts, not incidental
  implementation details.
- Include failure-path assertions when the change affects retries, validation,
  parsing, cleanup, or error reporting.
- Use deterministic examples and stable fake responses.
- Use `tmp_path` for newly written files.
- Do not add new `pytest-local.ini` ignores or deselects unless the test is
  intentionally live-only and marked accordingly.

## Example Fixtures

Shared fixtures should make the common path easy:

- fake OpenAI Responses API success response;
- malformed OpenAI response body;
- transient transport error followed by success;
- rate-limit response with retry metadata;
- fake WrangleWorks model metadata;
- fake WrangleWorks model content;
- fake model creation response with a returned model id;
- cleanup registry for live-created models.

Keep fixtures small and explicit. Test-specific payloads can override the
default fake body rather than creating unrelated helper types in each file.

## Mocks Versus Live Calls

Use mocks for:

- payload shape;
- schema compilation;
- request headers and query parameters;
- retry and timeout behavior;
- cache key behavior;
- parsing and validation failures;
- model creation/update/delete request contracts.

Use live integration tests for:

- provider behavior that cannot be represented by a stable contract test;
- deployed WrangleWorks authentication and authorization behavior;
- model lifecycle behavior after the backend accepts a created model;
- S3 behavior that depends on real AWS object semantics.

Live tests should be narrow smoke tests. They should not duplicate broad unit or
contract coverage.

## Model Creation And Cleanup

Any test that creates a live model must:

1. Generate a unique model name with a test prefix, timestamp or run id, and a
   short random suffix.
2. Register the model id for cleanup immediately after creation.
3. Delete the model in a fixture finalizer or `finally` block.
4. Log the created model id clearly enough for manual cleanup if the process is
   interrupted.

Integration jobs should also include a periodic cleanup/audit path for stale
test models by prefix and age.

## Unit Test Writing Agent Evaluation

Microsoft's Unit Test Writing Agent framework is a good fit for WranglesPY's
unit and contract layers because it is designed to inspect project conventions,
generate tests, run them, and iterate on failures. Its published guidance also
explicitly discourages unit tests that call external URLs, open ports, depend on
exact timing, or exercise infrastructure.

Use it first as a focused assistant, not as a whole-suite rewrite tool.

Pilot scope:

- `wrangles/ai_cache.py`
- `wrangles/ai_definition.py`
- `wrangles/openai_responses.py`

Evaluation checklist:

- Does it follow existing pytest style?
- Does it reuse shared fixtures?
- Does it avoid live provider calls?
- Does it produce meaningful assertions?
- Does it cover both success and failure behavior?
- Does it run `pytest -c pytest-local.ini` or a focused equivalent?
- Does it avoid adding brittle sleeps or broad deselects?

References:

- Microsoft blog post: https://devblogs.microsoft.com/dotnet/polyglot-unit-testing-agent/
- Plugin repository: https://github.com/dotnet/skills/tree/main/plugins/dotnet-test

## Rollout Plan: Unit And Contract Tests

1. Register pytest markers and document local testing policy.
2. Add shared fake provider and model fixtures.
3. Pilot Unit Test Writing Agent on one AI-adjacent module.
4. Review generated tests for assertion quality and fixture reuse.
5. Convert repeated inline fake OpenAI/WrangleWorks responses to shared
   fixtures when doing nearby work.
6. Add or restore contract tests before touching `pytest-local.ini` ignores.
7. Require AI-authored PRs to report the focused pytest command they ran.

## Rollout Plan: Integration Tests

1. Mark existing live-service tests with `integration` and the relevant
   provider marker.
2. Move integration tests behind an explicit manual or scheduled command.
3. Standardize live model creation and cleanup fixtures.
4. Keep normal PR CI focused on unit and contract tests.
5. Add a credentialed scheduled integration job once cleanup is reliable.
6. Track flaky integration tests separately from product regressions.
7. Periodically audit stale live resources and remove or repair obsolete
   integration coverage.
