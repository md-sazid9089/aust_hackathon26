"""Deterministic arithmetic for the Exam Paper Auditor (no LLM involvement; D-006)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.db.enums import HIGHER_ORDER_BLOOM, LOWER_ORDER_BLOOM, BloomLevel


@dataclass
class QStat:
    number: str
    marks: float
    co_codes: list[str] = field(default_factory=list)
    bloom: BloomLevel | None = None


@dataclass
class CoStat:
    code: str
    weight: float


DEFAULT_PARAMS: dict[str, Any] = {
    "dup_threshold": 0.80,
    "overweight_factor": 1.5,
    "bloom_lower_cap": 0.40,
    "bloom_higher_floor": 0.30,
    "fairness_max_single_share": 0.30,
}


def coverage(questions: list[QStat], cos: list[CoStat], overweight_factor: float) -> list[dict[str, Any]]:
    """Marks per CO (split evenly when a question maps to several COs) vs expected share by CO weight."""
    total = sum(q.marks for q in questions) or 0.0
    total_weight = sum(c.weight for c in cos) or 1.0
    marks_by_co = {c.code: 0.0 for c in cos}
    questions_by_co: dict[str, list[str]] = {c.code: [] for c in cos}
    for q in questions:
        valid = [c for c in q.co_codes if c in marks_by_co]
        if not valid:
            continue
        share = q.marks / len(valid)
        for c in valid:
            marks_by_co[c] += share
            questions_by_co[c].append(q.number)
    rows = []
    for c in cos:
        marks = round(marks_by_co[c.code], 2)
        share = marks / total if total else 0.0
        expected = c.weight / total_weight
        if marks == 0:
            status = "uncovered"
        elif expected > 0 and share > expected * overweight_factor:
            status = "overweight"
        else:
            status = "covered"
        rows.append(
            {
                "target_kind": "course_outcome", "target_code": c.code, "marks": marks,
                "share": round(share, 4), "expected_share": round(expected, 4), "status": status,
                "questions": questions_by_co[c.code],
            }
        )
    return rows


def coverage_pct(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    covered = sum(1 for r in rows if r["status"] != "uncovered")
    return round(100.0 * covered / len(rows), 1)


def untagged(questions: list[QStat], known_codes: set[str]) -> list[QStat]:
    return [q for q in questions if not any(c in known_codes for c in q.co_codes)]


def bloom_distribution(questions: list[QStat]) -> dict[str, Any]:
    total = sum(q.marks for q in questions) or 0.0
    counts = {b.value: 0 for b in BloomLevel}
    marks = {b.value: 0.0 for b in BloomLevel}
    unclassified = 0
    for q in questions:
        if q.bloom is None:
            unclassified += 1
            continue
        counts[q.bloom.value] += 1
        marks[q.bloom.value] += q.marks
    lower = sum(marks[b.value] for b in LOWER_ORDER_BLOOM)
    higher = sum(marks[b.value] for b in HIGHER_ORDER_BLOOM)
    return {
        "counts": counts,
        "marks": {k: round(v, 2) for k, v in marks.items()},
        "lower_order_share": round(lower / total, 4) if total else 0.0,
        "higher_order_share": round(higher / total, 4) if total else 0.0,
        "unclassified": unclassified,
    }


def marks_total(questions: list[QStat], declared: float | None) -> dict[str, Any]:
    computed = round(sum(q.marks for q in questions), 2)
    return {
        "computed": computed,
        "declared": declared,
        "mismatch": declared is not None and not math.isclose(computed, declared, abs_tol=0.01),
    }


def fairness(questions: list[QStat], max_single_share: float) -> dict[str, Any]:
    """Coefficient of variation of question marks + any single question carrying too much weight."""
    marks = [q.marks for q in questions if q.marks > 0]
    total = sum(marks)
    if len(marks) < 2 or total == 0:
        return {"deviation_score": 0.0, "heavy_questions": [], "notes": []}
    mean = total / len(marks)
    var = sum((m - mean) ** 2 for m in marks) / len(marks)
    cv = math.sqrt(var) / mean if mean else 0.0
    heavy = [
        {"number": q.number, "marks": q.marks, "share": round(q.marks / total, 4)}
        for q in questions
        if q.marks / total > max_single_share
    ]
    notes = []
    if cv > 0.5:
        notes.append(f"Marks per question vary widely (CV {cv:.2f}).")
    for h in heavy:
        notes.append(f"Question {h['number']} alone carries {h['share'] * 100:.0f}% of the paper.")
    return {"deviation_score": round(cv, 3), "heavy_questions": heavy, "notes": notes}


def top_similar(
    draft: list[tuple[str, list[float]]],
    others: list[tuple[str, list[float]]],
    *,
    threshold: float,
    k: int = 3,
    cosine_fn,
) -> dict[str, list[tuple[str, float]]]:
    """For each draft question id → up to k other question ids with cosine ≥ threshold."""
    out: dict[str, list[tuple[str, float]]] = {}
    for did, dvec in draft:
        sims = [(oid, cosine_fn(dvec, ovec)) for oid, ovec in others if oid != did]
        sims = [(oid, round(s, 4)) for oid, s in sims if s >= threshold]
        sims.sort(key=lambda t: t[1], reverse=True)
        if sims:
            out[did] = sims[:k]
    return out
