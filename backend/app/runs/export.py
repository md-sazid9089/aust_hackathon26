from __future__ import annotations

from datetime import datetime

from app.db.models import Finding, Run

SEV_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def render_markdown(run: Run, findings: list[Finding], *, course_code: str, course_title: str, include: str) -> str:
    """Plain Markdown report of a run's findings (accepted-only by default)."""
    summary = run.summary or {}
    lines = [
        f"# Exam Paper Audit — {course_code} {course_title}",
        "",
        f"- Run: `{run.id}`  ",
        f"- Draft paper: {summary.get('draft_label', '—')}  ",
        f"- Status: {run.status.value}  ",
        f"- Finished: {run.finished_at.isoformat() if run.finished_at else '—'}  ",
        f"- Model: {run.model or 'n/a'}  ",
        f"- Findings included: {'accepted only' if include == 'accepted' else 'all'}",
        "",
    ]
    if summary:
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
