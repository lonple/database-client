#Requires -Version 5.1
# =============================================================================
# DBC local one-click start
# =============================================================================
# Usage (repo root):
#   .\scripts\local-start.cmd
#   .\scripts\local-start.cmd askdata gateway front
#   .\scripts\local-start.cmd uc manage sqlwork
#   .\scripts\local-start.cmd -Background askdata gateway
#   .\scripts\local-start.cmd -NoAskdataDebugger askdata
# Short names: askdata audit gateway front graph knowledge manage sqlwork usercenter(uc)
#
# No service names  => stop+start ALL modules
# Service names     => stop+start only those (space-separated)
# Default           => foreground: merge logs in THIS console; Ctrl+C stops selected
# -Background       => each service in its own console; this script exits
# -SingleConsole    => alias of default (compat)
#
# Does NOT start/stop: PostgreSQL :5432, Redis :6379, ES :9200, Nacos :8000/:8001
# First clone / after dbc-client changes: .\scripts\publish-dbc-client.ps1
# =============================================================================

[CmdletBinding()]
param(
    # Service names: space-separated. Empty = all.
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Services = @(),
    # Deprecated: same as trailing service names (kept for old docs/scripts)
    [string[]]$Only = @(),
    [string[]]$Skip = @(),
    [switch]$NoAskdataDebugger,
    [switch]$SkipFrontInstall,
    [switch]$DryRun,
    # Skip the stop phase (start only; not recommended)
    [switch]$NoStop,
    # Background: one console window per service; script exits
    [switch]$Background,
    # Compat alias: same as default foreground (ignored if -Background)
    [switch]$SingleConsole,
    # Delay between starting modules (seconds). askdata also waits for JWT file.
    [int]$StaggerSeconds = 2,
    # Max seconds to wait for secrets/jwt-secret.txt before starting askdata
    [int]$JwtWaitSeconds = 120,
    # After kill, wait until listen ports are free (seconds per module)
    [int]$StopWaitSeconds = 20
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

# gateway before askdata/front: Vite proxies all /dbc-* via :8003
$AllModules = @(
    "usercenter",
    "manage",
    "sqlwork",
    "audit",
    "knowledge",
    "graph",
    "gateway",
    "askdata",
    "front"
)

$Aliases = @{
    "uc"             = "usercenter"
    "user-center"    = "usercenter"
    "dbc-usercenter" = "usercenter"
    "dbc-manage"     = "manage"
    "dbc-sqlwork"    = "sqlwork"
    "dbc-audit"      = "audit"
    "dbc-knowledge"  = "knowledge"
    "dbc-graph"      = "graph"
    "dbc-askdata"    = "askdata"
    "dbc-gateway"    = "gateway"
    "dbc-front"      = "front"
    "frontend"       = "front"
}

$ModuleColors = @{
    usercenter = "DarkCyan"
    manage     = "Cyan"
    sqlwork    = "Green"
    audit      = "Yellow"
    knowledge  = "DarkGreen"
    graph      = "DarkMagenta"
    askdata    = "Magenta"
    gateway    = "Blue"
    front      = "DarkYellow"
}

function Normalize-ModuleName {
    param([Parameter(Mandatory = $true)][string]$Name)
    $key = $Name.Trim().ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($key)) { return $null }
    if ($Aliases.ContainsKey($key)) { return $Aliases[$key] }
    if ($AllModules -contains $key) { return $key }
    throw ("Unknown module: {0}. Allowed: {1} (usercenter also: uc)" -f $Name, ($AllModules -join ", "))
}

function Split-ModuleTokens {
    param([string[]]$Values)
    $out = New-Object System.Collections.Generic.List[string]
    foreach ($raw in @($Values)) {
        if ([string]::IsNullOrWhiteSpace($raw)) { continue }
        foreach ($part in ($raw -split '[, ]+')) {
            if (-not [string]::IsNullOrWhiteSpace($part)) {
                $out.Add($part.Trim())
            }
        }
    }
    return , $out.ToArray()
}

