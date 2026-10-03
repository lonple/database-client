# 本地 PG 创建 company schema + 灌入 3 年仿生产演示数据
# 用法（仓库根）：
#   powershell -File scripts\demo-company\run.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path "$PSScriptRoot\01_schema.sql")) {
  $Root = "e:\workspace\database-client"
}
$Here = Join-Path $Root "scripts\demo-company"
$Py = Join-Path $Root "dbc-askdata\.venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
  $Py = "python"
}

Write-Host "==> apply schema via dbc-postgres"
Get-Content -Raw -Encoding UTF8 (Join-Path $Here "01_schema.sql") | docker exec -i dbc-postgres psql -U postgres -d postgres -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) { throw "schema apply failed" }

Write-Host "==> seed data ($((Get-Item (Join-Path $Here 'seed_company.py')).Name) company_eval_v2, may take ~1min)"
& $Py (Join-Path $Here "seed_company.py") --dsn "postgresql://postgres:root@127.0.0.1:5432/postgres"
if ($LASTEXITCODE -ne 0) { throw "seed failed" }

Write-Host "==> done"
