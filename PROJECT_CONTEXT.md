# Project Context

> Living document. Every agent and contributor MUST read this before working and update it after making changes.
> Last updated: 2026-09-06 (Render deploy config added)

## 1. Overview

- **Name:** aust_hackathon26 — working title **Faculty Assessment & Curriculum Copilot**
- **Purpose:** AI tool for AUST faculty (AI Build Hackathon final, theme "AI for Academic Life"). Faculty upload syllabi, question papers, marks sheets, rubrics + answers → AI evaluates/compares → evidence-backed findings faculty accept or dismiss. AI advises; faculty decide.
- **Status:** Backend Tier 0 implemented and tested (`backend/`, 47 pytest tests green; P1 Exam Auditor end-to-end). Frontend scaffold in progress (`frontend/`, separate owner). Architecture in `architecture.md` v1.0 — see D-018–D-023 for implementation deviations.
- **Repository:** md-sazid9089/aust_hackathon26 (branch `main`)

## 2. Goals & Non-Goals

**Goals**

- Judges see: problem → input → what the AI does → useful result, live.
- One shared Course workspace (syllabus + Course Outcomes) reused by four modules: P1 Exam Paper Auditor, P4 CO–PO Attainment Analyst, P3 Syllabus Overlap/Gap Analyzer, P2 Grading Consistency Calibrator.
- Every finding carries rationale + evidence snippet; faculty accept/dismiss; export accepted findings.

**Non-goals**

- Student-facing views, LMS/Moodle integration, handwriting OCR, "ask anything" chatbot, fine-tuning, attendance/timetable, internet plagiarism checks, full academic management platform.

## 3. Tech Stack

| Layer                     | Choice                                                              | Notes                                |
| ------------------------- | ------------------------------------------------------------------- | ------------------------------------ |
| Frontend                  | React 18 + Vite 5 + TS 5, Tailwind + shadcn/ui, React Router v6, TanStack Query v5, RHF + zod, Recharts, native `EventSource` | SPA; Supabase JS used **only** for auth |
| Backend                   | Python 3.11+ (dev on 3.14), FastAPI 0.141, SQLAlchemy 2 async (asyncpg prod / aiosqlite dev+tests), Alembic, pydantic-settings, httpx, structlog, PyJWT, sse-starlette; pypdf / python-docx | REST `/api/v1` + SSE; runs = asyncio tasks + `run_events`; **no LangChain/LangGraph, no slowapi** (D-018, D-021) |
| Database / Auth / Storage | Postgres 17 (Supabase) in prod, **SQLite locally**; Alembic migrations (`backend/alembic/`); auth `AUTH_MODE=dev` or Supabase HS256 JWT; files on local disk via `StorageBackend` seam | Ownership enforced in service layer; RLS/pgvector/Supabase Storage deferred (D-019, D-020, D-022) |
| AI                        | `ai/providers`: `OpenAICompatibleProvider` (OpenRouter/OpenAI, `response_format=json_schema` strict) + `MockProvider` (deterministic lexical heuristics); `ai/client.structured_call` validates with Pydantic, 1 retry, fallback models, `usage_logs` | Temp 0, 60 s; LLM stage failure → run `partial`, deterministic stages still run |
| Tooling                   | BE pytest + pytest-asyncio + httpx + respx + ruff · FE Vitest/Playwright (planned) | |

Environment variables (names only; full list with comments in `backend/.env.example`): backend `ENV`, `LOG_LEVEL`, `DATABASE_URL`, `CORS_ORIGINS`, `MAX_UPLOAD_MB`, `STORAGE_DIR`, `SEED_DATA_DIR`, `RATE_LIMIT_ENABLED`, `AUTH_MODE`, `DEV_USER_EMAIL`, `SUPABASE_JWT_SECRET`, `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_FALLBACK_MODELS`, `LLM_TIMEOUT_S`, `LLM_MAX_RETRIES`, `EMBED_BASE_URL`, `EMBED_API_KEY`, `EMBED_MODEL` · frontend `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL`.

**MCP servers (dev tooling, `.vscode/mcp.json` for VS Code, `.mcp.json` for Claude Code):**

