-- 0002 enums (architecture.md §21.1). Idempotent via duplicate_object guard.

DO $$ BEGIN CREATE TYPE app_role AS ENUM ('faculty','admin'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE artefact_kind AS ENUM ('syllabus','question_paper','marks_sheet','rubric','answer_set'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE extraction_status AS ENUM ('pending','extracting','done','failed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE text_lang AS ENUM ('en','bn','mixed','unknown'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE bloom_level AS ENUM ('remember','understand','apply','analyze','evaluate','create'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE map_source AS ENUM ('ai','faculty'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE run_module AS ENUM ('exam_audit','attainment','syllabus_check','calibration'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE run_status AS ENUM ('queued','analyzing','completed','partial','failed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE run_input_role AS ENUM ('draft','past','marks','paper','syllabus','rubric','answer_set','compare_course'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE finding_severity AS ENUM ('info','low','medium','high'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE finding_status AS ENUM ('open','accepted','dismissed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE target_kind AS ENUM ('question','course_outcome','program_outcome','topic','answer','criterion','course','none'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE usage_purpose AS ENUM ('extraction','exam_audit','attainment','syllabus_check','calibration','suggestion','embedding'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
