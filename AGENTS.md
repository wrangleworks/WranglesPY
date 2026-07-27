# Codex repository instructions

## Code Review Rules

### Make the required action explicit

- For every GitHub review and every follow-up reply to an `@codex` mention,
  distinguish the finding from the action needed to advance the PR.
- End the response with the following compact block:

  ```md
  **Recommended disposition:** Approve | Request changes | Needs decision | Comment only

  **Next steps**
  1. **PR author:** <the first concrete code, test, or reply action>
  2. **@codex:** <the exact comment to post if Codex can safely implement it>
  3. **Reviewer:** <what to verify, resolve, approve, or decide>
  ```

- Include only applicable steps, never more than three. Do not use vague actions
  such as "consider," "address this," or "follow up." Name the file or behavior
  to change, the focused test to add or run, and the GitHub action that follows.
- If implementation can be delegated safely, provide a ready-to-paste command,
  such as `@codex address that feedback by <specific scope>, add <specific
  regression test>, and report the checks run`.
- If a product or security decision is still missing, ask one precise decision
  question and use `Needs decision`; do not imply that implementation should
  begin.
- A suggestion, reply, or pushed commit does not resolve a review thread.
  Explicitly tell the reviewer to verify the fix, resolve the conversation, and
  submit a fresh approval when applicable.

### Keep reviews consequential

- Prioritize correctness, regressions, compatibility, security, unintended
  scope, and missing behavioral tests.
- Put line-specific findings in inline threads. Use P0/P1 for blocking findings
  in GitHub Codex reviews; capture non-blocking improvements in a follow-up
  issue rather than obscuring the merge decision.
- Follow `docs/pull-request-workflow.md` for ownership, Draft/Ready state,
  requested-changes handling, and review resolution.
