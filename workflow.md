# Workflow — Faculty Assessment & Curriculum Copilot

> What every part of the website can do, end to end. This is the feature walkthrough for AUST faculty and admins.
> The product motto: **the AI advises, the faculty decides.** Every AI output carries a rationale and an evidence snippet, and nothing is acted on until a human accepts it.
> Last updated: 2026-09-06

---

## 1. The big picture

Faculty create a **Course workspace** (syllabus + Course Outcomes + CO→PO map), upload documents (question papers, marks sheets, rubrics, graded answers), and then run one of **four analysis modules**. Each run produces **findings** — evidence-backed observations the faculty accept or dismiss, then export.

```
Login → Course workspace → Upload artefacts → Confirm extracted data
      → Run a module → Watch live progress → Review findings
      → Accept / Dismiss → Export accepted findings
```

The four modules all reuse the same course core:

| # | Module | Answers the question |
|---|--------|----------------------|
| P1 | **Exam Paper Auditor** | Does this exam cover every CO, at the right Bloom levels, with fair marks and no duplicates from past papers? |
| P4 | **CO–PO Attainment Analyst** | From the marks sheet, which COs and POs did students actually attain, and which fell short? |
| P3 | **Syllabus Overlap / Gap Analyzer** | Does this syllabus overlap with, or depend on, other courses in the program? |
| P2 | **Grading Consistency Calibrator** | Where did two graders disagree, why, and how should the rubric be clarified? |

An in-app **Assistant** can drive most of this by chat, and an **Admin panel** gives read-only department oversight.

---

## 2. Roles

| Role | Can do |
|------|--------|
| **Faculty** (primary) | Everything below: create courses, upload, run analyses, decide findings, export, use the assistant. Sees only their own data. |
| **Admin** (oversight) | Read-only across all faculty: user management, all runs, LLM usage/cost, department attainment & exam-audit summaries, demo reset. **Cannot edit findings.** |

---

## 3. Authentication & account

- **Login** (`/login`) — email + password. Returns a session token held in the browser for the session. Supports a forced "change password on first login" flow.
- **Change password** — from the account menu at any time.
- **Logout** — clears the session.
- **Role-based routing** — faculty routes and admin routes are guarded; the wrong role is redirected.

Behind the scenes the backend supports three auth modes (`dev`, `local` email/password with signed JWT, and Supabase JWKS), selected by configuration.

---

## 4. Course workspace

### 4.1 Courses list — `/courses`
- See all your courses with **search** (by code or title) and **pagination**.
- **Create a course**: code, title, term, description. Codes are unique per owner.
- Cards preload the course page on hover for instant navigation.

### 4.2 Course detail — `/courses/:id`
A single workspace with tabs:

**Outcomes tab**
- List Course Outcomes (CO1…CON) with text, Bloom level, and weight.
- Edit the full CO list (replace-all).
- Edit the **CO→PO matrix** — map each CO to program outcomes PO1–PO12 with a strength of 1–3.

**Topics tab**
- List syllabus topics (extracted from an uploaded syllabus, or added manually).
- Confirm/edit topics after extraction.

**Artefacts tab**
- Upload or paste documents; see per-artefact status (**extracting / done / failed**).
- Manage all five artefact kinds (see §5).

**Runs tab**
- Full history of every analysis run for the course, with module, status, and summary.

- **Edit / delete course** — update metadata or soft-delete (which cascades to its artefacts, runs, and findings).

---

## 5. Uploading & preparing documents (artefacts)

You can **upload a file** or **paste text**. Supported kinds:

| Kind | Formats | What extraction pulls out |
|------|---------|---------------------------|
| **Question paper** | PDF, DOCX, TXT, MD, images | Questions (number, text, marks), AI-suggested CO mapping, AI Bloom level |
| **Syllabus** | PDF, DOCX, TXT | Topics (code, title) |
| **Marks sheet** | CSV, XLSX | Per-student scores per column (student IDs anonymised) |
| **Rubric** | PDF, DOCX, TXT | Criteria (code, text, max score, level descriptors) |
| **Answer set** | PDF, DOCX | Answer text + each grader's scores per criterion |

