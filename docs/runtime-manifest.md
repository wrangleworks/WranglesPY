# Versioned runtime manifest

WranglesPY exports the executable contract consumed by the Wrangles Registry.
This is the generation and artifact-delivery portion of [#1195](https://github.com/wrangleworks/WranglesPY/issues/1195);
automatic import and catalog synchronization are tracked in
[Wrangles-Docs #35](https://github.com/wrangleworks/Wrangles-Docs/issues/35).

## Origin and compatibility

The canonical generator is `schema/generate_wrangle_manifest.py`, brought forward
from Eric's [commit 7916bf15](https://github.com/wrangleworks/WranglesPY/commit/7916bf158e8b7e561270a1bea7b808f88956edc4)
on `codex/runtime-wrangle-manifest`. Focused generator and provenance checks live in
`tests/test_wrangle_runtime_manifest.py`; provenance fixtures use full revisions.
There is one runtime exporter. CI stores its output as GitHub Actions artifacts;
A temporary CI job copies the current feature branch's PR preview into the
separate Wrangles-Docs `test_deploying_manifest` branch. Production import and
catalog synchronization remain part of #35.

The original `--output <file>` and `--source-revision <sha>` options remain.
With no output option, the generator writes `schema/wrangle_runtime_manifest.json`.
The `--artifact-dir <directory>` option writes the manifest and checksum
files listed below. CI retains the original `schema` artifact with the recipe schema,
the legacy manifest filename, and its validation schema; the `runtime-manifest`
artifact contains the manifest and SHA-256 sidecar for that workflow run.

## Generate locally

The manifest jobs use the existing workflow Python versions: **3.12** in
`ci.yml` and **3.13** in `publish-tagged.yml`. Run these commands from the
repository root in an isolated environment with the matching Python version.
Runtime dependencies come from `requirements-full.txt`; `jsonschema` validates
the manifest and `pytest` runs the focused tests. There is no separate
manifest-specific constraints file or additional version pinning:

```sh
python -m pip install -r requirements-full.txt jsonschema pytest
python schema/generate_wrangle_manifest.py --artifact-dir output_files/runtime-manifest
```

The command reads the literal package version from `setup.py`, records the full
checkout commit SHA, discovers stock recipe operations, validates the manifest,
and writes:

- `wrangles-runtime-manifest.json`
- `wrangles-runtime-manifest.json.sha256` (standard `sha256sum` format)

Runtime and exporter inputs must be committed. Use `--allow-dirty` only for a
local development preview; its revision identifies the base checkout and does
not attest to uncommitted edits. A preview must not be used as a tagged-release
runtime contract. For a local preview of uncommitted changes, use:

```sh
python schema/generate_wrangle_manifest.py --allow-dirty --artifact-dir output_files/runtime-manifest
```

`--tag vX.Y.Z --source-revision <full-commit-sha>` additionally checks the exact tag,
package version, tag commit, and expected revision. It rejects `--allow-dirty`.

The export inspects callables; it does not execute recipes, authenticate to the
Wrangles API, allocate catalog IDs, or query PostgreSQL. Missing dependencies,
ambiguous discovery, malformed metadata, and unsupported defaults fail clearly.

## Contract and discovery

`schema/wrangles-runtime-manifest.schema.json` is the producer-owned format `0.1`
contract. It matches the Registry schema, including the coordinated optional
`catalog_id` extension from Docs #35. Consumers using a schema without that
extension must update it before consuming entries that carry an identity.

The exporter walks the stock namespace used by the recipe dispatcher. It includes
callable namespaces such as `standardize` and `standardize.custom`, executable
aliases, and reserved recipe names such as `try`. The internal `main` and
`pandas` module containers are re-exported at the root and are not duplicated.
The open-ended `custom.*` and arbitrary `pandas.*` extension surfaces are outside
this finite stock Registry contract.

Signatures, public/internal parameters, defaults, Python symbols, and docstrings
come from the actual callables. `if`, `where`, and `where_params` capabilities
follow the dispatcher's configuration. Adding an unsupported public export or a
namespace cycle fails discovery instead of quietly producing a partial manifest.

The original manifest's parameter rules are preserved: `variables` remains public
when declared in the callable's schema (including `anyOf`), as in `matrix` and
`recipe`; otherwise it is internal, as in `batch`. Plain-text docstrings are
retained even when they are not valid YAML. Malformed schema-looking docstrings
still fail export.

Evaluated union annotations use the existing Docs spelling, `Union[...]` and
`Optional[...]`, on all supported Python versions, including Python 3.14.
This applies to parameter annotations and complete signatures, including nested
types and return annotations. Type names such as `typing.Annotated` are rendered
without the `typing.` qualifier on every supported Python version. Quoted forward
references, literal values, and annotation metadata retain their text, including
any literal `typing.` prefix or pipe, without evaluation. Existing `X | Y`
annotations also use this canonical spelling; the textual representation changes,
while the accepted types, defaults, and recipe behavior stay the same.

JSON-compatible defaults are retained exactly. A named Python `object()` sentinel
(for example `convert.parse`'s `_DEFAULT_NOT_SET`) is represented by its stable
module-qualified name in the signature. Its parameter has `required: false` and
no JSON `default`: consumers must omit that argument when no value was supplied,
not substitute `null`. Format `0.1` already permits this distinction. Other
non-JSON or unnamed defaults fail export rather than receiving a lossy `repr`.

Entries and JSON object keys have deterministic order, bytes are UTF-8 with LF,
and the file contains no generation timestamp. There are no manifest-specific
dependency pins. The same source and environment produce the same bytes;
different Python or dependency versions may render annotations or defaults
differently. Use the same Python and resolved dependency versions when comparing
bytes from separate runs, rather than assuming a CI preview and a tagged-release
artifact must have identical checksums.

## Catalog identity annotations

The helper `wrangles.utils.catalog_identity` attaches a verified,
already allocated decimal-string ID directly to a callable without wrapping it:

```python
from wrangles.utils import catalog_identity as _catalog_identity

# allocated_catalog_id must come from the authoritative catalog registration.
@_catalog_identity(allocated_catalog_id)
def operation(df, input):
    ...
```

The private import avoids exposing this helper as a recipe operation. Retain the
annotation with the function when it moves or is renamed. The exporter copies
`__catalog_id__` unchanged, checks positive PostgreSQL BIGINT bounds, and rejects
duplicate references. It never infers an ID from a name or path. This change
does not bootstrap identity annotations onto existing functions; an operation
without a verified reference is exported without `catalog_id`.

A canonical operation carries the identity. For a legacy executable alias of
that same identity, use an unannotated forwarding function and test the actual
legacy recipe behavior. Assigning the same annotated function to two public
names would produce duplicate identities and is rejected. Separate catalog
entries binding to one operation remain the responsibility of catalog/Registry
bindings; they do not cause the exporter to invent additional operations.

## CI artifacts

The supported workflow paths are:

| Workflow | Trigger and recorded revision | Manifest output |
|---|---|---|
| `ci.yml` | PRs targeting `main`/`dev` and pushes to those branches; the checked-out `GITHUB_SHA` | Preview artifacts; temporary Docs copy for the feature-branch PR described below |
| `publish-tagged.yml` | A stable `vN.N.N` tag push, or a manual run selecting that tag; the verified tag commit | Versioned Actions artifacts |
| `deploy-dev.yml` | Existing DEV/RC deployment workflow | No runtime-manifest export or Docs synchronization |

For a PR, `source.revision` is the checked-out merge commit used by CI, not
necessarily the feature branch's head. The tagged-release workflow checks the
literal package version and full checkout SHA before export. Existing package
jobs depend on the schema job, so its artifacts may exist before the rest of the
release succeeds. Artifact availability alone does not confirm package publication.
Only a successful tagged-release run should be used as a package-version source.
CI previews record the stable source version in `setup.py` and are not
versioned RC contracts.

The export jobs use the default shallow `actions/checkout@v5` checkout. A tagged run
fetches the selected tag into its local tag reference, so the exporter can check
`refs/tags/<tag>^{commit}` without downloading the full repository history.

The CI and tagged-release manifest jobs upload:

- `schema`: `schema.json`, `wrangle_runtime_manifest.json`, and
  `wrangles-runtime-manifest.schema.json`;
- `runtime-manifest`: `wrangles-runtime-manifest.json` and
  `wrangles-runtime-manifest.json.sha256`.

The two manifest filenames contain identical JSON bytes; the legacy copy keeps
the original artifact layout compatible. The dedicated bundle includes the
checksum. The exporter prints the source version, revision, entry count and
checksum in the workflow logs. Both upload steps fail when no files are found.
The workflows do not set `retention-days`, so artifact expiry follows the
repository's settings; Actions artifacts are not permanent release storage.
See the [upload-artifact v6 options](https://github.com/actions/upload-artifact/tree/v6#usage).

CI and tagged releases store the manifest in Actions artifacts. They do not
create GitHub Releases or attach manifest files to them. The temporary CI preview
job additionally copies its artifact to Wrangles-Docs with a repository-scoped
GitHub App token. That job's `GITHUB_TOKEN` retains `contents: read`. Existing
package publication and Lambda deployment steps are unchanged.

## CI preview in Wrangles-Docs

The temporary `sync-runtime-manifest-preview` job in `ci.yml` runs only for a
`pull_request` whose source repository is this repository and whose head branch is
`generate-and-publish-a-versioned-runtime-manifest-for-every-WranglesPY-release`.
It waits for `test-generate-schema` and `build` to succeed; `build` already depends
on the pytest and pip-install matrices. Push runs, other PR branches, and fork PRs
do not run this publishing job. No `pull_request_target` workflow is used.

Add `Wrangles-Docs` to the deployment app's selected repositories with
**Contents: Read and write** before the first run, and ensure its branch rules
allow the app to update `test_deploying_manifest`; see
[GitHub App configuration](github-app-deployment.md). The job reuses
`DEPLOY_APP_CLIENT_ID` and `DEPLOY_APP_PRIVATE_KEY` without adding another secret.

The job downloads the `runtime-manifest` artifact from the same CI run and checks
its SHA-256 checksum before creating the publishing token. It updates only these
files in `wrangleworks/Wrangles-Docs`, branch `test_deploying_manifest`:

- `registry/runtime/wranglespy.json` (identical manifest bytes);
- `registry/runtime/wranglespy.json.sha256` (checksum with the destination filename).

If the branch does not exist, it is created from Docs `main`. Later runs build on
the existing preview branch and skip the commit when both files are unchanged.
The push names the preview branch explicitly and never force-pushes. Concurrent
updates can reject a push; rerun the failed sync job to pick up the new branch
head. Docs `main`, generated Registry files, and the central catalog are not
updated. This is a source preview for testing delivery, not a reviewed Registry
release; content reconciliation remains part of Docs #35.

To verify delivery before merging the WranglesPY PR:

1. Commit and push the workflow change to the feature branch above. Open its new
   CI run and check **Sync runtime manifest preview** after tests and build pass.
2. Open the two files on the Docs `test_deploying_manifest` branch and compare the
   manifest's `source.revision` with the WranglesPY run's checked-out merge SHA.
3. Download that run's `runtime-manifest` artifact and compare its JSON bytes
   with `registry/runtime/wranglespy.json`. In the Docs `registry/runtime`
   directory, run `sha256sum --check wranglespy.json.sha256`.

This PR path tests delivery without running `Deploy Dev`, publishing an RC, or
triggering Lambda deployment. The branch filter is deliberately temporary; remove
the sync job or agree on its long-term trigger after the delivery test.

## Retrieving the manifest

For now, download `runtime-manifest` from the selected workflow run's Artifacts
section. For a package version, select the successful tagged-release run for
`v<version>`. Verify the checksum and schema, check `source.repository` and
`source.version`, and compare the full `source.revision` with that tag's commit.
A PR preview is not a substitute for a tagged-release contract.

Production lookup, download and import into Wrangles-Docs will be added separately
under Docs #35. The importer must select the correct version and commit rather
than whichever workflow ran most recently. No release-download URL is provided
by this change. Docs `main` remains pinned to its reviewed snapshot; the CI
preview is available only on `test_deploying_manifest`.

## Wrangles-Docs readiness

The format remains `0.1`, with the required `source.version` used by Docs and the
optional identity reference already proposed in Docs #35. Eight independently
pinned complete Docs contracts live in `tests/fixtures/runtime_manifest/` and are
compared against the real runtime during CI. They cover public/injected variables,
legacy aliases, nested callables, reserved names, defaults, and capabilities.
Before union spelling was normalized, the historical runtime reproduced all 98
entries in the Docs snapshot. Normalization changes only union annotation text;
Registry reconciliation still uses the same executable parameter contract.

Format compatibility does not mean Docs' editorial sources already describe a
new runtime version. Before importing the 1.20.4 manifest, Docs #35 must:

- add Registry entries for `convert.parse` and `search.ai_mode`;
- add `create.embeddings.timeout`;
- remove `extract.ai.deadline` and add `extract.ai.metadata`;
- add `search.find_links.google_domain`;
- add `standardize.clean.latex_to_text` and `standardize.clean.unescape_unicode`.

Keep Docs pinned to its reviewed runtime until these content changes pass its
normal reconciliation. Do not filter the new producer's operations, fabricate
defaults, or relax validation to hide content drift. Automatic download/import
and these Registry source updates remain in Docs #35. The CI copy updates only
the preview branch's runtime input, not Docs `main` or the central catalog.

## Recovery

If export or artifact upload fails, rerun the schema job for the same commit or
tag after resolving the failure. If an artifact is no longer available,
regenerate it from the original commit using the same Python and resolved
dependency versions. Verify version, revision and checksum before importing the result.
The upload steps keep the default `overwrite: false`. If an upload reports an
existing artifact with the same name, first use and verify the existing bundle;
do not delete or replace it just to obtain a new download. If regeneration is
needed, use a separate run for that same revision and verify its provenance.
Existing releases are not modified by this process.

## Tests

```sh
python -m pytest tests/test_wrangle_runtime_manifest.py -q
```

Tests exercise actual runtime discovery and CLI output, identity/alias behavior,
defaults, deterministic artifacts, provenance failures, and the pinned Docs
contracts. They do not publish artifacts or call the Wrangles service.
