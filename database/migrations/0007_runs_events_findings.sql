-- 0007 runs, run_inputs, run_events, findings

CREATE TABLE IF NOT EXISTS public.runs (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id         uuid NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
  owner_id          uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  module            run_module NOT NULL,
  status            run_status NOT NULL DEFAULT 'queued',
  progress_pct      smallint NOT NULL DEFAULT 0,
  current_stage     text,
  error             text,
  params            jsonb NOT NULL DEFAULT '{}'::jsonb,
  summary           jsonb,
  context_snapshot  jsonb,
  model             text,
  prompt_versions   jsonb NOT NULL DEFAULT '{}'::jsonb,
  idempotency_key   text,
  started_at        timestamptz,
  finished_at       timestamptz,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT runs_progress_check CHECK (progress_pct BETWEEN 0 AND 100)
);
CREATE UNIQUE INDEX IF NOT EXISTS runs_owner_idempotency_uniq
  ON public.runs (owner_id, idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.run_inputs (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id       uuid NOT NULL REFERENCES public.runs(id) ON DELETE CASCADE,
  role         run_input_role NOT NULL,
  artefact_id  uuid,
  course_id    uuid,
  CONSTRAINT run_inputs_artefact_fk FOREIGN KEY (artefact_id) REFERENCES public.artefacts(id) ON DELETE RESTRICT,
  CONSTRAINT run_inputs_course_fk   FOREIGN KEY (course_id)   REFERENCES public.courses(id)   ON DELETE RESTRICT,
  CONSTRAINT run_inputs_exactly_one_check CHECK ((artefact_id IS NOT NULL) <> (course_id IS NOT NULL)),
  CONSTRAINT run_inputs_role_course_check CHECK ((role = 'compare_course') = (course_id IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS run_inputs_run_role_artefact_uniq ON public.run_inputs (run_id, role, artefact_id) WHERE artefact_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS run_inputs_run_role_course_uniq   ON public.run_inputs (run_id, role, course_id)   WHERE course_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.run_events (
  id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id   uuid NOT NULL REFERENCES public.runs(id) ON DELETE CASCADE,
  seq      int NOT NULL,
  stage    text NOT NULL,
  message  text,
  pct      smallint,
  at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT run_events_run_seq_key UNIQUE (run_id, seq),
  CONSTRAINT run_events_pct_check CHECK (pct IS NULL OR pct BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS public.findings (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id            uuid NOT NULL REFERENCES public.runs(id) ON DELETE CASCADE,
  owner_id          uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  type              text NOT NULL,
  severity          finding_severity NOT NULL DEFAULT 'medium',
  title             text NOT NULL,
  rationale         text NOT NULL,
  evidence_snippet  text,
  target_kind       target_kind NOT NULL DEFAULT 'none',
  target_id         uuid,
  target_label      text,
  payload           jsonb NOT NULL DEFAULT '{}'::jsonb,
  provenance        jsonb NOT NULL DEFAULT '{}'::jsonb,
  status            finding_status NOT NULL DEFAULT 'open',
  decided_by        uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  decided_at        timestamptz,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT findings_type_check CHECK (type IN (
    'coverage_gap','overweight','bloom_imbalance','duplicate','fairness',
    'marks_total_mismatch','marks_question_mismatch','suggestion',
    'co_underperformance','po_underperformance','action',
    'overlap','prerequisite_gap','missing_topic','repositioning',
    'divergence','prescore_note','rubric_clarification')),
  CONSTRAINT findings_decision_consistency_check CHECK ((status = 'open') = (decided_by IS NULL))
);
