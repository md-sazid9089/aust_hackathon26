# Database Implementation Plan — aust_hackathon26

**Owner:** Engineer 3 (DB) · **Source of truth:** `architecture.md` §20–23, §36, §38, §39, ADR-13/14 · **Status:** ready to execute · **Date:** 2026-09-06

This file turns the approved schema into an ordered, checkable build sequence. If anything here conflicts with `architecture.md`, `architecture.md` wins — fix this file.

---

## 0. Ground rules

| Rule | Detail |
|---|---|
| Target | One **hosted** Supabase project (Postgres 15, `vector`, `pgcrypto`). No local `supabase start` for the team. |
| Connections | Migrations: `SUPABASE_DB_URL` (postgres superuser, port 5432). App: `DATABASE_URL` as `app_backend` via pooler 6543. |
| Migrations | Sequential SQL files `database/migrations/NNNN_name.sql`, forward-only, idempotent (`IF NOT EXISTS`, `CREATE OR REPLACE`, `DO $$ … EXCEPTION WHEN duplicate_object …$$`). Applied twice must be a no-op. |
| Ownership | Only DB edits `database/**`. BE requests schema changes as issues; DB adds a new `NNNN_*.sql`. Never rewrite an applied file after Phase 0 freeze. |
| Contract freeze | End of Phase 0: table/column names, enums, function signatures, view columns, constraint names (§38). Bodies may change; signatures may not. |
| Security defaults | Every table `ENABLE ROW LEVEL SECURITY` + `FORCE`. All functions `SECURITY INVOKER` except `handle_new_user()`. `app_backend` is `NOBYPASSRLS`. |
| Naming | snake_case, plural tables, singular enums, `id uuid DEFAULT gen_random_uuid()`, append-only logs use `bigint GENERATED ALWAYS AS IDENTITY`. Constraint names explicit (`<table>_<cols>_<kind>`). |

---

## 1. Repository layout to create

```
database/
├── README.md                 # apply / reset / test instructions (short)
├── migrations/
│   ├── 0001_extensions_and_roles.sql
│   ├── 0002_enums.sql
│   ├── 0003_profiles_and_auth_trigger.sql
│   ├── 0004_courses_outcomes.sql
│   ├── 0005_artefacts_questions.sql
│   ├── 0006_marks_rubrics_answers.sql
│   ├── 0007_runs_events_findings.sql
│   ├── 0008_attainment_prescores_usage.sql
│   ├── 0009_indexes.sql
│   ├── 0010_rls_policies.sql
│   ├── 0011_functions.sql
│   └── 0012_views.sql
├── seeds/
│   ├── seed_demo.sql         # seed_demo(owner) body + fixture rows
│   ├── seed_admin.sql        # promote email → admin
│   └── fixtures/
│       ├── cse2201_syllabus.txt
│       ├── cse2201_paper_2024.txt
│       ├── cse2201_paper_2025.txt
│       ├── cse2201_paper_draft.txt
│       ├── cse2201_marks.csv
│       ├── cse2201_rubric.txt
│       ├── cse2201_answers.txt
│       └── cse2101_syllabus.txt
├── tests/
│   ├── test_constraints.sql
│   ├── test_rls.sql
│   └── test_functions.sql
└── scripts/
    ├── apply.sh              # psql loop over migrations (needs SUPABASE_DB_URL)
    ├── reset_local.sh        # CI only: drop schema public cascade + apply
    └── run_tests.sh          # psql -v ON_ERROR_STOP=1 -f tests/*.sql
```

---

## 2. Build sequence and time boxes

