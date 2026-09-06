-- Promote an existing user to admin. Usage:
--   psql "$SUPABASE_DB_URL" -v email='you@aust.edu' -f database/seeds/seed_admin.sql
-- The user must have signed in at least once (profiles row exists).

UPDATE public.profiles
   SET role = 'admin', is_active = true
 WHERE email = :'email';

SELECT id, email, role FROM public.profiles WHERE email = :'email';
