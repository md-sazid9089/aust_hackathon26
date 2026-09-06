-- 0005 ingestion: artefacts, questions, question_co_map, question_topic_map, normalize_qnum

CREATE TABLE IF NOT EXISTS public.artefacts (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id             uuid NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
  kind                  artefact_kind NOT NULL,
  label                 text NOT NULL,
  year                  smallint,
  term                  text,
  storage_path          text,
  mime                  text,
  size_bytes            int,
  extracted_text        text,
  lang                  text_lang NOT NULL DEFAULT 'unknown',
  status                extraction_status NOT NULL DEFAULT 'pending',
  error                 text,
  grader_labels         text[],
  declared_total_marks  numeric(6,2),
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT artefacts_size_check CHECK (size_bytes IS NULL OR size_bytes <= 10485760),
  CONSTRAINT artefacts_source_check CHECK (storage_path IS NOT NULL OR extracted_text IS NOT NULL),
  CONSTRAINT artefacts_declared_total_check CHECK (declared_total_marks IS NULL OR declared_total_marks > 0)
);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'topics_source_artefact_fk') THEN
    ALTER TABLE public.topics
      ADD CONSTRAINT topics_source_artefact_fk
      FOREIGN KEY (source_artefact_id) REFERENCES public.artefacts(id) ON DELETE SET NULL;
  END IF;
END $$;

-- Canonical question-number form shared by questions.number and marks_rows.question_number.
-- "Q2 (B)", "2.b", "2(b)" -> "2b"; "3(a)(ii)" -> "3aii"
CREATE OR REPLACE FUNCTION public.normalize_qnum(p text)
RETURNS text
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
AS $$
  SELECT regexp_replace(
           regexp_replace(lower(p), '^(question|q)\s*', ''),
           '[\s().\-_]+', '', 'g')
$$;

CREATE TABLE IF NOT EXISTS public.questions (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  artefact_id      uuid NOT NULL REFERENCES public.artefacts(id) ON DELETE CASCADE,
  number           text NOT NULL,
  text             text NOT NULL,
  marks            numeric(6,2) NOT NULL,
  bloom_level      bloom_level,
  bloom_source     map_source,
  embedding        vector(1536),
  embedding_model  text,
  sort_order       int NOT NULL DEFAULT 0,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT questions_artefact_number_key UNIQUE (artefact_id, number),
  CONSTRAINT questions_marks_check CHECK (marks >= 0),
  CONSTRAINT questions_number_normalized_check CHECK (number = public.normalize_qnum(number))
);

CREATE TABLE IF NOT EXISTS public.question_co_map (
  question_id  uuid NOT NULL REFERENCES public.questions(id) ON DELETE CASCADE,
  co_id        uuid NOT NULL,
  confidence   numeric(4,3),
  source       map_source NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (question_id, co_id),
  -- Deferred: blocks deleting a mapped CO (error at COMMIT -> 409 OUTCOME_IN_USE), but lets a course delete cascade
  CONSTRAINT question_co_map_co_fk FOREIGN KEY (co_id) REFERENCES public.course_outcomes(id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
  CONSTRAINT question_co_map_confidence_check CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1)
);

CREATE TABLE IF NOT EXISTS public.question_topic_map (
  question_id  uuid NOT NULL REFERENCES public.questions(id) ON DELETE CASCADE,
  topic_id     uuid NOT NULL REFERENCES public.topics(id) ON DELETE CASCADE,
  confidence   numeric(4,3),
  source       map_source NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (question_id, topic_id),
  CONSTRAINT question_topic_map_confidence_check CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1)
);
