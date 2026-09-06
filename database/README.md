# database/

Schema, RLS, functions, views, seeds and SQL tests for the Faculty Copilot. Spec: `architecture.md` §20–23; plan: `database_implementation_plan.md`.

## Apply (hosted Supabase)

```powershell
$env:SUPABASE_DB_URL = "postgresql://postgres:<pw>@db.<ref>.supabase.co:5432/postgres"   # superuser URL, NOT the pooler
$env:APP_BACKEND_PASSWORD = "<choose>"                                                  # first run only
.\database\scripts\apply.ps1          # or: ./database/scripts/apply.sh
```

Then the backend connects as `app_backend` through the pooler:
`DATABASE_URL=postgresql+asyncpg://app_backend:<pw>@db.<ref>.supabase.co:6543/postgres`

Make yourself admin after first sign-in:
`psql $env:SUPABASE_DB_URL -v email='you@aust.edu' -f database/seeds/seed_admin.sql`

## Test

```powershell
.\database\scripts\run_tests.ps1      # constraints, functions, RLS — each rolls back
```

CI (throwaway Postgres with pgvector): `SUPABASE_DB_URL=postgresql://postgres:postgres@localhost:5432/postgres ./database/scripts/reset_local.sh`

## Rules

- Migrations are forward-only and idempotent; never edit an applied file — add `0013_*.sql`.
- Backend must start every transaction with `SET LOCAL app.user_id = '<uuid>'; SET LOCAL app.role = 'faculty'|'admin';`. Unset ⇒ RLS returns nothing.
- `seed_demo(owner)` / `reset_demo(owner)` assert caller is owner or admin; when called by an admin they switch `app.user_id` to the owner for the rest of the transaction — call them in their own transaction.
- Question numbers must be normalised with the same rule as `normalize_qnum()` before insert (`"Q2 (B)" → "2b"`); the CHECK rejects anything else.
- `seed_demo()` inserts fully structured demo rows (`status='done'`), so the demo never depends on LLM extraction. `seeds/fixtures/*` mirror that content for the upload path and for `POST /demo/seed` to push bytes to Storage.