function Resolve-Selection {
    $named = New-Object System.Collections.Generic.List[string]
    foreach ($n in (Split-ModuleTokens -Values $Services)) {
        # Ignore accidental switch-like tokens if cmd quoting is odd
        if ($n.StartsWith("-")) { continue }
        $m = Normalize-ModuleName $n
        if ($m -and -not $named.Contains($m)) { $named.Add($m) }
    }
    # Compat: -Only still accepted
    foreach ($n in (Split-ModuleTokens -Values $Only)) {
        $m = Normalize-ModuleName $n
        if ($m -and -not $named.Contains($m)) { $named.Add($m) }
    }

    $selected = New-Object System.Collections.Generic.List[string]
    if ($named.Count -gt 0) {
        foreach ($m in $named) { $selected.Add($m) }
    } else {
        foreach ($m in $AllModules) { $selected.Add($m) }
    }

    $skipSet = New-Object System.Collections.Generic.HashSet[string]
    if ($Skip -and $Skip.Count -gt 0) {
        foreach ($n in (Split-ModuleTokens -Values $Skip)) {
            $m = Normalize-ModuleName $n
            if ($m) {
                [void]$skipSet.Add($m)
                [void]$selected.Remove($m)
            }
        }
    }

    # Front always goes through gateway :8003 — auto-include unless explicitly skipped
    $script:GatewayAutoIncluded = $false
    if (-not $selected.Contains("gateway") -and -not $skipSet.Contains("gateway")) {
        $selected.Add("gateway")
        $script:GatewayAutoIncluded = $true
    }

    return @($AllModules | Where-Object { $selected -contains $_ })
}

