# Repository instructions for AI agents

## Running tests locally

- Do not run bare `pytest` (or a broad `-k`/name-filter selection) to verify
  changes in an agent sandbox. The full suite intentionally exercises live
  databases, AWS, WrangleWorks/Keycloak SSO, and AI/search providers, and a
  sandbox without those credentials will fail on unrelated live-service tests
  rather than on anything your change touched.
- Instead run the credential-free local suite: `pytest -c pytest-local.ini`
  (on Windows, `scripts/test-local.ps1` also clears credential environment
  variables first and isolates pytest's temp state). This selection excludes
  tests that require live SSO tokens or other live-service credentials by
  design — it is not a smaller or lower-quality run, it is the correct one to
  use when you don't have those credentials.
- A failure that only reproduces when running bare `pytest` (not under
  `pytest-local.ini`) is very likely a live-service/credential issue, not a
  regression in your change. Say so explicitly in your handoff rather than
  reporting it as a contract failure, and separate that evidence from any
  local `pytest-local.ini` results.
- `pytest-local.ini` is checked in CI (`pytest-local-config` job, via
  `scripts/check_pytest_local_config.py`) to stay in sync with the real test
  suite. If you add a new `tests/**/test_*.py` file, that check will fail
  until it's covered by `testpaths` (if it's offline-safe) or explicitly
  `--ignore=`d (if it needs live credentials) — fix `pytest-local.ini`
  yourself rather than leaving the new file silently untested locally.

## Integration and recovery workflow

- Treat `main` as the only integration branch for new work. Create each feature,
  fix, or documentation branch from a freshly fetched `origin/main`, and target
  its pull request directly to `main`.
- Treat a development environment as a deployment destination, not as a Git
  integration branch. Build development packages and deployments from an
  explicit commit that is already on `main`; do not route new pull requests
  through a `dev` branch.
- For wanted work stranded on a legacy `dev` branch, freeze that branch and
  recover one logical change at a time on a clean branch from current
  `origin/main`. Bring over only the required product commits and their
  prerequisites, reference the original pull request, and validate the resulting
  scope and tests in a new pull request to `main`.
- Never merge a legacy `dev` branch wholesale into `main`, and never
  cherry-pick its synchronization or merge commits merely to preserve history.
  After every legacy change is recovered, superseded, or intentionally
  abandoned, archive or delete the legacy branch.

## Container ownership

- The repository-root `dockerfile` builds the WranglesPY CI test image published
  to `ghcr.io/wrangleworks/wrangles`. Do not describe it as the production
  runtime image.
- The deployed `execute-recipe` AWS Lambda image is built and deployed from the
  `wrangleworks/Lambda-Recipes` repository. Its `dockerfile` controls the
  production Python version; verify that repository before making production
  runtime claims.

## Code Review Rules

### Make the required action explicit

- For every GitHub review and every follow-up reply to a request directed at an
  AI agent, distinguish the finding from the action needed to advance the PR.
- End the response with the following compact block:

  ```md
  **Recommended disposition:** Approve | Request changes | Needs decision | Comment only

  **Next steps**
  1. **PR assignee:** <the first concrete code, test, or reply action>
  2. **AI agent:** <the exact agent-specific request to post if implementation
     is safe>
  3. **Reviewer:** <what to verify, resolve, approve, or decide>
  ```

- Include only applicable steps, never more than three. Do not use vague actions
  such as "consider," "address this," or "follow up." Name the file or behavior
  to change, the focused test to add or run, and the GitHub action that follows.
- If implementation can be delegated safely, provide a ready-to-paste,
  agent-specific command. For Codex, for example: `@codex address that feedback
  by <specific scope>, add <specific regression test>, and report the checks
  run`.
- If a product or security decision is still missing, ask one precise decision
  question and use `Needs decision`; do not imply that implementation should
  begin.
- A suggestion, reply, or pushed commit does not resolve a review thread.
  Explicitly tell the reviewer to verify the fix, resolve the conversation, and
  submit a fresh approval when applicable.
- Pushing fixes does not hand the PR back to the reviewer. After every blocking
  thread has a reply with the fixing commit or rationale, the human assignee
  must re-request review. That review request is the native GitHub signal that
  returns the PR to the reviewer's **Needs your review** queue.

### Keep the pull request description current

- Treat the PR description—not a top-level summary comment—as the canonical
  description of the branch's current behavior, scope, risks, and validation.
- When an AI agent authors a PR or materially changes its branch, update the
  existing PR description before requesting or re-requesting review. Refresh
  the summary, behavior/API impact, tests run, remaining work, compatibility,
  and rollback notes affected by the new commits.
- Preserve linked issues, human-authored notes, checklists, and required
  template sections. Edit only the stale portions; do not replace useful context
  or add a second cumulative summary comment.
- Do not rewrite the description for mechanical rebases, conflict-only merges,
  formatting-only commits, or other changes that do not alter the reviewer's
  understanding.
- If the agent cannot edit the PR description, state that limitation and
  provide the exact replacement text or sections for the delivery owner to
  apply.

### Keep reviews consequential

- Prioritize correctness, regressions, compatibility, security, unintended
  scope, and missing behavioral tests.
- Put line-specific findings in inline threads. Use P0/P1 for blocking findings
  in AI-assisted GitHub reviews; capture non-blocking improvements in a
  follow-up issue rather than obscuring the merge decision.
- Follow `docs/pull-request-workflow.md` for ownership, Draft/Ready state,
  requested-changes handling, and review resolution.
