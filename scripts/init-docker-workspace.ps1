# =============================================================================
# Init Docker host workspace: E:\app\docker\workspace\dbc
# =============================================================================
# Usage (repo root):
#   powershell -ExecutionPolicy Bypass -File .\scripts\init-docker-workspace.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

$WorkspaceRoot = "E:\app\docker\workspace\dbc"
$RepoRoot = Split-Path -Parent $PSScriptRoot

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
    "gateway\logs",
    "front\html",
    "front\conf"
)

Write-Host "Creating workspace under $WorkspaceRoot"
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

$serverP12 = Join-Path $wsSecrets "mtls\server.p12"
if (Test-Path $serverP12) {
    Write-Host "NOTE: If mTLS hostname mismatch in Docker, delete secrets/mtls/server.p12 and server.pass, restart usercenter to re-issue SAN."
}

Write-Host "Done. Workspace ready: $WorkspaceRoot"