- `supabase` — hosted HTTP endpoint `https://mcp.supabase.com/mcp?project_ref=etzxqeilgohiavdeybbw&features=…` (docs, account, database, debugging, development, functions, branching). Auth is OAuth in the browser on first use — no access token stored anywhere.
- `context7` — version-accurate docs lookup for whatever frontend/backend libs the architect picks. No secrets.
- Add nothing else unless needed (keep ≤5 servers). Playwright MCP is optional later for E2E of the demo flow.

## 4. Project Structure

```
aust_hackathon26/
├── .github/
│   └── copilot-instructions.md   # Copilot-specific rules (points here)
├── .mcp.json                     # Claude Code MCP config: supabase (hosted HTTP)
├── .vscode/
│   └── mcp.json                  # VS Code MCP servers: supabase (hosted HTTP), context7
├── AGENTS.md                     # generic agent rules (points here)
├── CLAUDE.md                     # Claude entry point, imports AGENTS.md
├── PROJECT_CONTEXT.md            # this file — single source of truth
├── render.yaml                   # Render Blueprint: backend web service (rootDir backend, free tier, Supabase DB)
├── architecture.md               # approved architecture: API §19, schema §21, contracts §38, plan §39, ADRs §42
├── database_implementation_plan.md  # DB engineer's ordered build plan: migrations 0001–0012, RLS matrix, seeds, tests, gates
└── database/                     # IMPLEMENTED — see database/README.md
    ├── migrations/0001–0012_*.sql # extensions+role, enums, profiles+trigger, workspace, artefacts/questions, marks/rubric/answers, runs/findings, results/usage, indexes, RLS, functions, views
    ├── seeds/seed_demo.sql       # seed_demo(owner): CSE2201 full demo + CSE2101 comparison course, structured rows, idempotent
    ├── seeds/seed_admin.sql      # promote email → admin
    ├── seeds/fixtures/*.txt|csv  # syllabus ×2, papers 2024/2025/draft, marks.csv (40 students), rubric, answers
    ├── tests/test_{constraints,rls,functions}.sql
    └── scripts/apply.{sh,ps1}, run_tests.{sh,ps1}, reset_local.sh
```

Planned, not yet created (`architecture.md` §9–10): `frontend/`, `backend/`, `database/`, `docker-compose.yml`, `.env.example`, `.github/workflows/ci.yml`.

## 5. How to Run

```bash
# database (implemented) — needs psql; superuser URL (port 5432), NOT the pooler
#   $env:SUPABASE_DB_URL="postgresql://postgres:<pw>@db.<ref>.supabase.co:5432/postgres"; $env:APP_BACKEND_PASSWORD="<pw>"
#   .\database\scripts\apply.ps1        # or ./database/scripts/apply.sh   (idempotent)
#   .\database\scripts\run_tests.ps1    # constraints, functions, RLS (each rolls back)
#   psql $env:SUPABASE_DB_URL -v email='you@aust.edu' -f database/seeds/seed_admin.sql

# backend (no Postgres needed locally — SQLite default)
cd backend
python3 -m venv .venv && source .venv/bin/activate      # if ensurepip missing: python3 -m venv --without-pip .venv && pip3 --python .venv/bin/python install pip
pip install -r requirements.txt
cp .env.example .env                                     # set LLM_PROVIDER=openrouter + LLM_API_KEY for real AI; mock works offline
alembic upgrade head
uvicorn app.main:app --reload                            # http://localhost:8000/docs
pytest                                                   # 47 tests
# demo: POST /api/v1/demo/seed → POST /api/v1/courses/{id}/runs {module: exam_audit, inputs:{draft_artefact_id, past_artefact_ids}} → GET /runs/{id}/findings
# frontend: cd frontend && npm i && npm run dev           (port 5173; VITE_API_BASE_URL=http://localhost:8000/api/v1)
# all:      docker compose up   (optional profile `free` starts freellmpool on 127.0.0.1:8080)

# deploy backend to Render: Dashboard → New → Blueprint → this repo (uses render.yaml).
#   Fill sync:false secrets in UI: DATABASE_URL (pooler 6543, asyncpg), CORS_ORIGINS, SUPABASE_URL,
#   SUPABASE_PUBLISHABLE_KEY, SUPABASE_SECRET_KEY, LLM_API_KEY. Start cmd runs `alembic upgrade head` then uvicorn (1 worker).
#   Health: https://<service>.onrender.com/api/v1/health
```

