#!/usr/bin/env bash
# Run SQL tests (each file is a self-contained transaction that rolls back).
set -euo pipefail
cd "$(dirname "$0")/.."
: "${SUPABASE_DB_URL:?SUPABASE_DB_URL is required}"

for f in tests/test_constraints.sql tests/test_functions.sql tests/test_rls.sql; do
  echo ">> $f"
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -q -f "$f"
done
echo "all tests passed."
