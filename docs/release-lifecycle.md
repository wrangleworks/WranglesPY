# Release lifecycle

This document records the current integration direction and runtime-manifest
artifact steps. The broader planning, ownership and release-closing process is
still being finalized; outstanding decisions are listed below.

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
  `main`. Create a production release deliberately from a matching `vN.N.N` tag on
  `main`, which invokes `publish-tagged.yml`.

PR #1115 established the current `ci.yml`, `deploy-dev.yml`, and
`publish-tagged.yml` workflows. Some of that automation still listens to the
legacy `dev` branch or moves mutable image tags. Treat those paths as
transitional compatibility, not as approval to integrate new work through
`dev`. [Issue #1117](https://github.com/wrangleworks/WranglesPY/issues/1117)
tracks the remaining main-SHA validation, secretless PR CI, environment
protection, immutable-artifact, and release-gate work.

## Runtime manifest release steps

Stable production tags use `vN.N.N` matching the literal version in `setup.py`.
The runtime-manifest work for [#1195](https://github.com/wrangleworks/WranglesPY/issues/1195)
extends the generator recovered from `codex/runtime-wrangle-manifest` at commit
`7916bf15`; it is integrated into the current workflow structure.

1. The schema job runs the focused generator tests with the existing Python
   3.13 release environment and dependencies from `requirements-full.txt`, plus
   `jsonschema` and `pytest`. It verifies the checkout SHA, tag and package version
   using the default shallow checkout.
2. It generates `wrangles-runtime-manifest.json` and its `.sha256` sidecar,
   then uploads them as the `runtime-manifest` Actions artifact. The original
   `schema` artifact also contains the recipe schema, legacy manifest filename
   and manifest validation schema.
3. Existing package distribution jobs depend on this validation job. The
   manifest is available in that workflow run's Artifacts section. Its presence
   alone does not confirm that package publication or deployment succeeded;
   select a successful tagged-release run before importing a package contract.
4. If generation or artifact upload fails, rerun the schema job for the same
   commit or tag. Reproducing the same bytes requires the same source, Python
   and resolved dependency versions; there are no separate manifest constraints.

Manifest delivery currently uses GitHub Actions artifacts only. There is no
manifest publication job for GitHub Releases. Existing package publishing and
Lambda deployment continue through their existing workflows. `ci.yml` also
exports preview manifests for its PR/push runs; `deploy-dev.yml` does not export
runtime manifests for DEV/RC packages in this change. Artifact expiry follows the
repository settings because these uploads do not override `retention-days`.

Automatic download and import into Wrangles-Docs remain a separate part of
[Docs #35](https://github.com/wrangleworks/Wrangles-Docs/issues/35). Before an
import, verify checksum, source version/repository and full tag SHA. Docs also
requires reviewed content updates before advancing from its 1.20.2 pin to 1.20.4;
see [Runtime manifest](runtime-manifest.md) for artifact contents, compatibility
boundaries, required Docs changes and recovery steps.

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
