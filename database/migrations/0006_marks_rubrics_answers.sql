-- 0006 P4/P2 data: marks_rows, rubric_criteria, answers, grader_scores

CREATE TABLE IF NOT EXISTS public.marks_rows (
  id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  artefact_id      uuid NOT NULL REFERENCES public.artefacts(id) ON DELETE CASCADE,
  student_anon_id  text NOT NULL,
  question_number  text NOT NULL,
  score            numeric(6,2) NOT NULL,
  max_score        numeric(6,2) NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT marks_rows_uniq UNIQUE (artefact_id, student_anon_id, question_number),
  CONSTRAINT marks_rows_score_check CHECK (score >= 0),
  CONSTRAINT marks_rows_max_check CHECK (max_score > 0),
  CONSTRAINT marks_rows_score_le_max_check CHECK (score <= max_score),
  CONSTRAINT marks_rows_qnum_normalized_check CHECK (question_number = public.normalize_qnum(question_number))
);

CREATE TABLE IF NOT EXISTS public.rubric_criteria (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  artefact_id  uuid NOT NULL REFERENCES public.artefacts(id) ON DELETE CASCADE,
  code         text NOT NULL,
  text         text NOT NULL,
  max_score    numeric(6,2) NOT NULL,
  levels       jsonb NOT NULL DEFAULT '[]'::jsonb,
  sort_order   int NOT NULL DEFAULT 0,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT rubric_criteria_artefact_code_key UNIQUE (artefact_id, code),
  CONSTRAINT rubric_criteria_max_check CHECK (max_score > 0),
  CONSTRAINT rubric_criteria_levels_array_check CHECK (jsonb_typeof(levels) = 'array')
);

CREATE TABLE IF NOT EXISTS public.answers (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  artefact_id      uuid NOT NULL REFERENCES public.artefacts(id) ON DELETE CASCADE,
  student_anon_id  text NOT NULL,
  question_ref     text,
  text             text NOT NULL,
  sort_order       int NOT NULL DEFAULT 0,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);
-- NULL question_ref must still collide, hence expression index instead of UNIQUE constraint
CREATE UNIQUE INDEX IF NOT EXISTS answers_artefact_student_qref_uniq
  ON public.answers (artefact_id, student_anon_id, COALESCE(question_ref, ''));

CREATE TABLE IF NOT EXISTS public.grader_scores (
  answer_id       uuid NOT NULL REFERENCES public.answers(id) ON DELETE CASCADE,
  grader_label    text NOT NULL,
  criterion_code  text NOT NULL,
  score           numeric(6,2) NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (answer_id, grader_label, criterion_code),
  CONSTRAINT grader_scores_score_check CHECK (score >= 0)
);
