"""P1 Exam Paper Auditor pipeline.

Stages: load_inputs → embed_questions → map_and_bloom → find_duplicates → compute_stats → persist.
Deterministic stages always run; an LLM stage that fails is recorded as a warning and the run ends `partial`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.ai.client import CallContext, get_provider, structured_call
from app.ai.embeddings import cosine, embed_texts
from app.ai.guard import wrap_untrusted
from app.config import get_settings
from app.db.enums import BloomLevel, FindingSeverity, FindingType, MapSource, TargetKind, UsagePurpose
from app.db.models import Artefact, CourseOutcome, Question, QuestionCoMap, QuestionTopicMap, Run, RunInput, Topic
from app.db.session import session_scope
from app.modules.base import FindingDraft, RunContext, StageFailed
from app.modules.exam_audit import prompts as P
from app.modules.exam_audit import stats
from app.modules.exam_audit.schemas import ConfirmDuplicatesOut, MapAndBloomOut

BATCH = 15
SNIPPET = 220


@dataclass
class QView:
    id: uuid.UUID
    artefact_id: uuid.UUID
    artefact_label: str
    number: str
    text: str
    marks: float
    bloom: BloomLevel | None
    bloom_source: MapSource | None
    co_codes: list[str] = field(default_factory=list)
    co_source: MapSource | None = None
    topic_codes: list[str] = field(default_factory=list)
    embedding: list[float] | None = None
    embedding_model: str | None = None
    map_rationale: str | None = None
    map_confidence: float | None = None
    prov: dict[str, Any] = field(default_factory=dict)

    @property
    def snippet(self) -> str:
        return self.text if len(self.text) <= SNIPPET else self.text[: SNIPPET - 1] + "…"


@dataclass
class State:
    draft: list[QView]
    past: list[QView]
    cos: list[CourseOutcome]
    topics: list[Topic]
    declared_total: float | None
    draft_label: str
    duplicates: list[dict[str, Any]] = field(default_factory=list)
    findings: list[FindingDraft] = field(default_factory=list)


def _hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def quote_is_verbatim(quote: str, source: str, *, min_len: int = 4) -> bool:
    """Whitespace/case-insensitive containment; guards against the model paraphrasing its 'verbatim' evidence."""
    q = _norm(quote)
    return len(q) >= min_len and q in _norm(source)


async def run_exam_audit(ctx: RunContext) -> dict[str, Any]:
    params = {**stats.DEFAULT_PARAMS, **(ctx.params or {})}
    state = await _load_inputs(ctx)
    await ctx.emit("load_inputs", f"Loaded {len(state.draft)} draft and {len(state.past)} past questions", 10)

    embedded = await _embed_questions(ctx, state)
    await ctx.emit("embed_questions", "Question embeddings ready" if embedded else "Embeddings unavailable", 30)

    await _map_and_bloom(ctx, state)
    await ctx.emit("map_and_bloom", "Questions mapped to outcomes and Bloom levels", 55)

    if embedded:
        await _find_duplicates(ctx, state, params)
    else:
        await ctx.warn("find_duplicates", "Skipped duplicate detection: embeddings unavailable")
    await ctx.emit("find_duplicates", f"{len(state.duplicates)} duplicate pair(s) confirmed", 75)

    summary = _compute_and_build(state, params)
    await ctx.emit("compute_stats", "Coverage, Bloom balance, marks and fairness computed", 90)

    async with session_scope() as db:
        run = await db.get(Run, ctx.run_id)
        assert run is not None
        db.add_all(f.to_model(run) for f in state.findings)
    return summary


# ---------------------------------------------------------------------------
async def _load_inputs(ctx: RunContext) -> State:
    async with session_scope() as db:
        run = await db.get(Run, ctx.run_id)
        if run is None:
            raise StageFailed("Run vanished")
        inputs = (await db.execute(select(RunInput).where(RunInput.run_id == ctx.run_id))).scalars().all()
        draft_ids = [i.artefact_id for i in inputs if i.role == "draft"]
        past_ids = [i.artefact_id for i in inputs if i.role == "past"]
        if len(draft_ids) != 1:
            raise StageFailed("Exactly one draft paper is required")
        artefacts = {a.id: a for a in (await db.execute(select(Artefact).where(Artefact.id.in_(draft_ids + past_ids)))).scalars()}
        if draft_ids[0] not in artefacts:
            raise StageFailed("Draft artefact no longer exists")
        cos = list((await db.execute(select(CourseOutcome).where(CourseOutcome.course_id == ctx.course_id).order_by(CourseOutcome.sort_order))).scalars())
        topics = list((await db.execute(select(Topic).where(Topic.course_id == ctx.course_id).order_by(Topic.sort_order))).scalars())
        co_code = {c.id: c.code for c in cos}
        topic_code = {t.id: t.code for t in topics}
        stmt = (
            select(Question)
            .where(Question.artefact_id.in_(list(artefacts)))
            .options(selectinload(Question.co_links), selectinload(Question.topic_links))
            .order_by(Question.sort_order)
        )
        views: dict[uuid.UUID, list[QView]] = {aid: [] for aid in artefacts}
        for q in (await db.execute(stmt)).scalars():
            links = [l for l in q.co_links if l.co_id in co_code]
            src = MapSource.faculty if any(l.source == MapSource.faculty for l in links) else (MapSource.ai if links else None)
            views[q.artefact_id].append(
                QView(
                    id=q.id, artefact_id=q.artefact_id, artefact_label=artefacts[q.artefact_id].label,
                    number=q.number, text=q.text, marks=float(q.marks), bloom=q.bloom_level, bloom_source=q.bloom_source,
                    co_codes=[co_code[l.co_id] for l in links if src is None or l.source == src],
                    co_source=src, topic_codes=[topic_code[l.topic_id] for l in q.topic_links if l.topic_id in topic_code],
                    embedding=q.embedding, embedding_model=q.embedding_model,
                )
            )
        draft = views[draft_ids[0]]
        if not draft:
            raise StageFailed("Draft paper has no questions; confirm the extraction first")
        if not cos:
            raise StageFailed("Course has no outcomes")
        run.context_snapshot = {
            "outcomes": [{"code": c.code, "text": c.text, "weight": float(c.weight)} for c in cos],
            "topics": [{"code": t.code, "title": t.title} for t in topics],
            "draft_questions": [{"number": q.number, "text": q.text, "marks": q.marks} for q in draft],
            "past_papers": [{"label": artefacts[a].label, "questions": len(views[a])} for a in past_ids if a in views],
        }
        return State(
            draft=draft, past=[q for a in past_ids if a in views for q in views[a]], cos=cos, topics=topics,
            declared_total=artefacts[draft_ids[0]].declared_total_marks, draft_label=artefacts[draft_ids[0]].label,
        )


async def _embed_questions(ctx: RunContext, state: State) -> bool:
    provider = get_provider()
    model = getattr(provider, "embed_model_name", None) or get_settings().embed_model
    need = [q for q in state.draft + state.past if not q.embedding or q.embedding_model != model]
    if need:
        res = await embed_texts([q.text for q in need], ctx=CallContext(ctx.owner_id, ctx.run_id))
        if res is None:
            await ctx.warn("embed_questions", "Embedding provider unavailable")
            return False
        vectors, used_model = res
        async with session_scope() as db:
            for q, vec in zip(need, vectors, strict=True):
                q.embedding, q.embedding_model = vec, used_model
                row = await db.get(Question, q.id)
                if row is not None:
                    row.embedding, row.embedding_model = vec, used_model
    # Cached vectors from a differently-sized model would silently score 0.0 in cosine.
    dims = {len(q.embedding) for q in state.draft + state.past if q.embedding}
    if len(dims) > 1:
        await ctx.warn("embed_questions", f"Mixed embedding dimensions {sorted(dims)}; duplicate detection skipped")
        return False
    return True


async def _map_and_bloom(ctx: RunContext, state: State) -> None:
    ctx.prompt_versions["MAP_AND_BLOOM"] = P.PROMPT_VERSIONS["MAP_AND_BLOOM"]
    co_by_code = {c.code: c for c in state.cos}
    topic_by_code = {t.code: t for t in state.topics}
    outcomes_txt = "\n".join(f"- {c.code}: {c.text}" for c in state.cos)
    topics_txt = "\n".join(f"- {t.code}: {t.title}" for t in state.topics) or "- (none provided)"
    failed_batches = 0
    deferred_warnings: list[str] = []
    for i in range(0, len(state.draft), BATCH):
        batch = state.draft[i : i + BATCH]
        questions_txt = "\n".join(f"{q.number} :: {wrap_untrusted(q.text, f'q{q.number}', 2000)}" for q in batch)
        context = {
            "outcomes": [{"code": c.code, "text": c.text} for c in state.cos],
            "topics": [{"code": t.code, "title": t.title} for t in state.topics],
            "questions": [{"number": q.number, "text": q.text} for q in batch],
        }
        async with session_scope() as db:
            res = await structured_call(
                purpose="map_and_bloom", usage_purpose=UsagePurpose.exam_audit, system=P.MAP_AND_BLOOM_SYSTEM,
                user=P.MAP_AND_BLOOM_USER.format(outcomes=outcomes_txt, topics=topics_txt, questions=questions_txt),
                schema=MapAndBloomOut, ctx=CallContext(ctx.owner_id, ctx.run_id), db=db, context=context,
            )
            if res.value is None:
                failed_batches += 1
                continue
            ctx.model_used = res.model
            out: MapAndBloomOut = res.value  # type: ignore[assignment]
            by_number = {q.number: q for q in batch}
            prov = {
                "model": res.model, "prompt_version": P.PROMPT_VERSIONS["MAP_AND_BLOOM"], "input_hash": _hash(context),
                "prompt_hash": res.prompt_hash, "response_mode": res.response_mode, "repaired": res.repaired,
            }
            for item in out.items:
                q = by_number.get("".join(item.number.split()))
                if q is None:
                    continue
                valid_cos = [c for c in dict.fromkeys(item.co_codes) if c in co_by_code][:2]
                valid_topics = [t for t in dict.fromkeys(item.topic_codes) if t in topic_by_code][:2]
                if len(valid_cos) != len(set(item.co_codes)) or len(valid_topics) != len(set(item.topic_codes)):
                    deferred_warnings.append(f"Dropped unknown or surplus CO/topic codes suggested for question {q.number}")
                evidence_ok = quote_is_verbatim(item.evidence_quote, q.text)
                if not evidence_ok:
                    deferred_warnings.append(f"AI evidence for question {q.number} is not a verbatim quote; confidence reduced")
                confidence = item.confidence if evidence_ok else min(item.confidence, 0.5)
                row = await db.get(Question, q.id, options=[selectinload(Question.co_links), selectinload(Question.topic_links)])
                if row is None:
                    continue
                if q.co_source != MapSource.faculty:
                    for l in list(row.co_links):
                        await db.delete(l)
                    await db.flush()
                    db.add_all(QuestionCoMap(question_id=q.id, co_id=co_by_code[c].id, confidence=confidence, source=MapSource.ai) for c in valid_cos)
                    q.co_codes, q.co_source = valid_cos, MapSource.ai if valid_cos else None
                for l in list(row.topic_links):
                    await db.delete(l)
                await db.flush()
                db.add_all(QuestionTopicMap(question_id=q.id, topic_id=topic_by_code[t].id, confidence=confidence, source=MapSource.ai) for t in valid_topics)
                q.topic_codes = valid_topics
                if q.bloom_source != MapSource.faculty:
                    row.bloom_level, row.bloom_source = item.bloom_level, MapSource.ai
                    q.bloom, q.bloom_source = item.bloom_level, MapSource.ai
                q.map_rationale = f"{item.rationale} Evidence: “{item.evidence_quote}”" if evidence_ok else item.rationale
                q.map_confidence = confidence
                q.prov = {**prov, "evidence_verbatim": evidence_ok}
    for w in deferred_warnings:  # emitted after the write session closed (SQLite single-writer)
        await ctx.warn("map_and_bloom", w)
    if failed_batches:
        await ctx.warn("map_and_bloom", f"AI mapping unavailable for {failed_batches} batch(es); using faculty mappings only")


async def _find_duplicates(ctx: RunContext, state: State, params: dict[str, Any]) -> None:
    ctx.prompt_versions["CONFIRM_DUPLICATES"] = P.PROMPT_VERSIONS["CONFIRM_DUPLICATES"]
    by_id = {str(q.id): q for q in state.draft + state.past}
    draft_vecs = [(str(q.id), q.embedding) for q in state.draft if q.embedding]
    other_vecs = [(str(q.id), q.embedding) for q in state.draft + state.past if q.embedding]
    candidates = stats.top_similar(draft_vecs, other_vecs, threshold=float(params["dup_threshold"]), cosine_fn=cosine)
    pairs = []
    seen: set[frozenset[str]] = set()
    for did, matches in candidates.items():
        for oid, sim in matches:
            key = frozenset((did, oid))
            if key in seen:
                continue
            seen.add(key)
            d, o = by_id[did], by_id[oid]
            pairs.append({"draft_number": d.number, "draft_id": did, "other_question_id": oid, "draft_text": d.text, "other_text": o.text, "similarity": sim})
    if not pairs:
        return
    # Similarity is deliberately NOT shown to the model (anchoring); it stays in `pairs` for provenance/findings.
    pairs_txt = "\n\n".join(
        f"PAIR draft_number={p['draft_number']} other_question_id={p['other_question_id']}\n"
        f"DRAFT: {wrap_untrusted(p['draft_text'], 'draft', 2000)}\nOTHER ({by_id[p['other_question_id']].artefact_label} {by_id[p['other_question_id']].number}): "
        f"{wrap_untrusted(p['other_text'], 'other', 2000)}"
        for p in pairs
    )
    async with session_scope() as db:
        res = await structured_call(
            purpose="confirm_duplicates", usage_purpose=UsagePurpose.exam_audit, system=P.CONFIRM_DUPLICATES_SYSTEM,
            user=P.CONFIRM_DUPLICATES_USER.format(pairs=pairs_txt), schema=ConfirmDuplicatesOut,
            ctx=CallContext(ctx.owner_id, ctx.run_id), db=db, context={"pairs": pairs},
        )
    if res.value is None:
        await ctx.warn("find_duplicates", f"AI confirmation unavailable; {len(pairs)} candidate pair(s) reported unconfirmed")
        for p in pairs:
            _add_duplicate(state, p, by_id, confirmed=False, rationale="Not confirmed by AI (provider unavailable); vector similarity only.", prov={})
        return
    ctx.model_used = ctx.model_used or res.model
    prov = {
        "model": res.model, "prompt_version": P.PROMPT_VERSIONS["CONFIRM_DUPLICATES"],
        "input_hash": _hash([p["draft_id"] + p["other_question_id"] for p in pairs]),
        "prompt_hash": res.prompt_hash, "response_mode": res.response_mode,
    }
    verdicts = {(v.draft_number, v.other_question_id): v for v in res.value.items}  # type: ignore[union-attr]
    for p in pairs:
        v = verdicts.get((p["draft_number"], p["other_question_id"]))
        if v is None or not v.is_duplicate:
            continue
        d, o = by_id[p["draft_id"]], by_id[p["other_question_id"]]
        verbatim = quote_is_verbatim(v.evidence_draft, d.text) and quote_is_verbatim(v.evidence_other, o.text)
        rationale = f"{v.rationale} ({v.level}, confidence {v.confidence:.2f})"
        if verbatim:
            rationale += f' Draft: “{v.evidence_draft}” — {o.artefact_label}: “{v.evidence_other}”.'
        _add_duplicate(state, p, by_id, confirmed=True, rationale=rationale, prov={**prov, "level": v.level, "confidence": v.confidence, "evidence_verbatim": verbatim})


def _add_duplicate(state: State, p: dict[str, Any], by_id: dict[str, QView], *, confirmed: bool, rationale: str, prov: dict) -> None:
    d, o = by_id[p["draft_id"]], by_id[p["other_question_id"]]
    intra = o.artefact_id == d.artefact_id
    state.duplicates.append({"draft_number": d.number, "past_label": o.artefact_label, "past_number": o.number, "similarity": p["similarity"], "confirmed": confirmed, "intra_paper": intra})
    state.findings.append(
        FindingDraft(
            type=FindingType.duplicate,
            severity=FindingSeverity.high if confirmed and not intra else FindingSeverity.medium,
            title=(f"Q{d.number} repeats {o.artefact_label} Q{o.number}" if not intra else f"Q{d.number} overlaps Q{o.number} in the same paper")
            + ("" if confirmed else " (unconfirmed)"),
            rationale=f"{rationale} Vector similarity {p['similarity']:.2f}.",
            evidence_snippet=f"Draft Q{d.number}: {d.snippet}\n{o.artefact_label} Q{o.number}: {o.snippet}",
            target_kind=TargetKind.question, target_id=d.id, target_label=d.number,
            payload={"other_question_id": str(o.id), "other_artefact_id": str(o.artefact_id), "other_label": o.artefact_label, "other_number": o.number, "similarity": p["similarity"], "confirmed": confirmed, "intra_paper": intra},
            provenance=prov,
        )
    )


def _compute_and_build(state: State, params: dict[str, Any]) -> dict[str, Any]:
    qstats = [stats.QStat(q.number, q.marks, q.co_codes, q.bloom) for q in state.draft]
    costats = [stats.CoStat(c.code, float(c.weight)) for c in state.cos]
    co_by_code = {c.code: c for c in state.cos}
    cov = stats.coverage(qstats, costats, float(params["overweight_factor"]))
    bloom = stats.bloom_distribution(qstats)
    total = stats.marks_total(qstats, state.declared_total)
    fair = stats.fairness(qstats, float(params["fairness_max_single_share"]))
    untagged = stats.untagged(qstats, set(co_by_code))
    q_by_number = {q.number: q for q in state.draft}

    for row in cov:
        co = co_by_code[row["target_code"]]
        if row["status"] == "uncovered":
            state.findings.append(FindingDraft(
                type=FindingType.coverage_gap, severity=FindingSeverity.high,
                title=f"{co.code} is not assessed by any question",
                rationale=f"No question in '{state.draft_label}' maps to {co.code} (expected ≈{row['expected_share'] * 100:.0f}% of marks by CO weight). Students cannot demonstrate this outcome.",
                evidence_snippet=f"{co.code}: {co.text}", target_kind=TargetKind.course_outcome, target_id=co.id, target_label=co.code, payload=row,
            ))
        elif row["status"] == "overweight":
            state.findings.append(FindingDraft(
                type=FindingType.overweight, severity=FindingSeverity.medium,
                title=f"{co.code} carries {row['share'] * 100:.0f}% of marks (expected ≈{row['expected_share'] * 100:.0f}%)",
                rationale=f"Questions {', '.join(row['questions'])} total {row['marks']:g} marks on {co.code}, more than {params['overweight_factor']}× its weighted share.",
                evidence_snippet=f"{co.code}: {co.text}", target_kind=TargetKind.course_outcome, target_id=co.id, target_label=co.code, payload=row,
            ))
    for q in untagged:
        qv = q_by_number[q.number]
        state.findings.append(FindingDraft(
            type=FindingType.untagged_question, severity=FindingSeverity.medium,
            title=f"Q{q.number} is not mapped to any course outcome",
            rationale=qv.map_rationale or "Neither faculty nor AI mapping links this question to a CO; its marks count toward no outcome.",
            evidence_snippet=qv.snippet, target_kind=TargetKind.question, target_id=qv.id, target_label=q.number,
            payload={"marks": q.marks}, provenance=qv.prov,
        ))
    lower_cap, higher_floor = float(params["bloom_lower_cap"]), float(params["bloom_higher_floor"])
    if bloom["lower_order_share"] > lower_cap:
        state.findings.append(FindingDraft(
            type=FindingType.bloom_imbalance, severity=FindingSeverity.medium,
            title=f"{bloom['lower_order_share'] * 100:.0f}% of marks test remember/understand (cap {lower_cap * 100:.0f}%)",
            rationale="Lower-order questions dominate; the paper under-tests application and analysis relative to the course policy.",
            evidence_snippet=_bloom_evidence(state.draft, {BloomLevel.remember, BloomLevel.understand}),
            target_kind=TargetKind.none, target_label="bloom_lower", payload=bloom,
        ))
    if bloom["higher_order_share"] < higher_floor and bloom["unclassified"] < len(qstats):
        state.findings.append(FindingDraft(
            type=FindingType.bloom_imbalance, severity=FindingSeverity.medium,
            title=f"Only {bloom['higher_order_share'] * 100:.0f}% of marks test analyze/evaluate/create (floor {higher_floor * 100:.0f}%)",
            rationale="Too few marks require higher-order thinking for a paper at this level.",
            evidence_snippet=_bloom_evidence(state.draft, set(BloomLevel) - {BloomLevel.remember, BloomLevel.understand, BloomLevel.apply}) or "No higher-order questions found.",
            target_kind=TargetKind.none, target_label="bloom_higher", payload=bloom,
        ))
    if total["mismatch"]:
        state.findings.append(FindingDraft(
            type=FindingType.marks_total_mismatch, severity=FindingSeverity.high,
            title=f"Questions total {total['computed']:g} marks but the paper declares {total['declared']:g}",
            rationale="Sum of extracted question marks differs from the declared total; check extraction or the paper.",
            evidence_snippet=", ".join(f"Q{q.number}={q.marks:g}" for q in qstats), target_kind=TargetKind.none, target_label="marks_total", payload=total,
        ))
    for h in fair["heavy_questions"]:
        qv = q_by_number[h["number"]]
        state.findings.append(FindingDraft(
            type=FindingType.fairness, severity=FindingSeverity.low,
            title=f"Q{h['number']} carries {h['share'] * 100:.0f}% of total marks",
            rationale="A single question dominating the paper makes the result sensitive to one topic.",
            evidence_snippet=qv.snippet, target_kind=TargetKind.question, target_id=qv.id, target_label=h["number"], payload=h,
        ))
    return {
        "draft_label": state.draft_label, "questions": len(state.draft), "past_questions": len(state.past),
        "coverage_pct": stats.coverage_pct(cov), "coverage": cov, "bloom": bloom, "marks_total": total,
        "duplicates": state.duplicates, "fairness": fair, "untagged": [q.number for q in untagged],
        "findings": len(state.findings),
        "mapping": [
            {"number": q.number, "co_codes": q.co_codes, "topic_codes": q.topic_codes, "bloom_level": q.bloom.value if q.bloom else None,
             "source": q.co_source.value if q.co_source else None, "confidence": q.map_confidence, "rationale": q.map_rationale}
            for q in state.draft
        ],
    }


def _bloom_evidence(draft: list[QView], levels: set[BloomLevel]) -> str:
    rows = [f"Q{q.number} [{q.bloom.value}, {q.marks:g}m]: {q.snippet[:80]}" for q in draft if q.bloom in levels]
    return "\n".join(rows[:6])