| Step | Task ID | Deliverable | Phase | Box | Blocked by | Done when |
|---|---|---|---|---|---|---|
| 1 | DB-00 | Supabase project created; Auth email+Google enabled; private bucket `artefacts`; `.env` filled (`SUPABASE_DB_URL`, `DATABASE_URL`) | 0 | 15 min | — | `psql $SUPABASE_DB_URL -c 'select 1'` works |
| 2 | DB-01 | `0001`, `0002` | 0 | 15 min | 1 | `\dT` lists 13 enums; role `app_backend` exists |
| 3 | DB-02 | `0003` | 0 | 15 min | 2 | Sign-up via Supabase creates `profiles` row |
| 4 | DB-03 | `0004` | 0 | 15 min | 2 | PO1–PO12 rows present |
| 5 | DB-04 | `0005` (+ `0006` marks_rows at minimum; rubric/answers/grader_scores may ship in Phase 4 if P2 deferred) | 0 | 25 min | 4 | tables exist, FKs correct |
| 6 | DB-05 | `0007`, `0008` | 0 | 25 min | 5 | **Phase 0 freeze** — notify BE to write `models.py` |
| 7 | DB-10a | Fixture files authored (TXT/CSV, both courses, planted defects §21.6) | 0 | 40 min | — (parallel) | Files reviewed by one other engineer |
| 8 | DB-06 | `0009` | 1 | 15 min | 6 | `\di` shows all indexes incl. 2 HNSW |
| 9 | DB-07 | `0010` — SELECT policies first, commit; then write policies | 1 | 45 min | 6 | `test_rls.sql` green |
| 10 | DB-08 | `0011` | 1 | 45 min | 6 | `test_functions.sql` green on fixtures |
| 11 | DB-09 | `0012` | 1 | 20 min | 10 | Views return rows for seed |
| 12 | DB-10b | `seed_demo()` body + `seed_admin.sql` | 1–2 | 40 min | 7, 10 | Called ×5 → same course id, no orphans |
| 13 | DB-11 | tests + scripts | 1 | 30 min | 9–12 | `run_tests.sh` exit 0 |
| 14 | DB-12 | CI job (`pgvector/pgvector:pg15`), apply ×2 + tests | 2 | 30 min | 13 | green on PR |
| 15 | DB-13 | `EXPLAIN ANALYZE` hot paths (§23) with BE | 3/8 | 30 min | BE-08/09 | no seq scan on `run_events`, `findings`, `questions` |
| 16 | DB-14 | Backup drill: `pg_dump` + restore to scratch schema | 8 | 15 min | — | documented in README |

Phase 0 target: steps 1–7 in ≈ 90 min (step 7 runs in parallel with 2–6).

---

## 3. Migration contents

Column-level detail lives in `architecture.md` §21; this section lists what each file must contain and the non-obvious parts.

### 0001_extensions_and_roles.sql
- `CREATE EXTENSION IF NOT EXISTS pgcrypto; CREATE EXTENSION IF NOT EXISTS vector;`
- `DO $$ … CREATE ROLE app_backend LOGIN NOBYPASSRLS PASSWORD '<set via \set>' … $$` (guard `duplicate_object`). Password is set out-of-band; migration file contains no secret — use `ALTER ROLE app_backend PASSWORD :'pw'` from `apply.sh` reading env.
- `GRANT USAGE ON SCHEMA public TO app_backend; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_backend; … GRANT USAGE, SELECT ON SEQUENCES …; … GRANT EXECUTE ON FUNCTIONS …`
- `GRANT USAGE ON SCHEMA auth TO app_backend` is **not** needed; backend never reads `auth.*`.

### 0002_enums.sql
13 enums: `app_role, artefact_kind, extraction_status, text_lang, bloom_level, map_source, run_module, run_status, run_input_role, finding_severity, finding_status, target_kind, usage_purpose`. Each wrapped in `DO $$ BEGIN CREATE TYPE … EXCEPTION WHEN duplicate_object THEN NULL; END $$;`.

