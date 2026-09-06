-- 0001 extensions, backend role, default grants, storage bucket
-- Run as the Supabase "postgres" role (SUPABASE_DB_URL). Idempotent.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_backend') THEN
    CREATE ROLE app_backend LOGIN NOBYPASSRLS NOINHERIT;
  END IF;
  -- PG15: creator is not auto-member; membership lets tests SET ROLE app_backend
  BEGIN
    EXECUTE format('GRANT app_backend TO %I', current_user);
  EXCEPTION WHEN OTHERS THEN NULL;
  END;
END $$;
-- Password is set by scripts/apply.* from env (never in this file):
--   ALTER ROLE app_backend PASSWORD :'app_backend_password';

GRANT USAGE ON SCHEMA public TO app_backend;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_backend;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_backend;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO app_backend;

-- Private storage bucket (Supabase only; no-op in plain Postgres CI)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'storage' AND table_name = 'buckets') THEN
    INSERT INTO storage.buckets (id, name, public)
    VALUES ('artefacts', 'artefacts', false)
    ON CONFLICT (id) DO NOTHING;
  END IF;
END $$;
