"""P2 Grading Consistency Calibrator.

Stages: load_inputs → divergence (deterministic) → explain (LLM) → prescore (LLM) → rubric_v2 (LLM) → persist.
Inputs: rubric_artefact_id (rubric), answer_set_artefact_id (answer_set with ≥2 graders' scores).
`409 SCORES_EXCEED_RUBRIC` is enforced at run creation (RunService), not here.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from app.ai.client import CallContext, structured_call
from app.ai.guard import wrap_untrusted
from app.db.enums import FindingSeverity, FindingType, TargetKind, UsagePurpose
from app.db.models import Answer, Artefact, RubricCriterion, Run, RunInput
from app.db.session import session_scope
from app.modules import tier1_prompts as P
from app.modules.base import FindingDraft, RunContext, StageFailed

DEFAULT_PARAMS: dict[str, Any] = {"divergence_share": 0.25, "flag_criterion_mean": 1.0, "prescore_batch": 6}


@dataclass
class State:
    criteria: list[RubricCriterion]
    answers: list[Answer]
    graders: list[str]
    rubric_label: str
    answers_label: str
    divergences: list[dict[str, Any]] = field(default_factory=list)
    criterion_mean_dev: dict[str, float] = field(default_factory=dict)
    prescores: list[dict[str, Any]] = field(default_factory=list)
    findings: list[FindingDraft] = field(default_factory=list)


async def run_calibration(ctx: RunContext) -> dict[str, Any]:
    params = {**DEFAULT_PARAMS, **(ctx.params or {})}
    state = await _load_inputs(ctx)
    await ctx.emit("load_inputs", f"Loaded {len(state.criteria)} criteria, {len(state.answers)} answers, graders {', '.join(state.graders)}", 10)

    _divergence(state, float(params["divergence_share"]), float(params["flag_criterion_mean"]))
    await ctx.emit("divergence", f"{len(state.divergences)} divergent answer/criterion pair(s)", 35)

    await _explain(ctx, state)
    await ctx.emit("explain", "Divergences explained", 55)

    await _prescore(ctx, state, int(params["prescore_batch"]))
    await ctx.emit("prescore", f"{len(state.prescores)} answers pre-scored", 80)

    flagged = [c for c in state.criteria if state.criterion_mean_dev.get(c.code, 0.0) >= float(params["flag_criterion_mean"])]
    await _rubric_v2(ctx, state, flagged)
    await ctx.emit("rubric_v2", "Rubric clarifications proposed" if flagged else "No criterion needs clarification", 92)

    async with session_scope() as db:
        run = await db.get(Run, ctx.run_id)
        assert run is not None
        db.add_all(f.to_model(run) for f in state.findings)
    devs = [d["abs_dev"] for d in state.divergences]
    return {
        "rubric_label": state.rubric_label, "answers_label": state.answers_label, "graders": state.graders,
        "answers": len(state.answers), "criteria": len(state.criteria),
        "divergent_answers": len({d["answer_id"] for d in state.divergences}),
        "mean_abs_dev": round(statistics.fmean(devs), 2) if devs else 0.0,
        "criteria_flagged": [c.code for c in flagged], "criterion_mean_dev": state.criterion_mean_dev,
        "divergences": state.divergences, "prescores": state.prescores, "findings": len(state.findings),
    }


async def _load_inputs(ctx: RunContext) -> State:
    async with session_scope() as db:
        run = await db.get(Run, ctx.run_id)
        if run is None:
            raise StageFailed("Run vanished")
        inputs = (await db.execute(select(RunInput).where(RunInput.run_id == ctx.run_id))).scalars().all()
        rub_id = next((i.artefact_id for i in inputs if i.role == "rubric"), None)
        ans_id = next((i.artefact_id for i in inputs if i.role == "answer_set"), None)
        if rub_id is None or ans_id is None:
            raise StageFailed("A rubric and an answer set are required")
        rub, ans = await db.get(Artefact, rub_id), await db.get(Artefact, ans_id)
        if rub is None or ans is None:
            raise StageFailed("Input artefact no longer exists")
        criteria = list((await db.execute(select(RubricCriterion).where(RubricCriterion.artefact_id == rub_id).order_by(RubricCriterion.sort_order))).scalars())
        answers = list((await db.execute(select(Answer).where(Answer.artefact_id == ans_id).order_by(Answer.sort_order))).scalars())
        if not criteria:
            raise StageFailed("Rubric has no criteria; confirm the extraction first")
        if not answers:
            raise StageFailed("Answer set has no answers; confirm the extraction first")
        graders = sorted({g["grader_label"] for a in answers for g in (a.grader_scores or [])})
        if len(graders) < 2:
            raise StageFailed("At least two graders' scores are required for calibration")
        run.context_snapshot = {
            "rubric": rub.label, "criteria": [{"code": c.code, "max_score": c.max_score} for c in criteria],
            "answers": len(answers), "graders": graders,
        }
        for a in answers:  # detach-safe copies
            db.expunge(a)
        for c in criteria:
            db.expunge(c)
        return State(criteria=criteria, answers=answers, graders=graders, rubric_label=rub.label, answers_label=ans.label)


def _scores_by(answer: Answer) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for g in answer.grader_scores or []:
        out.setdefault(g["criterion_code"], {})[g["grader_label"]] = float(g["score"])
    return out


def _divergence(state: State, share: float, flag_mean: float) -> None:
    """Deterministic (AI-004): divergence = max − min grader score per criterion; flagged if ≥ share × max_score."""
    per_criterion: dict[str, list[float]] = {c.code: [] for c in state.criteria}
    for a in state.answers:
        by_crit = _scores_by(a)
        for c in state.criteria:
            scores = by_crit.get(c.code, {})
            if len(scores) < 2:
                continue
            dev = max(scores.values()) - min(scores.values())
            per_criterion[c.code].append(dev)
            if dev >= share * float(c.max_score) and dev > 0:
                state.divergences.append({
                    "answer_id": str(a.id), "student_anon_id": a.student_anon_id, "criterion_code": c.code,
                    "scores": scores, "abs_dev": round(dev, 2), "max_score": float(c.max_score),
                })
    state.criterion_mean_dev = {code: round(statistics.fmean(v), 2) if v else 0.0 for code, v in per_criterion.items()}
    crit_by_code = {c.code: c for c in state.criteria}
    for d in state.divergences:
        c = crit_by_code[d["criterion_code"]]
        a = next(x for x in state.answers if str(x.id) == d["answer_id"])
        state.findings.append(FindingDraft(
            type=FindingType.divergence, severity=FindingSeverity.high if d["abs_dev"] >= 0.5 * d["max_score"] else FindingSeverity.medium,
            title=f"{a.student_anon_id} · {c.code}: graders differ by {d['abs_dev']:g} of {d['max_score']:g}",
            rationale="Scores: " + ", ".join(f"{g}={s:g}" for g, s in sorted(d["scores"].items())) + f". Criterion: {c.text}",
            evidence_snippet=a.text[:300] + ("…" if len(a.text) > 300 else ""),
            target_kind=TargetKind.answer, target_id=a.id, target_label=f"{a.student_anon_id}/{c.code}", payload=d,
        ))
    for code, mean in state.criterion_mean_dev.items():
        if mean >= flag_mean:
            c = crit_by_code[code]
            state.findings.append(FindingDraft(
                type=FindingType.rubric_clarification, severity=FindingSeverity.medium,
                title=f"{c.code} is interpreted inconsistently (mean divergence {mean:g} of {float(c.max_score):g})",
                rationale=f"Across {len(per_criterion[code])} answers graders disagree by {mean:g} marks on average; the descriptor may be ambiguous.",
                evidence_snippet=c.text, target_kind=TargetKind.criterion, target_id=c.id, target_label=c.code,
                payload={"mean_divergence": mean, "max_score": float(c.max_score)},
            ))


async def _explain(ctx: RunContext, state: State) -> None:
    if not state.divergences:
        return
    ctx.prompt_versions["EXPLAIN_DIVERGENCE"] = P.PROMPT_VERSIONS["EXPLAIN_DIVERGENCE"]
    crit_by_code = {c.code: c for c in state.criteria}
    ans_by_id = {str(a.id): a for a in state.answers}
    items = [{**d, "criterion_text": crit_by_code[d["criterion_code"]].text, "answer_excerpt": ans_by_id[d["answer_id"]].text[:600]} for d in state.divergences[:30]]
    criteria_txt = "\n".join(f"- {c.code} (max {float(c.max_score):g}): {c.text}" for c in state.criteria)
    items_txt = "\n".join(
        f"- answer {i['answer_id']} / {i['criterion_code']} scores {i['scores']}\n  {wrap_untrusted(i['answer_excerpt'], i['answer_id'][:8], 600)}" for i in items
    )
    async with session_scope() as db:
        res = await structured_call(
            purpose="explain_divergence", usage_purpose=UsagePurpose.calibration, system=P.EXPLAIN_DIVERGENCE_SYSTEM,
            user=P.EXPLAIN_DIVERGENCE_USER.format(criteria=criteria_txt, items=items_txt),
            schema=P.DivergenceExplainOut, ctx=CallContext(ctx.owner_id, ctx.run_id), db=db, context={"items": items},
        )
    if res.value is None:
        await ctx.warn("explain", f"AI explanation unavailable ({res.error}); divergence numbers are complete")
        return
    ctx.model_used = res.model
    by_key = {(it.answer_id, it.criterion_code): it.explanation for it in res.value.items}  # type: ignore[union-attr]
    for f in state.findings:
        if f.type == FindingType.divergence:
            exp = by_key.get((f.payload["answer_id"], f.payload["criterion_code"]))
            if exp:
                f.rationale = f"{f.rationale}\n\nAI explanation: {exp}"
                f.provenance = {"model": res.model, "prompt": "EXPLAIN_DIVERGENCE"}


async def _prescore(ctx: RunContext, state: State, batch: int) -> None:
    ctx.prompt_versions["PRESCORE_ANSWERS"] = P.PROMPT_VERSIONS["PRESCORE_ANSWERS"]
    criteria_ctx = [{"code": c.code, "text": c.text, "max_score": float(c.max_score), "levels": c.levels or []} for c in state.criteria]
    criteria_txt = "\n".join(
        f"- {c.code} (max {float(c.max_score):g}): {c.text}" + "".join(f"\n    {lv.get('score')}: {lv.get('descriptor')}" for lv in (c.levels or []))
        for c in state.criteria
    )
    failed = 0
    for i in range(0, len(state.answers), max(1, batch)):
        chunk = state.answers[i : i + batch]
        answers_ctx = [{"answer_id": str(a.id), "text": a.text} for a in chunk]
        answers_txt = "\n".join(f"### answer {a.id}\n{wrap_untrusted(a.text, str(a.id)[:8], 4000)}" for a in chunk)
        async with session_scope() as db:
            res = await structured_call(
                purpose="prescore_answers", usage_purpose=UsagePurpose.calibration, system=P.PRESCORE_SYSTEM,
                user=P.PRESCORE_USER.format(criteria=criteria_txt, answers=answers_txt),
                schema=P.PrescoreOut, ctx=CallContext(ctx.owner_id, ctx.run_id), db=db,
                context={"criteria": criteria_ctx, "answers": answers_ctx},
            )
        if res.value is None:
            failed += 1
            continue
        ctx.model_used = res.model
        by_id = {str(a.id): a for a in chunk}
        crit_by_code = {c.code: c for c in state.criteria}
        for item in res.value.items:  # type: ignore[union-attr]
            a = by_id.get(item.answer_id)
            if a is None:
                continue
            grader_by_crit = _scores_by(a)
            for s in item.scores:
                c = crit_by_code.get(s.criterion_code)
                if c is None:
                    continue
                score = max(0.0, min(float(c.max_score), float(s.score)))
                gs = grader_by_crit.get(c.code, {})
                state.prescores.append({"answer_id": str(a.id), "student_anon_id": a.student_anon_id, "criterion_code": c.code,
                                        "ai_score": score, "rationale": s.rationale, "grader_scores": gs})
                if gs and all(abs(score - g) >= 0.5 * float(c.max_score) for g in gs.values()):
                    state.findings.append(FindingDraft(
                        type=FindingType.prescore_note, severity=FindingSeverity.low,
                        title=f"{a.student_anon_id} · {c.code}: AI pre-score {score:g} differs from all graders",
                        rationale=s.rationale, evidence_snippet=a.text[:300], target_kind=TargetKind.answer, target_id=a.id,
                        target_label=f"{a.student_anon_id}/{c.code}", payload={"ai_score": score, "grader_scores": gs, "max_score": float(c.max_score)},
                        provenance={"model": res.model, "prompt": "PRESCORE_ANSWERS"},
                    ))
    if failed:
        await ctx.warn("prescore", f"AI pre-scoring unavailable for {failed} batch(es)")


async def _rubric_v2(ctx: RunContext, state: State, flagged: list[RubricCriterion]) -> None:
    if not flagged:
        return
    ctx.prompt_versions["PROPOSE_RUBRIC_V2"] = P.PROMPT_VERSIONS["PROPOSE_RUBRIC_V2"]
    crit_ctx = [{"code": c.code, "text": c.text, "max_score": float(c.max_score), "levels": c.levels or [], "mean_divergence": state.criterion_mean_dev.get(c.code, 0.0)} for c in flagged]
    crit_txt = "\n".join(f"- {c['code']} (max {c['max_score']:g}, mean divergence {c['mean_divergence']:g}): {c['text']}" for c in crit_ctx)
    async with session_scope() as db:
        res = await structured_call(
            purpose="propose_rubric_v2", usage_purpose=UsagePurpose.calibration, system=P.PROPOSE_RUBRIC_V2_SYSTEM,
            user=P.PROPOSE_RUBRIC_V2_USER.format(criteria=crit_txt), schema=P.RubricV2Out,
            ctx=CallContext(ctx.owner_id, ctx.run_id), db=db, context={"criteria": crit_ctx},
        )
    if res.value is None:
        await ctx.warn("rubric_v2", f"Rubric proposal unavailable ({res.error})")
        return
    ctx.model_used = res.model
    by_code = {c.code: c for c in flagged}
    for it in res.value.items:  # type: ignore[union-attr]
        c = by_code.get(it.criterion_code)
        if c is None:
            continue
        for f in state.findings:
            if f.type == FindingType.rubric_clarification and f.target_label == c.code:
                levels = [lv.model_dump() for lv in it.proposed_levels]
                f.payload = {
                    **f.payload,
                    "proposed": {"id": str(c.id), "code": c.code, "text": it.proposed_text, "max_score": float(c.max_score), "levels": levels},
                    "current": {"id": str(c.id), "code": c.code, "text": c.text, "max_score": float(c.max_score), "levels": c.levels or []},
                }
                f.rationale = f"{f.rationale}\n\nProposed v2: {it.proposed_text}\n{it.rationale}"
                f.provenance = {"model": res.model, "prompt": "PROPOSE_RUBRIC_V2"}