**MCP server setup (once per machine):**

1. VS Code + Copilot Chat: open the repo; VS Code detects `.vscode/mcp.json` and asks to trust/start the servers — accept. `supabase` opens a browser OAuth flow on first start (sign in to Supabase, grant access). `context7` needs Node.js ≥ 18 (`npx`), no input.
2. Claude Code: `.mcp.json` is picked up automatically; run `claude /mcp` in a regular terminal → select `supabase` → Authenticate. (Equivalent to `claude mcp add --scope project --transport http supabase "<url>"`, already done.)
3. Check status: Command Palette → `MCP: List Servers` (restart/stop from there). Tools appear in Chat under the tools picker.
4. Reuse guidance: ask the agent to inspect schema / write migrations via the Supabase tools rather than pasting SQL by hand; ask for library docs via Context7 before guessing APIs.

## 6. Architecture & Key Decisions

| ID    | Date       | Decision                                                                                                                                                                                     | Why                                                                                                                 |
| ----- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| D-001 | 2026-09-06 | Keep a single `PROJECT_CONTEXT.md` as the shared source of truth for agents                                                                                                                  | Avoids context loss between sessions and contributors                                                               |
| D-002 | 2026-09-06 | Agent instruction files (`copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md`) stay thin and only redirect to `PROJECT_CONTEXT.md`                                                            | One place to maintain; works across Copilot, Claude, and other tools                                                |
| D-003 | 2026-09-06 | Single unified app with a shared Course core; four modules layered in order P1 → P4 → P3 → P2                                                                                                | P1/P4/P3 all reuse the same CO list; P2 has highest data-prep risk; each module droppable at demo time              |
| D-004 | 2026-09-06 | Supabase for auth, DB, storage and vector search; RLS is the authorization layer                                                                                                             | Cheapest way to get login + pgvector in one day                                                                     |
| D-005 | 2026-09-06 | Findings are first-class rows (`status`, `rationale`, `evidence_snippet`), not JSON blobs                                                                                                    | Enables accept/dismiss, export of accepted findings, explainability                                                 |
| D-006 | 2026-09-06 | All arithmetic (attainment %, marks stats, divergence) is deterministic code; LLM only classifies, maps, explains                                                                            | Correctness and verifiability over LLM output                                                                       |
| D-007 | 2026-09-06 | Hosted LLM API with native structured output + embeddings endpoint; vendor left to architect                                                                                                 | One-day build; reliability > token cost                                                                             |
| D-008 | 2026-09-06 | Tiered build order (Tier 0–3, §12); Tier 3 must be droppable without core changes                                                                                                            | User selected all optional features; brief warns against slide-only features                                        |
| D-009 | 2026-09-06 | Admin actor added (system + department views); role in Supabase `app_metadata.role`, enforced by RLS; admin is read-only over faculty data                                                   | User request CF-001; keeps faculty as sole decision-maker                                                           |
| D-010 | 2026-09-06 | Two MCP servers only: Supabase (DB/migrations/RLS from the agent) + Context7 (docs). Secrets via VS Code `${input:}` prompts, never literals                                                 | Supabase is the whole data layer, so agent-driven schema work saves the most time; more servers cost context window |
| D-011 | 2026-09-06 | Modular monolith: FastAPI + React SPA + one Supabase Postgres; asyncio background runs with `run_events` table + SSE (no Redis/Celery)                                                       | One day, one team; queue seam kept in `RunOrchestrator.enqueue` (architecture.md ADR-01/04/10)                      |
| D-012 | 2026-09-06 | Role lives in `profiles.role` (DB), not JWT claims; backend connects as `app_backend` (NOBYPASSRLS) and sets `SET LOCAL app.user_id/app.role` per tx; RLS enforces. Supersedes D-009 wording | Single source of truth; no bypass path (ADR-02/11)                                                                  |
| D-013 | 2026-09-06 | SQL-file migrations owned by DB engineer (no Alembic); ORM↔DDL parity test in CI                                                                                                             | Clear ownership, DB marks focus (ADR-03)                                                                            |
| D-014 | 2026-09-06 | LLM via OpenAI-compatible adapter: OpenRouter primary (`require_parameters`, fallback models); freellmpool optional local proxy for free dev; `LLM_PROVIDER=mock` for tests/demo fallback    | Resolves A-005; env-only switching (ADR-05)                                                                         |
| D-015 | 2026-09-06 | Embeddings `text-embedding-3-small`, `vector(1536)` fixed; pgvector HNSW cosine                                                                                                              | Verified OpenRouter `/embeddings`; no local model download (ADR-06)                                                 |
| D-016 | 2026-09-06 | Findings first-class table; module aggregates in `runs.summary` jsonb; numeric results in `attainment_results` / `answer_prescores` tables                                                   | Queryable for views, flexible per module (ADR-07)                                                                   |
| D-017 | 2026-09-06 | Merge audit vs an external "versioned assessment platform" design: adopted copy-at-write + provenance columns (`runs.context_snapshot`, `runs.model`, `runs.prompt_versions`, `findings.provenance`, `findings.decided_by`, `questions/topics.embedding_model`, `artefacts.declared_total_marks`, finding `marks_total_mismatch`, `409 SCORES_EXCEED_RUBRIC`); rejected paper/CLO versioning tables, persisted similarity-match table, SIS/sections/released results/blind grading | Reproducible, defensible findings at column-level cost; rejected items violate §2 non-goals and would re-introduce the only partition-scale table (ADR-13) |
| D-018 | 2026-09-06 | Three-lens DB review (security / integrity / pragmatist) → ADR-14: `course_owner()` hides soft-deleted courses; functions SECURITY INVOKER, `seed_demo`/`reset_demo` assert owner-or-admin; explicit `run_events`/`usage_logs` RLS; `run_inputs` → nullable artefact/course + `run_input_role` enum; `attainment_results.target_code` copied; `normalize_qnum()` on both `questions.number` and `marks_rows.question_number` + `marks_question_mismatch` finding; IDENTITY not bigserial; final run stage single tx; RLS lands Phase 1 (app-layer ownership checks mandatory from Phase 0); hosted Supabase only (no local Docker); demo fixtures TXT/CSV-first + second course `CSE 2101`, authored in Phase 0; `0006` P2 tables may slip to Phase 4 | Fixes 3 High security findings (deleted-course leak, demo-fn abuse, cross-owner vector search), the silent marks-join drop, and the two biggest schedule risks (RLS in Phase 0, fixtures in Phase 2) without dropping the DB-as-authz principle |
| D-020 | 2026-09-06 | Backend hosted on Render free tier via `render.yaml` Blueprint (Python 3.12, `rootDir: backend`, migrations in `startCommand`, `--workers 1`); DB stays on Supabase; uploads on ephemeral local disk | Zero-cost, git-push deploy; `preDeployCommand` is paid-only so migrations chain into start; single worker required by in-process runs/rate limiter; Supabase already holds the data |
| D-019 | 2026-09-06 | `seed_demo()` inserts fully structured demo rows (questions, CO/topic maps, 280 marks rows, rubric, answers, grader scores) with `status='done'`; fixture files mirror them. Backend `POST /demo/seed` only pushes bytes to Storage and pre-runs P1/P4. `normalize_qnum` = lowercase, drop leading q/question, strip whitespace and `().-_` | Demo must not depend on LLM extraction succeeding; one normalisation rule shared by DB CHECK and backend |
| D-020 | 2026-09-06 | In-use guard FKs (`question_co_map_co_fk`, `run_inputs_artefact_fk`, `run_inputs_course_fk`) are `NO ACTION DEFERRABLE INITIALLY DEFERRED`, not `RESTRICT` | `RESTRICT` broke `reset_demo()`'s cascading course delete (found by `test_functions.sql`); deferred check still yields 409 on direct deletes, evaluated at COMMIT — backend must catch `IntegrityError` on commit, not on flush |

