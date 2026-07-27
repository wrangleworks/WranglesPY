# Release lifecycle

This document will define how WranglesPY plans, prepares, publishes, verifies,
and closes a release. It is intentionally a stub while the team finalizes the
release process.

## Interim milestone rules

- Treat a release milestone as a commitment, not a wishlist.
- Add a PR only after the linked issue has been accepted for the release.
- Remove or move a PR when it is no longer likely to be mergeable before the
  release freeze.
- Forty-eight hours before release, accept only fixes for a documented release
  blocker.
- Release readiness requires every milestone PR to be merged or explicitly
  moved out; do not carry conflicted, failing, or changes-requested PRs
  silently.

## To be defined

- release roles and decision ownership;
- milestone entry and exit criteria;
- freeze timing and release-candidate handling;
- version, changelog, tag, artifact, and publication steps;
- smoke tests and post-release verification;
- rollback and hotfix handling; and
- milestone closure and follow-up issue handling.

Until this document is expanded, follow
[the pull request workflow](pull-request-workflow.md) for PR ownership, review,
and merge readiness.