### 0003_profiles_and_auth_trigger.sql
- `profiles` (id FK `auth.users` CASCADE, email UNIQUE `profiles_email_key`, full_name, role default `'faculty'`, is_active default true, timestamps).
- `handle_new_user()` — `SECURITY DEFINER SET search_path = public`; `INSERT … ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, full_name = COALESCE(EXCLUDED.full_name, profiles.full_name)`; never touches `role`/`is_active`.
- `CREATE OR REPLACE TRIGGER on_auth_user_created AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION handle_new_user();`

### 0004_courses_outcomes.sql
- `courses` (owner_id FK profiles CASCADE, code, title, term, description, is_demo, deleted_at). Partial unique index `courses_owner_code_uniq ON courses(owner_id, code) WHERE deleted_at IS NULL`. CHECK `length(code) BETWEEN 2 AND 20`.
- `program_outcomes` (code UNIQUE, text, sort_order). Seed PO1–PO12 with `INSERT … ON CONFLICT (code) DO NOTHING`.
- `course_outcomes` (course_id CASCADE, code, text, bloom_level, weight numeric(5,2) > 0, sort_order). UNIQUE `(course_id, code)`.
- `co_po_map` (co_id CASCADE, po_id RESTRICT, strength smallint 0..3). PK `(co_id, po_id)`. No `updated_at`.
- `topics` (course_id CASCADE, code, title, source_artefact_id — **FK added in 0005** after `artefacts` exists, embedding vector(1536), embedding_model, sort_order). UNIQUE `(course_id, code)`.

### 0005_artefacts_questions.sql
- `artefacts` (course_id CASCADE, kind, label, year, term, storage_path, mime, size_bytes ≤ 10485760, extracted_text, lang default `'unknown'`, status default `'pending'`, error, grader_labels text[], declared_total_marks numeric(6,2)). CHECK `storage_path IS NOT NULL OR extracted_text IS NOT NULL`.
- `ALTER TABLE topics ADD CONSTRAINT topics_source_artefact_fk FOREIGN KEY (source_artefact_id) REFERENCES artefacts(id) ON DELETE SET NULL;`
- `normalize_qnum(text) RETURNS text IMMUTABLE` — define **here** (needed by CHECKs): `lower(regexp_replace(regexp_replace($1, '\s+', '', 'g'), '[.)]+$', ''))`.
- `questions` (artefact_id CASCADE, number CHECK `number = normalize_qnum(number)`, text, marks ≥ 0, bloom_level, bloom_source, embedding, embedding_model, sort_order). UNIQUE `(artefact_id, number)`.
- `question_co_map` (question_id CASCADE, co_id **RESTRICT** named `question_co_map_co_fk`, confidence 0..1, source, created_at). PK `(question_id, co_id)`.
- `question_topic_map` (question_id CASCADE, topic_id CASCADE, confidence, source, created_at). PK `(question_id, topic_id)`.

### 0006_marks_rubrics_answers.sql
- `marks_rows` (id IDENTITY, artefact_id CASCADE, student_anon_id, question_number CHECK normalized, score ≥ 0, max_score > 0, CHECK `score <= max_score`). UNIQUE `(artefact_id, student_anon_id, question_number)`. No `updated_at`.
- `rubric_criteria` (artefact_id CASCADE, code, text, max_score > 0, levels jsonb default `'[]'` CHECK `jsonb_typeof(levels) = 'array'`, sort_order). UNIQUE `(artefact_id, code)`.
- `answers` (artefact_id CASCADE, student_anon_id, question_ref, text, sort_order). UNIQUE `(artefact_id, student_anon_id, question_ref)` — use `COALESCE(question_ref,'')` in a unique index since NULLs don't collide.
- `grader_scores` (answer_id CASCADE, grader_label, criterion_code, score ≥ 0). PK `(answer_id, grader_label, criterion_code)`. No `updated_at`.

If P2 is deferred: ship `marks_rows` in this file in Phase 0 anyway (P4 needs it); the other three tables may be appended as `0013_p2_tables.sql` later rather than editing `0006`.

