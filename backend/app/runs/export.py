from __future__ import annotations

from datetime import datetime

from app.db.models import Finding, Run

SEV_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
MODULE_TITLE = {"exam_audit": "Exam Paper Audit", "attainment": "CO–PO Attainment", "syllabus_check": "Syllabus Overlap & Gap Check", "calibration": "Grading Calibration"}


def render_markdown(run: Run, findings: list[Finding], *, course_code: str, course_title: str, include: str) -> str:
    """Plain Markdown report of a run's findings (accepted-only by default)."""
    summary = run.summary or {}
    module = run.module.value
    lines = [
        f"# {MODULE_TITLE.get(module, module)} — {course_code} {course_title}",
        "",
        f"- Run: `{run.id}`  ",
    ]
    if module == "exam_audit":
        lines.append(f"- Draft paper: {summary.get('draft_label', '—')}  ")
    lines += [
        f"- Status: {run.status.value}  ",
        f"- Finished: {run.finished_at.isoformat() if run.finished_at else '—'}  ",
        f"- Model: {run.model or 'n/a'}  ",
        f"- Findings included: {'accepted only' if include == 'accepted' else 'all'}",
        "",
    ]
    if summary and module == "exam_audit":
        lines += ["## Summary", "", f"- CO coverage: {summary.get('coverage_pct', 0)}%"]
        bloom = summary.get("bloom") or {}
        if bloom:
            lines.append(f"- Lower-order marks: {bloom.get('lower_order_share', 0) * 100:.0f}% · higher-order: {bloom.get('higher_order_share', 0) * 100:.0f}%")
        mt = summary.get("marks_total") or {}
        if mt:
            lines.append(f"- Marks: {mt.get('computed')} computed vs {mt.get('declared') if mt.get('declared') is not None else '—'} declared")
        lines.append(f"- Duplicate pairs: {len(summary.get('duplicates') or [])}")
        cov = summary.get("coverage") or []
        if cov:
            lines += ["", "| CO | Marks | Share | Expected | Status |", "|---|---|---|---|---|"]
            lines += [f"| {r['target_code']} | {r['marks']:g} | {r['share'] * 100:.0f}% | {r['expected_share'] * 100:.0f}% | {r['status']} |" for r in cov]
        lines.append("")
    elif summary and module == "attainment":
        lines += ["## Summary", "", f"- Students: {summary.get('students', 0)} · threshold {summary.get('threshold', 0) * 100:.0f}% · target {summary.get('target_pct', 0):.0f}% of students",
                  f"- COs met: {summary.get('cos_met', 0)}/{summary.get('cos_total', 0)} · POs met: {summary.get('pos_met', 0)}/{summary.get('pos_total', 0)}", "",
                  "| CO | Attained % | Students | Met |", "|---|---|---|---|"]
        lines += [f"| {c['co_code']} | {c['attained_pct']:.0f}% | {c['students']} | {'yes' if c['met'] else 'no'} |" for c in summary.get("cos", [])]
        lines.append("")
    elif summary and module == "syllabus_check":
        lines += ["## Summary", "", f"- Compared against: {', '.join(summary.get('compare_courses', []))}",
                  f"- Topics overlapping: {summary.get('overlap_pct', 0):.0f}% · overlaps {summary.get('overlaps', 0)} · prerequisites {summary.get('prerequisites', 0)}", ""]
    elif summary and module == "calibration":
        lines += ["## Summary", "", f"- Graders: {', '.join(summary.get('graders', []))} · answers {summary.get('answers', 0)} · criteria {summary.get('criteria', 0)}",
                  f"- Divergent answers: {summary.get('divergent_answers', 0)} · mean abs deviation {summary.get('mean_abs_dev', 0)}",
                  f"- Criteria flagged: {', '.join(summary.get('criteria_flagged', [])) or 'none'}", ""]
    lines += ["## Findings", ""]
    if not findings:
        lines.append("_No findings in this selection._")
    for f in sorted(findings, key=lambda x: (SEV_ORDER.get(x.severity.value, 9), x.created_at)):
        lines += [
            f"### [{f.severity.value.upper()}] {f.title}",
            "",
            f"- Type: `{f.type.value}` · Status: **{f.status.value}**" + (f" · Target: {f.target_label}" if f.target_label else ""),
            f"- Rationale: {f.rationale}",
        ]
        if f.evidence_snippet:
            lines += ["- Evidence:", "", *(f"  > {ln}" for ln in f.evidence_snippet.splitlines())]
        lines.append("")
    lines += ["---", f"_Generated {datetime.now().isoformat(timespec='seconds')} by Faculty Copilot. AI findings are advisory; decisions recorded above were made by faculty._"]
    return "\n".join(lines)