## 7. Conventions

- Commits: Conventional Commits with scope `feat(fe|be|db): …`; branches `fe/<task>`, `be/<task>`, `db/<task>`; one task ID per PR; squash-merge (architecture.md §40)
- Ownership: `frontend/**` FE, `backend/**` + compose/CI/.env.example BE, `database/**` DB. Never edit another engineer's files; contract artefacts (`backend/openapi.json`, `backend/app/db/models.py`) have single writers (§37)
- API: `/api/v1`, error envelope `{error:{code,message,details,request_id}}`, pagination `items/page/page_size/total` (§19); `X-Request-Id` on every response
- DB: snake_case, plural tables, uuid PKs, `created_at/updated_at`, FKs with explicit ON DELETE; enums stored as varchar(32) (portable); Alembic `revision --autogenerate` after model changes
- AI: all calls via `ai/client.structured_call`, documents wrapped by `ai/guard.wrap_untrusted`, temperature 0, every output has `rationale`; prompts live in `*/prompts.py` with `PROMPT_VERSIONS`; never log document text or tokens
- Background work: `RunContext.emit/warn` write `run_events` in their own short transaction — never emit while another write session is open (SQLite single-writer)
- Tests: `pytest` from `backend/`; API tests go through httpx `ASGITransport` with `X-Dev-User` per user; use `mock_provider.queue(purpose, raw|Exception)` for failure paths