### 0007_runs_events_findings.sql
- `runs` (course_id CASCADE, owner_id FK profiles CASCADE, module, status default `'queued'`, progress_pct 0..100, current_stage, error, params jsonb `'{}'`, summary jsonb, context_snapshot jsonb, model, prompt_versions jsonb `'{}'`, idempotency_key, started_at, finished_at). Partial unique `runs_owner_idempotency_uniq (owner_id, idempotency_key) WHERE idempotency_key IS NOT NULL`.
- `run_inputs` (id IDENTITY, run_id CASCADE, role run_input_role, artefact_id NULL FK RESTRICT `run_inputs_artefact_fk`, course_id NULL FK RESTRICT `run_inputs_course_fk`). CHECK `(artefact_id IS NOT NULL) <> (course_id IS NOT NULL)`; CHECK `(role = 'compare_course') = (course_id IS NOT NULL)`; UNIQUE `(run_id, role, artefact_id)`; UNIQUE `(run_id, role, course_id)`.
- `run_events` (id IDENTITY, run_id CASCADE, seq, stage, message, pct 0..100, at). UNIQUE `(run_id, seq)`.
- `findings` (run_id CASCADE, owner_id CASCADE, type CHECK IN (18 values incl. `marks_total_mismatch`, `marks_question_mismatch`), severity default `'medium'`, title, rationale, evidence_snippet, target_kind default `'none'`, target_id, target_label, payload jsonb `'{}'`, provenance jsonb `'{}'`, status default `'open'`, decided_by FK profiles SET NULL, decided_at). CHECK `(status = 'open') = (decided_by IS NULL)`.

### 0008_attainment_prescores_usage.sql
- `attainment_results` (run_id CASCADE, target_kind CHECK IN ('course_outcome','program_outcome'), target_id, target_code, attained_pct 0..100, students, target_pct, met). PK `(run_id, target_kind, target_id)`. No FK on `target_id`.
- `answer_prescores` (run_id CASCADE, answer_id CASCADE, criterion_code, ai_score, rationale). PK `(run_id, answer_id, criterion_code)`.
- `usage_logs` (id IDENTITY, user_id SET NULL, run_id SET NULL, purpose, model, tokens_in, tokens_out, cost_usd numeric(10,6), latency_ms, status CHECK IN ('ok','retry','failed'), created_at). No `updated_at`.

### 0009_indexes.sql
Exactly the list in `architecture.md` §21.4 plus `run_inputs(artefact_id)`, `run_inputs(course_id) WHERE course_id IS NOT NULL`. HNSW: `USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)` on `questions` and `topics`. All `CREATE INDEX IF NOT EXISTS`.

### 0010_rls_policies.sql
Helpers first (`current_app_user()`, `is_admin()`, `course_owner()` — define here or in 0011 but **before** policies reference them; put them at the top of 0010 with `CREATE OR REPLACE`).

Pattern per table (write both SELECT and write policies; commit SELECT set first during Phase 1):

| Table group | SELECT | INSERT / UPDATE / DELETE |
|---|---|---|
| `profiles` | `id = current_app_user() OR is_admin()` | UPDATE: `is_admin()` (columns limited in app); no INSERT/DELETE for app_backend (trigger inserts) |
| `courses` | `(owner_id = current_app_user() AND deleted_at IS NULL) OR is_admin()` | `owner_id = current_app_user()` |
| `program_outcomes` | `true` | `is_admin()` |
| course children (`course_outcomes`, `topics`, `artefacts`) | `course_owner(course_id) = current_app_user() OR is_admin()` | `course_owner(course_id) = current_app_user()` |
| `co_po_map` | via `course_outcomes` subquery | same |
| artefact children (`questions`, `marks_rows`, `rubric_criteria`, `answers`) | `course_owner((SELECT course_id FROM artefacts a WHERE a.id = artefact_id)) = current_app_user() OR is_admin()` | owner only |
| `question_co_map`, `question_topic_map`, `grader_scores`, `answer_prescores` | through parent row | owner only |
| `runs`, `findings` | `owner_id = current_app_user() OR is_admin()` | `owner_id = current_app_user()` (admin cannot UPDATE findings — SEC-009) |
| `run_inputs`, `run_events`, `attainment_results` | `EXISTS (SELECT 1 FROM runs r WHERE r.id = run_id AND (r.owner_id = current_app_user() OR is_admin()))` | owner via same subquery |
| `usage_logs` | `user_id = current_app_user() OR is_admin()` | INSERT: `user_id = current_app_user()` |

