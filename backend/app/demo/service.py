"""Demo seed: loads the clearly-labelled sample dataset from data/seed-data into the caller's workspace.

Sample data only — not real university records. The draft paper contains deliberate flaws so the
Exam Auditor has something to find (see data/seed-data/_manifest.json → planted_flaws).
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.enums import ArtefactKind, BloomLevel, ExtractionStatus, MapSource, TextLang
from app.db.models import (
    Artefact,
    CoPoMap,
    Course,
    CourseOutcome,
    Profile,
    ProgramOutcome,
    Question,
    QuestionCoMap,
    Topic,
)
from app.errors import ApiError
from app.logging import get_logger

log = get_logger(__name__)

BLOOM_BY_ID = {"L1": BloomLevel.remember, "L2": BloomLevel.understand, "L3": BloomLevel.apply, "L4": BloomLevel.analyze, "L5": BloomLevel.evaluate, "L6": BloomLevel.create}


def _load(dir_: Path, name: str) -> list[dict[str, Any]]:
    path = dir_ / f"{name}.json"
    if not path.exists():
        raise ApiError("SEED_DATA_MISSING", 503, f"Seed data file missing: {name}.json")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


async def ensure_program_outcomes(db: AsyncSession) -> dict[str, ProgramOutcome]:
    existing = {p.code: p for p in (await db.execute(select(ProgramOutcome))).scalars()}
    if existing:
        return existing
    dir_ = get_settings().seed_data_dir
    pos = _load(dir_, "program_outcomes") if (dir_ / "program_outcomes.json").exists() else []
    if not pos:
        pos = [{"code": f"PO{i}", "statement": f"Programme outcome {i}"} for i in range(1, 13)]
    for i, p in enumerate(pos):
        row = ProgramOutcome(code=p["code"], text=p.get("statement") or p.get("text") or p["code"], sort_order=i)
        db.add(row)
        existing[row.code] = row
    await db.flush()
    return existing


def _paper_text(paper: dict[str, Any], questions: list[dict[str, Any]]) -> str:
    lines = [paper["title"], f"Total marks: {paper['declared_total_marks']}", ""]
    for q in questions:
        lines.append(f"{q['display_label']} {q['text']} [{q['marks']}]")
    return "\n".join(lines)


async def seed_demo(db: AsyncSession, user: Profile, *, with_gold_mapping: bool = False) -> tuple[Course, bool]:
    """Idempotent: returns the existing demo course for this user if present."""
    dir_ = get_settings().seed_data_dir
    courses = _load(dir_, "courses")
    seed_course = next((c for c in courses if c.get("is_seed_course")), courses[0])
    code = " ".join(seed_course["code"].upper().split())
    existing = (await db.execute(select(Course).where(Course.owner_id == user.id, Course.code == code, Course.deleted_at.is_(None)))).scalar_one_or_none()
    if existing is not None:
        return existing, False

    pos = await ensure_program_outcomes(db)
    course = Course(owner_id=user.id, code=code, title=seed_course["title"], term="Spring 2026 (demo)",
                    description="[DEMO DATA] " + seed_course.get("catalog_description", ""), is_demo=True)
    db.add(course)
    await db.flush()

    cos_by_seed_id: dict[str, CourseOutcome] = {}
    for i, co in enumerate(c for c in _load(dir_, "course_outcomes") if c["course_id"] == seed_course["course_id"]):
        row = CourseOutcome(course_id=course.id, code=co["code"], text=co["statement"], bloom_level=BLOOM_BY_ID.get(co.get("target_bloom_id")),
                            weight=float(co.get("weight_percent") or 1), sort_order=i)
        db.add(row)
        cos_by_seed_id[co["co_id"]] = row
    await db.flush()
    for m in _load(dir_, "co_po_map"):
        co, po = cos_by_seed_id.get(m["co_id"]), pos.get(m["po_id"])
        if co and po:
            db.add(CoPoMap(co_id=co.id, po_id=po.id, strength=int(m["strength"])))

    topics_by_seed_id: dict[str, Topic] = {}
    for i, t in enumerate(t for t in _load(dir_, "syllabus_topics") if t["course_id"] == seed_course["course_id"]):
        row = Topic(course_id=course.id, code=t["topic_id"], title=t["title"], sort_order=i)
        db.add(row)
        topics_by_seed_id[t["topic_id"]] = row

    questions = _load(dir_, "questions")
    for paper in (p for p in _load(dir_, "question_papers") if p["course_id"] == seed_course["course_id"]):
        pq = [q for q in questions if q["paper_id"] == paper["paper_id"]]
        art = Artefact(
            course_id=course.id, kind=ArtefactKind.question_paper,
            label=("[DRAFT] " if paper.get("is_draft") else "") + paper["title"],
            year=int(paper["session"].split()[-1]) if paper.get("session") else None, term=paper.get("session"),
            mime="text/plain", extracted_text=_paper_text(paper, pq), lang=TextLang.en, status=ExtractionStatus.done,
            declared_total_marks=float(paper["declared_total_marks"]) if paper.get("declared_total_marks") is not None else None,
        )
        art.size_bytes = len(art.extracted_text.encode())
        db.add(art)
        await db.flush()
        for i, q in enumerate(pq):
            row = Question(artefact_id=art.id, number=q["display_label"], text=q["text"], marks=float(q["marks"]), sort_order=i)
            db.add(row)
            # Past papers carry their archived CO tags as faculty ground truth; the draft is left for the AI.
            if with_gold_mapping or not paper.get("is_draft"):
                co = cos_by_seed_id.get(q.get("co_id") or "")
                if co is not None:
                    await db.flush()
                    db.add(QuestionCoMap(question_id=row.id, co_id=co.id, confidence=1.0, source=MapSource.faculty))
    await db.flush()
    log.info("demo.seeded", course_id=str(course.id), user_id=str(user.id))
    return course, True


def seed_dir_exists() -> bool:
    return (get_settings().seed_data_dir / "courses.json").exists()


__all__ = ["seed_demo", "ensure_program_outcomes", "seed_dir_exists", "uuid"]
