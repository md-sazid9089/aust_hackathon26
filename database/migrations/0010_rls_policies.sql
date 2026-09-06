-- 0010 Row-Level Security. Backend sets per transaction:
--   SET LOCAL app.user_id = '<uuid>'; SET LOCAL app.role = 'faculty'|'admin';
-- Unset -> current_app_user() IS NULL -> every owner predicate false (fail closed).
-- Admin: SELECT everywhere, writes only on profiles/program_outcomes (SEC-009).

-- ---------- helpers (SECURITY INVOKER; RLS applies inside) ----------
CREATE OR REPLACE FUNCTION public.current_app_user() RETURNS uuid
LANGUAGE sql STABLE AS $$ SELECT nullif(current_setting('app.user_id', true), '')::uuid $$;

CREATE OR REPLACE FUNCTION public.is_admin() RETURNS boolean
LANGUAGE sql STABLE AS $$ SELECT current_setting('app.role', true) = 'admin' $$;

-- NULL for soft-deleted courses so every child table hides with the parent
CREATE OR REPLACE FUNCTION public.course_owner(p_course uuid) RETURNS uuid
LANGUAGE sql STABLE AS $$ SELECT owner_id FROM public.courses WHERE id = p_course AND deleted_at IS NULL $$;

CREATE OR REPLACE FUNCTION public.artefact_owner(p_artefact uuid) RETURNS uuid
LANGUAGE sql STABLE AS $$ SELECT public.course_owner(course_id) FROM public.artefacts WHERE id = p_artefact $$;

CREATE OR REPLACE FUNCTION public.question_owner(p_question uuid) RETURNS uuid
LANGUAGE sql STABLE AS $$ SELECT public.artefact_owner(artefact_id) FROM public.questions WHERE id = p_question $$;

CREATE OR REPLACE FUNCTION public.answer_owner(p_answer uuid) RETURNS uuid
LANGUAGE sql STABLE AS $$ SELECT public.artefact_owner(artefact_id) FROM public.answers WHERE id = p_answer $$;

CREATE OR REPLACE FUNCTION public.co_owner(p_co uuid) RETURNS uuid
LANGUAGE sql STABLE AS $$ SELECT public.course_owner(course_id) FROM public.course_outcomes WHERE id = p_co $$;

CREATE OR REPLACE FUNCTION public.run_owner(p_run uuid) RETURNS uuid
LANGUAGE sql STABLE AS $$ SELECT owner_id FROM public.runs WHERE id = p_run $$;

-- ---------- enable RLS on every table ----------
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'profiles','courses','program_outcomes','course_outcomes','co_po_map','topics',
    'artefacts','questions','question_co_map','question_topic_map',
    'marks_rows','rubric_criteria','answers','grader_scores',
    'runs','run_inputs','run_events','findings',
    'attainment_results','answer_prescores','usage_logs'] LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
  END LOOP;
END $$;

-- ---------- profiles ----------
DROP POLICY IF EXISTS profiles_select ON public.profiles;
CREATE POLICY profiles_select ON public.profiles FOR SELECT
  USING (id = public.current_app_user() OR public.is_admin());
DROP POLICY IF EXISTS profiles_insert_self ON public.profiles;
CREATE POLICY profiles_insert_self ON public.profiles FOR INSERT
  WITH CHECK (id = public.current_app_user());
DROP POLICY IF EXISTS profiles_update_admin ON public.profiles;
CREATE POLICY profiles_update_admin ON public.profiles FOR UPDATE
  USING (public.is_admin()) WITH CHECK (public.is_admin());

-- ---------- courses ----------
DROP POLICY IF EXISTS courses_select ON public.courses;
CREATE POLICY courses_select ON public.courses FOR SELECT
  USING ((owner_id = public.current_app_user() AND deleted_at IS NULL) OR public.is_admin());
DROP POLICY IF EXISTS courses_write ON public.courses;
CREATE POLICY courses_write ON public.courses FOR ALL
  USING (owner_id = public.current_app_user())
  WITH CHECK (owner_id = public.current_app_user());

-- ---------- program_outcomes ----------
DROP POLICY IF EXISTS program_outcomes_select ON public.program_outcomes;
CREATE POLICY program_outcomes_select ON public.program_outcomes FOR SELECT USING (true);
DROP POLICY IF EXISTS program_outcomes_write_admin ON public.program_outcomes;
CREATE POLICY program_outcomes_write_admin ON public.program_outcomes FOR ALL
  USING (public.is_admin()) WITH CHECK (public.is_admin());

-- ---------- course children: course_id column ----------
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['course_outcomes','topics','artefacts'] LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t || '_select', t);
    EXECUTE format('CREATE POLICY %I ON public.%I FOR SELECT USING (public.course_owner(course_id) = public.current_app_user() OR public.is_admin())', t || '_select', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t || '_write', t);
    EXECUTE format('CREATE POLICY %I ON public.%I FOR ALL USING (public.course_owner(course_id) = public.current_app_user()) WITH CHECK (public.course_owner(course_id) = public.current_app_user())', t || '_write', t);
  END LOOP;