`ALTER TABLE … ENABLE ROW LEVEL SECURITY; ALTER TABLE … FORCE ROW LEVEL SECURITY;` on all 24 tables. Wrap `CREATE POLICY` in `DROP POLICY IF EXISTS` for idempotency.

### 0011_functions.sql
- `set_updated_at()` + triggers by **explicit list**: `profiles, courses, program_outcomes, course_outcomes, topics, artefacts, questions, rubric_criteria, answers, runs, findings`.
- `course_owner(uuid) RETURNS uuid STABLE` — `WHERE id = $1 AND deleted_at IS NULL`.
- `similar_questions(p_question uuid, p_course uuid, p_k int, p_min_sim numeric)` — SECURITY INVOKER; `SET LOCAL hnsw.ef_search = 40` inside via `SET` clause on function; excludes same artefact, NULL embeddings, and `embedding_model <> source.embedding_model`; returns `(question_id, artefact_id, similarity)`.
- `similar_topics(p_topic uuid, p_course_ids uuid[], p_k int, p_min_sim numeric)` — same shape over `topics`.
- `compute_co_attainment(p_run uuid, p_marks_artefact uuid, p_paper_artefact uuid, p_threshold numeric) RETURNS TABLE(co_id uuid, co_code text, attained_pct numeric, students int, unmatched_numbers text[])` — CTEs: `matched` (marks_rows ⋈ questions on `(artefact, number)`), `unmatched` (anti-join → `array_agg`), `per_student_co` (sum score / sum max via `question_co_map`), `attained` (≥ threshold), final aggregate; `unmatched_numbers` repeated on every row.
- `reset_demo(p_owner uuid) RETURNS void` — `IF p_owner <> current_app_user() AND NOT is_admin() THEN RAISE EXCEPTION USING ERRCODE = '42501'`; `DELETE FROM courses WHERE owner_id = p_owner AND is_demo`.
- `seed_demo(p_owner uuid) RETURNS uuid` — same guard; body lives in `seeds/seed_demo.sql` and is `\i`-included by `apply.sh` after 0011 (keeps fixture data out of migrations). Returns existing demo course id if present.

### 0012_views.sql
All `WITH (security_invoker = true)`:
- `v_course_run_summary` — lateral latest completed `exam_audit` and `attainment` run per course; `exam_coverage_pct = (summary->>'coverage_pct')::numeric`; `exam_open_findings` count; `cos_met/cos_total` from `attainment_results`.
- `v_admin_department_attainment` — joins `runs`, `profiles`, `courses`; `weakest_co_code/weakest_pct` via lateral `ORDER BY attained_pct LIMIT 1` on `attainment_results` using `target_code` (NULL when all met).
- `v_admin_exam_audit_summary` — `coverage_pct`, `duplicates = jsonb_array_length(summary->'duplicates')`, open findings.
- `v_admin_usage` — group by `user_id, email, date_trunc('day', created_at)`.

---

## 4. Seed data specification (DB-10a / DB-10b)

