-- 0011 functions & triggers (architecture.md §21.3). All SECURITY INVOKER.

-- ---------- updated_at ----------
CREATE OR REPLACE FUNCTION public.set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END $$;

DO $$
DECLARE t text;
BEGIN
  -- explicit list: never on append-only tables
  FOREACH t IN ARRAY ARRAY[
    'profiles','courses','program_outcomes','course_outcomes','topics',
    'artefacts','questions','rubric_criteria','answers','runs','findings'] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS set_updated_at ON public.%I', t);
    EXECUTE format('CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()', t);
  END LOOP;
END $$;

-- ---------- vector similarity ----------
-- Nearest questions from OTHER question papers of the same course.
CREATE OR REPLACE FUNCTION public.similar_questions(
  p_question uuid, p_course uuid, p_k int DEFAULT 5, p_min_sim numeric DEFAULT 0.80)
RETURNS TABLE(question_id uuid, artefact_id uuid, similarity numeric)
LANGUAGE sql STABLE SECURITY INVOKER
SET hnsw.ef_search = 40
AS $$
  WITH src AS (
    SELECT q.embedding, q.embedding_model, q.artefact_id
    FROM public.questions q
    WHERE q.id = p_question AND q.embedding IS NOT NULL
  )
  SELECT q.id, q.artefact_id, round((1 - (q.embedding <=> s.embedding))::numeric, 4)
  FROM public.questions q
  JOIN public.artefacts a ON a.id = q.artefact_id
  CROSS JOIN src s
  WHERE a.course_id = p_course
    AND a.kind = 'question_paper'
    AND q.artefact_id <> s.artefact_id
    AND q.embedding IS NOT NULL
    AND q.embedding_model IS NOT DISTINCT FROM s.embedding_model
    AND (1 - (q.embedding <=> s.embedding)) >= p_min_sim
  ORDER BY q.embedding <=> s.embedding
  LIMIT p_k
$$;

-- Nearest topics in comparison courses (caller's RLS limits visible courses).
CREATE OR REPLACE FUNCTION public.similar_topics(
  p_topic uuid, p_course_ids uuid[], p_k int DEFAULT 5, p_min_sim numeric DEFAULT 0.75)
RETURNS TABLE(topic_id uuid, course_id uuid, similarity numeric)
LANGUAGE sql STABLE SECURITY INVOKER
SET hnsw.ef_search = 40
AS $$
  WITH src AS (
    SELECT t.embedding, t.embedding_model, t.course_id
    FROM public.topics t
    WHERE t.id = p_topic AND t.embedding IS NOT NULL
  )
  SELECT t.id, t.course_id, round((1 - (t.embedding <=> s.embedding))::numeric, 4)
  FROM public.topics t
  CROSS JOIN src s
  WHERE t.course_id = ANY (p_course_ids)
    AND t.course_id <> s.course_id
    AND t.embedding IS NOT NULL
    AND t.embedding_model IS NOT DISTINCT FROM s.embedding_model
    AND (1 - (t.embedding <=> s.embedding)) >= p_min_sim
  ORDER BY t.embedding <=> s.embedding
  LIMIT p_k
$$;

-- ---------- deterministic attainment ----------
-- Per CO: % of students whose summed score on CO-mapped questions >= threshold% of summed max.
-- students = 0 means the CO has no mapped questions with marks (treat as "not assessed").
-- unmatched_numbers: marks_rows.question_number values with no question in the paper (same on every row).
CREATE OR REPLACE FUNCTION public.compute_co_attainment(
  p_run uuid, p_marks_artefact uuid, p_paper_artefact uuid, p_threshold numeric DEFAULT 60)
RETURNS TABLE(co_id uuid, co_code text, attained_pct numeric, students int, unmatched_numbers text[])
LANGUAGE sql STABLE SECURITY INVOKER
AS $$
  WITH marks AS (
    SELECT m.student_anon_id, m.question_number, m.score, m.max_score
    FROM public.marks_rows m
    WHERE m.artefact_id = p_marks_artefact
  ),
  qs AS (
    SELECT q.id, q.number
    FROM public.questions q
    WHERE q.artefact_id = p_paper_artefact
  ),
  unmatched AS (
    SELECT COALESCE(array_agg(DISTINCT m.question_number ORDER BY m.question_number), '{}'::text[]) AS nums
    FROM marks m
    LEFT JOIN qs ON qs.number = m.question_number
    WHERE qs.id IS NULL
  ),
  matched AS (
    SELECT m.student_anon_id, qs.id AS question_id, m.score, m.max_score
    FROM marks m
    JOIN qs ON qs.number = m.question_number
  ),
  per_student_co AS (
    SELECT qc.co_id, mt.student_anon_id, SUM(mt.score) AS got, SUM(mt.max_score) AS mx
    FROM matched mt
    JOIN public.question_co_map qc ON qc.question_id = mt.question_id
    GROUP BY qc.co_id, mt.student_anon_id
  ),
  agg AS (
    SELECT co_id,
           COUNT(*)::int AS students,
           COUNT(*) FILTER (WHERE mx > 0 AND got * 100 / mx >= p_threshold)::int AS attained
    FROM per_student_co
    GROUP BY co_id
  )
  SELECT co.id,
         co.code,
         CASE WHEN COALESCE(a.students, 0) > 0
              THEN round(a.attained::numeric * 100 / a.students, 2)
              ELSE 0::numeric END,
         COALESCE(a.students, 0),
         (SELECT nums FROM unmatched)
  FROM public.course_outcomes co
  JOIN public.artefacts pa ON pa.id = p_paper_artefact AND pa.course_id = co.course_id
  LEFT JOIN agg a ON a.co_id = co.id
  ORDER BY co.sort_order, co.code
$$;

-- ---------- demo lifecycle ----------
CREATE OR REPLACE FUNCTION public.assert_owner_or_admin(p_owner uuid) RETURNS void
LANGUAGE plpgsql STABLE AS $$
BEGIN
  IF p_owner IS DISTINCT FROM public.current_app_user() AND NOT public.is_admin() THEN
    RAISE EXCEPTION 'not allowed to act for owner %', p_owner USING ERRCODE = '42501';
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.reset_demo(p_owner uuid) RETURNS int
LANGUAGE plpgsql SECURITY INVOKER AS $$
DECLARE n int;
BEGIN
  PERFORM public.assert_owner_or_admin(p_owner);
  -- admin acts on another user's rows: RLS write policies require ownership,
  -- so temporarily adopt the owner's identity within this transaction
  IF public.is_admin() THEN
    PERFORM set_config('app.user_id', p_owner::text, true);
  END IF;
  DELETE FROM public.courses WHERE owner_id = p_owner AND is_demo;
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END $$;

-- seed_demo(p_owner uuid) RETURNS uuid is defined in seeds/seed_demo.sql (applied after 0012).
