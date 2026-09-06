#!/usr/bin/env bash
# Apply all migrations + seed function to the database in SUPABASE_DB_URL (superuser/postgres role).
# Idempotent: safe to run repeatedly.
#   SUPABASE_DB_URL=postgresql://postgres:...@db.xxx.supabase.co:5432/postgres \
#   APP_BACKEND_PASSWORD=... ./database/scripts/apply.sh
set -euo pipefail
cd "$(dirname "$0")/.."

: "${SUPABASE_DB_URL:?SUPABASE_DB_URL is required (superuser URL, port 5432)}"

for f in migrations/*.sql; do
  echo ">> $f"
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -q -f "$f"
done

echo ">> seeds/seed_demo.sql"
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -q -f seeds/seed_demo.sql

if [[ -n "${APP_BACKEND_PASSWORD:-}" ]]; then
  echo ">> set app_backend password"
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -q -v pw="$APP_BACKEND_PASSWORD" \
    -c "ALTER ROLE app_backend PASSWORD :'pw';"
fi

echo "done."
