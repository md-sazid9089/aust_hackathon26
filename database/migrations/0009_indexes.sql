-- 0009 indexes (architecture.md §21.4). All IF NOT EXISTS.

CREATE INDEX IF NOT EXISTS courses_owner_live_idx        ON public.courses (owner_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS course_outcomes_course_idx    ON public.course_outcomes (course_id, sort_order);
CREATE INDEX IF NOT EXISTS co_po_map_po_idx              ON public.co_po_map (po_id);
CREATE INDEX IF NOT EXISTS topics_course_idx             ON public.topics (course_id, sort_order);
CREATE INDEX IF NOT EXISTS topics_source_artefact_idx    ON public.topics (source_artefact_id);
CREATE INDEX IF NOT EXISTS artefacts_course_kind_status_idx ON public.artefacts (course_id, kind, status);
CREATE INDEX IF NOT EXISTS questions_artefact_sort_idx   ON public.questions (artefact_id, sort_order);
CREATE INDEX IF NOT EXISTS question_co_map_co_idx        ON public.question_co_map (co_id);
CREATE INDEX IF NOT EXISTS question_topic_map_topic_idx  ON public.question_topic_map (topic_id);
CREATE INDEX IF NOT EXISTS marks_rows_artefact_qnum_idx  ON public.marks_rows (artefact_id, question_number);
CREATE INDEX IF NOT EXISTS rubric_criteria_artefact_idx  ON public.rubric_criteria (artefact_id, sort_order);
CREATE INDEX IF NOT EXISTS answers_artefact_idx          ON public.answers (artefact_id, sort_order);
CREATE INDEX IF NOT EXISTS runs_course_created_idx       ON public.runs (course_id, created_at DESC);
CREATE INDEX IF NOT EXISTS runs_owner_status_idx         ON public.runs (owner_id, status);
CREATE INDEX IF NOT EXISTS runs_module_status_finished_idx ON public.runs (module, status, finished_at DESC);
CREATE INDEX IF NOT EXISTS run_inputs_run_idx            ON public.run_inputs (run_id);
CREATE INDEX IF NOT EXISTS run_inputs_artefact_idx       ON public.run_inputs (artefact_id) WHERE artefact_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS run_inputs_course_idx         ON public.run_inputs (course_id) WHERE course_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS findings_run_sev_created_idx  ON public.findings (run_id, severity DESC, created_at);
CREATE INDEX IF NOT EXISTS findings_owner_status_idx     ON public.findings (owner_id, status);
CREATE INDEX IF NOT EXISTS findings_run_type_label_idx   ON public.findings (run_id, type, target_label);
CREATE INDEX IF NOT EXISTS attainment_results_target_idx ON public.attainment_results (target_kind, target_id);
CREATE INDEX IF NOT EXISTS answer_prescores_answer_idx   ON public.answer_prescores (answer_id);
CREATE INDEX IF NOT EXISTS usage_logs_user_created_idx   ON public.usage_logs (user_id, created_at);
CREATE INDEX IF NOT EXISTS usage_logs_created_idx        ON public.usage_logs (created_at);
CREATE INDEX IF NOT EXISTS usage_logs_run_idx            ON public.usage_logs (run_id);

-- Exact-scan-equivalent at demo size; created now so no migration is needed at scale
CREATE INDEX IF NOT EXISTS questions_embedding_hnsw ON public.questions USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS topics_embedding_hnsw    ON public.topics    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
