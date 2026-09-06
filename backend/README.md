# Faculty Copilot — Backend

FastAPI backend for the **Faculty Assessment & Curriculum Copilot** (AI Build Hackathon, theme *AI for Academic Life*).

## Overview

**Problem.** Setting a fair exam paper is slow, error-prone work: does every Course Outcome (CO) get assessed? Are marks
balanced? Does the paper accidentally repeat last year's questions? Do the questions total what the cover page says?

**Workflow this backend implements (P1 — Exam Paper Auditor):**

```
Faculty creates a course workspace (COs, syllabus topics)
        ↓
Uploads a DRAFT question paper (+ optional past papers) — PDF/DOCX/TXT or pasted text
        ↓
Backend extracts questions (AI, structured JSON) → faculty confirms/edits them
        ↓
Faculty starts an "exam_audit" run
        ↓
AI maps each question → COs / topics / Bloom level, confirms near-duplicate pairs
Deterministic code computes coverage, Bloom balance, marks total, fairness
        ↓
Findings (title, rationale, evidence snippet, severity, provenance) are persisted
        ↓
Faculty accepts / dismisses each finding → exports accepted findings as Markdown
```

AI **evaluates and explains**; all arithmetic is deterministic; the faculty member is the decision-maker.

## Architecture

```
Frontend (React SPA)  ──HTTP/JSON + SSE──▶  FastAPI  /api/v1
                                              │
                    router → service → repository (SQLAlchemy 2 async)
                                              │
                 ┌───────────────┬────────────┴───────────┐
           extraction      modules/exam_audit           ai/
        (documents → rows)  (pipeline, stats)   client.structured_call
                                                 providers: OpenAI-compatible / OpenRouter / Mock
                                              │
                                    PostgreSQL (prod)  ·  SQLite (dev/tests)
```

- `app/main.py` app factory, middleware (request id, CORS), routers, lifespan (stale-run sweep, PO seed)
- `app/config.py` pydantic-settings — **all secrets via environment**
- `app/errors.py` one error envelope `{"error": {"code","message","details","request_id"}}`
- `app/deps.py` DB session per request, auth (`dev` | `supabase` JWT), in-memory per-user rate limiter
- `app/db/` ORM models + enums (portable SQLite/Postgres types), Alembic in `alembic/`
- `app/courses`, `app/outcomes`, `app/artefacts`, `app/runs` — router / schemas / service / repository
- `app/artefacts/parsers.py` PDF/DOCX/TXT text extraction, magic-byte sniffing, heuristic splitters
- `app/extraction/` LLM structured extraction (questions, syllabus topics) as background tasks
- `app/modules/exam_audit/` pipeline (`graph.py`), prompts, output schemas, deterministic `stats.py`
- `app/ai/` provider interface, `structured_call` (schema validation, retry, fallback models, usage log), `guard.wrap_untrusted`
- `app/runs/orchestrator.py` asyncio runner writing `run_events` (SSE) — queue seam for Celery/Redis later
- `app/demo/` seeds the labelled sample dataset from `../data/seed-data`

## Requirements

- Python **3.11+** (developed on 3.14)
- PostgreSQL 15+ for production (Supabase works); **no database install needed locally** — SQLite is the default
- An OpenAI-compatible LLM API key (OpenRouter recommended) for real analysis; `LLM_PROVIDER=mock` works offline

## Installation

```bash
cd backend
python3 -m venv .venv            # if ensurepip is missing: python3 -m venv --without-pip .venv && pip3 --python .venv/bin/python install pip
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then edit
```

## Environment

