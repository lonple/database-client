# =============================================================================
# DBC Docker start / deploy (local learning only, NOT production)
# =============================================================================
# Same script for first install AND later daily start.
#
# Usage (repo root):
#   powershell -ExecutionPolicy Bypass -File .\scripts\docker-deploy.ps1
#
# Default (recommended for daily start):
#   - keep data and certs
#   - do not kill host ports
#   - do not down running stacks first
#   - package jars only if app.jar missing
#   - docker compose up -d; --build only if app image missing
#
# Options:
#   -WorkspaceRoot   host data root (Postgres/Redis/ES/secrets/…). Persisted to
#                    deploy/dbc-docker.env. First run prompts if omitted.
#   -Full            first-time / heavy refresh: down stacks, free ports, package,
#                    rebuild images, renew mTLS if first-time marker missing
#   -Build           force bootJar + npm package
#   -RebuildImages   force compose --build
#   -RenewMtls       force re-issue server.p12
#   -FreePorts       kill host listeners on DBC ports (may affect IDEA / local PG)
#   -ResetPostgres   if postgres unhealthy, wipe local PG data dir and retry
# =============================================================================

param(
    [string]$WorkspaceRoot = "",
    [switch]$Full,
    [switch]$Build,
    [switch]$RebuildImages,
    [switch]$RenewMtls,
    [switch]$FreePorts,
    [switch]$ResetPostgres
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\Resolve-DbcDockerWorkspace.ps1"
$ws = Resolve-DbcDockerWorkspace -RepoRoot $RepoRoot -WorkspaceRoot $WorkspaceRoot -AllowPrompt
$WorkspaceRoot = $ws.HostPath
$ComposeEnvFile = $ws.EnvFile
$MarkerFile = Join-Path $WorkspaceRoot ".mtls-docker-ready"
$MiddlewareCompose = Join-Path $RepoRoot "deploy\middleware\docker-compose.yml"
$AppsCompose = Join-Path $RepoRoot "deploy\apps\docker-compose.yml"
$JavaServices = @("dbc-gateway", "dbc-usercenter", "dbc-manage", "dbc-sqlwork", "dbc-audit")
$AppImages = @("dbc-gateway:0.1.0", "dbc-usercenter:0.1.0", "dbc-manage:0.1.0", "dbc-sqlwork:0.1.0", "dbc-audit:0.1.0", "dbc-front:0.1.0")
$Ports = @(5432, 6379, 8000, 8001, 8003, 8004, 8005, 8006, 8007, 8008, 8044, 8048, 8080, 9000, 9200)

if ($Full) {
    $Build = $true
    $RebuildImages = $true
    $FreePorts = $true
    $ResetPostgres = $true
    if (-not (Test-Path $MarkerFile)) {
        $RenewMtls = $true
    }
}

function Write-Step([string]$msg) {
    Write-Host ""
    Write-Host "==== $msg ====" -ForegroundColor Cyan
}

# PowerShell 5 treats docker stderr warnings as terminating errors when ErrorActionPreference=Stop.
# Always run docker via this helper.
function Invoke-Docker {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$DockerArgs,
        [switch]$Quiet,
        [switch]$IgnoreExitCode
    )
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = & docker.exe @DockerArgs 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if (-not $Quiet) {
        foreach ($line in @($output)) {
            if ($null -ne $line) { Write-Host ($line.ToString()) }
        }
    }
    if (-not $IgnoreExitCode -and $code -ne 0) {
        throw ("docker " + ($DockerArgs -join " ") + " failed, exit=$code")
    }
    return $code
}

function Assert-Docker {
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
        throw "docker not found. Start Docker Desktop, then reopen Cursor terminal (or add Docker\resources\bin to PATH)."
    }
    $code = Invoke-Docker -DockerArgs @("info") -Quiet -IgnoreExitCode
    if ($code -ne 0) {
        throw "Docker engine not running. Start Docker Desktop and wait until it is ready."
    }
}

function Test-ImageExists([string]$image) {
    $code = Invoke-Docker -DockerArgs @("image", "inspect", $image) -Quiet -IgnoreExitCode
    return ($code -eq 0)
}

function Test-AllAppJars {
    foreach ($svc in $JavaServices) {
        $jar = Join-Path $RepoRoot "$svc\build\libs\app.jar"
        if (-not (Test-Path $jar)) { return $false }
    }
    return $true
}

function Test-AllAppImages {
    foreach ($img in $AppImages) {
        if (-not (Test-ImageExists $img)) { return $false }
    }
    return $true
}

