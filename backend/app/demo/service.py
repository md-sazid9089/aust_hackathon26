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
    await _seed_tier1(db, user, course, dir_, seed_course, cos_by_seed_id)
    log.info("demo.seeded", course_id=str(course.id), user_id=str(user.id))
    return course, True


DEMO_COMPARE_COURSES = ("CSE 1203", "CSE 3101", "CSE 4101")  # Data Structures, OS, Advanced DB → overlaps/prereqs vs CSE 3103
DEMO_GRADERS = {"F-002": "Grader A", "F-003": "Grader B"}


def _band_score(key: str) -> float:
    """'4', '4-5', '18-20' -> highest number in the band label."""
    import re

    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", key)]
    return max(nums) if nums else 0.0


def _bands(c: dict[str, Any]) -> list[tuple[str, str]]:
    return sorted(c.get("band_descriptors", {}).items(), key=lambda kv: -_band_score(kv[0]))


async def _seed_tier1(db: AsyncSession, user: Profile, course: Course, dir_: Path, seed_course: dict[str, Any], cos: dict[str, CourseOutcome]) -> None:
    """Marks sheet (P4), rubric + typed answers with two graders (P2), comparison courses with topics (P3)."""
    from app.artefacts.parsers import parse_marks_csv
    from app.db.models import Answer, MarksColumn, MarksRow, RubricCriterion

    def _art(kind: ArtefactKind, label: str, text: str, mime: str = "text/plain") -> Artefact:
        a = Artefact(course_id=course.id, kind=kind, label=label, term="Spring 2025", year=2025, mime=mime,
                     extracted_text=text, lang=TextLang.en, status=ExtractionStatus.done)
        a.size_bytes = len(text.encode())
        db.add(a)
        return a

    csv_path = dir_ / "student_marks_wide.csv"
    if csv_path.exists():
        text = csv_path.read_text(encoding="utf-8")
        art = _art(ArtefactKind.marks_sheet, "Final Examination marks, Spring 2025", text, "text/csv")
        await db.flush()
        parsed = parse_marks_csv(text)
        for i, c in enumerate(parsed["columns"]):
            db.add(MarksColumn(artefact_id=art.id, number=c["number"], max_marks=float(c["max_marks"] or 0), co_code=c["co_code"], sort_order=i))
        for i, r in enumerate(parsed["rows"]):
            db.add(MarksRow(artefact_id=art.id, student_anon_id=r["student_anon_id"], scores=r["scores"], sort_order=i))

    if (dir_ / "rubric_criteria.json").exists() and (dir_ / "answer_scripts.json").exists():
        rubrics = _load(dir_, "rubrics")
        criteria = _load(dir_, "rubric_criteria")
        rubric = rubrics[0] if rubrics else {"rubric_id": None, "title": "Rubric"}
        crit_rows = [c for c in criteria if c["rubric_id"] == rubric.get("rubric_id")] or criteria
        rubric_text = "\n".join(
            [f"Rubric: {rubric.get('title', 'Rubric')} ({rubric.get('total_marks', '')} marks)", ""]
            + [line for c in crit_rows for line in ([f"{c['code']} ({c['max_marks']} marks): {c['title']} — {c['descriptor']}"]
                                                       + [f"{_band_score(s):g}: {d}" for s, d in _bands(c)])]
        )
        rub_art = _art(ArtefactKind.rubric, f"Rubric — {rubric.get('title', 'Q6')}", rubric_text)
        await db.flush()
        for i, c in enumerate(crit_rows):
            levels = [{"label": s, "score": _band_score(s), "descriptor": d} for s, d in _bands(c)]
            db.add(RubricCriterion(artefact_id=rub_art.id, code=c["code"], text=f"{c['title']} — {c['descriptor']}", max_score=float(c["max_marks"]), levels=levels, sort_order=i))

        scripts = _load(dir_, "answer_scripts")
        scores = _load(dir_, "grader_scores")
        crit_code = {c["criterion_id"]: c["code"] for c in criteria}
        blocks = []
        for s in scripts:
            by_grader: dict[str, list[str]] = {}
            for g in scores:
                if g["script_id"] == s["script_id"]:
                    by_grader.setdefault(DEMO_GRADERS.get(g["grader_id"], g["grader_id"]), []).append(f"{crit_code.get(g['criterion_id'], g['criterion_id'])}={g['awarded_marks']}")
            blocks.append("\n".join([f"Student: {s['student_id']}   Question: 6", s["answer_text"]] + [f"{gl}: {', '.join(v)}" for gl, v in sorted(by_grader.items())]))
        ans_art = _art(ArtefactKind.answer_set, "Q6 typed answers — 6 scripts, 2 graders", "\n\n".join(blocks))
        await db.flush()
        for i, s in enumerate(scripts):
            gs = [{"grader_label": DEMO_GRADERS.get(g["grader_id"], g["grader_id"]), "criterion_code": crit_code.get(g["criterion_id"], g["criterion_id"]), "score": float(g["awarded_marks"])}
                  for g in scores if g["script_id"] == s["script_id"]]
            db.add(Answer(artefact_id=ans_art.id, student_anon_id=s["student_id"], question_ref="6", text=s["answer_text"], grader_scores=gs, sort_order=i))

    if (dir_ / "curriculum_courses.json").exists():
        for cc in _load(dir_, "curriculum_courses"):
            if cc["code"] not in DEMO_COMPARE_COURSES:
                continue
            code = " ".join(cc["code"].upper().split())
            exists = (await db.execute(select(Course).where(Course.owner_id == user.id, Course.code == code, Course.deleted_at.is_(None)))).scalar_one_or_none()
            if exists is not None:
                continue
            other = Course(owner_id=user.id, code=code, title=cc["title"], term="Catalogue (demo)", description="[DEMO DATA] comparison course for the syllabus check", is_demo=True)
            db.add(other)
            await db.flush()
            for i, kw in enumerate(cc.get("topic_keywords", [])):
                db.add(Topic(course_id=other.id, code=f"T-{i + 1:02d}", title=kw.capitalize(), sort_order=i))
    # a syllabus artefact for the seed course whose topics are the course's topics
    topics = [t for t in _load(dir_, "syllabus_topics") if t["course_id"] == seed_course["course_id"]]
    syl_text = "\n".join([f"{seed_course['code']} — Course syllabus", ""] + [f"Week {i + 1}: {t['title']}" for i, t in enumerate(topics)])
    syl = _art(ArtefactKind.syllabus, "Draft syllabus, Spring 2026", syl_text)
    await db.flush()
    await db.execute(
        Topic.__table__.update().where(Topic.course_id == course.id, Topic.source_artefact_id.is_(None)).values(source_artefact_id=syl.id)
    )
    await db.flush()


def seed_dir_exists() -> bool:
    return (get_settings().seed_data_dir / "courses.json").exists()


__all__ = ["seed_demo", "ensure_program_outcomes", "seed_dir_exists", "uuid"]
