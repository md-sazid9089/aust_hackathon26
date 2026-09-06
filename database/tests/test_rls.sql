-- RLS tests. Runs as app_backend (via SET ROLE) inside one transaction; rolls back.
-- Requires the migrating role to be a member of app_backend (granted in 0001).
BEGIN;

INSERT INTO auth.users (id, email) VALUES
  ('00000000-0000-0000-0000-0000000000b1', 'rls_a@test.local'),
  ('00000000-0000-0000-0000-0000000000b2', 'rls_b@test.local'),
  ('00000000-0000-0000-0000-0000000000b9', 'rls_admin@test.local');
UPDATE profiles SET role = 'admin' WHERE id = '00000000-0000-0000-0000-0000000000b9';

-- Seed both users' demo data as superuser (bypasses RLS) but with identity set so seed_demo's guard passes
SELECT set_config('app.role', 'faculty', true);
SELECT set_config('app.user_id', '00000000-0000-0000-0000-0000000000b1', true);
SELECT seed_demo('00000000-0000-0000-0000-0000000000b1');
SELECT set_config('app.user_id', '00000000-0000-0000-0000-0000000000b2', true);
SELECT seed_demo('00000000-0000-0000-0000-0000000000b2');

SET ROLE app_backend;

DO $$
DECLARE
  ua  uuid := '00000000-0000-0000-0000-0000000000b1';
  ub  uuid := '00000000-0000-0000-0000-0000000000b2';
  n   int;
  cb  uuid;
  fb  uuid;
  ca  uuid;
  qa  uuid;
