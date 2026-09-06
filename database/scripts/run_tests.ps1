# Run SQL tests (Windows). Each file is one transaction that rolls back.
$ErrorActionPreference = "Stop"
if (-not $env:SUPABASE_DB_URL) { throw "SUPABASE_DB_URL is required" }
Push-Location (Join-Path $PSScriptRoot "..")
try {
  foreach ($f in @("tests\test_constraints.sql", "tests\test_functions.sql", "tests\test_rls.sql")) {
    Write-Host ">> $f"
    psql $env:SUPABASE_DB_URL -v ON_ERROR_STOP=1 -q -f $f
    if ($LASTEXITCODE -ne 0) { throw "failed: $f" }
  }
  Write-Host "all tests passed."
} finally { Pop-Location }
