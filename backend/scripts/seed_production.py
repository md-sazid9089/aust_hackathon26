"""Seed production-grade showcase data: real faculty/admin accounts, courses, syllabi, papers, marks, rubrics.

Usage (from backend/, uses DATABASE_URL etc. from .env):

    .venv/bin/python scripts/seed_production.py                      # create/refresh accounts + courses
    .venv/bin/python scripts/seed_production.py --replace            # drop previously seeded courses first
    .venv/bin/python scripts/seed_production.py --run-api http://localhost:8000   # also start every module via the live API
    .venv/bin/python scripts/seed_production.py --credentials .seed-credentials.json

Passwords: read from --credentials (JSON list of {email, password}) when given; otherwise strong random
passwords are generated, written to backend/.seed-credentials.json (gitignored, mode 600) and printed once.
Re-running with the same credentials file is idempotent and resets those passwords.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import secrets
import string
import sys
import time
import uuid
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "scripts"))

import seed_content as C  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.artefacts.parsers import parse_marks_csv  # noqa: E402
from app.auth.passwords import hash_password  # noqa: E402
from app.auth.service import sync_role_permissions  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db.enums import AppRole, ArtefactKind, BloomLevel, ExtractionStatus, MapSource, TextLang  # noqa: E402
from app.db.models import (  # noqa: E402
    Answer,
    Artefact,
    CoPoMap,
    Course,
    CourseOutcome,
    MarksColumn,
    MarksRow,
    Profile,
    ProgramOutcome,
    Question,
    QuestionCoMap,
    RubricCriterion,
    Run,
    Topic,
)
from app.db.session import get_engine, get_sessionmaker  # noqa: E402
from app.demo.service import BLOOM_BY_ID, ensure_program_outcomes  # noqa: E402

CRED_FILE = BACKEND_DIR / ".seed-credentials.json"
SEED_COURSE_CODE = "CSE 3103"  # loaded from data/seed-data for rezwana.karim@aust.edu


def _gen_password() -> str:
    alphabet = string.ascii_letters + string.digits
    core = "".join(secrets.choice(alphabet) for _ in range(12))
    return f"{core[:4]}-{core[4:8]}-{core[8:]}!{secrets.choice(string.digits)}"


def load_credentials(path: Path | None) -> dict[str, str]:
    creds: dict[str, str] = {}
    if path and path.exists():
        for row in json.loads(path.read_text()):
            creds[row["email"].lower()] = row["password"]
    return creds


def save_credentials(path: Path, accounts: list[dict], creds: dict[str, str]) -> None:
    rows = [{"email": a["email"], "password": creds[a["email"]], "role": a["role"], "full_name": a["full_name"]} for a in accounts]
    path.write_text(json.dumps(rows, indent=2) + "\n")
    os.chmod(path, 0o600)


# ------------------------------------------------------------------------------------------------------------
# accounts
# ------------------------------------------------------------------------------------------------------------
async def upsert_accounts(db: AsyncSession, creds: dict[str, str]) -> dict[str, Profile]:
    out: dict[str, Profile] = {}
    for a in C.ACCOUNTS:
        email = a["email"].lower()
        profile = (await db.execute(select(Profile).where(Profile.email == email))).scalar_one_or_none()
        if profile is None:
            profile = Profile(id=uuid.uuid4(), email=email)
            db.add(profile)
        profile.full_name = a["full_name"]
        profile.role = AppRole(a["role"])
        profile.is_active = True
        profile.password_hash = hash_password(creds[email])
        out[email] = profile
    await db.flush()
    return out


# ------------------------------------------------------------------------------------------------------------
# course builders
# ------------------------------------------------------------------------------------------------------------
async def _existing_course(db: AsyncSession, owner: Profile, code: str) -> Course | None:
    return (await db.execute(select(Course).where(Course.owner_id == owner.id, Course.code == code, Course.deleted_at.is_(None)))).scalar_one_or_none()


async def _hard_delete_course(db: AsyncSession, course: Course) -> None:
    # Runs first: run_inputs → artefacts is ON DELETE RESTRICT, so the course cascade alone would be blocked.
    for run in (await db.execute(select(Run).where(Run.course_id == course.id))).scalars():
        await db.delete(run)
    await db.flush()
    await db.delete(course)
    await db.flush()


def _artefact(course: Course, kind: ArtefactKind, label: str, text: str, *, year: int | None, term: str | None, declared: float | None = None) -> Artefact:
    art = Artefact(course_id=course.id, kind=kind, label=label, year=year, term=term, mime="text/plain",
                   extracted_text=text, lang=TextLang.en, status=ExtractionStatus.done, declared_total_marks=declared)
    art.size_bytes = len(text.encode())
    return art


async def _add_paper(db: AsyncSession, course: Course, paper: dict, cos: dict[str, CourseOutcome]) -> Artefact:
    art = _artefact(course, ArtefactKind.question_paper, paper["label"], C.paper_text(paper),
                    year=paper["year"], term=paper["term"], declared=float(paper["declared_total"]))
    db.add(art)
    await db.flush()
    for i, (number, text, marks, co_code) in enumerate(paper["questions"]):
        q = Question(artefact_id=art.id, number=number, text=text, marks=float(marks), sort_order=i)
        db.add(q)
        await db.flush()
        if co_code and co_code in cos:
            db.add(QuestionCoMap(question_id=q.id, co_id=cos[co_code].id, confidence=1.0, source=MapSource.faculty))
    return art


def _generate_marks(paper: dict, spec: dict, seed: str) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    columns = [{"number": n, "max_marks": float(m), "co_code": co} for n, _t, m, co in paper["questions"]]
    rows: list[dict] = []
    for s in range(1, spec["students"] + 1):
        student_bias = rng.gauss(0, 0.10)
        scores: dict[str, float] = {}
        for col in columns:
            mu = spec["ability"].get(col["co_code"], 0.7) + student_bias
            frac = min(1.0, max(0.0, rng.gauss(mu, 0.16)))
            scores[col["number"]] = round(frac * col["max_marks"] * 2) / 2
        rows.append({"student_anon_id": f"S-{s:03d}", "scores": scores})
    return columns, rows


async def _add_marks(db: AsyncSession, course: Course, label: str, columns: list[dict], rows: list[dict], *, year: int | None, term: str | None) -> Artefact:
    header = ["student_id", *[f"{c['number']} ({c['co_code']}/{c['max_marks']:g})" if c["co_code"] else f"{c['number']} ({c['max_marks']:g})" for c in columns]]
    lines = [",".join(header)]
    for r in rows:
        lines.append(",".join([r["student_anon_id"], *[f"{r['scores'].get(c['number'], 0):g}" for c in columns]]))
    art = _artefact(course, ArtefactKind.marks_sheet, label, "\n".join(lines), year=year, term=term)
    art.mime = "text/csv"
    db.add(art)
    await db.flush()
    for i, c in enumerate(columns):
        db.add(MarksColumn(artefact_id=art.id, number=c["number"], max_marks=float(c["max_marks"] or 0), co_code=c["co_code"], sort_order=i))
    for i, r in enumerate(rows):
        db.add(MarksRow(artefact_id=art.id, student_anon_id=r["student_anon_id"][:40], scores=r["scores"], sort_order=i))
    return art


async def _add_rubric(db: AsyncSession, course: Course, spec: dict) -> Artefact:
    lines = [spec["label"], ""]
    for code, text, max_score, levels in spec["criteria"]:
        lines.append(f"{code} ({max_score} marks): {text}")
        for label, _score, desc in levels:
            lines.append(f"  {label}: {desc}")
    art = _artefact(course, ArtefactKind.rubric, spec["label"], "\n".join(lines), year=spec.get("year"), term=spec.get("term"))
    db.add(art)
    await db.flush()
    for i, (code, text, max_score, levels) in enumerate(spec["criteria"]):
        db.add(RubricCriterion(artefact_id=art.id, code=code, text=text, max_score=float(max_score),
                               levels=[{"label": lab, "score": float(sc), "descriptor": d} for lab, sc, d in levels], sort_order=i))
    return art


async def _add_answers(db: AsyncSession, course: Course, spec: dict) -> Artefact:
    lines = [spec["label"], ""]
    for sid, qref, text, grades in spec["items"]:
        lines += [f"Student: {sid}  Question: {qref}", text]
        for grader, scores in grades.items():
            lines.append(f"{grader}: " + ", ".join(f"{k}={v}" for k, v in scores.items()))
        lines.append("")
    art = _artefact(course, ArtefactKind.answer_set, spec["label"], "\n".join(lines), year=spec.get("year"), term=spec.get("term"))
    db.add(art)
    await db.flush()
    for i, (sid, qref, text, grades) in enumerate(spec["items"]):
        gs = [{"grader_label": g, "criterion_code": crit, "score": float(sc)} for g, scores in grades.items() for crit, sc in scores.items()]
        db.add(Answer(artefact_id=art.id, student_anon_id=sid, question_ref=qref, text=text, grader_scores=gs, sort_order=i))
    return art


async def build_authored_course(db: AsyncSession, owner: Profile, spec: dict, pos: dict[str, ProgramOutcome]) -> Course:
    course = Course(owner_id=owner.id, code=spec["code"], title=spec["title"], term=spec["term"], description=spec["description"], is_demo=False)
    db.add(course)
    await db.flush()

    cos: dict[str, CourseOutcome] = {}
    for i, (code, text, bloom, weight) in enumerate(spec["outcomes"]):
        row = CourseOutcome(course_id=course.id, code=code, text=text, bloom_level=BloomLevel(bloom), weight=float(weight), sort_order=i)
        db.add(row)
        cos[code] = row
    await db.flush()
    for co_code, links in spec["co_po"].items():
        for po_code, strength in links:
            if po_code in pos:
                db.add(CoPoMap(co_id=cos[co_code].id, po_id=pos[po_code].id, strength=int(strength)))

    syllabus = _artefact(course, ArtefactKind.syllabus, f"Course outline — {spec['code']} {spec['term']}", C.syllabus_text(spec), year=None, term=spec["term"])
    db.add(syllabus)
    await db.flush()
    for i, (code, title) in enumerate(spec["topics"]):
        db.add(Topic(course_id=course.id, code=code, title=title, source_artefact_id=syllabus.id, sort_order=i))

    papers: list[Artefact] = []
    for paper in spec["papers"]:
        papers.append(await _add_paper(db, course, paper, cos))

    if spec.get("marks"):
        m = spec["marks"]
        paper = spec["papers"][m["paper"]]
        cols, rows = _generate_marks(paper, m, seed=f"{owner.email}:{spec['code']}")
        await _add_marks(db, course, f"Marks sheet — {paper['label']}", cols, rows, year=paper["year"], term=m.get("term"))
    if spec.get("rubric"):
        await _add_rubric(db, course, spec["rubric"])
    if spec.get("answers"):
        await _add_answers(db, course, spec["answers"])
    await db.flush()
    return course


def _load_json(name: str) -> Any:
    return json.loads((get_settings().seed_data_dir / f"{name}.json").read_text(encoding="utf-8"))


async def build_dataset_course(db: AsyncSession, owner: Profile, pos: dict[str, ProgramOutcome]) -> Course:
    """CSE 3103 from data/seed-data: 3 papers, marks CSV, rubric + 6 scripts × 2 graders (no demo labels)."""
    seed_course = next(c for c in _load_json("courses") if c.get("is_seed_course"))
    cid = seed_course["course_id"]
    course = Course(owner_id=owner.id, code=SEED_COURSE_CODE, title=seed_course["title"], term="Spring 2026",
                    description=seed_course.get("catalog_description", ""), is_demo=False)
    db.add(course)
    await db.flush()

    cos: dict[str, CourseOutcome] = {}
    for i, co in enumerate(c for c in _load_json("course_outcomes") if c["course_id"] == cid):
        row = CourseOutcome(course_id=course.id, code=co["code"], text=co["statement"], bloom_level=BLOOM_BY_ID.get(co.get("target_bloom_id")),
                            weight=float(co.get("weight_percent") or 1), sort_order=i)
        db.add(row)
        cos[co["co_id"]] = row
    await db.flush()
    for m in _load_json("co_po_map"):
        if m["co_id"] in cos and m["po_id"] in pos:
            db.add(CoPoMap(co_id=cos[m["co_id"]].id, po_id=pos[m["po_id"]].id, strength=int(m["strength"])))

    topics = [t for t in _load_json("syllabus_topics") if t["course_id"] == cid]
    syl_lines = [f"{SEED_COURSE_CODE} {seed_course['title']}", "Ahsanullah University of Science and Technology — Department of CSE", "",
                 "Course description", seed_course.get("catalog_description", ""), "", "Course outcomes"]
    syl_lines += [f"{c.code}: {c.text} (weight {c.weight:g}%)" for c in cos.values()]
    syl_lines += ["", "Weekly topics"] + [f"Week {t['week']}: {t['title']}" for t in topics]
    syllabus = _artefact(course, ArtefactKind.syllabus, f"Course outline — {SEED_COURSE_CODE} Spring 2026", "\n".join(syl_lines), year=None, term="Spring 2026")
    db.add(syllabus)
    await db.flush()
    for i, t in enumerate(topics):
        db.add(Topic(course_id=course.id, code=t["topic_id"], title=t["title"], source_artefact_id=syllabus.id, sort_order=i))

    questions = _load_json("questions")
    paper_art: dict[str, Artefact] = {}
    for paper in (p for p in _load_json("question_papers") if p["course_id"] == cid):
        pq = [q for q in questions if q["paper_id"] == paper["paper_id"]]
        spec = {"label": paper["title"].replace(" (DRAFT)", ""), "year": int(paper["session"].split()[-1]), "term": paper["session"],
                "declared_total": paper["declared_total_marks"],
                "questions": [(q["display_label"], q["text"], q["marks"], None if paper.get("is_draft") else q.get("co_id")) for q in pq]}
        by_code = {c.code: c for c in cos.values()}
        paper_art[paper["paper_id"]] = await _add_paper(db, course, spec, by_code)

    csv_path = get_settings().seed_data_dir / "student_marks_wide.csv"
    if csv_path.exists():
        parsed = parse_marks_csv(csv_path.read_text(encoding="utf-8"))
        await _add_marks(db, course, "Marks sheet — Final Examination, Spring 2025", parsed["columns"], parsed["rows"], year=2025, term="Spring 2025")

    rubric = next(iter(_load_json("rubrics")), None)
    if rubric:
        crits = sorted((c for c in _load_json("rubric_criteria") if c["rubric_id"] == rubric["rubric_id"]), key=lambda c: c["sequence"])

        def band_score(label: str) -> float:  # "4-5" → 5 (top of band)
            return float(label.split("-")[-1])

        rubric_spec = {
            "label": f"Rubric — Q6 {rubric['title']} ({rubric['total_marks']} marks)", "year": 2025, "term": "Spring 2025",
            "criteria": [(c["code"], f"{c['title']}: {c['descriptor']}", c["max_marks"],
                          [(k, band_score(k), v) for k, v in sorted(c["band_descriptors"].items(), key=lambda kv: -band_score(kv[0]))]) for c in crits],
        }
        await _add_rubric(db, course, rubric_spec)
        crit_code = {c["criterion_id"]: c["code"] for c in crits}
        grader_label: dict[str, str] = {}
        scores_by_script: dict[str, dict[str, dict[str, float]]] = {}
        for g in _load_json("grader_scores"):
            label = grader_label.setdefault(g["grader_id"], f"Grader {chr(ord('A') + len(grader_label))}")
            scores_by_script.setdefault(g["script_id"], {}).setdefault(label, {})[crit_code[g["criterion_id"]]] = g["awarded_marks"]
        items = [(s["student_id"], "6", s["answer_text"], scores_by_script.get(s["script_id"], {})) for s in _load_json("answer_scripts")]
        await _add_answers(db, course, {"label": "Answer scripts — Q6 Normalisation, Spring 2025 (two graders)", "year": 2025, "term": "Spring 2025", "items": items})
    await db.flush()
    return course


# ------------------------------------------------------------------------------------------------------------
# optional: exercise every module through the live API so dashboards have history
# ------------------------------------------------------------------------------------------------------------
def run_modules_via_api(base: str, creds: dict[str, str]) -> None:
    import httpx

    api = base.rstrip("/") + "/api/v1"
    with httpx.Client(base_url=api, timeout=60) as c:
        for a in C.ACCOUNTS:
            if a["role"] != "faculty":
                continue
            r = c.post("/auth/login", json={"email": a["email"], "password": creds[a["email"].lower()]})
            r.raise_for_status()
            h = {"Authorization": f"Bearer {r.json()['access_token']}"}
            courses = c.get("/courses", headers=h, params={"page_size": 50}).json()["items"]
            course_ids = [k["id"] for k in courses]
            for course in courses:
                arts = c.get(f"/courses/{course['id']}/artefacts", headers=h).json()
                by_kind: dict[str, list[dict]] = {}
                for art in arts:
                    by_kind.setdefault(art["kind"], []).append(art)
                papers = sorted(by_kind.get("question_paper", []), key=lambda x: (x.get("year") or 0, x["label"]))
                jobs: list[tuple[str, dict]] = []
                if len(papers) >= 2:
                    jobs.append(("exam_audit", {"draft_artefact_id": papers[-1]["id"], "past_artefact_ids": [p["id"] for p in papers[:-1]]}))
                if by_kind.get("marks_sheet") and papers:
                    jobs.append(("attainment", {"marks_artefact_id": by_kind["marks_sheet"][0]["id"], "paper_artefact_id": papers[0]["id"]}))
                if by_kind.get("rubric") and by_kind.get("answer_set"):
                    jobs.append(("calibration", {"rubric_artefact_id": by_kind["rubric"][0]["id"], "answer_set_artefact_id": by_kind["answer_set"][0]["id"]}))
                others = [k for k in course_ids if k != course["id"]]
                if by_kind.get("syllabus") and others:
                    jobs.append(("syllabus_check", {"syllabus_artefact_id": by_kind["syllabus"][0]["id"], "compare_course_ids": others[:3]}))
                for module, inputs in jobs:
                    r = c.post(f"/courses/{course['id']}/runs", headers=h, json={"module": module, "inputs": inputs, "params": {}})
                    if r.status_code != 202:
                        print(f"  ! {course['code']} {module}: {r.status_code} {r.text[:160]}")
                        continue
                    run_id = r.json()["id"]
                    status = "queued"
                    for _ in range(90):
                        time.sleep(1)
                        status = c.get(f"/runs/{run_id}", headers=h).json()["status"]
                        if status in ("completed", "partial", "failed"):
                            break
                    print(f"  {a['email']:28s} {course['code']:9s} {module:15s} → {status}")
                    if module == "exam_audit" and status in ("completed", "partial"):
                        body = c.get(f"/runs/{run_id}/findings", headers=h, params={"page_size": 50}).json()
                        findings = body if isinstance(body, list) else body.get("items", [])
                        for f in findings:
                            if f["severity"] == "high" and f["status"] == "open":
                                c.patch(f"/findings/{f['id']}", headers=h, json={"status": "accepted"})
                                break
                        for f in findings:
                            if f["severity"] == "info" and f["status"] == "open":
                                c.patch(f"/findings/{f['id']}", headers=h, json={"status": "dismissed"})
                                break


# ------------------------------------------------------------------------------------------------------------
async def main(args: argparse.Namespace) -> None:
    settings = get_settings()
    print(f"database: {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}")

    cred_path = Path(args.credentials) if args.credentials else CRED_FILE
    creds = load_credentials(cred_path)
    generated = False
    for a in C.ACCOUNTS:
        if a["email"].lower() not in creds:
            creds[a["email"].lower()] = _gen_password()
            generated = True
    if generated:
        save_credentials(cred_path, C.ACCOUNTS, creds)

    sm = get_sessionmaker()
    async with sm() as db:
        try:
            await sync_role_permissions(db)
            profiles = await upsert_accounts(db, creds)
            pos = await ensure_program_outcomes(db)
            summary: list[str] = []
            targets = [(SEED_COURSE_CODE, "rezwana.karim@aust.edu", None)] + [(s["code"], s["owner"], s) for s in C.COURSES]
            for code, owner_email, spec in targets:
                owner = profiles[owner_email]
                existing = await _existing_course(db, owner, code)
                if existing is not None and args.replace:
                    await _hard_delete_course(db, existing)
                    existing = None
                if existing is not None:
                    summary.append(f"  = {owner_email:28s} {code}  (kept)")
                    continue
                course = await build_dataset_course(db, owner, pos) if spec is None else await build_authored_course(db, owner, spec, pos)
                summary.append(f"  + {owner_email:28s} {code}  {course.title}")
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    await get_engine().dispose()

    print("\ncourses:")
    print("\n".join(summary))
    print(f"\ncredentials file: {cred_path}")
    print(f"{'role':8s} {'email':28s} password")
    for a in C.ACCOUNTS:
        print(f"{a['role']:8s} {a['email']:28s} {creds[a['email'].lower()]}")

    if args.run_api:
        print(f"\nrunning modules via {args.run_api} …")
        run_modules_via_api(args.run_api, creds)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--credentials", help="JSON file with [{email, password}] (default: backend/.seed-credentials.json)")
    p.add_argument("--replace", action="store_true", help="delete previously seeded courses for these accounts and rebuild")
    p.add_argument("--run-api", metavar="URL", help="after seeding, log in as each faculty and start every module against this running API")
    asyncio.run(main(p.parse_args()))
