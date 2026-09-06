-- 0004 course workspace: courses, program_outcomes, course_outcomes, co_po_map, topics

CREATE TABLE IF NOT EXISTS public.courses (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id     uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  code         text NOT NULL,
  title        text NOT NULL,
  term         text,
  description  text,
  is_demo      boolean NOT NULL DEFAULT false,
  deleted_at   timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT courses_code_len_check CHECK (length(code) BETWEEN 2 AND 20)
);
CREATE UNIQUE INDEX IF NOT EXISTS courses_owner_code_uniq
  ON public.courses (owner_id, code) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS public.program_outcomes (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code        text NOT NULL,
  text        text NOT NULL,
  sort_order  int  NOT NULL DEFAULT 0,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT program_outcomes_code_key UNIQUE (code)
);

INSERT INTO public.program_outcomes (code, text, sort_order) VALUES
  ('PO1',  'Engineering knowledge', 1),
  ('PO2',  'Problem analysis', 2),
  ('PO3',  'Design/development of solutions', 3),
  ('PO4',  'Investigation', 4),
  ('PO5',  'Modern tool usage', 5),
  ('PO6',  'The engineer and society', 6),
  ('PO7',  'Environment and sustainability', 7),
  ('PO8',  'Ethics', 8),
  ('PO9',  'Individual work and teamwork', 9),
  ('PO10', 'Communication', 10),
  ('PO11', 'Project management and finance', 11),
  ('PO12', 'Life-long learning', 12)
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.course_outcomes (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id    uuid NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
  code         text NOT NULL,
  text         text NOT NULL,
  bloom_level  bloom_level,
  weight       numeric(5,2) NOT NULL DEFAULT 1.00,
  sort_order   int NOT NULL DEFAULT 0,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT course_outcomes_course_code_key UNIQUE (course_id, code),
  CONSTRAINT course_outcomes_weight_check CHECK (weight > 0)
);

CREATE TABLE IF NOT EXISTS public.co_po_map (
  co_id     uuid NOT NULL REFERENCES public.course_outcomes(id) ON DELETE CASCADE,
  po_id     uuid NOT NULL REFERENCES public.program_outcomes(id) ON DELETE RESTRICT,
  strength  smallint NOT NULL,
  PRIMARY KEY (co_id, po_id),
  CONSTRAINT co_po_map_strength_check CHECK (strength BETWEEN 0 AND 3)
);

-- source_artefact_id FK is added in 0005 once artefacts exists
CREATE TABLE IF NOT EXISTS public.topics (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id           uuid NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
  code                text NOT NULL,
  title               text NOT NULL,
  source_artefact_id  uuid,
  embedding           vector(1536),
  embedding_model     text,
  sort_order          int NOT NULL DEFAULT 0,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT topics_course_code_key UNIQUE (course_id, code)
);