function Stop-PortListeners {
    Write-Step "Free host ports (-FreePorts / -Full)"
    foreach ($p in $Ports) {
        $owns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($procId in $owns) {
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            # do not kill Docker Desktop itself by name alone; stopping compose is preferred
            Write-Host "  stop PID $procId ($($proc.ProcessName)) port $p"
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

function Wait-HttpOk([string]$url, [int]$timeoutSec = 120) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) { return }
        } catch { }
        Start-Sleep -Seconds 3
    }
    throw "timeout waiting for $url"
}

function Get-DockerOutput([string[]]$DockerArgs) {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = & docker.exe @DockerArgs 2>&1
    $script:LastDockerExitCode = $LASTEXITCODE
    $ErrorActionPreference = $prev
    $text = ($output | ForEach-Object { $_.ToString() }) -join "`n"
    return $text.Trim()
}

function Wait-ContainerRunning([string]$name, [int]$timeoutSec = 90) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        $status = Get-DockerOutput @("inspect", "-f", "{{.State.Status}}", $name)
        if ($status -eq "running") {
            $restarting = Get-DockerOutput @("inspect", "-f", "{{.State.Restarting}}", $name)
            if ($restarting -eq "false") { return }
        }
        Start-Sleep -Seconds 3
    }
    Invoke-Docker -DockerArgs @("logs", $name, "--tail", "40") -IgnoreExitCode | Out-Null
    throw "container $name not running stably"
}

function Sync-SecretsToRepo {
    $wsSecrets = Join-Path $WorkspaceRoot "secrets"
    $repoSecrets = Join-Path $RepoRoot "secrets"
    if (-not (Test-Path $wsSecrets)) { return }
    New-Item -ItemType Directory -Force -Path $repoSecrets | Out-Null
    robocopy $wsSecrets $repoSecrets /E /XO /NFL /NDL /NJH /NJS | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy secrets failed, exit=$LASTEXITCODE"
    }
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

function Start-Middleware {
    Write-Step "Start middleware (compose up -d)"
    Set-Location $RepoRoot
    Invoke-Compose -ComposeFile $MiddlewareCompose -ComposeArgs @("up", "-d") | Out-Null

    Start-Sleep -Seconds 5
    $pgStatus = Get-DockerOutput @("inspect", "-f", "{{.State.Status}}", "dbc-postgres")
    $pgRestarting = Get-DockerOutput @("inspect", "-f", "{{.State.Restarting}}", "dbc-postgres")
    if ($pgStatus -ne "running" -or $pgRestarting -eq "true") {
        if (-not $ResetPostgres) {
            Invoke-Docker -DockerArgs @("logs", "dbc-postgres", "--tail", "30") -IgnoreExitCode | Out-Null
            throw "postgres unhealthy. Fix mount/data, or re-run with -ResetPostgres / -Full (will wipe local PG data)."
        }
        Write-Host "postgres unhealthy -> wipe local data (-ResetPostgres/-Full) and retry"
        Invoke-Compose -ComposeFile $MiddlewareCompose -ComposeArgs @("stop", "postgres") -IgnoreExitCode | Out-Null
        $pgData = Join-Path $WorkspaceRoot "postgres\data"
        if (Test-Path $pgData) {
            Get-ChildItem -Path $pgData -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        }
        Invoke-Compose -ComposeFile $MiddlewareCompose -ComposeArgs @("up", "-d", "postgres") | Out-Null
        Start-Sleep -Seconds 8
    }

    Wait-ContainerRunning "dbc-postgres" 120
    Wait-ContainerRunning "dbc-redis" 60
    Wait-ContainerRunning "dbc-nacos" 120
    Wait-ContainerRunning "dbc-elasticsearch" 180
    Write-Host "wait nacos readiness..."
    # Nacos 3.x removed /nacos/v1/console/health/readiness (404). Use operator metrics instead.
    Wait-HttpOk "http://127.0.0.1:8000/nacos/v1/ns/operator/metrics" 180
    Write-Host "middleware ready"
}

function Ensure-MtlsFiles {
    $serverP12 = Join-Path $WorkspaceRoot "secrets\mtls\server.p12"
    $needRenew = $RenewMtls -or (-not (Test-Path $MarkerFile)) -or (-not (Test-Path $serverP12))
    if (-not $needRenew) {
        Write-Step "mTLS: reuse existing certs"
        return $false
    }

    Write-Step "mTLS: remove old server cert so usercenter can re-issue"
    @(
        (Join-Path $WorkspaceRoot "secrets\mtls\server.p12"),
        (Join-Path $WorkspaceRoot "secrets\mtls\server.pass"),
        (Join-Path $RepoRoot "secrets\mtls\server.p12"),
        (Join-Path $RepoRoot "secrets\mtls\server.pass")
    ) | ForEach-Object { Remove-Item -Force $_ -ErrorAction SilentlyContinue }
    return $true
}

