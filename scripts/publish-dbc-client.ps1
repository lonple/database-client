# =============================================================================
# Publish dbc-client modules to local Maven repo
# =============================================================================
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\publish-dbc-client.ps1
# If jar locked: stop Java processes that hold dbc-*-client jars, then retry.
# =============================================================================

$ErrorActionPreference = "Stop"

$clientDir = Join-Path $PSScriptRoot "..\dbc-client"
Set-Location $clientDir

if (-not (Test-Path ".\gradlew.bat")) {
    throw "dbc-client missing gradlew.bat"
}

& .\gradlew.bat publishToMavenLocal
if ($LASTEXITCODE -ne 0) {
    throw "publishToMavenLocal failed"
}

Write-Host "Published dbc-client to mavenLocal."
Write-Host "Keep dbc.client.composite=false in services, then Reload Gradle."
