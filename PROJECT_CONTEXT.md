# Project Context

> Living document. Every agent and contributor MUST read this before working and update it after making changes.
> Last updated: 2026-09-06

## 1. Overview

- **Name:** aust_hackathon26 — working title **Faculty Assessment & Curriculum Copilot**
- **Purpose:** AI tool for AUST faculty (AI Build Hackathon final, theme "AI for Academic Life"). Faculty upload syllabi, question papers, marks sheets, rubrics + answers → AI evaluates/compares → evidence-backed findings faculty accept or dismiss. AI advises; faculty decide.
- **Status:** Requirements locked (see §12); architecture design next; no source code yet
- **Repository:** md-sazid9089/aust_hackathon26 (branch `main`)

## 2. Goals & Non-Goals

**Goals**
- Judges see: problem → input → what the AI does → useful result, live.
- One shared Course workspace (syllabus + Course Outcomes) reused by four modules: P1 Exam Paper Auditor, P4 CO–PO Attainment Analyst, P3 Syllabus Overlap/Gap Analyzer, P2 Grading Consistency Calibrator.
- Every finding carries rationale + evidence snippet; faculty accept/dismiss; export accepted findings.

**Non-goals**
- Student-facing views, LMS/Moodle integration, handwriting OCR, "ask anything" chatbot, fine-tuning, attendance/timetable, internet plagiarism checks, full academic management platform.

## 3. Tech Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Language | _TODO (architect)_ | |
| Frontend | _TODO (architect)_ | web app, desktop-first responsive |
| Backend | _TODO (architect)_ | server-side LLM calls, SSE progress |
| Database / Auth / Storage | **Supabase** (Postgres + pgvector, Auth, Storage) | D-004; RLS on `owner_id` |
| AI | Hosted LLM with JSON-schema output + embeddings (vendor TBD, A-005) | D-007 |
| Tooling | _TODO (architect)_ | package manager, linter, test runner |

Environment variables (names only): `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `LLM_API_KEY`.

## 4. Project Structure

```
aust_hackathon26/
├── .github/
│   └── copilot-instructions.md   # Copilot-specific rules (points here)
├── AGENTS.md                     # generic agent rules (points here)
├── CLAUDE.md                     # Claude entry point, imports AGENTS.md
└── PROJECT_CONTEXT.md            # this file — single source of truth
```

## 5. How to Run

```bash
# install
# TODO

# dev
# TODO

# test
# TODO
```

## 6. Architecture & Key Decisions

| ID | Date | Decision | Why |
|----|------|----------|-----|
| D-001 | 2026-09-06 | Keep a single `PROJECT_CONTEXT.md` as the shared source of truth for agents | Avoids context loss between sessions and contributors |
| D-002 | 2026-09-06 | Agent instruction files (`copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md`) stay thin and only redirect to `PROJECT_CONTEXT.md` | One place to maintain; works across Copilot, Claude, and other tools |
| D-003 | 2026-09-06 | Single unified app with a shared Course core; four modules layered in order P1 → P4 → P3 → P2 | P1/P4/P3 all reuse the same CO list; P2 has highest data-prep risk; each module droppable at demo time |
| D-004 | 2026-09-06 | Supabase for auth, DB, storage and vector search; RLS is the authorization layer | Cheapest way to get login + pgvector in one day |
| D-005 | 2026-09-06 | Findings are first-class rows (`status`, `rationale`, `evidence_snippet`), not JSON blobs | Enables accept/dismiss, export of accepted findings, explainability |
| D-006 | 2026-09-06 | All arithmetic (attainment %, marks stats, divergence) is deterministic code; LLM only classifies, maps, explains | Correctness and verifiability over LLM output |
| D-007 | 2026-09-06 | Hosted LLM API with native structured output + embeddings endpoint; vendor left to architect | One-day build; reliability > token cost |
| D-008 | 2026-09-06 | Tiered build order (Tier 0–3, §12); Tier 3 must be droppable without core changes | User selected all optional features; brief warns against slide-only features |
| D-009 | 2026-09-06 | Admin actor added (system + department views); role in Supabase `app_metadata.role`, enforced by RLS; admin is read-only over faculty data | User request CF-001; keeps faculty as sole decision-maker |

## 7. Conventions

- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:` ...)
- Branches: `feat/<name>`, `fix/<name>`
- _TODO — code style, naming, folder rules_

## 8. Current State / What's Done

- [x] Repository initialised
- [x] Project context + agent instructions added
- [x] `AGENTS.md` + `CLAUDE.md` added for non-Copilot agents

## 9. Next Steps / TODO

- [x] Lock requirements (Prompt 1)
- [ ] Architecture design (Prompt 2): choose stack/LLM vendor, schema, folder structure
- [ ] Scaffold app + Supabase project, auth, Course workspace
- [ ] Tier 0: ingestion/extraction, P1 Exam Auditor, findings + accept/dismiss, demo seed + admin seed-reset
- [ ] Tier 1: P4, P3, P2, export, question suggestion
- [ ] Tier 2: SSE progress, Bangla support, system-admin panel (users, runs, LLM usage)
- [ ] Tier 3: dashboard, paper version compare, department-admin views
- [ ] Author demo data set before module coding (see §10)