## 8. Current State / What's Done

- [x] Repository initialised
- [x] Project context + agent instructions added
- [x] `AGENTS.md` + `CLAUDE.md` added for non-Copilot agents
- [x] Requirements locked (§12)
- [x] `architecture.md` written: stack, 45 sections, API contract, DB schema (24 tables, RLS, functions, views), file-level plan for 3 engineers; merge-audit amendments applied (ADR-13 / D-017)
- [x] `database/` implemented: 12 migrations, RLS on 21 tables, 8 helper fns, `similar_questions/topics`, `compute_co_attainment`, `reset_demo`, `seed_demo` (2 courses, planted defects), 4 views, 3 SQL test files, apply/test scripts (sh + ps1). **Validated locally on `pgvector/pgvector:pg15`: apply ×2 idempotent, all 3 test suites green.** Not yet applied to a Supabase project.
- [x] `.vscode/mcp.json` with Supabase + Context7 MCP servers
- [x] Backend Supabase auth: `AUTH_MODE=supabase` verifies ES256/RS256 tokens via JWKS (HS256 fallback); `backend/.env` has `SUPABASE_URL`/`SUPABASE_PUBLISHABLE_KEY`/`SUPABASE_JWKS_URL` filled for project `etzxqeilgohiavdeybbw`, `SUPABASE_SECRET_KEY` left for the developer to paste locally
- [x] **Backend Tier 0** (`backend/`): FastAPI app, config, structlog + request ids, error envelope, SQLite/Postgres ORM (15 tables) + Alembic initial migration, auth (dev/Supabase JWT), courses CRUD, COs/POs/CO–PO map/topics replace-all, artefact upload (pdf/docx/txt/paste, magic-byte + size validation) with background extraction, faculty confirm/edit of questions + CO map, `exam_audit` pipeline (embed → map & Bloom → duplicate confirm → deterministic stats → findings), runs + SSE events + idempotency, findings accept/dismiss/reopen, Markdown export, demo seed from `data/seed-data`, `/health` `/readyz`, Swagger/ReDoc. 47 tests green; live smoke test on demo data reproduces planted flaws (CO6 uncovered, 58 vs 60 marks, 3 duplicate pairs, Bloom skew).

## 9. Next Steps / TODO