BEGIN
  -- ---------- no identity: everything hidden ----------
  PERFORM set_config('app.user_id', '', true);
  PERFORM set_config('app.role', '', true);
  SELECT count(*) INTO n FROM courses;
  IF n <> 0 THEN RAISE EXCEPTION 'unset app.user_id must see 0 courses, saw %', n; END IF;
  SELECT count(*) INTO n FROM questions;
  IF n <> 0 THEN RAISE EXCEPTION 'unset app.user_id must see 0 questions, saw %', n; END IF;

  -- ---------- A sees own, not B's ----------
  PERFORM set_config('app.user_id', ua::text, true);
  PERFORM set_config('app.role', 'faculty', true);
  SELECT count(*) INTO n FROM courses WHERE owner_id = ua;
  IF n <> 2 THEN RAISE EXCEPTION 'A must see 2 own courses, saw %', n; END IF;
  SELECT count(*) INTO n FROM courses WHERE owner_id = ub;
  IF n <> 0 THEN RAISE EXCEPTION 'A must see 0 of B courses, saw %', n; END IF;

  -- B's children invisible to A across every child level
  PERFORM set_config('app.user_id', ub::text, true);
  SELECT id INTO cb FROM courses WHERE owner_id = ub AND code = 'CSE2201';
  PERFORM set_config('app.user_id', ua::text, true);

  SELECT count(*) INTO n FROM artefacts WHERE course_id = cb;
  IF n <> 0 THEN RAISE EXCEPTION 'A sees B artefacts (%)', n; END IF;
  SELECT count(*) INTO n FROM questions q JOIN artefacts a ON a.id = q.artefact_id WHERE a.course_id = cb;
  IF n <> 0 THEN RAISE EXCEPTION 'A sees B questions (%)', n; END IF;
  SELECT count(*) INTO n FROM marks_rows m JOIN artefacts a ON a.id = m.artefact_id WHERE a.course_id = cb;
  IF n <> 0 THEN RAISE EXCEPTION 'A sees B marks (%)', n; END IF;
  SELECT count(*) INTO n FROM course_outcomes WHERE course_id = cb;
  IF n <> 0 THEN RAISE EXCEPTION 'A sees B outcomes (%)', n; END IF;

  -- A cannot write into B's course (WITH CHECK)
  BEGIN
    INSERT INTO course_outcomes (course_id, code, text) VALUES (cb, 'CO9', 'sneak');
    RAISE EXCEPTION 'A inserted into B course';
  EXCEPTION WHEN insufficient_privilege THEN NULL; END;

  -- A cannot reset B's demo
  BEGIN
    PERFORM reset_demo(ub);
    RAISE EXCEPTION 'A reset B demo';
  EXCEPTION WHEN insufficient_privilege THEN NULL; END;

  -- similar_questions over B's course returns nothing (not an error)
  SELECT count(*) INTO n FROM similar_questions(gen_random_uuid(), cb, 5, 0.0);
  IF n <> 0 THEN RAISE EXCEPTION 'similar_questions leaked B rows'; END IF;

  -- ---------- runs / findings ----------
  SELECT id INTO ca FROM courses WHERE owner_id = ua AND code = 'CSE2201';
  INSERT INTO runs (course_id, owner_id, module) VALUES (ca, ua, 'exam_audit') RETURNING id INTO qa;
  INSERT INTO findings (run_id, owner_id, type, title, rationale) VALUES (qa, ua, 'coverage_gap', 't', 'r') RETURNING id INTO fb;

  -- A cannot forge a run owned by B
  BEGIN
    INSERT INTO runs (course_id, owner_id, module) VALUES (ca, ub, 'exam_audit');
    RAISE EXCEPTION 'A forged run for B';
  EXCEPTION WHEN insufficient_privilege THEN NULL; END;

  PERFORM set_config('app.user_id', ub::text, true);
  SELECT count(*) INTO n FROM findings WHERE id = fb;
  IF n <> 0 THEN RAISE EXCEPTION 'B sees A finding'; END IF;
  SELECT count(*) INTO n FROM run_events WHERE run_id = qa;
  IF n <> 0 THEN RAISE EXCEPTION 'B sees A run_events'; END IF;

  -- ---------- soft delete hides children ----------
  PERFORM set_config('app.user_id', ua::text, true);
  UPDATE courses SET deleted_at = now() WHERE id = ca;
  SELECT count(*) INTO n FROM artefacts WHERE course_id = ca;
  IF n <> 0 THEN RAISE EXCEPTION 'soft-deleted course children still visible to owner (%)', n; END IF;
  SELECT count(*) INTO n FROM course_outcomes WHERE course_id = ca;
  IF n <> 0 THEN RAISE EXCEPTION 'soft-deleted course outcomes still visible (%)', n; END IF;

  -- ---------- admin: read all, cannot mutate findings ----------
  PERFORM set_config('app.user_id', '00000000-0000-0000-0000-0000000000b9', true);
  PERFORM set_config('app.role', 'admin', true);
  SELECT count(*) INTO n FROM courses WHERE owner_id IN (ua, ub);
  IF n <> 4 THEN RAISE EXCEPTION 'admin must see all 4 courses (incl. soft-deleted), saw %', n; END IF;
  SELECT count(*) INTO n FROM artefacts WHERE course_id = ca;
  IF n = 0 THEN RAISE EXCEPTION 'admin must still see soft-deleted course children'; END IF;

  UPDATE findings SET status = 'accepted', decided_by = '00000000-0000-0000-0000-0000000000b9', decided_at = now() WHERE id = fb;
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 0 THEN RAISE EXCEPTION 'admin updated a finding (SEC-009)'; END IF;

  -- admin may deactivate a user
  UPDATE profiles SET is_active = false WHERE id = ub;
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 1 THEN RAISE EXCEPTION 'admin could not update profiles'; END IF;

  -- admin reset of another user's demo is allowed
  SELECT reset_demo(ub) INTO n;
  IF n <> 2 THEN RAISE EXCEPTION 'admin reset_demo should delete 2 demo courses, deleted %', n; END IF;

  -- views apply RLS of caller
  SELECT count(*) INTO n FROM v_admin_department_attainment;  -- may be 0, must not error

  RAISE NOTICE 'test_rls: OK';
END $$;

RESET ROLE;
ROLLBACK;
