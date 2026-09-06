#!/usr/bin/env bash
# CI / throwaway DB only. Drops schema public and re-applies everything twice (idempotency check), then tests.
#   SUPABASE_DB_URL=postgresql://postgres:postgres@localhost:5432/postgres ./database/scripts/reset_local.sh
set -euo pipefail
cd "$(dirname "$0")"
: "${SUPABASE_DB_URL:?SUPABASE_DB_URL is required}"

case "$SUPABASE_DB_URL" in
  *supabase.co*|*supabase.com*) echo "refusing to reset a hosted Supabase project"; exit 1;;
esac

psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -q -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; DROP SCHEMA IF EXISTS auth CASCADE;"
./apply.sh
./apply.sh   # second pass must be a no-op
./run_tests.sh