## 10. Known Issues & Gotchas

- Demo depends on venue network (Supabase + LLM API). Keep the one-click demo seed and partial-result fallback working.
- Scanned/image PDFs are unsupported — prompt faculty to paste text.
- Demo data is on the critical path: 1 course, 5–6 COs, 2 past papers, 1 draft paper with deliberate gaps/duplicates, marks CSV with one weak CO, rubric + 6 typed answers × 2 graders (2 divergent). Seed both a faculty and an admin account. Cache last successful analysis JSON for the seed course as offline fallback. Watch LLM quota during the pitch.

## 12. Locked Product Scope (Prompt 1 output, 2026-09-06)

**Actors:** faculty member (primary, decision-maker); admin (read-only oversight, CF-001).

**Mandatory (Core):** REQ-F-001–004 (submit artefact, AI evaluates not generates, useful result, faculty decides); REQ-F-010 Course workspace (syllabus + CO list + CO→PO map); F-011 PDF/DOCX/TXT/CSV/XLSX ingestion + paste; F-012 structured extraction (questions w/ marks, topics, COs) with faculty confirm/edit step; F-013 per-item evidence; F-014 loading/failure/empty states; F-020 login; F-021 export accepted findings (MD/PDF); F-022 accept/dismiss finding; DATA-001 persist courses/artefacts/runs/findings; NF-003 <30 s per analysis; NF-004 one-click demo seed; AI-001 JSON-schema outputs; AI-002 retry once → partial; AI-003 rationale + evidence_snippet on every finding; AI-004 deterministic arithmetic; SEC-001 untrusted-document prompt delimiting; SEC-002 keys server-side; SEC-003 upload allow-list/size cap; SEC-004 no raw-HTML rendering; SEC-005 RLS by owner_id; SEC-006 per-user rate limit; SEC-007 anonymised student IDs; SEC-008 service-role key never client-side.

**P1 Exam Auditor:** F-101 extract questions; F-102 question→topic/CO map w/ confidence; F-103 coverage/uncovered/over-weighted; F-104 Bloom's level (6-level enum) + diversity; F-105 near-duplicate vs past papers (pgvector cosine, LLM confirms); F-106 marks fairness; F-107 bounded question *suggestion* for uncovered COs; F-108 diff two runs.
**P4 Attainment:** F-401 marks CSV/XLSX; F-402 question→CO + CO→PO mapping (reuse P1); F-403 deterministic attainment; F-404 AI explanation + actions.
**P3 Syllabus:** F-301 draft syllabus + comparison courses; F-302 overlap matrix; F-303 gaps/prerequisites; F-304 repositioning notes.
**P2 Calibration:** F-201 rubric + typed answers (+ ≥2 graders' scores); F-202 divergence report + explanation; F-203 AI pre-score w/ rationale; F-204 rubric v2 proposal; NF-201 no OCR.
**Other selected:** F-023 cross-course dashboard; F-024 SSE progress; NF-006 Bangla/mixed text.
**Admin panel (CF-001):** F-030 admin route guard; F-031 user list + enable/disable; F-032 all courses/runs browser; F-033 LLM usage/cost per user (`UsageLog` written per LLM call); F-034 demo-seed reset; F-035 department CO–PO attainment view (all faculty, read-only, "Department Head view"); F-036 department exam-audit summary; SEC-009 admins cannot edit findings.

**Pages:** `/login`, `/` courses, `/courses/:id` (setup, artefacts, run history), `/courses/:id/{exam-audit|attainment|syllabus-check|calibration}/new` and `/:runId`, `/courses/:id/exam-audit/compare`, `/dashboard`, `/admin` (users, runs, usage, seed reset), `/admin/department` (attainment + audit summaries).

**Preliminary data model:** User → Course → CourseOutcome(po_map); Artefact(kind, storage_path, extracted_text, lang); Question(marks, bloom_level, co_ids, embedding); Topic(embedding); Run(module, status, summary); Finding(type, severity, evidence_snippet, rationale, status open|accepted|dismissed, payload); AttainmentResult; MarksRow(student_anon_id); UsageLog(user_id, run_id, model, tokens_in/out, cost).

**Build tiers:** T0 auth + workspace + ingestion + P1 + findings + seed · T1 P4, P3, P2, export, suggestions · T2 SSE, Bangla · T3 dashboard, compare.

**Assumptions:** A-001 superseded by login; A-002 web app; A-003/A-005 hosted LLM API; A-004 module order. Open for architect: LLM vendor/model, PDF export lib, embedding dimension.

## 11. Changelog

| Date | Who | Change |
|------|-----|--------|
| 2026-09-06 | Copilot | Created PROJECT_CONTEXT.md and agent instructions |
| 2026-09-06 | Copilot | Added AGENTS.md and CLAUDE.md pointing agents to PROJECT_CONTEXT.md |
| 2026-09-06 | Copilot | Requirements locked: 4-module Faculty Copilot scope, Supabase, tiered build (D-003–D-008, §12) |
| 2026-09-06 | Copilot | Added admin panel CF-001 (system + department views, D-009), demo-data critical-path notes |
