# =============================================================================
# Build jars (and optional front dist) before docker compose --build
# =============================================================================
# Usage (repo root):
#   powershell -ExecutionPolicy Bypass -File .\scripts\build-docker-apps.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\build-docker-apps.ps1 -WorkspaceRoot E:\app\docker\workspace\dbc
#
# Flow:
#   1) init-docker-workspace.ps1
#   2) publish-dbc-client.ps1
#   3) gradlew bootJar for each Java service -> build/libs/app.jar
#   4) optional: npm run build, copy dist to workspace front/html
# Then:
#   docker compose --env-file deploy/dbc-docker.env -f deploy/middleware/docker-compose.yml up -d
#   docker compose --env-file deploy/dbc-docker.env -f deploy/apps/docker-compose.yml up -d --build
# =============================================================================

param(
    [string]$WorkspaceRoot = "",
    [string[]]$Services = @()
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\Resolve-DbcDockerWorkspace.ps1"
$ws = Resolve-DbcDockerWorkspace -RepoRoot $RepoRoot -WorkspaceRoot $WorkspaceRoot -AllowPrompt
$WorkspaceRoot = $ws.HostPath
$FrontHtml = Join-Path $WorkspaceRoot "front\html"

Set-Location $RepoRoot

Write-Host "==> [0/4] init workspace"
& "$PSScriptRoot\init-docker-workspace.ps1" -WorkspaceRoot $WorkspaceRoot
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
    # child script may not set LASTEXITCODE; ignore when null
}

$allJava = @("dbc-gateway", "dbc-usercenter", "dbc-manage", "dbc-sqlwork", "dbc-audit", "dbc-knowledge", "dbc-graph")
$selected = @($Services | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $_.Trim() })
if ($selected.Count -eq 0) {
    $javaToBuild = $allJava
    $buildFront = $true
} else {
    $javaToBuild = @($allJava | Where-Object { $selected -contains $_ })
    $buildFront = $selected -contains "dbc-front"
}

if ($javaToBuild.Count -eq 0 -and -not $buildFront) {
    Write-Host "==> skip jar/npm (no Java/front in -Services)"
} else {
    if ($javaToBuild.Count -gt 0) {
        Write-Host "==> [1/4] publish dbc-client to mavenLocal"
        & "$PSScriptRoot\publish-dbc-client.ps1"
        if ($LASTEXITCODE -ne 0) {
            throw "publish-dbc-client failed"
        }

        Write-Host "==> [2/4] bootJar for Java services"
        foreach ($svc in $javaToBuild) {
            Write-Host "    bootJar $svc"
            Set-Location (Join-Path $RepoRoot $svc)
            & .\gradlew.bat bootJar -x test
            if ($LASTEXITCODE -ne 0) {
                throw "bootJar failed: $svc"
            }
            $jar = Join-Path (Get-Location) "build\libs\app.jar"
            if (-not (Test-Path $jar)) {
                throw "missing $jar - check bootJar.archiveFileName=app.jar in build.gradle.kts"
            }
        }
    } else {
        Write-Host "==> skip Java bootJar"
    }

    if ($buildFront) {
        Write-Host "==> [3/4] frontend npm build, sync dist to workspace"
        Set-Location (Join-Path $RepoRoot "dbc-front")
        if (Test-Path "package-lock.json") {
            & npm.cmd ci
        } else {
            & npm.cmd install
        }
        if ($LASTEXITCODE -ne 0) {
            throw "npm install failed"
        }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) {
            throw "npm run build failed"
        }
        if (-not (Test-Path "dist\index.html")) {
            throw "front dist/index.html missing"
        }

        Write-Host "    sync dist -> $FrontHtml"
        New-Item -ItemType Directory -Force -Path $FrontHtml | Out-Null
        Get-ChildItem -Path $FrontHtml -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Copy-Item -Path "dist\*" -Destination $FrontHtml -Recurse -Force
    } else {
        Write-Host "==> skip frontend npm build"
    }
}

Set-Location $RepoRoot
Write-Host "==> [4/4] package done. Next: build images and run"
Write-Host "  docker compose --env-file deploy/dbc-docker.env -f deploy/middleware/docker-compose.yml up -d"
Write-Host "  docker compose --env-file deploy/dbc-docker.env -f deploy/apps/docker-compose.yml up -d --build"
Write-Host ""
Write-Host "Summary:"
Write-Host "  workspace     = $WorkspaceRoot"
Write-Host "  package jars  = this script"
Write-Host "  build images  = Dockerfiles + compose --build"
Write-Host "  run containers = compose up"