- [x] Lock requirements (Prompt 1)
- [x] Architecture design (Prompt 2) → `architecture.md`
- [ ] Phase 0 contracts: hosted Supabase project (Auth providers, `artefacts` bucket), **apply `database/` (DB-00, DB-01…DB-05 done as code)**, backend Pydantic schemas + `openapi.json`
- [x] Demo fixtures authored (TXT/CSV, 2 courses) — `database/seeds/fixtures/`
- [ ] Run `database/scripts/run_tests.*` against the hosted project; fix anything Supabase-specific (`auth.users` insert in tests, `SET ROLE app_backend` membership)
- [ ] Phase 1 foundation: FE scaffold + auth, BE skeleton + `/me` + ORM parity + service-layer ownership checks; DB: CI job (`pgvector/pgvector:pg15`, `reset_local.sh`)
- [ ] Phase 2–3 (Tier 0): ingestion/extraction, P1 Exam Auditor, findings + accept/dismiss, demo seed → W1 live
- [ ] Tier 1: P4, P3, P2, export, question suggestion
- [ ] Tier 2: SSE progress, Bangla support, system-admin panel (users, runs, LLM usage)
- [ ] Tier 3: dashboard, paper version compare, department-admin views
- [ ] Author demo data set before module coding (see §10)

## 10. Known Issues & Gotchas

- Demo depends on venue network (Supabase + LLM API). Keep the one-click demo seed and partial-result fallback working.
- Scanned/image PDFs are unsupported — prompt faculty to paste text.
- Demo data is on the critical path: 1 course, 5–6 COs, 2 past papers, 1 draft paper with deliberate gaps/duplicates, marks CSV with one weak CO, rubric + 6 typed answers × 2 graders (2 divergent). Seed both a faculty and an admin account. Cache last successful analysis JSON for the seed course as offline fallback. Watch LLM quota during the pitch.
- `grader_scores.score ≤ rubric_criteria.max_score` cannot be a DB CHECK (rubric and answers are separate artefacts) — enforced in backend at calibration run start (`409 SCORES_EXCEED_RUBRIC`). Same for `marks_rows.question_number` → `questions.number`: no FK possible; both sides pass through `normalize_qnum()` and unmatched numbers become a `marks_question_mismatch` finding.
- Doc nits still open in `architecture.md`: IDs `AI-005/006`, `DATA-002`, `NF-005`, `OPT-*` referenced there are not defined in §12 below.
- Migrations `0001` (role creation) and `0003` (trigger on `auth.users`) need the superuser `SUPABASE_DB_URL`, not `app_backend`.
- `reset_demo`/`seed_demo` called by an admin switch `app.user_id` to the target owner for the rest of the transaction — backend must call them in a dedicated transaction.
- `test_rls.sql` inserts directly into `auth.users` and does `SET ROLE app_backend`; both work on plain Postgres, verify on Supabase (auth.users NOT NULL columns; membership granted in `0001`).
- Backend must normalise question numbers exactly like `normalize_qnum()` (`lower`, drop leading `q`/`question`, strip whitespace and `().-_`) or the CHECK rejects inserts.
- `OUTCOME_IN_USE` / `ARTEFACT_IN_USE` FKs are deferred: the violation surfaces at `COMMIT`, so the backend's 409 mapping must wrap the commit, not just the statement.
- Local validation: `database/scripts/ci_container.sh` runs inside a `pgvector/pgvector:pg15` container (`docker cp database <ctr>:/database`, strip CRLF with `sed`, then run). No local `psql` needed.
- Transaction pooler (6543): use `SET LOCAL` (never `SET`) for RLS vars; asyncpg `statement_cache_size=0`.
- Supabase project ref `etzxqeilgohiavdeybbw`, region ap-south-1. Prefer the IPv4 shared pooler `aws-0-ap-south-1.pooler.supabase.com` (user `postgres.etzxqeilgohiavdeybbw`): 6543 transaction mode for the app, 5432 session mode for migrations/psql. Direct host `db.etzxqeilgohiavdeybbw.supabase.co:5432` (user `postgres`) is IPv6-only. `DATABASE_URL` must use `postgresql+asyncpg://`, no `?pgbouncer=true` (Prisma-only); percent-encode special characters in the password. Password lives only in gitignored `backend/.env`.
- Supabase dashboard's ORM quick-start suggests Prisma — **not used**; backend ORM is SQLAlchemy 2 + asyncpg (D-013). Ignore `npm install prisma` / `prisma init` steps.
- Optional: `npx skills add supabase/agent-skills` installs Supabase agent skills for AI tooling (not required by the build).
- Supabase JWT may be ES256 (JWKS) or HS256 (legacy secret) — both supported by `backend/app/auth/jwt.py`; real-token check against the live project still pending (needs frontend login flow).
- `backend/tests` occasionally fail with `sqlite3.OperationalError: attempt to write a readonly database` when run inside the VS Code terminal sandbox; delete `backend/tests/.test.db*` and rerun (full suite: 51 passed).
- WeasyPrint needs system libs; run backend in Docker or accept md-only export locally (current build: Markdown export only).
- Backend background tasks (extraction, runs) are in-process asyncio tasks: run **one uvicorn worker**; on restart, in-flight runs are marked `failed` at startup. Rate limiter is per-process.
- SQLite is single-writer: never call `RunContext.emit/warn` while another `session_scope()` write is open (caused `database is locked` → run `failed`). Deferred-warnings pattern in `exam_audit/graph.py`.
- Do not mutate ORM objects after `db.commit()` inside a request when a background task owns the row — the request's final commit overwrote the task's status (fixed in `ArtefactService`).
- `MockProvider` heuristics are lexical; with `LLM_PROVIDER=mock` the demo still reproduces CO6-uncovered / marks mismatch / duplicates, but CO mapping quality is only indicative. Use a real key for judging.
- Render free tier: instance sleeps after 15 min idle (cold start 30–60 s — warm it before the pitch); disk is ephemeral so uploaded files under `STORAGE_DIR` are lost on redeploy while DB rows persist. Attach a Render Disk + set `STORAGE_DIR` to its mount if needed. Render runs Python 3.12 (pinned), local dev is 3.14.
- Python 3.14 venv: `ensurepip` may be missing → `python3 -m venv --without-pip .venv && pip3 --python .venv/bin/python install pip`.