All configuration is read from `backend/.env` (never committed). See `.env.example` for every variable. Key ones:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./dev.db` (default) or `postgresql+asyncpg://user:pass@host:6543/postgres` |
| `AUTH_MODE` | `dev` = fixed local faculty user, optional `X-Dev-User: email` header · `local` = email+password sign-in → HS256 JWT (see below) · `supabase` = verify Supabase JWT (JWKS / `SUPABASE_JWT_SECRET`) |
| `JWT_SECRET`, `JWT_TTL_S`, `SEED_*_EMAIL/PASSWORD` | `local` mode: signing secret (≥32 chars), token lifetime, the faculty and admin accounts created at startup |
| `LLM_PROVIDER` | `mock` (offline heuristics, tests) · `openrouter` · `openai_compatible` |
| `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_FALLBACK_MODELS` | model gateway; `EMBED_*` default to the same gateway |
| `CORS_ORIGINS`, `MAX_UPLOAD_MB`, `STORAGE_DIR`, `SEED_DATA_DIR`, `RATE_LIMIT_ENABLED` | runtime knobs (relative paths resolve against `backend/`) |

### Sign-in (`AUTH_MODE=local`)

There is **no sign-up**. Accounts come from `SEED_FACULTY_*` / `SEED_ADMIN_*` in `.env` (created or password-refreshed on every startup) or are inserted by an operator. Passwords are PBKDF2-HMAC-SHA256 in `profiles.password_hash`.

```bash
curl -s localhost:8000/api/v1/auth/login -H 'content-type: application/json' \
  -d '{"email":"teacher@aust.edu","password":"Teacher#2026"}'
# → {"access_token":"…","token_type":"bearer","expires_at":…,"user":{…,"role":"faculty","dashboards":[…],"permissions":[…]}}
curl -s localhost:8000/api/v1/me -H "Authorization: Bearer $TOKEN"
```

- Token claims: `sub` (profile id), `email`, `role`, `iss=faculty-copilot-api`, `aud=faculty-copilot`, `exp`. The `role` claim is informational only — permissions are always read from `profiles.role` in the DB.
- SSE: pass `?access_token=` (EventSource cannot set headers).
- `POST /auth/change-password`, `POST /auth/logout` (stateless; client drops the token).
- `GET /auth/permissions` (public) returns the role → dashboards/permissions matrix; the same rows live in the `role_permissions` table (synced from `app/db/enums.py::ROLE_PERMISSIONS` at startup).

| Dashboard / action | faculty | admin |
|---|---|---|
| `/` courses, course workspace, exam-audit, attainment, syllabus-check, calibration, `/dashboard` | ✓ | ✓ (read-only, own view) |
| `/admin`, `/admin/department`, `admin:users/runs/usage` | – | ✓ |
| create/edit courses & outcomes, upload/confirm artefacts, start runs, accept/dismiss findings, demo seed | ✓ | – (`403 PERMISSION_DENIED`) |

Live check of the whole flow (sign-in → every page → run → decide → export): `python scripts/audit_auth_flow.py http://localhost:8000`.

## Database

```bash
alembic upgrade head          # apply migrations (SQLite or Postgres, from DATABASE_URL)
alembic downgrade base        # roll back
alembic revision --autogenerate -m "describe change"
```

## Running

```bash
uvicorn app.main:app --reload                              # http://localhost:8000
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload   # on the LAN
```

- Swagger UI: http://localhost:8000/docs · ReDoc: http://localhost:8000/redoc · OpenAPI: `/api/v1/openapi.json`
- Liveness `GET /api/v1/health` → `{"status":"ok"}` · Readiness `GET /api/v1/readyz` → `{db, llm, provider, env}`

## Deploying to Render