function Start-Apps([bool]$doBuild, [bool]$waitCert) {
    Set-Location $RepoRoot
    $buildArgs = @()
    if ($doBuild) { $buildArgs += "--build" }

    if ($waitCert -or $doBuild -or -not (Test-ImageExists "dbc-usercenter:0.1.0")) {
        Write-Step ("Start usercenter first " + ($(if ($doBuild) { "(with --build)" } else { "" })))
        $ucArgs = @("up", "-d") + $buildArgs + @("dbc-usercenter")
        Invoke-Compose -ComposeFile $AppsCompose -ComposeArgs $ucArgs | Out-Null
        Wait-ContainerRunning "dbc-usercenter" 180

        $serverP12 = Join-Path $WorkspaceRoot "secrets\mtls\server.p12"
        $deadline = (Get-Date).AddSeconds(120)
        while ((Get-Date) -lt $deadline) {
            if (Test-Path $serverP12) { break }
            Start-Sleep -Seconds 3
        }
        if (Test-Path $serverP12) {
            Write-Host "server.p12 ready"
        } else {
            Write-Host "WARN: server.p12 not found yet; continuing"
        }
    }

    Write-Step ("Start all apps " + ($(if ($doBuild) { "(with --build)" } else { "(reuse images)" })))
    $allArgs = @("up", "-d") + $buildArgs
    Invoke-Compose -ComposeFile $AppsCompose -ComposeArgs $allArgs | Out-Null

    Write-Step "Sync secrets workspace -> repo (IDEA compatible)"
    Sync-SecretsToRepo
    New-Item -ItemType Directory -Force -Path $WorkspaceRoot | Out-Null
    Set-Content -Path $MarkerFile -Value ("ready " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) -Encoding ascii
}

# ----- main -----
Set-Location $RepoRoot
Assert-Docker

Write-Host "DBC Docker deploy/start"
Write-Host "Repo:      $RepoRoot"
Write-Host "Workspace: $WorkspaceRoot"
Write-Host ("Mode:      " + $(if ($Full) { "Full" } else { "Daily/start (compatible)" }))
Write-Host "Flags:     Build=$Build RebuildImages=$RebuildImages RenewMtls=$RenewMtls FreePorts=$FreePorts ResetPostgres=$ResetPostgres"

if ($Full) {
    Write-Step "Full mode: stop existing compose stacks"
    # warning "No resource found to remove" is normal when nothing is running
    Invoke-Compose -ComposeFile $AppsCompose -ComposeArgs @("down") -IgnoreExitCode | Out-Null
    Invoke-Compose -ComposeFile $MiddlewareCompose -ComposeArgs @("down") -IgnoreExitCode | Out-Null
}

if ($FreePorts) {
    Stop-PortListeners
}

Write-Step "Init workspace (idempotent)"
& "$PSScriptRoot\init-docker-workspace.ps1" -WorkspaceRoot $WorkspaceRoot

$needPackage = $Build -or -not (Test-AllAppJars)
if ($needPackage) {
    Write-Step "Package jars / front"
    & "$PSScriptRoot\build-docker-apps.ps1" -WorkspaceRoot $WorkspaceRoot
} else {
    Write-Step "Reuse existing app.jar (pass -Build or -Full to repackage)"
}

$needImageBuild = $RebuildImages -or -not (Test-AllAppImages) -or $needPackage
# if we packaged new jars, images should be rebuilt to pick them up
if ($needPackage) { $needImageBuild = $true }

Start-Middleware
$renewed = Ensure-MtlsFiles
Start-Apps -doBuild:$needImageBuild -waitCert:($renewed -or $RenewMtls -or -not (Test-Path $MarkerFile))

Write-Step "DONE"
Invoke-Compose -ComposeFile $MiddlewareCompose -ComposeArgs @("ps") | Out-Null
Invoke-Compose -ComposeFile $AppsCompose -ComposeArgs @("ps") | Out-Null
Write-Host ""
Write-Host "Open:  http://127.0.0.1:8080"
Write-Host "Login: admin / admin"
Write-Host "Nacos: http://127.0.0.1:8001/nacos"
Write-Host "Data:  $WorkspaceRoot"
Write-Host ""
Write-Host "Daily start again:  .\scripts\docker-deploy.cmd"
Write-Host "Change data dir:    .\scripts\docker-deploy.cmd -WorkspaceRoot <path>"
Write-Host "Code changed:       .\scripts\docker-deploy.cmd -Build"
Write-Host "Heavy refresh:      .\scripts\docker-deploy.cmd -Full"
Write-Host "Stop:               .\scripts\docker-stop.cmd"
