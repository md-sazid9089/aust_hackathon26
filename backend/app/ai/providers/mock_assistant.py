"""Deterministic keyword planner used by MockProvider for purpose `assistant_plan`.

Round 1 picks at most one tool from the message; round 2 renders the tool results as Markdown.
It never fabricates data: replies are built only from the tool results supplied in `ctx["results"]`.
"""

from __future__ import annotations

import json
import re
from typing import Any

_KIND_WORDS = {
    "syllabus": ("syllabus", "outline", "curriculum"),
    "marks_sheet": ("marks", "scores", "grades", "csv", "xlsx", "results sheet"),
    "rubric": ("rubric",),
    "answer_set": ("answers", "answer set", "scripts"),
}


def _call(tool: str, **args: Any) -> dict[str, Any]:
    return {"tool": tool, "arguments": json.dumps(args)}


def _guess_kind(text: str, filename: str) -> str:
    hay = f"{text} {filename}".lower()
    for kind, words in _KIND_WORDS.items():
        if any(w in hay for w in words):
            return kind
    return "question_paper"


def _course_ref(msg: str, app: dict[str, Any]) -> str | None:
    lowered = msg.lower()
    for c in app.get("courses", []):
        code = str(c["code"]).lower()
        if code in lowered or code.replace(" ", "") in lowered.replace(" ", ""):
            return c["id"]
    m = re.search(r"\b([a-z]{2,4}\s?-?\d{3,4})\b", lowered)
    if m:
        return m.group(1).upper()
    return None


def _plan_tools(ctx: dict[str, Any]) -> list[dict[str, Any]] | str:
    msg: str = ctx.get("message", "")
    low = msg.lower()
    app: dict[str, Any] = ctx.get("app", {})
    attachment = app.get("attachment")
    current = (app.get("current_course") or {}).get("id")
    course = _course_ref(msg, app) or current
    if attachment:
        kind = _guess_kind(msg, attachment.get("filename", ""))
        courses = app.get("courses", [])
        if not course and len(courses) == 1:
            course = courses[0]["id"]
        if not course:
            return ("Which course should I attach this file to? " + ("Your courses: " + ", ".join(c["code"] for c in courses) if courses else "You have no courses yet — say e.g. “create course CSE 3103 Database Systems” first."))
        if any(w in low for w in ("upload", "store", "save", "add")) and not any(w in low for w in ("analy", "audit", "check", "review")):
            return [_call("upload_attachment", course=course, kind=kind)]
        return [_call("analyze_attachment", course=course, kind=kind)]
    if "demo" in low and any(w in low for w in ("seed", "load", "create", "sample")):
        return [_call("seed_demo")]
    if re.search(r"\b(create|new|add)\b.*\bcourse\b", low):
        m = re.search(r"course\s+(?:called\s+|named\s+)?([a-z]{2,4}\s?-?\d{3,4})\s*[:\-–]?\s*(.*)$", msg, re.IGNORECASE)
        if m:
            title = m.group(2).strip().strip('"“”') or m.group(1).upper()
            return [_call("create_course", code=m.group(1).upper(), title=title)]
        return "What is the course code and title? e.g. “create course CSE 3103 Database Systems”."
    if re.search(r"\b(delete|remove|archive)\b.*\bcourse\b", low):
        return [_call("delete_course", course=course)] if course else "Which course should I delete?"
    if "finding" in low or "accept" in low or "dismiss" in low or "reopen" in low:
        status = "accepted" if "accept" in low else "dismissed" if "dismiss" in low else "open" if "reopen" in low else None
        if status:
            args: dict[str, Any] = {"status": status}
            if course:
                args["course"] = course
            for t in ("coverage_gap", "duplicate", "overweight", "bloom_imbalance", "fairness", "marks_total_mismatch", "untagged_question"):
                if t.replace("_", " ") in low or t in low:
                    args["type"] = t
            return [_call("decide_findings", **args)]
        return [_call("list_findings", **({"course": course} if course else {}))]
    if "export" in low or "report" in low:
        rid = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", low)
        if rid:
            return [_call("export_run", run_id=rid.group(0), include="all" if "all" in low else "accepted")]
        return "Which run should I export? Open the run page or tell me its id."
    if any(w in low for w in ("audit", "analy", "check the paper", "run exam")):
        if not course:
            return "Which course's paper should I audit?"
        return [_call("run_exam_audit", course=course)]
    if "question" in low and course:
        return [_call("course_overview", course=course)]
    if any(w in low for w in ("outcome", "topic", "overview", "artefact", "artifact", "what's in", "show me", "status")) and course:
        return [_call("course_overview", course=course)]
    if "course" in low or "list" in low or "what do i have" in low:
        return [_call("list_courses")]
    if any(w in low for w in ("how", "what", "help", "can you", "?")):
        return (
            "I'm the Faculty Copilot assistant. I can: list or create courses, upload a PDF/DOCX you attach as a question paper or "
            "syllabus, run an **Exam Paper Audit** (CO coverage, Bloom balance, duplicates vs past papers, marks totals), list and "
            "accept/dismiss findings, export a Markdown report, and seed the demo course. Attach a paper and say "
            "“analyze this for CSE 3103” to try it."
        )
    return [_call("list_courses")]