**OCR for scanned exams** — scanned PDFs and image uploads (`.png`, `.jpg`, `.jpeg`) are transcribed via a hybrid Vision-LLM + optional local OCR pipeline. Completely blank documents are detected and rejected without cost.

**The confirm/edit step (important):** Extraction is AI-assisted, so after it finishes you **review and correct** what was found before running an analysis:
- Confirm/edit **questions** and their marks.
- Set the **faculty Q→CO mapping** (your mapping overrides the AI's).
- Confirm/edit **topics**, **rubric criteria**, and **answers + grader scores**.

Other artefact actions: view extracted text, re-run extraction after replacing a file, and delete (blocked if a completed run depends on it).

Guardrails: file-type allow-list, size cap, decompression-bomb protection, and anonymised student IDs.

---

## 6. Running an analysis

From a course, start a module run at `/courses/:id/{module}/new`. Each module asks for its own inputs, then runs **asynchronously** while you watch a **live progress bar** (Server-Sent Events stream). Results open at `/courses/:id/{module}/:runId`.

Common behaviour for all runs:
- **Live progress** with named stages and messages.
- **Deterministic arithmetic** — all percentages, statistics, and divergences are computed in code; the LLM only classifies, maps, and explains.
- **Partial results** — if an AI stage fails, deterministic stages still complete and the run is marked `partial` rather than lost.
- **Idempotency** — re-submitting the same run doesn't double-execute.
- Runs finish as **completed**, **partial**, or **failed**.

### 6.1 P1 — Exam Paper Auditor
**Inputs:** a draft question paper + any past papers.
**Does:** embeds questions → AI maps each question to CO(s) and a Bloom level → detects near-duplicates against past papers (cosine similarity) → computes coverage %, Bloom distribution, and marks fairness → checks declared vs. summed marks.
**Findings:** uncovered COs, near-duplicate questions, unfair marks, Bloom imbalance, marks-total mismatch.
**Extra:** **Suggest questions** — AI proposes one new question per uncovered CO (bounded, advisory).

### 6.2 P4 — CO–PO Attainment Analyst
**Inputs:** a marks sheet + the mapped question paper + an attainment threshold.
**Does:** for each CO, sums each student's marks on that CO's items and checks against the threshold → computes % of students who attained each CO → rolls up PO attainment as a weighted average of linked COs → flags the weakest questions per CO.
**Findings:** COs not met, weak items, POs at risk — with AI-suggested root causes and actions.
**Result view:** CO attainment table (attained %, mean %, met/not-met), PO attainment table, and any unmatched columns.

### 6.3 P3 — Syllabus Overlap / Gap Analyzer
**Inputs:** a syllabus + other courses to compare against.
**Does:** embeds all topics → builds a similarity matrix → AI classifies candidate pairs as **overlap**, **prerequisite**, or **distinct**, with a repositioning suggestion.
**Findings:** overlapping topics across courses, prerequisite gaps, repositioning notes.
**Result view:** the relation matrix and an overlap %.

### 6.4 P2 — Grading Consistency Calibrator
**Inputs:** a rubric + an answer set graded by **two or more graders**.
**Does:** for each answer/criterion pair, computes the spread between graders and flags large divergences → AI explains *why* graders disagreed → AI suggests a reconciled pre-score (advisory) → AI proposes a clearer **rubric v2** for the ambiguous criteria.
**Findings:** grader divergences, ambiguous criteria (with proposed wording), pre-scores.
**Result view:** divergence pairs, per-criterion mean deviation, and pre-scores.
**Guardrail:** scores exceeding the rubric max are rejected at run start.

---

## 7. Findings — review & decide

Every run produces **findings**, each with:
- a **type** and **severity** (low / medium / high),
- a plain-language **title**,
- a **rationale** (why it matters),
- an **evidence snippet** (a quote or the exact calculation),
- a **target** (e.g. "Q1", "CO3", "Criterion A").

On the run page you can **filter** findings by type, status, and severity, then for each one:
- **Accept** — you agree; it's included in exports.
- **Dismiss** — you reject it.
- **Reopen** — change your mind later.

Only faculty can decide findings; admins see them read-only. The Assistant can also decide findings in bulk (e.g. "dismiss all coverage-gap findings").

---

## 8. Comparing runs

`/courses/:id/exam-audit/compare` — pick **two finished exam-audit runs** and see a side-by-side diff (e.g. coverage and findings before vs. after revising the paper).

---

## 9. Exporting

From any run: **Export** the findings as **Markdown**, choosing **accepted only** or **all**. The export includes course info, run metadata, summary stats, and each finding's rationale, evidence, target, and your decision. (PDF export gracefully falls back to Markdown on the current build.)

---

## 10. Dashboard — `/dashboard`

A cross-course summary for faculty: each course's latest exam-audit and attainment results, plus totals for runs and accepted/dismissed findings. A fast at-a-glance health check across everything you teach.

---

## 11. The Assistant (in-app chat)

A launcher floats on every page. The Assistant is scoped to **product help + actions in your own workspace** (not a general chatbot). You can attach a file to a message.

It can, on your behalf and with your permissions:
- **Courses** — list, create, rename/update, archive, and give an overview.
- **Outcomes & topics** — add or replace COs and topics.
- **Artefacts** — upload a file (and wait for extraction), paste text as an artefact, delete an artefact, and list extracted questions.
- **Analysis** — run an exam audit (optionally waiting for it to finish), fetch a run's status/summary/findings, list findings, and **accept/dismiss findings in bulk**.
- **Export** — export a run's findings to Markdown.
- **Demo** — seed the demo course.
- **End-to-end** — `analyze_attachment`: upload a paper → extract → run a full exam audit in one step, then hand you a link to the results.

Each reply summarises what happened, and can include a **navigate link** straight to the relevant page.

---

## 12. Admin panel (read-only oversight)

| Page | What it shows |
|------|----------------|
| `/admin` (Users) | All users; create users, enable/disable, change role, force password change. (Cannot demote yourself.) |
| `/admin/runs` | Every run across all faculty, filterable by module and status. |
| `/admin/usage` | LLM usage and cost, grouped by user or by day, over a date range. |
| `/admin/seed` | Reset/reload the demo course for testing. |
| `/admin/department` | **Department Head view:** latest attainment per course (COs met, weakest CO) and latest exam-audit per course (coverage %, duplicates, open findings) across all faculty. |

Admins are strictly read-only over faculty decisions — they can observe but not edit findings.

---

## 13. Demo mode

**One-click demo seed** creates a ready-made CSE 3103 course containing a syllabus, COs, a CO→PO map, past + draft question papers, a marks sheet, a rubric, and graded answers — with **deliberately planted flaws** (an uncovered CO, a marks mismatch, duplicate questions, a Bloom skew, grader divergences). Running the modules on it reproduces those flaws, making the value obvious in a live pitch. Admins can reset it anytime.

---

## 14. Behind the scenes (cross-cutting behaviour)

- **Live progress** on every run via Server-Sent Events (stages, messages, percentage, heartbeat).
- **Deterministic math, AI judgement** — arithmetic is code; the LLM only classifies/maps/explains, always with a rationale.
- **Structured, validated AI output** — JSON-schema responses, one retry, and a partial-result fallback.
- **Ownership isolation** — you only ever see your own data; others' resources return "not found".
- **Rate limits** on chat, runs, and uploads per user.
- **Bangla / mixed-language** text is supported in ingestion and prompts.
- **Consistent error envelope** with a request id for every failure.
- **Health endpoints** (`/health`, `/readyz`) for uptime and readiness checks.
```
