"""P3 Syllabus Overlap / Gap Analyzer.

Stages: load_inputs → embed_topics → similarity matrix (deterministic cosine) → relate (LLM classifies candidate pairs) → persist.
Inputs: syllabus_artefact_id (syllabus), compare_course_ids (other courses of the same owner).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from app.ai.client import CallContext, structured_call
from app.ai.embeddings import cosine, embed_texts
from app.config import get_settings
from app.db.enums import FindingSeverity, FindingType, TargetKind, UsagePurpose
from app.db.models import Artefact, Course, Run, RunInput, Topic
from app.db.session import session_scope
from app.modules import tier1_prompts as P
from app.modules.base import FindingDraft, RunContext, StageFailed

DEFAULT_PARAMS: dict[str, Any] = {"candidate_threshold": 0.45, "overlap_threshold": 0.70, "max_pairs": 40}


@dataclass
class TView:
    id: uuid.UUID
    course_code: str
    code: str
    title: str
    embedding: list[float] | None
    embedding_model: str | None


@dataclass
class State:
    course: Course
    mine: list[TView]
    others: list[TView]
    syllabus_label: str
    compare_codes: list[str]
    matrix: list[dict[str, Any]] = field(default_factory=list)
    findings: list[FindingDraft] = field(default_factory=list)


async def run_syllabus_check(ctx: RunContext) -> dict[str, Any]:
    params = {**DEFAULT_PARAMS, **(ctx.params or {})}
    state = await _load_inputs(ctx)
    await ctx.emit("load_inputs", f"Loaded {len(state.mine)} draft topics and {len(state.others)} topics from {len(state.compare_codes)} course(s)", 10)

    if not await _embed(ctx, state):
        raise StageFailed("Embedding provider unavailable; overlap cannot be computed")
    await ctx.emit("embed_topics", "Topic embeddings ready", 35)

    candidates = _candidates(state, float(params["candidate_threshold"]), int(params["max_pairs"]))
    await ctx.emit("similarity", f"{len(candidates)} candidate pair(s) above {params['candidate_threshold']:.2f}", 55)

    await _relate(ctx, state, candidates, float(params["overlap_threshold"]))
    await ctx.emit("relate", "Pairs classified", 85)

    async with session_scope() as db:
        run = await db.get(Run, ctx.run_id)
        assert run is not None
        db.add_all(f.to_model(run) for f in state.findings)
    overlapping = {c["topic_a"] for c in state.matrix if c["relation"] == "overlap"}
    return {
        "syllabus_label": state.syllabus_label, "compare_courses": state.compare_codes,
        "topics": len(state.mine), "compared_topics": len(state.others),
        "matrix": state.matrix, "overlap_pct": round(100.0 * len(overlapping) / len(state.mine), 1) if state.mine else 0.0,
        "overlaps": sum(1 for c in state.matrix if c["relation"] == "overlap"),
        "prerequisites": sum(1 for c in state.matrix if c["relation"] == "prerequisite"),
        "findings": len(state.findings),
    }


async def _load_inputs(ctx: RunContext) -> State:
    async with session_scope() as db:
        run = await db.get(Run, ctx.run_id)
        if run is None:
            raise StageFailed("Run vanished")
        inputs = (await db.execute(select(RunInput).where(RunInput.run_id == ctx.run_id))).scalars().all()
        syl_id = next((i.artefact_id for i in inputs if i.role == "syllabus"), None)
        if syl_id is None:
            raise StageFailed("A syllabus artefact is required")
        syl = await db.get(Artefact, syl_id)
        course = await db.get(Course, ctx.course_id)
        if syl is None or course is None:
            raise StageFailed("Input artefact no longer exists")
        compare_ids = [uuid.UUID(str(c)) for c in (run.inputs or {}).get("compare_course_ids", [])]
        others_courses = list((await db.execute(select(Course).where(Course.id.in_(compare_ids), Course.deleted_at.is_(None)))).scalars()) if compare_ids else []
        if not others_courses:
            raise StageFailed("No comparison courses found")
        mine_rows = list((await db.execute(select(Topic).where(Topic.course_id == ctx.course_id, Topic.source_artefact_id == syl_id).order_by(Topic.sort_order))).scalars())
        if not mine_rows:  # fall back to every topic of the course (manually entered topics)
            mine_rows = list((await db.execute(select(Topic).where(Topic.course_id == ctx.course_id).order_by(Topic.sort_order))).scalars())
        if not mine_rows:
            raise StageFailed("Draft syllabus has no topics; confirm the extraction first")
        code_by_course = {c.id: c.code for c in others_courses}
        other_rows = list((await db.execute(select(Topic).where(Topic.course_id.in_(list(code_by_course))).order_by(Topic.course_id, Topic.sort_order))).scalars())
        if not other_rows:
            raise StageFailed("Comparison courses have no topics")
        run.context_snapshot = {
            "syllabus": syl.label, "topics": [{"code": t.code, "title": t.title} for t in mine_rows],
            "compare_courses": [{"code": c.code, "topics": sum(1 for t in other_rows if t.course_id == c.id)} for c in others_courses],
        }
        mk = lambda t, cc: TView(id=t.id, course_code=cc, code=t.code, title=t.title, embedding=t.embedding, embedding_model=t.embedding_model)  # noqa: E731
        return State(course=course, mine=[mk(t, course.code) for t in mine_rows], others=[mk(t, code_by_course[t.course_id]) for t in other_rows],
                     syllabus_label=syl.label, compare_codes=[c.code for c in others_courses])


async def _embed(ctx: RunContext, state: State) -> bool:
    model = get_settings().embed_model
    need = [t for t in state.mine + state.others if not t.embedding or t.embedding_model != model]
    if need:
        res = await embed_texts([t.title for t in need], ctx=CallContext(ctx.owner_id, ctx.run_id))
        if res is None:
            return False
        vectors, used = res
        async with session_scope() as db:
            for t, vec in zip(need, vectors, strict=True):
                t.embedding, t.embedding_model = vec, used
                row = await db.get(Topic, t.id)
                if row is not None:
                    row.embedding, row.embedding_model = vec, used
    return True


def _candidates(state: State, threshold: float, max_pairs: int) -> list[dict[str, Any]]:
    pairs = []
    for a in state.mine:
        for b in state.others:
            sim = cosine(a.embedding or [], b.embedding or [])
            if sim >= threshold:
                pairs.append({"topic_a": a.title, "topic_a_code": a.code, "topic_a_id": str(a.id), "topic_b": b.title, "topic_b_code": b.code,
                              "course_code": b.course_code, "similarity": round(sim, 3)})
    pairs.sort(key=lambda p: -p["similarity"])
    return pairs[:max_pairs]


async def _relate(ctx: RunContext, state: State, candidates: list[dict[str, Any]], overlap_threshold: float) -> None:
    if not candidates:
        return
    ctx.prompt_versions["RELATE_TOPICS"] = P.PROMPT_VERSIONS["RELATE_TOPICS"]
    pairs_txt = "\n".join(f"- [{p['course_code']}] '{p['topic_a']}' ↔ '{p['topic_b']}' (similarity {p['similarity']:.2f})" for p in candidates)
    context = {"course_code": state.course.code, "pairs": candidates}
    async with session_scope() as db:
        res = await structured_call(
            purpose="relate_topics", usage_purpose=UsagePurpose.syllabus_check, system=P.RELATE_TOPICS_SYSTEM,
            user=P.RELATE_TOPICS_USER.format(course_code=state.course.code, pairs=pairs_txt),
            schema=P.RelateTopicsOut, ctx=CallContext(ctx.owner_id, ctx.run_id), db=db, context=context,
        )
    by_key = {(p["topic_a"], p["topic_b"], p["course_code"]): p for p in candidates}
    classified: dict[tuple[str, str, str], Any] = {}
    prov: dict[str, Any] = {}
    if res.value is None:
        await ctx.warn("relate", f"AI classification unavailable ({res.error}); relations derived from similarity only")
    else:
        ctx.model_used = res.model
        prov = {"model": res.model, "prompt": "RELATE_TOPICS"}
        for it in res.value.items:  # type: ignore[union-attr]
            classified[(it.topic_a, it.topic_b, it.course_code)] = it
    for key, p in by_key.items():
        it = classified.get(key)
        relation = it.relation if it and it.relation in ("overlap", "prerequisite", "distinct") else ("overlap" if p["similarity"] >= overlap_threshold else "distinct")
        rationale = it.rationale if it else f"Cosine similarity {p['similarity']:.2f} (threshold {overlap_threshold:.2f})."
        suggestion = it.suggestion if it else ""
        state.matrix.append({"course_code": p["course_code"], "topic_a": p["topic_a"], "topic_b": p["topic_b"], "similarity": p["similarity"], "relation": relation})
        if relation == "distinct":
            continue
        ftype = FindingType.overlap if relation == "overlap" else FindingType.prerequisite_gap
        state.findings.append(FindingDraft(
            type=ftype, severity=FindingSeverity.medium if relation == "overlap" and p["similarity"] >= 0.85 else FindingSeverity.low,
            title=(f"'{p['topic_a']}' overlaps {p['course_code']} · {p['topic_b']}" if relation == "overlap"
                   else f"'{p['topic_a']}' builds on {p['course_code']} · {p['topic_b']}"),
            rationale=rationale, evidence_snippet=f"{state.course.code} {p['topic_a_code']}: {p['topic_a']}\n{p['course_code']} {p['topic_b_code']}: {p['topic_b']}",
            target_kind=TargetKind.topic, target_id=uuid.UUID(p["topic_a_id"]), target_label=p["topic_a_code"],
            payload={**p, "relation": relation}, provenance=prov,
        ))
        if suggestion:
            state.findings.append(FindingDraft(
                type=FindingType.repositioning, severity=FindingSeverity.info,
                title=f"Reposition '{p['topic_a']}'", rationale=suggestion,
                evidence_snippet=f"{relation} with {p['course_code']} · {p['topic_b']} (similarity {p['similarity']:.2f})",
                target_kind=TargetKind.topic, target_id=uuid.UUID(p["topic_a_id"]), target_label=p["topic_a_code"],
                payload={"relation": relation, "course_code": p["course_code"]}, provenance=prov,
            ))
