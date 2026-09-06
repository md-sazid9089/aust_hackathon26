-- 0008 attainment_results, answer_prescores, usage_logs

CREATE TABLE IF NOT EXISTS public.attainment_results (
  run_id        uuid NOT NULL REFERENCES public.runs(id) ON DELETE CASCADE,
  target_kind   target_kind NOT NULL,
  target_id     uuid NOT NULL,
  target_code   text NOT NULL,
  attained_pct  numeric(5,2) NOT NULL,
  students      int NOT NULL,
  target_pct    numeric(5,2) NOT NULL,
  met           boolean NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (run_id, target_kind, target_id),
  CONSTRAINT attainment_results_kind_check CHECK (target_kind IN ('course_outcome','program_outcome')),
  CONSTRAINT attainment_results_pct_check CHECK (attained_pct BETWEEN 0 AND 100),
  CONSTRAINT attainment_results_students_check CHECK (students >= 0)
);

CREATE TABLE IF NOT EXISTS public.answer_prescores (
  run_id          uuid NOT NULL REFERENCES public.runs(id) ON DELETE CASCADE,
  answer_id       uuid NOT NULL REFERENCES public.answers(id) ON DELETE CASCADE,
  criterion_code  text NOT NULL,
  ai_score        numeric(6,2) NOT NULL,
  rationale       text NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (run_id, answer_id, criterion_code),
  CONSTRAINT answer_prescores_score_check CHECK (ai_score >= 0)
);

CREATE TABLE IF NOT EXISTS public.usage_logs (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id     uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  run_id      uuid REFERENCES public.runs(id) ON DELETE SET NULL,
  purpose     usage_purpose NOT NULL,
  model       text NOT NULL,
  tokens_in   int,
  tokens_out  int,
  cost_usd    numeric(10,6),
  latency_ms  int,
  status      text NOT NULL DEFAULT 'ok',
  created_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT usage_logs_status_check CHECK (status IN ('ok','retry','failed'))
);
