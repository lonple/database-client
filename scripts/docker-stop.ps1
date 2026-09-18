# =============================================================================
# DBC one-click Docker stop (apps + middleware)
# =============================================================================
# Usage:
#   .\scripts\docker-stop.cmd
#   .\scripts\docker-stop.cmd -WipeData
# =============================================================================

param(
    [switch]$WipeData
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$WorkspaceRoot = "E:\app\docker\workspace\dbc"
$MiddlewareCompose = Join-Path $RepoRoot "deploy\middleware\docker-compose.yml"
$AppsCompose = Join-Path $RepoRoot "deploy\apps\docker-compose.yml"

function Invoke-Docker {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$DockerArgs,
        [switch]$IgnoreExitCode
    )
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = & docker.exe @DockerArgs 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    foreach ($line in @($output)) {
        if ($null -ne $line) { Write-Host ($line.ToString()) }
    }
    if (-not $IgnoreExitCode -and $code -ne 0) {
        throw ("docker " + ($DockerArgs -join " ") + " failed, exit=$code")
    }
    return $code
}

Set-Location $RepoRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $dockerBins = @(
        "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin",
        "$env:ProgramFiles\Docker\Docker\resources\bin"
    )
    foreach ($bin in $dockerBins) {
        if (Test-Path (Join-Path $bin "docker.exe")) {
            $env:Path = "$bin;" + $env:Path
            Write-Host "Added Docker CLI to PATH for this session: $bin"
            break
        }
    }
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "docker not found. Start Docker Desktop, then reopen Cursor terminal."
}

Write-Host "==== Stop apps ====" -ForegroundColor Cyan
Invoke-Docker -DockerArgs @("compose", "-f", $AppsCompose, "down") -IgnoreExitCode | Out-Null
Write-Host "==== Stop middleware ====" -ForegroundColor Cyan
Invoke-Docker -DockerArgs @("compose", "-f", $MiddlewareCompose, "down") -IgnoreExitCode | Out-Null

if ($WipeData) {
    Write-Host "==== Wipe workspace data (-WipeData) ====" -ForegroundColor Yellow
    $targets = @(
        "postgres\data",
        "redis\data",
        "elasticsearch\data",
        "nacos\logs"
    )
    foreach ($rel in $targets) {
        $path = Join-Path $WorkspaceRoot $rel
        if (Test-Path $path) {
            Write-Host "  clear $path"
            Get-ChildItem -Path $path -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    $marker = Join-Path $WorkspaceRoot ".mtls-docker-ready"
    Remove-Item -Force $marker -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Stopped. Data kept under $WorkspaceRoot (unless -WipeData)."
Write-Host "Deploy again: .\scripts\docker-deploy.cmd"
