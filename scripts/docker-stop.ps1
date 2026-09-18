# =============================================================================
# DBC one-click Docker stop (apps + middleware)
# =============================================================================
# Usage:
#   .\scripts\docker-stop.cmd
#   .\scripts\docker-stop.cmd -WipeData
#   .\scripts\docker-stop.cmd -WorkspaceRoot D:\data\dbc
# =============================================================================

param(
    [string]$WorkspaceRoot = "",
    [switch]$WipeData
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\Resolve-DbcDockerWorkspace.ps1"
# Stop should not prompt; use persisted path / env / -WorkspaceRoot
$ws = Resolve-DbcDockerWorkspace -RepoRoot $RepoRoot -WorkspaceRoot $WorkspaceRoot
$WorkspaceRoot = $ws.HostPath
$ComposeEnvFile = $ws.EnvFile
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

function Invoke-Compose {
    param(
        [Parameter(Mandatory = $true)][string]$ComposeFile,
        [Parameter(Mandatory = $true)][string[]]$ComposeArgs,
        [switch]$IgnoreExitCode
    )
    $args = @("compose", "--env-file", $ComposeEnvFile, "-f", $ComposeFile) + $ComposeArgs
    return Invoke-Docker -DockerArgs $args -IgnoreExitCode:$IgnoreExitCode
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

Write-Host "Workspace: $WorkspaceRoot"
Write-Host "==== Stop apps ====" -ForegroundColor Cyan
Invoke-Compose -ComposeFile $AppsCompose -ComposeArgs @("down") -IgnoreExitCode | Out-Null
Write-Host "==== Stop middleware ====" -ForegroundColor Cyan
Invoke-Compose -ComposeFile $MiddlewareCompose -ComposeArgs @("down") -IgnoreExitCode | Out-Null

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