| Fixture | Content | Planted defect (must trigger) |
|---|---|---|
| `cse2201_syllabus.txt` | CSE 2201 Design & Analysis of Algorithms; 10 topics; CO1–CO6 with text | — |
| `cse2201_paper_2024.txt`, `_2025.txt` | 8 questions each, numbers `1`, `2(a)`, `2(b)`, … marks summing to 100 | 2024 Q3 is the duplicate source |
| `cse2201_paper_draft.txt` | 8 questions, `declared_total_marks: 100` | CO5 uncovered; Q4 ≈ 2024 Q3 (cosine ≥ 0.85); CO2 gets 40 marks; sum = 90 → `marks_total_mismatch`; no `create`-level question → `bloom_imbalance` |
| `cse2201_marks.csv` | header `student_anon_id,1,2(a),2(b),…`; 40 rows `S001…S040`; max row | CO3 questions avg < 40% → CO3 unmet; one header cell written `2 (B)` to exercise `normalize_qnum` |
| `cse2201_rubric.txt` | 4 criteria, max 5 each, 3 levels | — |
| `cse2201_answers.txt` | 6 typed answers × 2 graders (`A`, `B`) scores per criterion | answers 2 and 5 diverge ≥ 25% on ≥ 1 criterion |
| `cse2101_syllabus.txt` | CSE 2101 Data Structures; 10 topics | ≈ 7 topics overlap CSE 2201 → P3 matrix non-empty |

`seed_demo(p_owner)` inserts: 2 courses (`is_demo = true`), COs, CO→PO map, topics for both, artefact rows (`status = 'pending'`, `storage_path = 'demo/<file>'`, `extracted_text` = file body pasted in). Backend `POST /demo/seed` then uploads the same bytes to Storage, runs extraction, and pre-runs P1 + P4 to cache results. Idempotency: `SELECT id FROM courses WHERE owner_id = p_owner AND is_demo AND code = 'CSE2201' AND deleted_at IS NULL` short-circuits.

`seed_admin.sql`: `UPDATE profiles SET role = 'admin' WHERE email = :'email';` run once per team member who needs admin.

---

## 5. Tests (DB-11)

`tests/test_constraints.sql` — each block `DO $$ BEGIN <violating stmt>; RAISE EXCEPTION 'should have failed'; EXCEPTION WHEN check_violation | unique_violation | foreign_key_violation THEN NULL; END $$;` for:
- `courses.code` length; duplicate `(owner_id, code)` live vs soft-deleted allowed
- `co_po_map.strength = 4`; `questions.marks = -1`; `questions.number = '2 (B)'` (not normalized)
- `marks_rows.score > max_score`; duplicate `(artefact, student, qnum)`
- delete `course_outcomes` row referenced by `question_co_map` → FK violation
- delete `artefacts` row referenced by `run_inputs` → FK violation
- `run_inputs` with both/neither of `artefact_id`/`course_id`
- `findings` with `status='accepted'` and `decided_by IS NULL`
- `attainment_results.attained_pct = 101`

`tests/test_rls.sql` — run as `app_backend` (`SET ROLE app_backend`):
- `SET LOCAL app.user_id = A; app.role = 'faculty'` → sees own course, 0 rows of B's course and children (`artefacts`, `questions`, `runs`, `findings`, `run_events`)
- Soft-delete A's course → A sees 0 children rows; admin still sees them
- `app.role = 'admin'` → SELECT B's rows OK; `UPDATE findings SET status='accepted'` on B's row → 0 rows affected
- `app.user_id` unset → all owner tables return 0 rows
- `SELECT reset_demo(B)` as A → `42501`
- `similar_questions()` as A over B's course → 0 rows (not error)
- After transaction end, `current_setting('app.user_id', true)` is NULL (pooler safety)

`tests/test_functions.sql` — on seeded fixtures:
- `compute_co_attainment(...)` → CO3 `met = false`; `unmatched_numbers` empty after normalisation; hand-computed pct matches ±0.01
- `similar_questions(draft Q4, course, 3, 0.8)` → 2024 Q3 ranked first (requires embeddings; in CI stub embeddings with fixed vectors)
- `seed_demo(owner)` called twice → same uuid; row counts unchanged
- `set_updated_at` fires on `courses` update, not present on `run_events`

