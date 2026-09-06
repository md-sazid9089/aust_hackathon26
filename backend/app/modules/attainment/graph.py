"""P4 CO–PO Attainment Analyst.

Stages: load_inputs → compute_attainment (deterministic) → explain (LLM, optional) → persist.
Inputs: marks_artefact_id (marks_sheet), paper_artefact_id (question_paper), threshold (fraction of a CO's marks).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.ai.client import CallContext, structured_call
from app.artefacts.parsers import normalize_qnum
from app.db.enums import FindingSeverity, FindingType, TargetKind, UsagePurpose
from app.db.models import (
    Artefact,
    CoPoMap,
    Course,
    CourseOutcome,
    MarksColumn,
    MarksRow,
    ProgramOutcome,
    Question,
    Run,
    RunInput,
)
from app.db.session import session_scope
from app.modules import tier1_prompts as P
from app.modules.base import FindingDraft, RunContext, StageFailed

DEFAULT_PARAMS: dict[str, Any] = {"threshold": 0.60, "target_pct": 60.0}


@dataclass
class CoStat:
    id: uuid.UUID
    code: str
    text: str
    bloom_level: str | None
    questions: list[str] = field(default_factory=list)
    max_marks: float = 0.0
    attained: int = 0
    students: int = 0
    mean_pct: float = 0.0
    weak_questions: list[str] = field(default_factory=list)

    @property
    def attained_pct(self) -> float:
        return round(100.0 * self.attained / self.students, 1) if self.students else 0.0


@dataclass
class State:
    course: Course
    cos: list[CourseOutcome]
    pos: list[ProgramOutcome]
    co_po: list[CoPoMap]
    columns: list[MarksColumn]
    rows: list[MarksRow]
    paper_label: str
    marks_label: str
    question_cos: dict[str, list[str]]  # normalised number -> CO codes (faculty/AI map from the paper)
    question_marks: dict[str, float]
    findings: list[FindingDraft] = field(default_factory=list)


async def run_attainment(ctx: RunContext) -> dict[str, Any]:
    params = {**DEFAULT_PARAMS, **(ctx.params or {})}
    threshold, target = float(params["threshold"]), float(params["target_pct"])
    state = await _load_inputs(ctx)
    await ctx.emit("load_inputs", f"Loaded {len(state.rows)} students × {len(state.columns)} items", 15)

    co_stats, unmatched = _compute(state, threshold)
    if unmatched:
        await ctx.warn("compute_attainment", f"Columns not matched to any CO: {', '.join(unmatched)}")
    po_rows = _po_attainment(state, co_stats, target)
    await ctx.emit("compute_attainment", "CO and PO attainment computed", 55)

    _build_findings(state, co_stats, po_rows, target)
    explained = await _explain(ctx, state, co_stats, threshold, target)
    await ctx.emit("explain", "AI explanations added" if explained else "AI explanation unavailable", 85)

    async with session_scope() as db:
        run = await db.get(Run, ctx.run_id)
        assert run is not None
        db.add_all(f.to_model(run) for f in state.findings)
    cos_out = [
        {"co_id": str(c.id), "co_code": c.code, "attained_pct": c.attained_pct, "students": c.students, "target_pct": target,
         "met": c.attained_pct >= target and c.students > 0, "max_marks": c.max_marks, "mean_pct": c.mean_pct, "questions": c.questions}
        for c in co_stats
    ]
    return {
        "threshold": threshold, "threshold_pct": round(threshold * 100), "target_pct": target, "students": len(state.rows),
        "cos_met": sum(1 for c in cos_out if c["met"]), "cos_total": len(cos_out),
        "pos_met": sum(1 for p in po_rows if p["met"]), "pos_total": len(po_rows),
        "cos": cos_out, "pos": po_rows, "unmatched_columns": unmatched, "findings": len(state.findings),
        "paper_label": state.paper_label, "marks_label": state.marks_label,
    }


async def _load_inputs(ctx: RunContext) -> State:
    async with session_scope() as db:
        run = await db.get(Run, ctx.run_id)
        if run is None:
            raise StageFailed("Run vanished")
        inputs = (await db.execute(select(RunInput).where(RunInput.run_id == ctx.run_id))).scalars().all()
        marks_id = next((i.artefact_id for i in inputs if i.role == "marks"), None)
        paper_id = next((i.artefact_id for i in inputs if i.role == "paper"), None)
        if marks_id is None or paper_id is None:
            raise StageFailed("A marks sheet and a question paper are required")
        marks_art, paper_art = await db.get(Artefact, marks_id), await db.get(Artefact, paper_id)
        if marks_art is None or paper_art is None:
            raise StageFailed("Input artefact no longer exists")
        course = await db.get(Course, ctx.course_id)
        cos = list((await db.execute(select(CourseOutcome).where(CourseOutcome.course_id == ctx.course_id).order_by(CourseOutcome.sort_order))).scalars())
        if not cos:
            raise StageFailed("Course has no outcomes")
        co_ids = [c.id for c in cos]
        co_po = list((await db.execute(select(CoPoMap).where(CoPoMap.co_id.in_(co_ids)))).scalars())
        pos = list((await db.execute(select(ProgramOutcome).order_by(ProgramOutcome.sort_order))).scalars())
        columns = list((await db.execute(select(MarksColumn).where(MarksColumn.artefact_id == marks_id).order_by(MarksColumn.sort_order))).scalars())
        rows = list((await db.execute(select(MarksRow).where(MarksRow.artefact_id == marks_id).order_by(MarksRow.sort_order))).scalars())
        if not columns or not rows:
            raise StageFailed("Marks sheet has no parsed columns/students; check the upload")
        co_code = {c.id: c.code for c in cos}
        qs = (await db.execute(select(Question).where(Question.artefact_id == paper_id).options(selectinload(Question.co_links)))).scalars()
        question_cos: dict[str, list[str]] = {}
        question_marks: dict[str, float] = {}
        for q in qs:
            n = normalize_qnum(q.number)
            question_cos[n] = sorted({co_code[l.co_id] for l in q.co_links if l.co_id in co_code})
            question_marks[n] = float(q.marks)
        run.context_snapshot = {
            "outcomes": [{"code": c.code, "text": c.text} for c in cos],
            "columns": [{"number": c.number, "max": c.max_marks, "co_code": c.co_code} for c in columns],
            "students": len(rows), "paper": paper_art.label, "marks_sheet": marks_art.label,
        }
        assert course is not None
        return State(course=course, cos=cos, pos=pos, co_po=co_po, columns=columns, rows=rows, paper_label=paper_art.label,
                     marks_label=marks_art.label, question_cos=question_cos, question_marks=question_marks)


def _compute(state: State, threshold: float) -> tuple[list[CoStat], list[str]]:
    """Deterministic (AI-004): per student, CO score = Σ marks on that CO's items; attained if ≥ threshold × CO max."""
    stats = {c.code: CoStat(id=c.id, code=c.code, text=c.text, bloom_level=c.bloom_level.value if c.bloom_level else None) for c in state.cos}
    col_cos: dict[str, list[str]] = {}
    unmatched: list[str] = []
    for col in state.columns:
        n = normalize_qnum(col.number)
        codes = state.question_cos.get(n) or ([col.co_code] if col.co_code and col.co_code in stats else [])
        codes = [c for c in codes if c in stats]
        if not codes:
            unmatched.append(col.number)
            continue
        col_cos[col.number] = codes
        mx = float(col.max_marks) if col.max_marks else state.question_marks.get(n, 0.0)
        for code in codes:
            stats[code].questions.append(col.number)
            stats[code].max_marks += mx
    for code, st in stats.items():
        if st.max_marks <= 0:
            continue
        per_q_pct: dict[str, list[float]] = {q: [] for q in st.questions}
        total_pct = 0.0
        for row in state.rows:
            score = 0.0
            for col in state.columns:
                if code in col_cos.get(col.number, []) and col.number in row.scores:
                    v = float(row.scores[col.number])
                    score += v
                    mx = float(col.max_marks) or state.question_marks.get(normalize_qnum(col.number), 0.0)
                    if mx:
                        per_q_pct[col.number].append(v / mx)
            st.students += 1
            pct = score / st.max_marks
            total_pct += pct
            if pct >= threshold:
                st.attained += 1
        st.mean_pct = round(100.0 * total_pct / st.students, 1) if st.students else 0.0
        weak = sorted(((sum(v) / len(v) if v else 1.0), q) for q, v in per_q_pct.items())
        st.weak_questions = [q for avg, q in weak if avg < threshold][:3]
    return [stats[c.code] for c in state.cos], unmatched