def _render(results: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    navigate_hint = None
    for r in results:
        ok = r.get("ok", True)
        lines.append(("✅ " if ok else "⚠️ ") + str(r.get("summary", "")))
        data = r.get("data") or {}
        if "courses" in data:
            lines += [f"- **{c['code']}** — {c['title']}" for c in data["courses"][:20]]
        if "outcomes" in data and r.get("tool") == "course_overview":
            lines.append("\n**Outcomes:** " + ", ".join(o["code"] for o in data["outcomes"]) if data["outcomes"] else "\n_No course outcomes yet._")
        if "artefacts" in data:
            arts = data["artefacts"]
            if arts:
                lines.append("\n**Artefacts:**")
                lines += [f"- {a['label']} ({a['kind']}, {a['status']})" for a in arts[:15]]
        if "questions" in data:
            lines += [f"- Q{q['number']} [{q['marks']}] {', '.join(q['cos']) or '—'} · {q.get('bloom_level') or '—'}" for q in data["questions"][:30]]
        if "findings" in data and data["findings"]:
            lines.append("\n**Findings:**")
            for f in data["findings"][:12]:
                lines.append(f"- **{f['severity'].upper()}** · {f['type'].replace('_', ' ')} — {f['title']}" + (f" _(status: {f['status']})_" if f.get("status") != "open" else ""))
            if len(data["findings"]) > 12:
                lines.append(f"- … and {len(data['findings']) - 12} more")
        if "markdown" in data:
            lines.append("\n```markdown\n" + data["markdown"][:2500] + "\n```")
        run = data.get("run")
        if run and run.get("summary"):
            s = run["summary"]
            mt = s.get("marks_total")
            if isinstance(mt, dict):
                lines.append(f"\nMarks: computed {mt.get('computed')} vs declared {mt.get('declared')}" + (" — **mismatch**" if mt.get("mismatch") else ""))
        if not ok and "details" in data and data["details"]:
            lines.append(f"  details: {json.dumps(data['details'])[:300]}")
        navigate_hint = navigate_hint or ("Open the highlighted page to review the details." if ok else None)
    if navigate_hint:
        lines.append(f"\n{navigate_hint}")
    return "\n".join(lines)


def plan(ctx: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = ctx.get("results") or []
    if results or ctx.get("final_round"):
        return {"thought": "Summarise tool results", "tool_calls": [], "reply": _render(results)}
    out = _plan_tools(ctx)
    if isinstance(out, str):
        return {"thought": "Answer directly", "tool_calls": [], "reply": out}
    return {"thought": "Run the matching tool", "tool_calls": out, "reply": ""}
