-- Constraint tests. Each block must raise the expected SQLSTATE; run with -v ON_ERROR_STOP=1.
-- Whole file runs in one transaction and rolls back.
BEGIN;

INSERT INTO auth.users (id, email) VALUES
  ('00000000-0000-0000-0000-0000000000a1', 'tc_a@test.local');
-- trigger created profiles row

DO $$
DECLARE
  u  uuid := '00000000-0000-0000-0000-0000000000a1';
  c  uuid; c2 uuid; co uuid; art uuid; q uuid; r uuid;
BEGIN
  -- course code too short
  BEGIN
    INSERT INTO courses (owner_id, code, title) VALUES (u, 'X', 'bad');
    RAISE EXCEPTION 'expected check_violation (code length)';
  EXCEPTION WHEN check_violation THEN NULL; END;

  INSERT INTO courses (owner_id, code, title) VALUES (u, 'CSE1', 'one') RETURNING id INTO c;

  -- duplicate live code
  BEGIN
    INSERT INTO courses (owner_id, code, title) VALUES (u, 'CSE1', 'dup');
    RAISE EXCEPTION 'expected unique_violation (owner, code)';
  EXCEPTION WHEN unique_violation THEN NULL; END;

  -- soft-deleted course frees the code
  UPDATE courses SET deleted_at = now() WHERE id = c;
  INSERT INTO courses (owner_id, code, title) VALUES (u, 'CSE1', 'again') RETURNING id INTO c2;

  INSERT INTO course_outcomes (course_id, code, text) VALUES (c2, 'CO1', 'x') RETURNING id INTO co;

  -- co_po_map strength out of range
  BEGIN
    INSERT INTO co_po_map (co_id, po_id, strength)
    SELECT co, id, 4 FROM program_outcomes WHERE code = 'PO1';
    RAISE EXCEPTION 'expected check_violation (strength)';
  EXCEPTION WHEN check_violation THEN NULL; END;

  -- artefact needs storage_path or extracted_text
  BEGIN
    INSERT INTO artefacts (course_id, kind, label) VALUES (c2, 'question_paper', 'none');
    RAISE EXCEPTION 'expected check_violation (artefact source)';
  EXCEPTION WHEN check_violation THEN NULL; END;

  INSERT INTO artefacts (course_id, kind, label, extracted_text, status)
  VALUES (c2, 'question_paper', 'paper', 'q text', 'done') RETURNING id INTO art;

  -- negative marks
  BEGIN
    INSERT INTO questions (artefact_id, number, text, marks) VALUES (art, '1', 't', -1);
    RAISE EXCEPTION 'expected check_violation (marks)';
  EXCEPTION WHEN check_violation THEN NULL; END;

  -- non-normalised question number
  BEGIN
    INSERT INTO questions (artefact_id, number, text, marks) VALUES (art, '2 (B)', 't', 5);
    RAISE EXCEPTION 'expected check_violation (normalize_qnum)';
  EXCEPTION WHEN check_violation THEN NULL; END;

  IF normalize_qnum('Q2 (B)') <> '2b' OR normalize_qnum('3(a)(ii)') <> '3aii' OR normalize_qnum('Q3.') <> '3' THEN
    RAISE EXCEPTION 'normalize_qnum produced unexpected output';
  END IF;

  INSERT INTO questions (artefact_id, number, text, marks) VALUES (art, '2b', 't', 5) RETURNING id INTO q;
  INSERT INTO question_co_map (question_id, co_id, source) VALUES (q, co, 'faculty');

  -- CO referenced by a question cannot be deleted (RESTRICT)
  BEGIN
    DELETE FROM course_outcomes WHERE id = co;
    RAISE EXCEPTION 'expected foreign_key_violation (question_co_map_co_fk)';
  EXCEPTION WHEN foreign_key_violation THEN NULL; END;

  -- marks_rows: score > max
  BEGIN
    INSERT INTO marks_rows (artefact_id, student_anon_id, question_number, score, max_score)
    VALUES (art, 'S1', '1', 11, 10);
    RAISE EXCEPTION 'expected check_violation (score <= max)';
  EXCEPTION WHEN check_violation THEN NULL; END;

  -- marks_rows: non-normalised question_number
  BEGIN
    INSERT INTO marks_rows (artefact_id, student_anon_id, question_number, score, max_score)
    VALUES (art, 'S1', 'Q1.', 5, 10);
    RAISE EXCEPTION 'expected check_violation (marks qnum normalised)';
  EXCEPTION WHEN check_violation THEN NULL; END;

  INSERT INTO runs (course_id, owner_id, module) VALUES (c2, u, 'exam_audit') RETURNING id INTO r;

  -- run_inputs: both artefact and course
  BEGIN
    INSERT INTO run_inputs (run_id, role, artefact_id, course_id) VALUES (r, 'draft', art, c2);
    RAISE EXCEPTION 'expected check_violation (exactly one)';
  EXCEPTION WHEN check_violation THEN NULL; END;

  -- run_inputs: compare_course role with artefact
  BEGIN
    INSERT INTO run_inputs (run_id, role, artefact_id) VALUES (r, 'compare_course', art);
    RAISE EXCEPTION 'expected check_violation (role/course)';
  EXCEPTION WHEN check_violation THEN NULL; END;

  INSERT INTO run_inputs (run_id, role, artefact_id) VALUES (r, 'draft', art);

  -- artefact referenced by run cannot be deleted (RESTRICT)
  BEGIN
    DELETE FROM artefacts WHERE id = art;
    RAISE EXCEPTION 'expected foreign_key_violation (run_inputs_artefact_fk)';
  EXCEPTION WHEN foreign_key_violation THEN NULL; END;

  -- findings: accepted without decided_by
  BEGIN
    INSERT INTO findings (run_id, owner_id, type, title, rationale, status)
    VALUES (r, u, 'coverage_gap', 't', 'r', 'accepted');
    RAISE EXCEPTION 'expected check_violation (decision consistency)';
  EXCEPTION WHEN check_violation THEN NULL; END;

  -- findings: unknown type
  BEGIN
    INSERT INTO findings (run_id, owner_id, type, title, rationale) VALUES (r, u, 'bogus', 't', 'r');
    RAISE EXCEPTION 'expected check_violation (finding type)';
  EXCEPTION WHEN check_violation THEN NULL; END;

  -- attainment_results: pct > 100
  BEGIN
    INSERT INTO attainment_results (run_id, target_kind, target_id, target_code, attained_pct, students, target_pct, met)
    VALUES (r, 'course_outcome', co, 'CO1', 101, 10, 60, true);
    RAISE EXCEPTION 'expected check_violation (attained_pct)';
  EXCEPTION WHEN check_violation THEN NULL; END;

  -- attainment_results: wrong kind
  BEGIN
    INSERT INTO attainment_results (run_id, target_kind, target_id, target_code, attained_pct, students, target_pct, met)
    VALUES (r, 'question', co, 'CO1', 50, 10, 60, false);
    RAISE EXCEPTION 'expected check_violation (target_kind)';
  EXCEPTION WHEN check_violation THEN NULL; END;

  -- updated_at trigger fires on courses (now() is fixed per tx, so back-date created_at first)
  UPDATE courses SET created_at = created_at - interval '1 minute' WHERE id = c2;
  UPDATE courses SET title = 'renamed' WHERE id = c2;
  IF (SELECT updated_at <= created_at FROM courses WHERE id = c2) THEN
    RAISE EXCEPTION 'set_updated_at did not fire on courses';
  END IF;

  -- no updated_at trigger on run_events
  IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at' AND tgrelid = 'public.run_events'::regclass) THEN
    RAISE EXCEPTION 'run_events must not have set_updated_at';
  END IF;

  RAISE NOTICE 'test_constraints: OK';
END $$;

ROLLBACK;