def _po_attainment(state: State, co_stats: list[CoStat], target: float) -> list[dict[str, Any]]:
    by_code = {c.code: c for c in co_stats}
    co_code_by_id = {c.id: c.code for c in state.cos}
    out = []
    for po in state.pos:
        links = [(co_code_by_id[m.co_id], m.strength) for m in state.co_po if m.po_id == po.id and m.strength > 0 and m.co_id in co_code_by_id]
        links = [(code, s) for code, s in links if by_code[code].students > 0]
        if not links:
            continue
        weight = sum(s for _, s in links)
        pct = round(sum(by_code[code].attained_pct * s for code, s in links) / weight, 1)
        out.append({"po_id": str(po.id), "po_code": po.code, "attained_pct": pct, "met": pct >= target,
                    "contributing_cos": [{"co_code": code, "strength": s} for code, s in links]})
    return out


def _build_findings(state: State, co_stats: list[CoStat], po_rows: list[dict[str, Any]], target: float) -> None:
    for c in co_stats:
        if c.students == 0:
            state.findings.append(FindingDraft(
                type=FindingType.co_underperformance, severity=FindingSeverity.info,
                title=f"{c.code} has no assessed items in '{state.paper_label}'",
                rationale="No marks column maps to this outcome, so attainment cannot be computed for it.",
                evidence_snippet=f"{c.code}: {c.text}", target_kind=TargetKind.course_outcome, target_id=c.id, target_label=c.code,
                payload={"attained_pct": None, "students": 0},
            ))
            continue
        if c.attained_pct < target:
            gap = target - c.attained_pct
            state.findings.append(FindingDraft(
                type=FindingType.co_underperformance, severity=FindingSeverity.high if gap >= 15 else FindingSeverity.medium,
                title=f"{c.code} attained by {c.attained_pct:.0f}% of students (target {target:.0f}%)",
                rationale=(f"{c.attained} of {c.students} students reached the threshold on items {', '.join(c.questions)}; "
                           f"mean score {c.mean_pct:.0f}% of {c.max_marks:g} marks."
                           + (f" Weakest items: {', '.join(c.weak_questions)}." if c.weak_questions else "")),
                evidence_snippet=f"{c.code}: {c.text}", target_kind=TargetKind.course_outcome, target_id=c.id, target_label=c.code,
                payload={"attained_pct": c.attained_pct, "target_pct": target, "students": c.students, "attained": c.attained,
                         "mean_pct": c.mean_pct, "questions": c.questions, "weak_questions": c.weak_questions},
            ))
    for p in po_rows:
        if not p["met"]:
            state.findings.append(FindingDraft(
                type=FindingType.po_underperformance, severity=FindingSeverity.medium,
                title=f"{p['po_code']} attained at {p['attained_pct']:.0f}% (target {target:.0f}%)",
                rationale="Strength-weighted mean of the contributing COs' attainment is below target: "
                          + ", ".join(f"{l['co_code']} (×{l['strength']})" for l in p["contributing_cos"]) + ".",
                evidence_snippet=None, target_kind=TargetKind.program_outcome, target_id=uuid.UUID(p["po_id"]), target_label=p["po_code"],
                payload=p,
            ))


