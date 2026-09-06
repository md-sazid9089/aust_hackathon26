-- Function tests on seeded fixtures. One transaction; rolls back.
BEGIN;

INSERT INTO auth.users (id, email) VALUES ('00000000-0000-0000-0000-0000000000c1', 'fn_a@test.local');
SELECT set_config('app.role', 'faculty', true);
SELECT set_config('app.user_id', '00000000-0000-0000-0000-0000000000c1', true);

DO $$
DECLARE
  u        uuid := '00000000-0000-0000-0000-0000000000c1';
  c1       uuid; c2 uuid;
  paper25  uuid; marks uuid; draft uuid; p2024 uuid;
  q_draft4 uuid; q_2024_3 uuid; q_other uuid;
  n        int;
  rec      record;
  v_same   vector(1536);
  v_diff   vector(1536);
BEGIN
  -- ---------- seed_demo idempotent ----------
  c1 := seed_demo(u);
  c2 := seed_demo(u);
  IF c1 <> c2 THEN RAISE EXCEPTION 'seed_demo not idempotent'; END IF;
  SELECT count(*) INTO n FROM courses WHERE owner_id = u AND is_demo;
  IF n <> 2 THEN RAISE EXCEPTION 'expected 2 demo courses, got %', n; END IF;
  SELECT count(*) INTO n FROM marks_rows m JOIN artefacts a ON a.id = m.artefact_id WHERE a.course_id = c1;
  IF n <> 280 THEN RAISE EXCEPTION 'expected 280 marks rows, got %', n; END IF;
  SELECT count(*) INTO n FROM grader_scores g JOIN answers an ON an.id = g.answer_id JOIN artefacts a ON a.id = an.artefact_id WHERE a.course_id = c1;
  IF n <> 48 THEN RAISE EXCEPTION 'expected 48 grader scores, got %', n; END IF;

  -- draft paper sums to 90 vs declared 100 (marks_total_mismatch input)
  SELECT id INTO draft FROM artefacts WHERE course_id = c1 AND kind = 'question_paper' AND year = 2026;
  SELECT sum(marks)::int INTO n FROM questions WHERE artefact_id = draft;
  IF n <> 90 THEN RAISE EXCEPTION 'draft should sum to 90, got %', n; END IF;

  -- ---------- compute_co_attainment ----------
  SELECT id INTO paper25 FROM artefacts WHERE course_id = c1 AND kind = 'question_paper' AND year = 2025;
  SELECT id INTO marks   FROM artefacts WHERE course_id = c1 AND kind = 'marks_sheet';

  FOR rec IN SELECT * FROM compute_co_attainment(gen_random_uuid(), marks, paper25, 60) LOOP
    IF rec.unmatched_numbers <> '{}'::text[] THEN
      RAISE EXCEPTION 'unexpected unmatched numbers: %', rec.unmatched_numbers;
    END IF;
    IF rec.students <> 40 THEN
      RAISE EXCEPTION 'CO % students should be 40, got %', rec.co_code, rec.students;
    END IF;
    -- Q3 formula 2+((i*7)%9) in 2..10 over 15 marks; >=9 (60%) for i*7%9 in {7,8}: 9 of 40 students -> 22.5 %
    IF rec.co_code = 'CO3' AND rec.attained_pct <> 22.50 THEN
      RAISE EXCEPTION 'CO3 attained_pct expected 22.50, got %', rec.attained_pct;
    END IF;
    -- Q1 10-(i%4) in 7..10, all >= 6 -> 100 %
    IF rec.co_code = 'CO1' AND rec.attained_pct <> 100.00 THEN
      RAISE EXCEPTION 'CO1 attained_pct expected 100, got %', rec.attained_pct;
    END IF;
    -- CO5 = Q5 (15-(i%4) in 12..15) + Q6 (10-(i%3) in 8..10): min 20/25 = 80 % -> 100 %
    IF rec.co_code = 'CO5' AND rec.attained_pct <> 100.00 THEN
      RAISE EXCEPTION 'CO5 attained_pct expected 100, got %', rec.attained_pct;
    END IF;
  END LOOP;

  -- unmatched detection: a stray marks row
  INSERT INTO marks_rows (artefact_id, student_anon_id, question_number, score, max_score) VALUES (marks, 'S001', '9', 1, 5);
  SELECT unmatched_numbers INTO rec FROM compute_co_attainment(gen_random_uuid(), marks, paper25, 60) LIMIT 1;
  IF rec.unmatched_numbers <> ARRAY['9'] THEN
    RAISE EXCEPTION 'expected unmatched {9}, got %', rec.unmatched_numbers;
  END IF;
  DELETE FROM marks_rows WHERE artefact_id = marks AND question_number = '9';

  -- ---------- similar_questions with stubbed embeddings ----------
  v_same := (ARRAY[1::real] || array_fill(0::real, ARRAY[1535]))::vector;
  v_diff := (ARRAY[0::real, 1::real] || array_fill(0::real, ARRAY[1534]))::vector;

  SELECT id INTO p2024 FROM artefacts WHERE course_id = c1 AND kind = 'question_paper' AND year = 2024;
  SELECT id INTO q_draft4 FROM questions WHERE artefact_id = draft AND number = '4';
  SELECT id INTO q_2024_3 FROM questions WHERE artefact_id = p2024 AND number = '3';
  SELECT id INTO q_other  FROM questions WHERE artefact_id = p2024 AND number = '1';

  UPDATE questions SET embedding = v_same, embedding_model = 'stub' WHERE id IN (q_draft4, q_2024_3);
  UPDATE questions SET embedding = v_diff, embedding_model = 'stub' WHERE id = q_other;

  SELECT question_id, similarity INTO rec FROM similar_questions(q_draft4, c1, 3, 0.8) LIMIT 1;
  IF rec.question_id IS DISTINCT FROM q_2024_3 THEN
    RAISE EXCEPTION 'similar_questions should rank 2024 Q3 first';
  END IF;
  IF rec.similarity < 0.99 THEN RAISE EXCEPTION 'similarity should be ~1, got %', rec.similarity; END IF;

  -- embedding_model mismatch is ignored
  UPDATE questions SET embedding_model = 'other' WHERE id = q_2024_3;
  SELECT count(*) INTO n FROM similar_questions(q_draft4, c1, 3, 0.8);
  IF n <> 0 THEN RAISE EXCEPTION 'similar_questions must skip rows with different embedding_model'; END IF;

  -- ---------- reset_demo ----------
  SELECT reset_demo(u) INTO n;
  IF n <> 2 THEN RAISE EXCEPTION 'reset_demo should remove 2 courses, removed %', n; END IF;
  SELECT count(*) INTO n FROM courses WHERE owner_id = u;
  IF n <> 0 THEN RAISE EXCEPTION 'courses remain after reset'; END IF;

  RAISE NOTICE 'test_functions: OK';
END $$;

ROLLBACK;
