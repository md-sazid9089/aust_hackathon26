#!/usr/bin/env bash
# Container-side runner used by local validation: apply twice, then tests.
set -euo pipefail
cd /database
export PGUSER=postgres
for pass in 1 2; do
  echo "=== apply pass $pass"
  for f in migrations/*.sql; do
    echo ">> $f"
    psql -v ON_ERROR_STOP=1 -q -f "$f"
  done
  echo ">> seeds/seed_demo.sql"
  psql -v ON_ERROR_STOP=1 -q -f seeds/seed_demo.sql
done
echo "=== tests"
for f in tests/test_constraints.sql tests/test_functions.sql tests/test_rls.sql; do
  echo ">> $f"
  psql -v ON_ERROR_STOP=1 -q -f "$f"
done
echo "ALL_OK"