END $$;

-- ---------- co_po_map: via course_outcomes ----------
DROP POLICY IF EXISTS co_po_map_select ON public.co_po_map;
CREATE POLICY co_po_map_select ON public.co_po_map FOR SELECT
  USING (public.co_owner(co_id) = public.current_app_user() OR public.is_admin());
DROP POLICY IF EXISTS co_po_map_write ON public.co_po_map;
CREATE POLICY co_po_map_write ON public.co_po_map FOR ALL
  USING (public.co_owner(co_id) = public.current_app_user())
  WITH CHECK (public.co_owner(co_id) = public.current_app_user());

-- ---------- artefact children: artefact_id column ----------
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['questions','marks_rows','rubric_criteria','answers'] LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t || '_select', t);
    EXECUTE format('CREATE POLICY %I ON public.%I FOR SELECT USING (public.artefact_owner(artefact_id) = public.current_app_user() OR public.is_admin())', t || '_select', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t || '_write', t);
    EXECUTE format('CREATE POLICY %I ON public.%I FOR ALL USING (public.artefact_owner(artefact_id) = public.current_app_user()) WITH CHECK (public.artefact_owner(artefact_id) = public.current_app_user())', t || '_write', t);
  END LOOP;
END $$;

-- ---------- question children ----------
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['question_co_map','question_topic_map'] LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t || '_select', t);
    EXECUTE format('CREATE POLICY %I ON public.%I FOR SELECT USING (public.question_owner(question_id) = public.current_app_user() OR public.is_admin())', t || '_select', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t || '_write', t);
    EXECUTE format('CREATE POLICY %I ON public.%I FOR ALL USING (public.question_owner(question_id) = public.current_app_user()) WITH CHECK (public.question_owner(question_id) = public.current_app_user())', t || '_write', t);
  END LOOP;
END $$;

-- ---------- grader_scores: via answers ----------
DROP POLICY IF EXISTS grader_scores_select ON public.grader_scores;
CREATE POLICY grader_scores_select ON public.grader_scores FOR SELECT
  USING (public.answer_owner(answer_id) = public.current_app_user() OR public.is_admin());
DROP POLICY IF EXISTS grader_scores_write ON public.grader_scores;
CREATE POLICY grader_scores_write ON public.grader_scores FOR ALL
  USING (public.answer_owner(answer_id) = public.current_app_user())
  WITH CHECK (public.answer_owner(answer_id) = public.current_app_user());

-- ---------- runs / findings: denormalised owner_id ----------
DROP POLICY IF EXISTS runs_select ON public.runs;
CREATE POLICY runs_select ON public.runs FOR SELECT
  USING (owner_id = public.current_app_user() OR public.is_admin());
DROP POLICY IF EXISTS runs_write ON public.runs;
CREATE POLICY runs_write ON public.runs FOR ALL
  USING (owner_id = public.current_app_user())
  WITH CHECK (owner_id = public.current_app_user() AND public.course_owner(course_id) = public.current_app_user());

DROP POLICY IF EXISTS findings_select ON public.findings;
CREATE POLICY findings_select ON public.findings FOR SELECT
  USING (owner_id = public.current_app_user() OR public.is_admin());
DROP POLICY IF EXISTS findings_write ON public.findings;
CREATE POLICY findings_write ON public.findings FOR ALL
  USING (owner_id = public.current_app_user())
  WITH CHECK (owner_id = public.current_app_user() AND public.run_owner(run_id) = public.current_app_user());

-- ---------- run children: run_id column ----------
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['run_inputs','run_events','attainment_results','answer_prescores'] LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t || '_select', t);
    EXECUTE format('CREATE POLICY %I ON public.%I FOR SELECT USING (public.run_owner(run_id) = public.current_app_user() OR public.is_admin())', t || '_select', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t || '_write', t);
    EXECUTE format('CREATE POLICY %I ON public.%I FOR ALL USING (public.run_owner(run_id) = public.current_app_user()) WITH CHECK (public.run_owner(run_id) = public.current_app_user())', t || '_write', t);
  END LOOP;
END $$;

-- ---------- usage_logs ----------
DROP POLICY IF EXISTS usage_logs_select ON public.usage_logs;
CREATE POLICY usage_logs_select ON public.usage_logs FOR SELECT
  USING (user_id = public.current_app_user() OR public.is_admin());
DROP POLICY IF EXISTS usage_logs_insert ON public.usage_logs;
CREATE POLICY usage_logs_insert ON public.usage_logs FOR INSERT
  WITH CHECK (user_id = public.current_app_user());