## 12. Locked Product Scope (Prompt 1 output, 2026-09-06)

**Actors:** faculty member (primary, decision-maker); admin (read-only oversight, CF-001).

**Mandatory (Core):** REQ-F-001–004 (submit artefact, AI evaluates not generates, useful result, faculty decides); REQ-F-010 Course workspace (syllabus + CO list + CO→PO map); F-011 PDF/DOCX/TXT/CSV/XLSX ingestion + paste; F-012 structured extraction (questions w/ marks, topics, COs) with faculty confirm/edit step; F-013 per-item evidence; F-014 loading/failure/empty states; F-020 login; F-021 export accepted findings (MD/PDF); F-022 accept/dismiss finding; DATA-001 persist courses/artefacts/runs/findings; NF-003 <30 s per analysis; NF-004 one-click demo seed; AI-001 JSON-schema outputs; AI-002 retry once → partial; AI-003 rationale + evidence_snippet on every finding; AI-004 deterministic arithmetic; SEC-001 untrusted-document prompt delimiting; SEC-002 keys server-side; SEC-003 upload allow-list/size cap; SEC-004 no raw-HTML rendering; SEC-005 RLS by owner_id; SEC-006 per-user rate limit; SEC-007 anonymised student IDs; SEC-008 service-role key never client-side.

