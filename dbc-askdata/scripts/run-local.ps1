#Requires -Version 5.1
param(
  [switch]$SkipInstall,
  [switch]$Reload,
  [string]$DatabaseUrl = "postgresql+asyncpg://postgres:root@127.0.0.1:5432/postgres",
  [string]$SqlworkBaseUrl = "http://127.0.0.1:8007",
  [string]$ListenAddress = "0.0.0.0",
  [int]$Port = 8009,
  [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

$AskdataRoot = Split-Path -Parent $PSScriptRoot
$RepoRoot = Split-Path -Parent $AskdataRoot
$SecretsDir = Join-Path $RepoRoot "secrets"
$JwtFile = Join-Path $SecretsDir "jwt-secret.txt"
$VenvDir = Join-Path $AskdataRoot ".venv"

Write-Host "==> dbc-askdata local start" -ForegroundColor Cyan
Write-Host ("    askdata : {0}" -f $AskdataRoot)
Write-Host ("    secrets : {0}" -f $SecretsDir)
Write-Host ("    port    : {0}" -f $Port)

if (-not (Test-Path -LiteralPath $JwtFile)) {
  throw ("JWT secret missing: {0}. Start usercenter first or create repo-root secrets/jwt-secret.txt" -f $JwtFile)
}

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
  $pyCmd = Get-Command python -ErrorAction SilentlyContinue
  if ($null -eq $pyCmd) {
    throw "python not found. Install Python 3.11+ and add to PATH."
  }
  $PythonExe = $pyCmd.Source
}

if (-not (Test-Path -LiteralPath $VenvDir)) {
  Write-Host "==> create .venv" -ForegroundColor Yellow
  & $PythonExe -m venv $VenvDir
  if ($LASTEXITCODE -ne 0) {
    throw "venv create failed"
  }
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
  throw ("venv broken, missing: {0}" -f $VenvPython)
}

if (-not $SkipInstall) {
  Write-Host "==> pip install -e . (use -SkipInstall to skip)" -ForegroundColor Yellow
  Push-Location $AskdataRoot
  try {
    # Windows: must use "python -m pip" to upgrade pip itself (pip.exe self-modify fails)
    & $VenvPython -m pip install -U pip
    if ($LASTEXITCODE -ne 0) {
      throw "pip self-upgrade failed"
    }
    & $VenvPython -m pip install -e .
    if ($LASTEXITCODE -ne 0) {
      throw "pip install failed"
    }
  }
  finally {
    Pop-Location
  }
}

$env:DBC_ASKDATA_SECRETS_DIR = $SecretsDir
$env:DBC_SECRETS_DIR = $SecretsDir
$env:DBC_ASKDATA_DATABASE_URL = $DatabaseUrl
$env:DBC_ASKDATA_SQLWORK_BASE_URL = $SqlworkBaseUrl
if (-not $env:DBC_ASKDATA_USERCENTER_BASE_URL) {
  $env:DBC_ASKDATA_USERCENTER_BASE_URL = "http://127.0.0.1:8004"
}
# 默认云端 LLM：对齐 ai-dev-assistant（ada.llm → DashScope compatible-mode + qwen-max）
# 本地 Ollama 须显式 DBC_ASKDATA_LLM_RESIDENCY=local
if (-not $env:DBC_ASKDATA_LLM_RESIDENCY) {
  $env:DBC_ASKDATA_LLM_RESIDENCY = "cloud"
}
$llmResidency = ($env:DBC_ASKDATA_LLM_RESIDENCY).ToLowerInvariant()
if ($llmResidency -eq "local") {
  if (-not $env:DBC_ASKDATA_LLM_BASE_URL) {
    $env:DBC_ASKDATA_LLM_BASE_URL = "http://127.0.0.1:11434/v1"
  }
  if (-not $env:DBC_ASKDATA_LLM_MODEL) {
    $env:DBC_ASKDATA_LLM_MODEL = "qwen2.5-coder"
  }
} else {
  # 与 ada.llm.base-url / chat-model 默认值一致（可不带 /v1）
  if (-not $env:DBC_ASKDATA_LLM_BASE_URL) {
    if ($env:ADA_LLM_BASE_URL) {
      $env:DBC_ASKDATA_LLM_BASE_URL = $env:ADA_LLM_BASE_URL
    } else {
      $env:DBC_ASKDATA_LLM_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode"
    }
  }
  if (-not $env:DBC_ASKDATA_LLM_MODEL) {
    if ($env:ADA_LLM_CHAT_MODEL) {
      $env:DBC_ASKDATA_LLM_MODEL = $env:ADA_LLM_CHAT_MODEL
    } else {
      $env:DBC_ASKDATA_LLM_MODEL = "qwen-max"
    }
  }
  if (-not $env:DBC_ASKDATA_LLM_API_KEY -and $env:ADA_LLM_API_KEY) {
    $env:DBC_ASKDATA_LLM_API_KEY = $env:ADA_LLM_API_KEY
  }
  $keyFile = Join-Path $SecretsDir "askdata-llm-api-key.txt"
  if (-not $env:DBC_ASKDATA_LLM_API_KEY -and -not (Test-Path -LiteralPath $keyFile)) {
    throw ("cloud LLM missing API key. Write {0} or set DBC_ASKDATA_LLM_API_KEY / ADA_LLM_API_KEY" -f $keyFile)
  }
}
# 经网关 lb://dbc-askdata 访问：本地默认注册到 Nacos（与 Java 服务一致）
if (-not $env:DBC_NACOS_ADDR) {
  $env:DBC_NACOS_ADDR = "127.0.0.1:8000"
}
if (-not $env:DBC_ASKDATA_NACOS_REGISTER) {
  $env:DBC_ASKDATA_NACOS_REGISTER = "true"
}
if (-not $env:DBC_ASKDATA_NACOS_IP) {
  $env:DBC_ASKDATA_NACOS_IP = "127.0.0.1"
}
# Local default: audit ON (same as prod). Missing p12 fails fast instead of silent disable.
$AskdataP12 = Join-Path $SecretsDir "mtls\clients\dbc-askdata.p12"
$AskdataPass = Join-Path $SecretsDir "mtls\clients\dbc-askdata.pass"
$CaCrt = Join-Path $SecretsDir "mtls\ca.crt"
if (-not $env:DBC_ASKDATA_AUDIT_ENABLED) {
  $env:DBC_ASKDATA_AUDIT_ENABLED = "true"
}
if (-not $env:DBC_ASKDATA_AUDIT_MTLS_BASE_URL) {
  $env:DBC_ASKDATA_AUDIT_MTLS_BASE_URL = "https://127.0.0.1:8048"
}
$auditOn = ($env:DBC_ASKDATA_AUDIT_ENABLED -eq "true" -or $env:DBC_ASKDATA_AUDIT_ENABLED -eq "1")
if ($auditOn) {
  if (-not (Test-Path -LiteralPath $AskdataP12) -or -not (Test-Path -LiteralPath $AskdataPass)) {
    throw ("Audit enabled but missing mTLS client cert: {0} (+ .pass). Restart usercenter to issue cert for app dbc-askdata, or POST /apps/{id}/reissue-cert." -f $AskdataP12)
  }
  if (-not (Test-Path -LiteralPath $CaCrt)) {
    throw ("Audit enabled but missing CA: {0}" -f $CaCrt)
  }
} else {
  Write-Host "==> WARN: DBC_ASKDATA_AUDIT_ENABLED=false (audit ingest off; only when explicitly disabled)" -ForegroundColor Yellow
}

Write-Host "==> env" -ForegroundColor Green
Write-Host ("    DBC_ASKDATA_SECRETS_DIR      = {0}" -f $env:DBC_ASKDATA_SECRETS_DIR)
Write-Host ("    DBC_ASKDATA_DATABASE_URL     = {0}" -f $env:DBC_ASKDATA_DATABASE_URL)
Write-Host ("    DBC_ASKDATA_SQLWORK_BASE_URL = {0}" -f $env:DBC_ASKDATA_SQLWORK_BASE_URL)
Write-Host ("    DBC_ASKDATA_USERCENTER_BASE_URL = {0}" -f $env:DBC_ASKDATA_USERCENTER_BASE_URL)
Write-Host ("    DBC_ASKDATA_LLM_RESIDENCY    = {0}" -f $env:DBC_ASKDATA_LLM_RESIDENCY)
Write-Host ("    DBC_ASKDATA_LLM_BASE_URL     = {0}" -f $env:DBC_ASKDATA_LLM_BASE_URL)
Write-Host ("    DBC_ASKDATA_LLM_MODEL        = {0}" -f $env:DBC_ASKDATA_LLM_MODEL)
Write-Host ("    DBC_ASKDATA_AUDIT_ENABLED    = {0}" -f $env:DBC_ASKDATA_AUDIT_ENABLED)
Write-Host ("    DBC_ASKDATA_AUDIT_MTLS_BASE_URL = {0}" -f $env:DBC_ASKDATA_AUDIT_MTLS_BASE_URL)
Write-Host ("    DBC_NACOS_ADDR               = {0}" -f $env:DBC_NACOS_ADDR)
Write-Host ("    DBC_ASKDATA_NACOS_REGISTER   = {0}" -f $env:DBC_ASKDATA_NACOS_REGISTER)
Write-Host ("    DBC_ASKDATA_NACOS_IP         = {0}" -f $env:DBC_ASKDATA_NACOS_IP)
Write-Host ("==> health: http://127.0.0.1:{0}/health" -f $Port) -ForegroundColor Green

# 启动前释放端口，避免 WinError 10048 / Address already in use
Write-Host ("==> stop existing listener on port {0}" -f $Port) -ForegroundColor Yellow
$listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -eq 0) {
  Write-Host "    (idle)"
} else {
  $pids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($procId in $pids) {
    if ($null -eq $procId -or $procId -le 4) { continue }
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    $procName = if ($proc) { $proc.ProcessName } else { "?" }
    Write-Host ("    stop pid={0} name={1}" -f $procId, $procName)
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
  }
  $deadline = (Get-Date).AddSeconds(10)
  do {
    Start-Sleep -Milliseconds 200
    $still = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
  } while ($still.Count -gt 0 -and (Get-Date) -lt $deadline)
  $still = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
  if ($still.Count -gt 0) {
    throw ("port {0} still in use after stop; refuse to start" -f $Port)
  }
  Write-Host "    port freed"
}

Write-Host "==> starting uvicorn ..." -ForegroundColor Cyan

Set-Location $AskdataRoot
$uvicornArgs = @(
  "-m", "uvicorn",
  "dbc_askdata.main:app",
  "--host", $ListenAddress,
  "--port", "$Port"
)
if ($Reload) {
  $uvicornArgs += "--reload"
}

& $VenvPython @uvicornArgs
exit $LASTEXITCODE