function Test-TcpPortOpen {
    param([string]$HostName = "127.0.0.1", [int]$Port, [int]$TimeoutMs = 400)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($HostName, $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        if (-not $ok) {
            $client.Close()
            return $false
        }
        $client.EndConnect($iar)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

function Write-Step {
    param([string]$Message, [string]$Color = "Cyan")
    Write-Host ("==> {0}" -f $Message) -ForegroundColor $Color
}

# Primary HTTP + optional mTLS / debug ports owned by each local module
$ModulePorts = @{
    usercenter = @(8004, 8044)
    manage     = @(8006)
    sqlwork    = @(8007)
    audit      = @(8008, 8048)
    knowledge  = @(8010)
    graph      = @(8011)
    askdata    = @(8009, 5678)
    gateway    = @(8003)
    front      = @(8005)
}

$ModuleWindowTitle = @{
    usercenter = "dbc-usercenter"
    manage     = "dbc-manage"
    sqlwork    = "dbc-sqlwork"
    audit      = "dbc-audit"
    knowledge  = "dbc-knowledge"
    graph      = "dbc-graph"
    askdata    = "dbc-askdata"
    gateway    = "dbc-gateway"
    front      = "dbc-front"
}

function Get-ListenPids {
    param([Parameter(Mandatory = $true)][int[]]$Ports)
    $pids = New-Object System.Collections.Generic.HashSet[int]
    foreach ($p in $Ports) {
        $owns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($procId in @($owns)) {
            if ($procId -and $procId -gt 0) { [void]$pids.Add([int]$procId) }
        }
    }
    return @($pids)
}

function Stop-ModuleListeners {
    param(
        [Parameter(Mandatory = $true)][string]$Module,
        [switch]$WhatIfOnly
    )
    $ports = @($ModulePorts[$Module])
    if (-not $ports -or $ports.Count -eq 0) { return }

    $title = $ModuleWindowTitle[$Module]
    $pids = Get-ListenPids -Ports $ports
    if ($pids.Count -eq 0 -and -not $title) {
        Write-Host ("    idle   : {0} (ports {1})" -f $Module, ($ports -join ",")) -ForegroundColor DarkGray
        return
    }

    if ($pids.Count -eq 0) {
        Write-Host ("    idle   : {0} ports {1} (try console title)" -f $Module, ($ports -join ",")) -ForegroundColor DarkGray
    } else {
        foreach ($procId in $pids) {
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            $name = if ($proc) { $proc.ProcessName } else { "?" }
            Write-Host ("    stop   : {0} PID {1} ({2}) ports {3}" -f $Module, $procId, $name, ($ports -join ",")) -ForegroundColor Yellow
            if (-not $WhatIfOnly) {
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        }
    }

    # Close prior multi-window local-start cmd consoles
    if ($title -and -not $WhatIfOnly) {
        $filter = 'WINDOWTITLE eq {0}*' -f $title
        & taskkill.exe /F /FI $filter 2>$null | Out-Null
    }

    if ($WhatIfOnly) { return }

    $deadline = (Get-Date).AddSeconds($StopWaitSeconds)
    while ((Get-Date) -lt $deadline) {
        $left = Get-ListenPids -Ports $ports
        if ($left.Count -eq 0) { break }
        Start-Sleep -Milliseconds 500
    }
    $still = Get-ListenPids -Ports $ports
    if ($still.Count -gt 0) {
        Write-Host ("    WARN   : {0} still listening after stop: PIDs {1}" -f $Module, ($still -join ",")) -ForegroundColor Yellow
    } else {
        Write-Host ("    freed  : {0} :{1}" -f $Module, ($ports -join ",")) -ForegroundColor DarkGreen
    }
}

function Start-ServiceWindow {
    param(
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$CommandLine
    )
    if (-not (Test-Path -LiteralPath $WorkingDirectory)) {
        throw ("Directory not found: {0}" -f $WorkingDirectory)
    }
    $inner = 'title {0} & cd /d "{1}" & {2}' -f $Title, $WorkingDirectory, $CommandLine
    Write-Host ("    [{0}] {1}" -f $Title, $CommandLine) -ForegroundColor DarkGray
    if ($DryRun) { return $null }
    return Start-Process -FilePath "cmd.exe" -ArgumentList @("/k", $inner) -WorkingDirectory $WorkingDirectory -PassThru
}

# Foreground mode: redirect each service to a log file, then poll+print with prefix.
# (PowerShell Register-ObjectEvent often never paints to the host console.)
$script:LocalRunLogDir = Join-Path $RepoRoot "scripts\.local-run\logs"

function Start-ServiceMerged {
    param(
        [Parameter(Mandatory = $true)][string]$Module,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$CommandLine,
        [Parameter(Mandatory = $true)][ConsoleColor]$Color
    )
    if (-not (Test-Path -LiteralPath $WorkingDirectory)) {
        throw ("Directory not found: {0}" -f $WorkingDirectory)
    }
    if (-not (Test-Path -LiteralPath $script:LocalRunLogDir)) {
        New-Item -ItemType Directory -Force -Path $script:LocalRunLogDir | Out-Null
    }
    $logFile = Join-Path $script:LocalRunLogDir ("{0}.log" -f $Module)
    Write-Host ("    [{0}] {1}" -f $Module, $CommandLine) -ForegroundColor DarkGray
    Write-Host ("           log -> {0}" -f $logFile) -ForegroundColor DarkGray
    if ($DryRun) { return $null }

    # Truncate previous run
    [System.IO.File]::WriteAllText($logFile, "")

    # cmd redirection captures the whole gradle/java/npm tree more reliably than Process.Redirect*
    $quotedCmd = $CommandLine.Replace('"', '""')
    $inner = 'set PYTHONUNBUFFERED=1&& set TERM=dumb&& cd /d "{0}" && ({1}) >> "{2}" 2>&1' -f `
        $WorkingDirectory, $quotedCmd, $logFile
    $p = Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $inner) `
        -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -PassThru

    return @{
        Module  = $Module
        Color   = $Color
        LogFile = $logFile
        Process = $p
    }
}

function Start-LogTailers {
    param([Parameter(Mandatory = $true)][object[]]$Entries)
    $tailers = New-Object System.Collections.Generic.List[hashtable]
    foreach ($e in $Entries) {
        if ($null -eq $e) { continue }
        $share = [System.IO.FileShare]::ReadWrite
        $fs = [System.IO.File]::Open(
            [string]$e.LogFile,
            [System.IO.FileMode]::OpenOrCreate,
            [System.IO.FileAccess]::Read,
            $share
        )
        # Avoid New-Object ctor binding issues on PS 5.1 ("参数类型不匹配")
        $enc = New-Object System.Text.UTF8Encoding $false
        $sr = New-Object System.IO.StreamReader($fs, $enc)
        $tailers.Add(@{
            Module  = [string]$e.Module
            Color   = [ConsoleColor]$e.Color
            Stream  = $fs
            Reader  = $sr
            Process = $e.Process
        }) | Out-Null
    }
    return $tailers
}

function Read-LogTailersOnce {
    param($Tailers)
    $any = $false
    foreach ($t in @($Tailers)) {
        if ($null -eq $t -or $null -eq $t.Reader) { continue }
        while (-not $t.Reader.EndOfStream) {
            $line = $t.Reader.ReadLine()
            if ($null -eq $line) { break }
            $any = $true
            Write-Host ("[{0}] {1}" -f $t.Module, $line) -ForegroundColor $t.Color
        }
    }
    return $any
}

function Close-LogTailers {
    param($Tailers)
    foreach ($t in @($Tailers)) {
        if ($null -eq $t) { continue }
        try { if ($null -ne $t.Reader) { $t.Reader.Dispose() } } catch { }
        try { if ($null -ne $t.Stream) { $t.Stream.Dispose() } } catch { }
    }
}

function Get-ModuleCommand {
    param([Parameter(Mandatory = $true)][string]$Module)
    switch ($Module) {
        "usercenter" {
            return @{
                Dir  = (Join-Path $RepoRoot "dbc-usercenter")
                Cmd  = "gradlew.bat --console=plain bootRun"
                Note = "start usercenter :8004"
            }
        }
        "manage" {
            return @{
                Dir  = (Join-Path $RepoRoot "dbc-manage")
                Cmd  = "gradlew.bat --console=plain bootRun"
                Note = "start manage :8006"
            }
        }
        "sqlwork" {
            return @{
                Dir  = (Join-Path $RepoRoot "dbc-sqlwork")
                Cmd  = "gradlew.bat --console=plain bootRun"
                Note = "start sqlwork :8007"
            }
        }
        "audit" {
            return @{
                Dir  = (Join-Path $RepoRoot "dbc-audit")
                Cmd  = "gradlew.bat --console=plain bootRun"
                Note = "start audit :8008 (needs ES :9200)"
            }
        }
        "knowledge" {
            return @{
                Dir  = (Join-Path $RepoRoot "dbc-knowledge")
                Cmd  = "gradlew.bat --console=plain bootRun"
                Note = "start knowledge :8010 (needs Milvus :19530)"
            }
        }
        "graph" {
            return @{
                Dir  = (Join-Path $RepoRoot "dbc-graph")
                Cmd  = "gradlew.bat --console=plain bootRun"
                Note = "start graph :8011 (needs Neo4j :7687)"
            }
        }
        "askdata" {
            $askCmd = "scripts\run-local.cmd"
            if ($NoAskdataDebugger) { $askCmd = "$askCmd -NoDebugger" }
            $dbgLabel = if ($NoAskdataDebugger) { "no debugpy" } else { "debugpy :5678" }
            return @{
                Dir  = (Join-Path $RepoRoot "dbc-askdata")
                Cmd  = $askCmd
                Note = ("start askdata :8009 ({0})" -f $dbgLabel)
            }
        }
        "gateway" {
            return @{
                Dir  = (Join-Path $RepoRoot "dbc-gateway")
                Cmd  = "gradlew.bat --console=plain bootRun"
                Note = "start gateway :8003"
            }
        }
        "front" {
            if ($SkipFrontInstall) {
                $frontCmd = "npm.cmd run dev"
            } else {
                $frontCmd = "npm.cmd install & npm.cmd run dev"
            }
            return @{
                Dir  = (Join-Path $RepoRoot "dbc-front")
                Cmd  = $frontCmd
                Note = "start front :8005"
            }
        }
        default { throw ("Unhandled module: {0}" -f $Module) }
    }
}

function Wait-AskdataJwt {
    if ($DryRun) { return }
    if (Test-Path -LiteralPath $JwtFile) { return }
    Write-Step ("wait JWT: {0} (max {1}s; ensure usercenter is up)" -f $JwtFile, $JwtWaitSeconds) "Yellow"
    $deadline = (Get-Date).AddSeconds($JwtWaitSeconds)
    while (-not (Test-Path -LiteralPath $JwtFile)) {
        if ((Get-Date) -gt $deadline) {
            throw ("Timeout waiting for {0}. Start usercenter first, or create the file, then retry askdata." -f $JwtFile)
        }
        Start-Sleep -Seconds 2
    }
    Write-Host "    ok     : jwt-secret.txt ready" -ForegroundColor DarkGreen
}

$selected = Resolve-Selection
if ($selected.Count -eq 0) {
    throw "No modules selected (check -Only / -Skip)"
}

Write-Step "DBC local start"
Write-Host ("    repo   : {0}" -f $RepoRoot)
Write-Host ("    modules: {0}" -f ($selected -join ", "))
if ($script:GatewayAutoIncluded) {
    Write-Host "    note   : auto-include gateway (front proxies via :8003; use -Skip gateway to omit)" -ForegroundColor DarkYellow
}
# Default = foreground merged logs; -Background for multi-window
$useBackground = [bool]$Background
if ($SingleConsole -and $Background) {
    Write-Host "    WARN   : -Background overrides -SingleConsole" -ForegroundColor Yellow
}
if ($useBackground) {
    Write-Host "    mode   : background (one console per service; this script exits)" -ForegroundColor DarkGray
} else {
    Write-Host "    mode   : foreground (merged logs in this window; Ctrl+C to stop)" -ForegroundColor Yellow
}
if ($DryRun) {
    Write-Host "    mode   : DryRun (no kill / no start)" -ForegroundColor Yellow
}
if ($NoStop) {
    Write-Host "    mode   : NoStop (start only)" -ForegroundColor Yellow
}

$infra = @(
    @{ Name = "PostgreSQL"; Port = 5432 },
    @{ Name = "Redis"; Port = 6379 },
    @{ Name = "Elasticsearch"; Port = 9200 },
    @{ Name = "Nacos"; Port = 8000 },
    @{ Name = "Milvus"; Port = 19530 },
    @{ Name = "Neo4j"; Port = 7687 }
)
foreach ($item in $infra) {
    if (Test-TcpPortOpen -Port $item.Port) {
        Write-Host ("    ok     : {0} :{1}" -f $item.Name, $item.Port) -ForegroundColor DarkGreen
    } else {
        Write-Host ("    WARN   : {0} :{1} not listening (start middleware first)" -f $item.Name, $item.Port) -ForegroundColor Yellow
    }
}

$JwtFile = Join-Path $RepoRoot "secrets\jwt-secret.txt"

# ---- stop selected modules, then start ----
if (-not $NoStop) {
    Write-Step ("stop selected modules: {0}" -f ($selected -join ", "))
    foreach ($mod in $selected) {
        Stop-ModuleListeners -Module $mod -WhatIfOnly:$DryRun
    }
    if (-not $DryRun) {
        Start-Sleep -Seconds 1
    }
}

$started = New-Object System.Collections.Generic.List[string]
$mergedEntries = New-Object System.Collections.Generic.List[object]
$logTailers = @()
$last = $selected[$selected.Count - 1]

try {
    foreach ($mod in $selected) {
        if ($mod -eq "askdata") {
            Wait-AskdataJwt
        }
        $spec = Get-ModuleCommand -Module $mod
        Write-Step $spec.Note
        $colorName = $ModuleColors[$mod]
        if (-not $colorName) { $colorName = "Gray" }
        $color = [ConsoleColor]([Enum]::Parse([ConsoleColor], $colorName))

        if ($useBackground) {
            $title = $ModuleWindowTitle[$mod]
            # Background windows: keep plain gradle console for readability
            $bgCmd = $spec.Cmd -replace ' --console=plain', ''
            $null = Start-ServiceWindow -Title $title -WorkingDirectory $spec.Dir -CommandLine $bgCmd
        } else {
            $entry = Start-ServiceMerged -Module $mod -WorkingDirectory $spec.Dir -CommandLine $spec.Cmd -Color $color
            if ($null -ne $entry) { [void]$mergedEntries.Add($entry) }
        }
        [void]$started.Add($mod)
        if ($StaggerSeconds -gt 0 -and $mod -ne $last -and -not $DryRun) {
            Start-Sleep -Seconds $StaggerSeconds
        }
    }

    Write-Host ""
    if ($useBackground) {
        Write-Step ("windows opened: {0}" -f ($started -join ", ")) "Green"
    } else {
        Write-Step ("merged logs running: {0}" -f ($started -join ", ")) "Green"
        Write-Host ("    logdir  : {0}" -f $script:LocalRunLogDir) -ForegroundColor DarkGray
    }
    Write-Host "    UI      : http://127.0.0.1:8005  (admin / admin)"
    Write-Host "    gateway : http://127.0.0.1:8003"
    Write-Host "    Nacos   : http://127.0.0.1:8001"
    Write-Host "    docs    : doc/运维/01-本地启动说明.md"

    if ($DryRun) {
        return
    }

    if ($useBackground) {
        Write-Host "    note    : close a console or Ctrl+C there to stop that service."
    } else {
        Write-Host "    note    : Ctrl+C stops selected modules and exits this script." -ForegroundColor Yellow
        Write-Host ""
        $entryArr = @($mergedEntries.ToArray())
        $logTailers = Start-LogTailers -Entries $entryArr
        while ($true) {
            $null = Read-LogTailersOnce -Tailers $logTailers
            $alive = @(
                $entryArr | Where-Object {
                    $null -ne $_.Process -and -not $_.Process.HasExited
                }
            )
            if ($alive.Count -eq 0) {
                Start-Sleep -Milliseconds 300
                $null = Read-LogTailersOnce -Tailers $logTailers
                Write-Step "all child processes exited" "Yellow"
                break
            }
            Start-Sleep -Milliseconds 200
        }
    }
} finally {
    # Only tear down when we actually entered the wait loop (or Ctrl+C after services up).
    # Avoid killing services if an early setup error already printed — still cleanup on Ctrl+C.
    if (-not $useBackground -and -not $DryRun -and $started.Count -gt 0) {
        Write-Host ""
        Write-Step ("foreground cleanup: stop {0}" -f ($started -join ", ")) "Yellow"
        Close-LogTailers -Tailers $logTailers
        foreach ($mod in $started) {
            Stop-ModuleListeners -Module $mod
        }
        foreach ($e in $mergedEntries) {
            try {
                if ($null -ne $e.Process -and -not $e.Process.HasExited) {
                    Stop-Process -Id $e.Process.Id -Force -ErrorAction SilentlyContinue
                }
            } catch { }
            try { if ($null -ne $e.Process) { $e.Process.Dispose() } } catch { }
        }
    }
}
