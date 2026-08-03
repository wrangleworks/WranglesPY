# Release Runbook

How the release pipelines are wired, and how to recover when one stops partway
through.

## Workflows

| Workflow | Trigger | Produces |
| --- | --- | --- |
| `ci.yml` | push to `main` / `dev`, PR into `main` / `dev` | `ghcr.io/wrangleworks/wrangles` tagged `sha-<sha>`, promoted to `:dev` or `:latest` |
| `deploy-dev.yml` | manual, from `dev` or `main` | `<version>rcN` in CodeArtifact, `schema_dev.json`, DEV deploy in Lambda-Recipes |
| `publish-tagged.yml` (*Deploy Prod*) | push of a `v*` tag | `:<version>` container, wheel + sdist in CodeArtifact and PyPI |

The prod workflow's file name is deliberately out of step with its display name:
PyPI Trusted Publishing matches on the workflow **file name**, so
`publish-tagged.yml` cannot be renamed without updating the publisher on PyPI
first (project → Manage → Publishing).

## Required configuration

`deploy-dev.yml` and `publish-tagged.yml` both fail fast if any of these
repository-level Actions **Variables** are missing (Settings → Secrets and
variables → Actions → Variables):

- `AWS_PUBLISH_ROLE_ARN` — role assumed via OIDC to publish to CodeArtifact.
  Its trust policy must allow this repository's OIDC subject.
- `AWS_REGION`
- `CODEARTIFACT_DOMAIN`
- `CODEARTIFACT_DOMAIN_OWNER` — the AWS account ID owning the domain.
- `CODEARTIFACT_REPOSITORY`

Secrets used across the pipelines: `CROSS_REPO_PAT` (dispatch into
Lambda-Recipes), `CROSS_REPO_PAT_V2` (push schema to `wrangleworks.github.io`),
plus the provider credentials consumed by the test suites.

## Ordering rules

Two constraints drive the job order, and both matter when recovering:

1. **CodeArtifact before PyPI.** If the CodeArtifact repository has an upstream
   connection to PyPI, it rejects a version that already exists upstream.
   Publishing to CodeArtifact first avoids that conflict permanently.
2. **Container before packages.** `publish-codeartifact` depends on
   `test-container`, so a broken image blocks the package release rather than
   letting the container and the wheel diverge.

## What is visible after each job

`publish-tagged.yml`, in order. Everything above the line is private to the run and
can be discarded by simply re-running; everything below it is visible to
consumers and needs the recovery steps in the next section.

| Job | External effect |
| --- | --- |
| `validate`, `pytest`, `test-pip-install`, `pytest-macos`, `test-generate-schema` | none |
| `build-dist` | none (`dist` artifact is run-scoped) |
| `build` | pushes `ghcr.io/wrangleworks/wrangles:<version>` |
| `test-container` | none |
| — release gate — | |
| `publish-codeartifact` | `wrangles==<version>` in CodeArtifact |
| `publish-pypi` | `wrangles==<version>` on PyPI, permanent |

The container is pushed before it is tested because a version tag is immutable
and nothing references it until the release is announced. The mutable tags
(`:dev`, `:latest`) are handled differently — see *Mutable tags* below.

## Resuming a partially published release

Both publish steps are idempotent (`--skip-existing` on twine, `skip-existing:
true` on the PyPI action), so the normal recovery is:

> Open the failed run → **Re-run failed jobs**.

Already-published artifacts are skipped and the run continues from the failure.
Prefer this over re-running the whole workflow: it reuses the existing `dist`
artifact, so the bytes you publish are the ones that were tested.

Work out where you are before acting:

```bash
VERSION=1.2.3

# CodeArtifact
aws codeartifact describe-package-version \
  --domain "$CODEARTIFACT_DOMAIN" --domain-owner "$CODEARTIFACT_DOMAIN_OWNER" \
  --repository "$CODEARTIFACT_REPOSITORY" \
  --format pypi --package wrangles --package-version "$VERSION" \
  --query 'packageVersion.status'

# PyPI
curl -sSf -o /dev/null -w '%{http_code}\n' "https://pypi.org/pypi/wrangles/$VERSION/json"

# Container
docker manifest inspect "ghcr.io/wrangleworks/wrangles:$VERSION" > /dev/null && echo present
```

### Failure before the release gate

Nothing is published. Fix the cause and re-run failed jobs. If the Docker build
already pushed `:<version>`, the next run overwrites that tag — no cleanup
needed.

### CodeArtifact succeeded, PyPI failed

Re-run failed jobs. `publish-pypi` re-downloads the same `dist` artifact and
retries; `publish-codeartifact` is not re-executed.

If the `dist` artifact has expired (artifacts are retained 90 days by default),
re-running the whole workflow rebuilds from the tag and re-uploads. The
CodeArtifact upload is skipped as already-existing, so the wheel on PyPI may not
be byte-identical to the one in CodeArtifact — acceptable for a recovery, but
prefer cutting a new patch version if reproducibility matters to you.

### PyPI succeeded, CodeArtifact failed

Unusual, since CodeArtifact runs first. Re-run failed jobs. If CodeArtifact now
refuses the version because it can see it upstream on PyPI, publish it directly
against the repository with the upstream connection temporarily removed, or cut
a new patch version.

### The version is published but wrong

**PyPI versions cannot be replaced or reused, even after deletion.** Do not try
to fix in place:

1. Yank the bad version so resolvers skip it while existing pins keep working:
   `PyPI → Manage project → Releases → Options → Yank`.
2. Delete it from CodeArtifact so RC computation and consumers stay clean:

```bash
aws codeartifact delete-package-versions \
  --domain "$CODEARTIFACT_DOMAIN" --domain-owner "$CODEARTIFACT_DOMAIN_OWNER" \
  --repository "$CODEARTIFACT_REPOSITORY" \
  --format pypi --package wrangles --versions "$VERSION"
```

3. Bump `setup.py`, tag the new version, and release again.

### A release re-run is stuck on a CodeArtifact conflict

`--skip-existing` covers an asset that is fully stored. A version left in
`Unfinished` state can still block the upload; delete it with
`delete-package-versions` above and re-run.

### The tag and `setup.py` disagree

`validate` fails before anything runs. Delete the tag, bump `setup.py`, and
re-tag:

```bash
git push --delete origin "v$VERSION" && git tag -d "v$VERSION"
# bump setup.py, commit
git tag "v$VERSION" && git push origin "v$VERSION"
```

## Mutable tags

`ci.yml` never pushes straight to `:dev` or `:latest`. It pushes `sha-<sha>`,
runs `test-container` against exactly that image, and only then does
`promote-image` retag it by digest. A failed container test therefore leaves the
previous `:dev` / `:latest` in place, and no manual rollback is required.

To roll a mutable tag back to an earlier commit, retag by digest:

```bash
docker buildx imagetools create \
  --tag ghcr.io/wrangleworks/wrangles:latest \
  ghcr.io/wrangleworks/wrangles:sha-<good-sha>
```

The `sha-<sha>` tags accumulate in GHCR. Prune them on whatever schedule suits
you, but keep enough history to roll back to.

## RC releases (`deploy-dev.yml`)

RC versions are derived by scanning existing `<base>rcN` versions in
CodeArtifact and incrementing, so a failed run does not burn a number — the next
run resolves to the same `rcN`. RCs go to CodeArtifact only, never PyPI.

The workflow patches `setup.py` in the runner and does not commit it, so no
cleanup is needed after a failure. If `trigger-deploy-dev` fails after the
package published, re-run only that job, or dispatch `deploy-dev.yml` in
Lambda-Recipes directly with the `wrangles_version` payload.
