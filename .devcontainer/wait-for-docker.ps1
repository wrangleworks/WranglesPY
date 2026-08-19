[CmdletBinding()]
param(
    [ValidateRange(10, 600)]
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker CLI was not found. Install or repair Docker Desktop before opening the dev container.'
}

function Get-DockerServerOs {
    $serverOs = docker version --format '{{.Server.Os}}' 2>$null
    if ($LASTEXITCODE -eq 0) {
        return $serverOs.Trim()
    }

    return $null
}

$serverOs = Get-DockerServerOs
if (-not $serverOs) {
    $dockerDesktopPath = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if (-not (Test-Path -LiteralPath $dockerDesktopPath)) {
        throw "Docker Desktop is not responding and was not found at '$dockerDesktopPath'."
    }

    Write-Host 'Starting Docker Desktop...'
    Start-Process -FilePath $dockerDesktopPath
}

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
Write-Host "Waiting up to $TimeoutSeconds seconds for the Docker Linux engine..."

do {
    $serverOs = Get-DockerServerOs
    if ($serverOs -eq 'linux') {
        $context = docker context show
        Write-Host "Docker is ready (context: $context, server: linux)."
        Write-Host "In VS Code, run 'Dev Containers: Reopen in Container'."
        exit 0
    }

    if ($serverOs) {
        throw "Docker is running a '$serverOs' engine. Switch Docker Desktop to Linux containers and try again."
    }

    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)

throw "Docker Desktop did not expose its Linux engine within $TimeoutSeconds seconds. Check Docker Desktop before retrying."
