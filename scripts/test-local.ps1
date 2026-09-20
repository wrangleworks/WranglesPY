[CmdletBinding()]
param(
    [string]$Python = ".venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))

if (-not [System.IO.Path]::IsPathRooted($Python)) {
    $Python = Join-Path $repoRoot $Python
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python interpreter not found: $Python"
}

# The complete CI suite intentionally exercises credentialed databases, AWS,
# WrangleWorks services, and AI/search providers. Local tests must not inherit
# credentials and accidentally make live calls or echo a secret in a traceback.
foreach ($name in @(
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "GEMINI_API_KEY",
    "HUGGINGFACE_TOKEN",
    "OPENAI_API_KEY",
    "SERPAPI_API_KEY",
    "WRANGLES_PASSWORD",
    "WRANGLES_USER"
)) {
    [Environment]::SetEnvironmentVariable($name, $null, "Process")
}

$localConfig = Join-Path $repoRoot "pytest-local.ini"
if (-not (Test-Path -LiteralPath $localConfig)) {
    throw "Local pytest configuration not found: $localConfig"
}

# Pytest's default per-user temp root and repository cache can become
# inaccessible when alternating between the restricted sandbox and Eric's
# normal Windows identity. Keep each identity's generated state separate.
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$identitySlug = $identity -replace "[^A-Za-z0-9_.-]", "-"
$testTemp = Join-Path $repoRoot ".test-local\$identitySlug\pytest"
$testTempParent = Split-Path -Parent $testTemp
New-Item -ItemType Directory -Path $testTempParent -Force | Out-Null
$localState = @(
    "--basetemp=$testTemp"
)

Push-Location $repoRoot
try {
    foreach ($relativePath in @("tests/temp/temp.db", "tests/temp/temp_run.db")) {
        $generatedDatabase = Join-Path $repoRoot $relativePath
        if (Test-Path -LiteralPath $generatedDatabase) {
            Remove-Item -LiteralPath $generatedDatabase
        }
    }

    & $Python -m pytest -c $localConfig @localState
    if ($LASTEXITCODE -ne 0) {
        throw "The self-contained local test suite failed."
    }
}
finally {
    Pop-Location
}