`scripts/run_tests.sh` applies migrations twice (idempotency), loads seed, runs the three files with `-v ON_ERROR_STOP=1`.

---

## 6. Contracts owed to Backend (freeze at end of Phase 0)

- Enum names/values (§21.1), table/column names (§21.2) → `backend/app/db/models.py` + `enums.py`; parity test reflects live DB.
- Function signatures: `normalize_qnum(text)`, `similar_questions(uuid,uuid,int,numeric)`, `similar_topics(uuid,uuid[],int,numeric)`, `compute_co_attainment(uuid,uuid,uuid,numeric)`, `reset_demo(uuid)`, `seed_demo(uuid)`.
- View column lists (§21.5).
- Constraint names for 409 mapping: `courses_owner_code_uniq`, `question_co_map_co_fk`, `run_inputs_artefact_fk`, `run_inputs_course_fk`, `profiles_email_key`.
- `runs.summary` keys read by views: `coverage_pct`, `duplicates`.
- Session protocol: BE must `SET LOCAL app.user_id = '<uuid>'; SET LOCAL app.role = 'faculty'|'admin'` first in every transaction (incl. background tasks). Unset → RLS returns nothing (fail closed).
- Backend must call `normalize_qnum` semantics (same regex) before inserting `questions.number` / `marks_rows.question_number`, or the CHECK rejects the row.

---

## 7. Acceptance criteria per phase

| Phase gate | DB must show |
|---|---|
| End Phase 0 | `0001–0005, 0007–0008` (+ `marks_rows`) applied on hosted project; `\dt` = 21–24 tables; fixtures drafted; BE unblocked on `models.py` |
| End Phase 1 | `0009–0012` applied; `test_rls.sql` + `test_constraints.sql` green; `seed_demo` idempotent |
| Phase 3 (W1 live) | `similar_questions` returns planted duplicate; `findings` rows for `coverage_gap`, `duplicate`, `overweight`, `marks_total_mismatch` exist for demo run; export query returns accepted only |
| Phase 4 | `compute_co_attainment` yields CO3 unmet; `attainment_results` populated; P2 tables present if P2 shipped |
| Phase 6 | CI job green: fresh `pgvector/pgvector:pg15`, apply ×2, tests |
| Phase 7 | Every table has ≥ 1 SELECT policy and ≥ 1 write policy; no `SECURITY DEFINER` except `handle_new_user`; grants reviewed |

---

## 8. Risks specific to this plan

| Risk | Mitigation |
|---|---|
| `CREATE ROLE` / `auth.users` trigger need superuser | `apply.sh` uses `SUPABASE_DB_URL`; document in README; never run migrations as `app_backend` |
| Pooler leaks `SET` | Only `SET LOCAL`; `test_rls.sql` asserts reset; BE `get_db()` reviewed by DB (DB-13) |
| RLS helper functions referenced before creation | Helpers defined at top of `0010`; `0011` uses `CREATE OR REPLACE` for the rest |
| `normalize_qnum` CHECK rejects backend inserts | Share the regex with BE in §38; BE unit test against DB function output |
| Fixture PDFs without text layer | Fixtures are TXT/CSV; PDFs optional |
| `seed_demo` half-applies | Single function = single tx; idempotency test ×5 |
| HNSW build on empty table then bulk insert | Fine at this scale; if ever slow, `REINDEX` after seed |
| Embedding model swap | `embedding_model` column; `similar_*` ignore mismatched rows; BE lazily re-embeds |

---

## 9. Definition of done (DB track)

- [ ] All 12 migrations applied to hosted project; applying again is a no-op
- [ ] `database/README.md` explains apply / reset / test in ≤ 20 lines
- [ ] `seed_demo`, `seed_admin` work; demo course visible to seeded faculty; admin sees it read-only
- [ ] Three test files green locally and in CI
- [ ] BE parity test green against live schema
- [ ] `PROJECT_CONTEXT.md` §8/§9/§11 updated by BE (send text) when each phase gate passes
