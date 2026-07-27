# WranglesPY development container

The shared `devcontainer.json` is intentionally host-neutral. VS Code on Windows
and GitHub Codespaces both use the same Python 3.13 container definition.

## Windows with Docker Desktop

Docker Desktop's Linux engine must be ready before VS Code evaluates the
devcontainer. From the repository root, run:

```powershell
.\.devcontainer\wait-for-docker.ps1
```

The helper starts Docker Desktop when necessary and waits until the selected
Docker context can reach a Linux server. When it reports that Docker is ready,
open the repository in VS Code and run:

```text
Dev Containers: Reopen in Container
```

Use `Dev Containers: Rebuild Container` after changing `devcontainer.json` or
the dependency files.

`Dev Containers: Attach to Running Container...` remains useful as a recovery
option when this repository's container is already running. It is not the
normal workflow because attaching does not necessarily apply this repository's
creation commands and VS Code customizations.

## GitHub Codespaces

Create or reopen the Codespace normally. Codespaces reads
`.devcontainer/devcontainer.json` directly. The Windows readiness helper is not
referenced by the configuration and does not run in Codespaces.

## Quick diagnosis

Before reopening locally, both commands should succeed:

```powershell
docker context show
docker version
```

`docker version` must show a Linux server section. A missing
`dockerDesktopLinuxEngine` named pipe means Docker Desktop is still starting,
not that `devcontainer.json` selected the wrong engine.