async def _explain(ctx: RunContext, state: State, co_stats: list[CoStat], threshold: float, target: float) -> bool:
    unmet = [c for c in co_stats if c.students > 0 and c.attained_pct < target]
    if not unmet:
        return True
    ctx.prompt_versions["EXPLAIN_ATTAINMENT"] = P.PROMPT_VERSIONS["EXPLAIN_ATTAINMENT"]
    context = {
        "course": state.course.code,
        "cos": [{"code": c.code, "text": c.text, "attained_pct": c.attained_pct, "target_pct": target, "met": False,
                 "students": c.students, "weak_questions": c.weak_questions} for c in unmet],
    }
    results = "\n".join(
        f"- {c.code} ({c.text}): {c.attained_pct:.0f}% attained (target {target:.0f}%), items {', '.join(c.questions)}, weakest {', '.join(c.weak_questions) or '-'}"
        for c in unmet
    )
    async with session_scope() as db:
        res = await structured_call(
            purpose="explain_attainment", usage_purpose=UsagePurpose.attainment, system=P.EXPLAIN_ATTAINMENT_SYSTEM,
            user=P.EXPLAIN_ATTAINMENT_USER.format(course_code=state.course.code, course_title=state.course.title,
                                                  threshold_pct=threshold * 100, target_pct=target, results=results),
            schema=P.AttainmentExplainOut, ctx=CallContext(ctx.owner_id, ctx.run_id), db=db, context=context,
        )
    if res.value is None:
        await ctx.warn("explain", f"AI explanation unavailable ({res.error}); numeric results are complete")
        return False
    ctx.model_used = res.model
    by_code = {c.code: c for c in unmet}
    for item in res.value.items:  # type: ignore[union-attr]
        c = by_code.get(item.co_code)
        if c is None:
            continue
        for f in state.findings:
            if f.type == FindingType.co_underperformance and f.target_label == c.code:
                f.rationale = f"{f.rationale}\n\nAI explanation: {item.explanation}"
                f.provenance = {"model": res.model, "prompt": "EXPLAIN_ATTAINMENT"}
        for i, action in enumerate(item.actions[:3]):
            state.findings.append(FindingDraft(
                type=FindingType.action, severity=FindingSeverity.low,
                title=f"Action for {c.code}: {action[:90]}" + ("…" if len(action) > 90 else ""),
                rationale=item.explanation, evidence_snippet=f"{c.code} attained {c.attained_pct:.0f}% vs target {target:.0f}%",
                target_kind=TargetKind.course_outcome, target_id=c.id, target_label=c.code,
                payload={"action": action, "order": i}, provenance={"model": res.model, "prompt": "EXPLAIN_ATTAINMENT"},
            ))
    return True