**P1 Exam Auditor:** F-101 extract questions; F-102 question→topic/CO map w/ confidence; F-103 coverage/uncovered/over-weighted; F-104 Bloom's level (6-level enum) + diversity; F-105 near-duplicate vs past papers (pgvector cosine, LLM confirms); F-106 marks fairness; F-107 bounded question _suggestion_ for uncovered COs; F-108 diff two runs.
**P4 Attainment:** F-401 marks CSV/XLSX; F-402 question→CO + CO→PO mapping (reuse P1); F-403 deterministic attainment; F-404 AI explanation + actions.
**P3 Syllabus:** F-301 draft syllabus + comparison courses; F-302 overlap matrix; F-303 gaps/prerequisites; F-304 repositioning notes.
**P2 Calibration:** F-201 rubric + typed answers (+ ≥2 graders' scores); F-202 divergence report + explanation; F-203 AI pre-score w/ rationale; F-204 rubric v2 proposal; NF-201 no OCR.
**Other selected:** F-023 cross-course dashboard; F-024 SSE progress; NF-006 Bangla/mixed text.
**Admin panel (CF-001):** F-030 admin route guard; F-031 user list + enable/disable; F-032 all courses/runs browser; F-033 LLM usage/cost per user (`UsageLog` written per LLM call); F-034 demo-seed reset; F-035 department CO–PO attainment view (all faculty, read-only, "Department Head view"); F-036 department exam-audit summary; SEC-009 admins cannot edit findings.

**Pages:** `/login`, `/` courses, `/courses/:id` (setup, artefacts, run history), `/courses/:id/{exam-audit|attainment|syllabus-check|calibration}/new` and `/:runId`, `/courses/:id/exam-audit/compare`, `/dashboard`, `/admin` (users, runs, usage, seed reset), `/admin/department` (attainment + audit summaries).

**Preliminary data model:** User → Course → CourseOutcome(po_map); Artefact(kind, storage_path, extracted_text, lang); Question(marks, bloom_level, co_ids, embedding); Topic(embedding); Run(module, status, summary); Finding(type, severity, evidence_snippet, rationale, status open|accepted|dismissed, payload); AttainmentResult; MarksRow(student_anon_id); UsageLog(user_id, run_id, model, tokens_in/out, cost).

**Build tiers:** T0 auth + workspace + ingestion + P1 + findings + seed · T1 P4, P3, P2, export, suggestions · T2 SSE, Bangla · T3 dashboard, compare.

**Assumptions:** A-001 superseded by login; A-002 web app; A-003/A-005 resolved by D-014; A-004 module order. Open for architect: none — see `architecture.md`.

## 11. Changelog

| Date       | Who     | Change                                                                                                             |
| ---------- | ------- | ------------------------------------------------------------------------------------------------------------------ |
| 2026-09-06 | Copilot | Created PROJECT_CONTEXT.md and agent instructions                                                                  |
| 2026-09-06 | Copilot | Added AGENTS.md and CLAUDE.md pointing agents to PROJECT_CONTEXT.md                                                |
| 2026-09-06 | Copilot | Requirements locked: 4-module Faculty Copilot scope, Supabase, tiered build (D-003–D-008, §12)                     |
| 2026-09-06 | Copilot | Added admin panel CF-001 (system + department views, D-009), demo-data critical-path notes                         |
| 2026-09-06 | Copilot | Added `.vscode/mcp.json` (Supabase + Context7 MCP servers, D-010)                                                  |
| 2026-09-06 | Copilot | Wrote `architecture.md` (React/FastAPI/Supabase/LangGraph/OpenRouter); filled Tech Stack, conventions, D-011–D-016 |
| 2026-09-06 | Copilot | Merge audit vs external versioned-assessment design: provenance/copy-at-write columns, `marks_total_mismatch`, `SCORES_EXCEED_RUBRIC` (D-017, ADR-13); filled §3 stack table + env names; added `architecture.md` to §4 |
| 2026-09-06 | Copilot | Multi-agent DB review (security/integrity/pragmatist) → ADR-14 / D-018: RLS hardening, `run_inputs` redesign, `normalize_qnum`, `target_code`, IDENTITY, phase re-sequencing, fixture plan; fixed `compute_co_attainment` signature + removed `alembic/` |
| 2026-09-06 | Copilot | Added `database_implementation_plan.md` (user-requested): per-migration contents, RLS policy matrix, seed spec, SQL test list, phase gates, BE contracts |
| 2026-09-06 | Copilot | Implemented `database/`: migrations 0001–0012, seed_demo + fixtures (2 courses), seed_admin, 3 SQL test suites, apply/test scripts; D-019 |
| 2026-09-06 | Copilot | Validated `database/` on pgvector:pg15 (apply ×2 + 3 suites green); in-use FKs → deferred NO ACTION (D-020); added `scripts/ci_container.sh` |
| 2026-09-06 | Copilot | `edge_cases.md`: added §14 access-pattern queries Q1–Q16 with volume/latency budgets and per-query edge cases |
| 2026-09-06 | Copilot | Render deploy: `render.yaml` Blueprint + `backend/.python-version`, README deploy section (D-020) |
