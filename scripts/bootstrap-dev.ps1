[CmdletBinding()]
param(
    [string]$VenvPath = ".venv",
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))

if (-not [System.IO.Path]::IsPathRooted($VenvPath)) {
    $VenvPath = Join-Path $repoRoot $VenvPath
}

$launcher = Get-Command py.exe -ErrorAction SilentlyContinue
if (-not $launcher) {
    throw "Python Launcher for Windows (py.exe) is required. Install Python 3.13 and retry."
}

$bootstrapVersion = & $launcher.Source -3.13 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or $bootstrapVersion -ne "3.13") {
    throw "Python 3.13 is required, but py -3.13 did not resolve to it."
}

$python = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    Write-Host "Creating Python 3.13 environment at $VenvPath..."
    & $launcher.Source -3.13 -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create the virtual environment."
    }
}

$venvVersion = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or $venvVersion -ne "3.13") {
    throw "$VenvPath is not a Python 3.13 environment. Choose a new -VenvPath; this script will not replace it."
}

Push-Location $repoRoot
try {
    & $python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "pip upgrade failed."
    }

    & $python -m pip install --requirement requirements-dev.txt --editable .
    if ($LASTEXITCODE -ne 0) {
        throw "Development dependency installation failed."
    }

    & $python -m pip check
    if ($LASTEXITCODE -ne 0) {
        throw "Installed packages have incompatible requirements."
    }

    & $python -c "from importlib.metadata import version; import duckdb, numpy, pandas, pyarrow, pytest, sqlalchemy, wrangles; print('Python development imports OK: wrangles={}, pandas={}, numpy={}, pyarrow={}, duckdb={}, sqlalchemy={}, pytest={}'.format(version('wrangles'), pandas.__version__, numpy.__version__, pyarrow.__version__, duckdb.__version__, sqlalchemy.__version__, pytest.__version__))"
    if ($LASTEXITCODE -ne 0) {
        throw "Development dependency import check failed."
    }

    if ($RunTests) {
        & (Join-Path $PSScriptRoot "test-local.ps1") -Python $python
        if ($LASTEXITCODE -ne 0) {
            throw "The self-contained local test suite failed."
        }
    }
}
finally {
    Pop-Location
}

Write-Host "WranglesPY Python 3.13 development environment is ready."
Write-Host "Interpreter: $python"
