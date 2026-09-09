# GitHub App authentication for deployments

The DEV and PROD deployment workflows use an organization-owned GitHub App for
operations in other repositories. Normal WranglesPY CI uses `GITHUB_TOKEN` for
checkout and GHCR publishing. AWS publishing and Lambda updates continue to use
GitHub OIDC. No personal access token is required by these deployment workflows.

The registered organization app is
[Wrangleworks Deployments](https://github.com/organizations/wrangleworks/settings/apps/wrangleworks-deployments).
Its [installation](https://github.com/organizations/wrangleworks/settings/installations/160195536)
is restricted to `wrangleworks.github.io` and `Lambda-Recipes`. Reuse this app for
the workflow configuration below.

## Register and install the app

An administrator of `wrangleworks` performs this setup once:

1. In the organization's developer settings, register a private GitHub App, for
   example **Wrangleworks Deployments**. Set its homepage to
   `https://github.com/wrangleworks/WranglesPY` and allow installation only on the
   `wrangleworks` account. Disable webhooks; no callback URL, user authorization,
   or event subscriptions are needed.
2. Grant these **repository permissions**: **Contents: Read and write** and
   **Actions: Read and write**. GitHub includes **Metadata: Read-only**. Leave
   other repository, organization, and account permissions unset.
3. Install the app on **Only select repositories** and select exactly
   `wrangleworks.github.io` and `Lambda-Recipes`. It does not need installation
   on WranglesPY to issue tokens for those two repositories.
4. Copy the app's **Client ID** into the WranglesPY Actions repository variable
   `DEPLOY_APP_CLIENT_ID`. Use the Client ID, not the numeric App ID.
5. Generate an app private key and store the complete PEM, including its header
   and footer, as the WranglesPY Actions repository secret
   `DEPLOY_APP_PRIVATE_KEY`. Handle the key through GitHub's secret interface;
   never paste it into a recipe, issue, log, workflow file, or committed file.
   Do not put an installation token in this secret.

Organization-scoped configuration may be used instead, provided both names are
available only to the repositories that need the app credentials. A repository
variable or secret with the same name takes precedence over organization
configuration, so remove stale overrides when moving configuration.

## Token scope and lifetime

The app's registration permissions are its maximum access across the two
installed repositories. Each workflow requests a narrower installation token:

| Operation | Token repository | Token permission |
| --- | --- | --- |
| Publish `schema/recipes/schema_dev.json` | `wrangleworks.github.io` | Contents: write |
| Dispatch and wait for DEV or PROD deployment | `Lambda-Recipes` | Actions: write |

The first DEV job validates both repository scopes; the first PROD job validates
the Lambda scope. Missing configuration, invalid app credentials, or insufficient
installation permissions stop the workflow before tests and package publishing.
These validation steps create tokens but do not write to either repository or
start a deployment. Repository branch rules can still reject a later schema push.

Each publishing or dispatch job creates a fresh token immediately before use.
Tokens are limited to one repository and automatically revoked when their job
finishes; GitHub installation tokens also expire after one hour. The pinned
`actions/create-github-app-token` action handles generation, masking, and
revocation. Tokens are not passed between jobs or retained as secrets.

Schema commits use `github-actions[bot]` as the author. This is commit attribution;
the app installation token supplies the actual authorization. Deployment payloads
continue to record the original initiating user through `github.actor`.

## Validate the migration in DEV

1. Configure the app, installation, variable, and secret before running the
   updated deployment workflow. Merge the workflow changes to `main` first.
2. Run **Deploy Dev** from `main` with the intended base version. Record the
   workflow's commit SHA and resulting RC version. An old failed run retains its
   old workflow definition; rerunning it will not apply this migration.
3. Verify the early app checks, schema publication, RC publication, and downstream
   Lambda-Recipes DEV workflow. Confirm its image tag, image digest, and
   `execute-recipe-dev` update result before calling the deployment complete.
   DEV validation does not require dispatching the PROD workflow.

The existing test and publishing gates, downstream `main` refs, and AWS roles
remain in place. GHCR is the WranglesPY CI/test image; Lambda-Recipes builds the
image deployed to `execute-recipe-dev`.

The workflows contain no fallback to `CROSS_REPO_PAT_V2`. After successful DEV
validation, an administrator may retire that old secret once its remaining
consumers elsewhere have been checked. Do not remove shared credentials merely
because WranglesPY no longer references them.

For key rotation, create a replacement key on the same app, update
`DEPLOY_APP_PRIVATE_KEY`, validate the app checks, and then revoke the old key.
The app and Client ID can remain unchanged.

## References

- [GitHub App authentication in Actions](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow)
- [Installation token permissions and expiration](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app)
- [Pinned token action and inputs](https://github.com/actions/create-github-app-token/blob/bcd2ba49218906704ab6c1aa796996da409d3eb1/action.yml)
- [Repository scope of GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token)
