# Apply all migrations + seed function (Windows). Idempotent.
#   $env:SUPABASE_DB_URL = "postgresql://postgres:...@db.xxx.supabase.co:5432/postgres"
#   $env:APP_BACKEND_PASSWORD = "..."   # optional
#   .\database\scripts\apply.ps1
$ErrorActionPreference = "Stop"
if (-not $env:SUPABASE_DB_URL) { throw "SUPABASE_DB_URL is required (superuser URL, port 5432)" }

Push-Location (Join-Path $PSScriptRoot "..")
try {
  Get-ChildItem migrations\*.sql | Sort-Object Name | ForEach-Object {
    Write-Host ">> $($_.Name)"
    psql $env:SUPABASE_DB_URL -v ON_ERROR_STOP=1 -q -f $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "failed: $($_.Name)" }
  }
  Write-Host ">> seeds\seed_demo.sql"
  psql $env:SUPABASE_DB_URL -v ON_ERROR_STOP=1 -q -f seeds\seed_demo.sql
  if ($LASTEXITCODE -ne 0) { throw "failed: seed_demo.sql" }

  if ($env:APP_BACKEND_PASSWORD) {
    Write-Host ">> set app_backend password"
    psql $env:SUPABASE_DB_URL -v ON_ERROR_STOP=1 -q -v "pw=$env:APP_BACKEND_PASSWORD" -c "ALTER ROLE app_backend PASSWORD :'pw';"
    if ($LASTEXITCODE -ne 0) { throw "failed: set password" }
  }
  Write-Host "done."
} finally { Pop-Location }
