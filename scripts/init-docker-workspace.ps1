# =============================================================================
# Init Docker host workspace (data / logs / secrets mount root)
# =============================================================================
# Usage (repo root):
#   powershell -ExecutionPolicy Bypass -File .\scripts\init-docker-workspace.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\init-docker-workspace.ps1 -WorkspaceRoot E:\app\docker\workspace\dbc
# Creates one folder per container under DBC_DOCKER_WORKSPACE (product dir).
# =============================================================================

param(
    [string]$WorkspaceRoot = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\Resolve-DbcDockerWorkspace.ps1"
$ws = Resolve-DbcDockerWorkspace -RepoRoot $RepoRoot -WorkspaceRoot $WorkspaceRoot -AllowPrompt
$WorkspaceRoot = $ws.HostPath

$dirs = @(
    "postgres\data",
    "redis\data",
    "nacos\logs",
    "elasticsearch\data",
    "secrets",
    "secrets\manage\drivers",
    "manage\drivers",
    "manage\logs",
    "usercenter\logs",
    "sqlwork\logs",
    "audit\logs",
    "askdata\logs",
    "askdata\eval-cases",
    "gateway\logs",
    "front\html",
    "front\conf"
)

Write-Host "Creating per-container folders under $WorkspaceRoot"
foreach ($rel in $dirs) {
    $path = Join-Path $WorkspaceRoot $rel
    New-Item -ItemType Directory -Force -Path $path | Out-Null
}

$nginxSrc = Join-Path $RepoRoot "deploy\apps\nginx\default.conf"
$nginxDst = Join-Path $WorkspaceRoot "front\conf\default.conf"
Copy-Item -Force $nginxSrc $nginxDst
Write-Host "Copied nginx conf -> $nginxDst"

$repoSecrets = Join-Path $RepoRoot "secrets"
$wsSecrets = Join-Path $WorkspaceRoot "secrets"
if (Test-Path $repoSecrets) {
    Write-Host "Syncing secrets from repo -> workspace"
    robocopy $repoSecrets $wsSecrets /E /XO /NFL /NDL /NJH /NJS | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy secrets failed, exit=$LASTEXITCODE"
    }
} else {
    Write-Host "WARN: repo secrets/ not found. Start usercenter once to generate certs, then re-run."
}

$evalSrc = Join-Path $RepoRoot "scripts\demo-company\eval\cases"
$evalDst = Join-Path $WorkspaceRoot "askdata\eval-cases"
if (Test-Path $evalSrc) {
    Write-Host "Syncing askdata eval cases -> workspace"
    New-Item -ItemType Directory -Force -Path $evalDst | Out-Null
    robocopy $evalSrc $evalDst *.jsonl /XO /NFL /NDL /NJH /NJS | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy eval-cases failed, exit=$LASTEXITCODE"
    }
} else {
    Write-Host "WARN: scripts/demo-company/eval/cases not found; askdata container will skip template seed."
}

$serverP12 = Join-Path $wsSecrets "mtls\server.p12"
if (Test-Path $serverP12) {
    Write-Host "NOTE: If mTLS hostname mismatch in Docker, delete secrets/mtls/server.p12 and server.pass, restart usercenter to re-issue SAN."
}

Write-Host "Done. Workspace ready: $WorkspaceRoot"
