# 本地 PG 创建 company schema + 灌入 3 年仿生产演示数据
# 用法（仓库根）：
#   powershell -File scripts\demo-company\run.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path "$PSScriptRoot\01_schema.sql")) {
  $Root = "e:\workspace\agent-project\database-client"
}
$Here = Join-Path $Root "scripts\demo-company"
$Py = Join-Path $Root "dbc-askdata\.venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
  $Py = "python"
}

function Apply-SqlFile([string]$HostPath, [string]$Label) {
  # Windows PowerShell 管道会弄坏 UTF-8 中文 COMMENT；docker cp + 容器内 -f 可保真
  $containerPath = "/tmp/company_apply.sql"
  docker cp $HostPath "dbc-postgres:$containerPath"
  if ($LASTEXITCODE -ne 0) { throw "$Label docker cp failed" }
  docker exec -e PGCLIENTENCODING=UTF8 dbc-postgres psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f $containerPath
  if ($LASTEXITCODE -ne 0) { throw "$Label apply failed" }
}

Write-Host "==> apply core schema via dbc-postgres"
Apply-SqlFile (Join-Path $Here "01_schema.sql") "core schema"

$ExtSql = Join-Path $Here "02_schema_extended.sql"
if (-not (Test-Path $ExtSql)) {
  Write-Host "==> generate extended schema (~200 tables)"
  & $Py (Join-Path $Here "gen_extended_schema.py")
  if ($LASTEXITCODE -ne 0) { throw "gen_extended_schema failed" }
}
Write-Host "==> apply extended schema (no seed data)"
Apply-SqlFile $ExtSql "extended schema"

Write-Host "==> fix any garbled COMMENT (keep empty comments as-is)"
& $Py (Join-Path $Here "refresh_pg_comments.py")
if ($LASTEXITCODE -ne 0) { Write-Host "WARN: comment refresh failed" }

Write-Host "==> seed core data ($((Get-Item (Join-Path $Here 'seed_company.py')).Name) company_eval_v2, may take ~1min)"
& $Py (Join-Path $Here "seed_company.py") --dsn "postgresql://postgres:root@127.0.0.1:5432/postgres"
if ($LASTEXITCODE -ne 0) { throw "seed failed" }

Write-Host "==> seed extended tables (clean, ~10k/fact, may take several minutes)"
& $Py (Join-Path $Here "seed_extended.py") --dsn "postgresql://postgres:root@127.0.0.1:5432/postgres"
if ($LASTEXITCODE -ne 0) { throw "seed_extended failed" }

Write-Host "==> refresh metadata docs (structure + relations)"
& $Py (Join-Path $Here "metadata\gen_db_structure_doc.py")
if ($LASTEXITCODE -ne 0) { Write-Host "WARN: metadata doc refresh failed" }
& $Py (Join-Path $Here "metadata\export_table_relations.py")
if ($LASTEXITCODE -ne 0) { Write-Host "WARN: table relations export failed" }

Write-Host "==> done"