`render.yaml` at the repo root is a Render Blueprint (Dashboard → New → Blueprint → select this repo). It creates one
free-tier Python web service with `rootDir: backend`, Python 3.12 (`PYTHON_VERSION` / `.python-version`),
`buildCommand: pip install -r requirements.txt` and
`startCommand: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
(migrations run at start because `preDeployCommand` is paid-only). Health check: `/api/v1/health`.

Set these secrets in the Render UI (marked `sync: false`): `DATABASE_URL` (Supabase **transaction pooler 6543**,
`postgresql+asyncpg://`, password percent-encoded), `CORS_ORIGINS` (deployed frontend origin), `SUPABASE_URL`,
`SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, `LLM_API_KEY`. Everything else has a value in the blueprint.

Notes: the free instance sleeps after 15 min idle (first request ~30–60 s) and its disk is **ephemeral** — uploaded
files in `STORAGE_DIR` vanish on redeploy (DB rows survive in Supabase). Attach a Render Disk and point `STORAGE_DIR`
at its mount path if persistence matters. Keep `--workers 1` (in-process runs + rate limiter).

## API (summary)

Base `/api/v1`. Auth header `Authorization: Bearer <token>` in `supabase` mode; nothing needed in `dev` mode.

| Method | Path | Purpose |
|---|---|---|
| GET | `/me` | current profile |
| GET/POST | `/courses` · GET/PATCH/DELETE `/courses/{id}` | course workspace (soft delete) |
| GET | `/program-outcomes` | global PO1–PO12 |
| GET/PUT | `/courses/{id}/outcomes` · `/co-po-map` · `/topics` | replace-all editors (`409 OUTCOME_IN_USE`) |
| POST | `/courses/{id}/artefacts` (multipart `kind,label,file|text,declared_total_marks?`) | upload → `202`, background extraction |
| GET | `/courses/{id}/artefacts` · `/artefacts/{id}` · `/artefacts/{id}/text` | status polling |
| DELETE / POST | `/artefacts/{id}` · `/artefacts/{id}/reextract` | `409 ARTEFACT_IN_USE` if a finished run uses it |
| GET/PUT | `/artefacts/{id}/questions` · PUT `/questions/co-map` | faculty confirm/edit step; faculty mapping overrides AI |
| POST | `/courses/{id}/runs` `{module, inputs, params?}` | `202 RunOut`; `Idempotency-Key` supported (same key + different payload → `409 IDEMPOTENCY_KEY_REUSED`). Modules: `exam_audit {draft_artefact_id, past_artefact_ids[]}` · `attainment {marks_artefact_id, paper_artefact_id, threshold}` · `syllabus_check {syllabus_artefact_id, compare_course_ids[]}` · `calibration {rubric_artefact_id, answer_set_artefact_id}` |
| GET | `/courses/{id}/runs` · `/runs/{id}` · `/runs/{id}/events` (SSE) | progress: `queued → analyzing → completed|partial|failed` |
| GET | `/runs/{id}/findings?type&status&severity` | findings ordered by severity |
| PATCH | `/findings/{id}` `{status: accepted|dismissed|open}` | faculty decision |
| GET | `/runs/{id}/export?format=md|pdf&include=accepted|all` | Markdown report (`503 EXPORT_PDF_UNAVAILABLE` without WeasyPrint) |
| GET | `/runs/compare?a&b` · `/runs/{id}/attainment` · `/runs/{id}/prescores` · POST `/runs/{id}/suggest-questions` | module-specific results (Tier 1) |
| GET/PUT | `/artefacts/{id}/marks` (GET) · `/artefacts/{id}/rubric` · `/artefacts/{id}/answers` | Tier 1 artefact data (marks_sheet / rubric / answer_set) |
| GET | `/dashboard/summary` | cross-course summary |
| GET/PATCH | `/admin/users` · `/admin/runs` · `/admin/usage` · `/admin/department/{attainment|exam-audits}` · POST `/admin/demo/reset` | admin (role=admin, read-only over faculty data) |
| POST/GET | `/auth/login` · `/auth/logout` · `/auth/change-password` · `/auth/permissions` | `AUTH_MODE=local` email+password sign-in |
| POST | `/assistant/chat` | scoped assistant over the caller's own data |
| POST | `/demo/seed` | one-click demo course (labelled sample data) |
| GET | `/health` · `/readyz` | liveness / readiness (db + llm) |

Error codes: `VALIDATION_ERROR 422`, `UNAUTHENTICATED 401`, `FORBIDDEN / USER_INACTIVE / PERMISSION_DENIED 403`, `*_NOT_FOUND 404`,
`COURSE_CODE_EXISTS / OUTCOME_IN_USE / ARTEFACT_IN_USE / ARTEFACT_NOT_READY / COURSE_HAS_NO_OUTCOMES / RUN_NOT_COMPLETED / IDEMPOTENCY_KEY_REUSED / SCORES_EXCEED_RUBRIC 409`,
`FILE_TOO_LARGE 413`, `UNSUPPORTED_FILE_TYPE 415`, `ARTEFACT_NO_TEXT 422`, `RATE_LIMITED 429`, `INTERNAL 500`,
`DB_UNAVAILABLE / LLM_UNAVAILABLE / EXPORT_PDF_UNAVAILABLE / SEED_DATA_MISSING / AUTH_MISCONFIGURED 503`. Full list: `GET /api/v1/openapi.json`.

## Testing

```bash
pytest            # 96 tests: unit (stats, parsers, guard, AI client w/ respx, JWT), API (auth, courses, artefacts, runs, Tier 1 modules, QA regressions)
```

Tests use SQLite and the deterministic `MockProvider`; **no real LLM calls**. Failure paths covered: invalid JSON from the
model (retry → `partial`), provider timeout, unknown codes dropped, oversized/wrong-type/blank uploads, cross-user isolation,
expired/invalid JWTs, rate limiting.

## AI configuration

- `LLM_PROVIDER=openrouter` + `LLM_API_KEY` + `LLM_MODEL=openai/gpt-4o-mini` is the intended demo setup;
  `LLM_FALLBACK_MODELS` are tried after the primary fails. Strict JSON-schema output, temperature 0, 60 s timeout, 1 retry.
- Every LLM output is validated with Pydantic (`extra="forbid"`); unknown CO/topic codes are dropped and logged as run warnings.
- Documents are wrapped in `<<<UNTRUSTED_DOCUMENT>>>` fences (`ai/guard.py`) — prompt-injection resistant, length-capped.
- `LLM_PROVIDER=mock`: deterministic lexical heuristics; used for tests and as an offline demo fallback (labelled `model: mock`).
- Each call is recorded in `usage_logs` (model, tokens, latency, status).

## Security

- Secrets only via environment; nothing hard-coded, `.env` git-ignored, API keys never reach the client.
- Uploads: magic-byte sniffing (extension alone is not trusted), size cap, server-generated storage paths.
- Ownership enforced in the service layer (non-owners get `404`, no existence leak); admins are read-only on findings.
- Pydantic validation everywhere; ORM only (no raw SQL); controlled error envelope (no stack traces).
- Per-user in-memory rate limit on run creation (10/min) and uploads (20/min).

## Demo workflow (≈2 minutes)

1. `POST /api/v1/demo/seed` → course **CSE 3103** with 6 COs, CO→PO map, 14 topics, two past papers and one **flawed draft**.
2. `GET /courses/{id}/artefacts` → pick the `[DRAFT]` paper (already extracted — normally you'd confirm `GET/PUT /artefacts/{id}/questions`).
3. `POST /courses/{id}/runs` with the draft + past paper ids → open `/runs/{id}/events` to watch the stages.
4. `GET /runs/{id}/findings` → expected: **CO6 uncovered**, **58 vs 60 marks**, **3 duplicate pairs** with evidence, Bloom skew, CO1 over-weighted.
5. `PATCH /findings/{id}` accept/dismiss → `GET /runs/{id}/export` downloads the accepted findings as Markdown.

## Limitations (this build)

- Duplicate search is in-process cosine (fine for course-scale data); pgvector can replace it without API changes.
- Scanned/image PDFs are not OCR'd → `422 ARTEFACT_NO_TEXT` (paste text instead). PDF export needs WeasyPrint system libs, otherwise `503 EXPORT_PDF_UNAVAILABLE` (Markdown always works).
- Uploads are bounded: `MAX_UPLOAD_MB` on the body, ≤200 PDF pages, extracted text capped at 200 000 chars, 20 s parse timeout. The multipart body is still spooled to disk before auth runs (FastAPI form parsing order).
- Files are stored on local disk (`STORAGE_DIR`); Supabase Storage is a drop-in `StorageBackend`.
- Rate limiter and run queue are in-process (run with `--workers 1`). SSE auth via `?access_token=` shows up in uvicorn access logs — use `--no-access-log` in production.
- `AUTH_MODE=dev` is refused when `ENV=prod`.
