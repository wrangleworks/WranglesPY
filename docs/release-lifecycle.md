# Release lifecycle

This document will define how WranglesPY plans, prepares, publishes, verifies,
and closes a release. It is intentionally a stub while the team finalizes the
release process.

## Current integration and deployment direction

- `main` is the only integration branch for new work. Create short-lived
  branches from current `main` and target their pull requests directly to
  `main`.
- The DEV environment is a deployment destination, not a Git integration
  branch. Do not target new pull requests to `dev`.
- Freeze the legacy `dev` branch while wanted changes are recovered one logical
  change at a time on clean branches from current `main`. Never merge `dev`
  wholesale into `main`.
- A merge to `main` runs CI and may publish a container image under the current
  transitional automation. It does not publish a Python package or deploy an
  environment.
- Create a DEV release deliberately by dispatching `deploy-dev.yml` from
  `main`. Create a production release deliberately from a matching `v*` tag on
  `main`, which invokes `publish-tagged.yml`.

PR #1115 established the current `ci.yml`, `deploy-dev.yml`, and
`publish-tagged.yml` workflows. Some of that automation still listens to the
legacy `dev` branch or moves mutable image tags. Treat those paths as
transitional compatibility, not as approval to integrate new work through
`dev`. [Issue #1117](https://github.com/wrangleworks/WranglesPY/issues/1117)
tracks the remaining main-SHA validation, secretless PR CI, environment
protection, immutable-artifact, and release-gate work.

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
- selection and recording of the exact `main` commit used for a DEV package;
- version, changelog, tag, artifact, and publication steps;
- smoke tests and post-release verification;
- rollback and hotfix handling; and
- milestone closure and follow-up issue handling.

Until this document is expanded, follow
[the pull request workflow](pull-request-workflow.md) for PR ownership, review,
and merge readiness.
