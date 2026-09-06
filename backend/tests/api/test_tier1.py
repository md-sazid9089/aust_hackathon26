"""Tier-1 modules and endpoints: attainment, syllabus_check, calibration, compare, suggest, dashboard, admin."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import DRAFT_PAPER, OUTCOMES, PAST_PAPER, as_user, make_course, upload_text, wait_until_done

MARKS_CSV = """student_id,name,1(a) (CO1/6),1(b) (CO1/6),2(a) (CO2/6),2(b) (CO3/7),3(a) (CO1/6),3(b) (CO4/10),4(a) (CO3/7),4(b) (CO5/5),5 (CO1/5),total
S-001,Alice,5,5,5,6,5,4,6,4,4,44
S-002,Bob,4,5,4,5,4,3,5,3,4,37
S-003,Carol,6,6,6,7,6,2,7,5,5,50
S-004,Dan,3,3,3,4,3,1,4,2,3,26
S-005,Eve,5,4,5,6,5,3,6,4,4,42
"""

RUBRIC_TXT = """Rubric: Normalisation to 3NF (20 marks)
R1 (4 marks): Anomaly identification — All three anomaly types named and illustrated.
4: All three anomalies with concrete examples.
2: Two anomalies identified.
0: No anomaly correctly identified.
R2 (6 marks): Functional dependencies — complete minimal FD set stated.
6: Complete and minimal.
3: Partially complete.
0: Missing.
R3 (10 marks): Decomposition — lossless 3NF decomposition with justification.
10: Lossless, justified.
5: Correct end state, no justification.
0: Incorrect.
"""

ANSWERS_TXT = """Student: S-004   Question: 6
Update anomaly: if the course title changes it must be edited in every row. Insertion anomaly: a course with no student cannot be stored. Deletion anomaly: removing the last enrolment erases the course. FDs: course_code -> course_title, instructor; student_id, course_code -> grade. Decompose into Course(course_code, title, instructor) and Enrollment(student_id, course_code, grade); lossless because course_code is a key of Course.
Grader A: R1=4, R2=6, R3=10
Grader B: R1=4, R2=5, R3=9

Student: S-011   Question: 6
Only the update anomaly is named. course_code -> course_title. Split into two tables.
Grader A: R1=2, R2=3, R3=5
Grader B: R1=1, R2=3, R3=10

Student: S-017   Question: 6
Anomalies: update, insert, delete with examples. FDs listed. Decomposition given without proof.
Grader A: R1=4, R2=6, R3=5
Grader B: R1=4, R2=6, R3=10
"""


@pytest.fixture
async def ws(client, user_a):
    course = await make_course(client, user_a)
    cos = (await client.put(f"/courses/{course['id']}/outcomes", json=OUTCOMES, headers=user_a)).json()
    draft = await upload_text(client, user_a, course["id"], kind="question_paper", label="Draft 2026", text=DRAFT_PAPER, declared=60)
    past = await upload_text(client, user_a, course["id"], kind="question_paper", label="Mid 2024", text=PAST_PAPER)
    return {"course": course, "cos": cos, "draft": draft, "past": past}


async def _start(client, headers, course_id, module, inputs, params=None):
    r = await client.post(f"/courses/{course_id}/runs", json={"module": module, "inputs": inputs, "params": params or {}}, headers=headers)
    assert r.status_code == 202, r.text
    await wait_until_done()
    return (await client.get(f"/runs/{r.json()['id']}", headers=headers)).json()


# --- artefact kinds -------------------------------------------------------------------
async def test_marks_sheet_upload_and_view(client, user_a, ws):
    art = await upload_text(client, user_a, ws["course"]["id"], kind="marks_sheet", label="Marks", text=MARKS_CSV)
    assert art["status"] == "done", art
    assert art["counts"]["students"] == 5
    m = (await client.get(f"/artefacts/{art['id']}/marks", headers=user_a)).json()
    assert m["students"] == 5 and len(m["questions"]) == 9
    assert m["questions"][0] == {"number": "1(a)", "max": 6.0, "co_code": "CO1"}
    assert m["rows"][0]["student_anon_id"] == "S-001" and m["rows"][0]["scores"]["3(b)"] == 4.0
    assert "Alice" not in str(m)  # SEC-007: names never stored
    # wrong kind → 422
    assert (await client.get(f"/artefacts/{ws['draft']['id']}/marks", headers=user_a)).status_code == 422


async def test_rubric_and_answers_upload_edit(client, user_a, user_b, ws):
    cid = ws["course"]["id"]
    rub = await upload_text(client, user_a, cid, kind="rubric", label="Rubric", text=RUBRIC_TXT)
    assert rub["status"] == "done" and rub["counts"]["criteria"] == 3
    crit = (await client.get(f"/artefacts/{rub['id']}/rubric", headers=user_a)).json()
    assert [c["code"] for c in crit] == ["R1", "R2", "R3"] and crit[2]["max_score"] == 10.0 and len(crit[0]["levels"]) == 3
    # edit: rename R3 text, drop R2
    edited = [crit[0], {**crit[2], "text": "Decomposition (edited)"}]
    r = await client.put(f"/artefacts/{rub['id']}/rubric", json=edited, headers=user_a)
    assert r.status_code == 200 and [c["code"] for c in r.json()] == ["R1", "R3"]
    assert (await client.put(f"/artefacts/{rub['id']}/rubric", json=[crit[0], crit[0]], headers=user_a)).status_code == 422
    assert (await client.get(f"/artefacts/{rub['id']}/rubric", headers=user_b)).status_code == 404

    ans = await upload_text(client, user_a, cid, kind="answer_set", label="Answers", text=ANSWERS_TXT)
    assert ans["status"] == "done" and ans["counts"]["answers"] == 3
    rows = (await client.get(f"/artefacts/{ans['id']}/answers", headers=user_a)).json()
    assert rows[0]["student_anon_id"] == "S-004" and rows[0]["question_ref"] == "6"
    assert len(rows[0]["grader_scores"]) == 6 and {g["grader_label"] for g in rows[0]["grader_scores"]} == {"A", "B"}
    r = await client.put(f"/artefacts/{ans['id']}/answers", json=rows[:2], headers=user_a)
    assert r.status_code == 200 and len(r.json()) == 2


# --- attainment --------------------------------------------------------------------------
async def test_attainment_end_to_end(client, user_a, ws, mock_provider):
    cid = ws["course"]["id"]
    marks = await upload_text(client, user_a, cid, kind="marks_sheet", label="Marks", text=MARKS_CSV)
    pos = (await client.get("/program-outcomes", headers=user_a)).json()
    await client.put(f"/courses/{cid}/co-po-map", json=[{"co_id": ws["cos"][3]["id"], "po_id": pos[0]["id"], "strength": 3}], headers=user_a)
    run = await _start(client, user_a, cid, "attainment", {"marks_artefact_id": marks["id"], "paper_artefact_id": ws["draft"]["id"], "threshold": 0.6}, {"target_pct": 60})
    assert run["status"] == "completed", run
    s = run["summary"]
    assert s["students"] == 5 and s["cos_total"] == 6
    co4 = next(c for c in s["cos"] if c["co_code"] == "CO4")
    assert co4["students"] == 5 and co4["attained_pct"] == 0.0 and not co4["met"]  # 3(b) scores 4,3,2,1,3 of 10 → nobody ≥ 60%
    co1 = next(c for c in s["cos"] if c["co_code"] == "CO1")
    assert co1["attained_pct"] == 80.0  # Dan fails: 3+3+3+3=12/23
    assert s["cos"][5]["students"] == 0  # CO6 has no items
    assert s["pos"][0]["po_code"] == pos[0]["code"] and s["pos"][0]["attained_pct"] == 0.0
    att = (await client.get(f"/runs/{run['id']}/attainment", headers=user_a)).json()
    assert att["threshold"] == 0.6 and len(att["cos"]) == 6 and len(att["pos"]) == 1
    findings = (await client.get(f"/runs/{run['id']}/findings", headers=user_a)).json()
    types = [f["type"] for f in findings]
    assert "co_underperformance" in types and "po_underperformance" in types and "action" in types
    f = next(f for f in findings if f["type"] == "co_underperformance" and f["target_label"] == "CO4")
    assert "AI explanation" in f["rationale"] and f["provenance"]["model"] == "mock"
    assert "explain_attainment" in {c["purpose"] for c in mock_provider.calls}
    md = (await client.get(f"/runs/{run['id']}/export?include=all", headers=user_a)).text
    assert "CO–PO Attainment" in md and "| CO4 |" in md
    # validation: wrong kind, missing outcomes
    r = await client.post(f"/courses/{cid}/runs", json={"module": "attainment", "inputs": {"marks_artefact_id": ws["draft"]["id"], "paper_artefact_id": ws["draft"]["id"]}}, headers=user_a)
    assert r.status_code == 422
    assert (await client.get(f"/runs/{ws['draft']['id']}/attainment", headers=user_a)).status_code == 404


# --- syllabus check ------------------------------------------------------------------------
async def test_syllabus_check_end_to_end(client, user_a, user_b, ws, mock_provider):
    cid = ws["course"]["id"]
    syl = await upload_text(client, user_a, cid, kind="syllabus", label="Draft syllabus", text="Week 1: Relational model and relational algebra\nWeek 2: SQL joins and aggregation\nWeek 3: Transactions and concurrency control\nWeek 4: Indexing and query optimisation")
    other = await make_course(client, user_a, code="CSE 3101")
    await client.put(f"/courses/{other['id']}/topics", json=[{"code": "T-01", "title": "Process scheduling"}, {"code": "T-02", "title": "Concurrency control and deadlock"}, {"code": "T-03", "title": "Indexing and query optimisation"}], headers=user_a)
    foreign = await make_course(client, user_b)
    r = await client.post(f"/courses/{cid}/runs", json={"module": "syllabus_check", "inputs": {"syllabus_artefact_id": syl["id"], "compare_course_ids": [foreign["id"]]}}, headers=user_a)
    assert r.status_code == 404  # cannot compare against another user's course
    run = await _start(client, user_a, cid, "syllabus_check", {"syllabus_artefact_id": syl["id"], "compare_course_ids": [other["id"]]}, {"candidate_threshold": 0.3})
    assert run["status"] == "completed", run
    s = run["summary"]
    assert s["compare_courses"] == ["CSE 3101"] and s["topics"] == 4 and s["compared_topics"] == 3
    assert any(c["relation"] == "overlap" and "ndexing" in c["topic_a"] for c in s["matrix"]), s["matrix"]
    findings = (await client.get(f"/runs/{run['id']}/findings", headers=user_a)).json()
    assert {f["type"] for f in findings} & {"overlap", "prerequisite_gap"}
    assert all(f["evidence_snippet"] for f in findings)
    assert "relate_topics" in {c["purpose"] for c in mock_provider.calls}


# --- calibration ----------------------------------------------------------------------------
async def test_calibration_end_to_end(client, user_a, ws, mock_provider):
    cid = ws["course"]["id"]
    rub = await upload_text(client, user_a, cid, kind="rubric", label="Rubric", text=RUBRIC_TXT)
    ans = await upload_text(client, user_a, cid, kind="answer_set", label="Answers", text=ANSWERS_TXT)
    run = await _start(client, user_a, cid, "calibration", {"rubric_artefact_id": rub["id"], "answer_set_artefact_id": ans["id"]})
    assert run["status"] == "completed", run
    s = run["summary"]
    assert s["graders"] == ["A", "B"] and s["answers"] == 3 and s["criteria"] == 3
    assert s["divergent_answers"] == 2  # S-011 R3 (5 vs 10), S-017 R3 (5 vs 10)
    assert "R3" in s["criteria_flagged"] and s["criterion_mean_dev"]["R3"] >= 3
    assert len(s["prescores"]) == 9
    findings = (await client.get(f"/runs/{run['id']}/findings", headers=user_a)).json()
    types = {f["type"] for f in findings}
    assert {"divergence", "rubric_clarification"} <= types
    div = next(f for f in findings if f["type"] == "divergence")
    assert "AI explanation" in div["rationale"] and div["target_kind"] == "answer"
    rc = next(f for f in findings if f["type"] == "rubric_clarification")
    assert rc["payload"]["proposed_levels"] and rc["payload"]["current_text"]
    pre = (await client.get(f"/runs/{run['id']}/prescores", headers=user_a)).json()
    assert len(pre) == 9 and pre[0]["grader_scores"] and pre[0]["rationale"]
    assert {"explain_divergence", "prescore_answers", "propose_rubric_v2"} <= {c["purpose"] for c in mock_provider.calls}


async def test_calibration_rejects_scores_over_rubric(client, user_a, ws):
    cid = ws["course"]["id"]
    rub = await upload_text(client, user_a, cid, kind="rubric", label="Rubric", text=RUBRIC_TXT)
    bad = ANSWERS_TXT.replace("Grader A: R1=4, R2=6, R3=10", "Grader A: R1=9, R2=6, R3=10")
    ans = await upload_text(client, user_a, cid, kind="answer_set", label="Answers", text=bad)
    r = await client.post(f"/courses/{cid}/runs", json={"module": "calibration", "inputs": {"rubric_artefact_id": rub["id"], "answer_set_artefact_id": ans["id"]}}, headers=user_a)
    assert r.status_code == 409 and r.json()["error"]["code"] == "SCORES_EXCEED_RUBRIC"
    assert r.json()["error"]["details"]["violations"][0]["criterion_code"] == "R1"
    # single grader → not ready
    one = "\n".join(line for line in ANSWERS_TXT.splitlines() if not line.startswith("Grader B"))
    ans1 = await upload_text(client, user_a, cid, kind="answer_set", label="One grader", text=one)
    r = await client.post(f"/courses/{cid}/runs", json={"module": "calibration", "inputs": {"rubric_artefact_id": rub["id"], "answer_set_artefact_id": ans1["id"]}}, headers=user_a)
    assert r.status_code == 409 and r.json()["error"]["code"] == "ARTEFACT_NOT_READY"


# --- exam-audit extras: suggest + compare -------------------------------------------------------
async def test_suggest_and_compare(client, user_a, user_b, ws, mock_provider):
    cid = ws["course"]["id"]
    inputs = {"draft_artefact_id": ws["draft"]["id"], "past_artefact_ids": [ws["past"]["id"]]}
    run1 = await _start(client, user_a, cid, "exam_audit", inputs)
    r = await client.post(f"/runs/{run1['id']}/suggest-questions", json={}, headers=user_a)
    assert r.status_code == 200, r.text
    sugg = r.json()
    assert sugg and all(f["type"] == "suggestion" and f["payload"]["question"] and f["rationale"] for f in sugg)
    assert {f["target_label"] for f in sugg} >= {"CO6"}
    n = len(sugg)
    assert len((await client.post(f"/runs/{run1['id']}/suggest-questions", json={}, headers=user_a)).json()) == n  # idempotent
    assert (await client.post(f"/runs/{run1['id']}/suggest-questions", json={}, headers=user_b)).status_code == 404
    # second run after fixing marks total → mismatch resolved
    qs = (await client.get(f"/artefacts/{ws['draft']['id']}/questions", headers=user_a)).json()
    qs[-1]["marks"] = 7
    await client.put(f"/artefacts/{ws['draft']['id']}/questions", json=[{"id": q["id"], "number": q["number"], "text": q["text"], "marks": q["marks"]} for q in qs], headers=user_a)
    run2 = await _start(client, user_a, cid, "exam_audit", inputs)
    cmp_ = (await client.get(f"/runs/compare?a={run1['id']}&b={run2['id']}", headers=user_a)).json()
    assert "marks_total_mismatch" in {f["type"] for f in cmp_["resolved"]}
    assert cmp_["persisting"] and all("a" in p and "b" in p for p in cmp_["persisting"])
    assert (await client.get(f"/runs/compare?a={run1['id']}&b={uuid.uuid4()}", headers=user_a)).status_code == 404


# --- dashboard + admin -------------------------------------------------------------------------
async def test_dashboard_and_admin(client, user_a, ws):
    cid = ws["course"]["id"]
    run = await _start(client, user_a, cid, "exam_audit", {"draft_artefact_id": ws["draft"]["id"], "past_artefact_ids": []})
    d = (await client.get("/dashboard/summary", headers=user_a)).json()
    me = (await client.get("/me", headers=user_a)).json()
    mine = next(c for c in d["courses"] if c["course_id"] == cid)
    assert mine["last_exam_audit"]["run_id"] == run["id"] and mine["last_exam_audit"]["open_findings"] > 0
    assert d["totals"]["runs"] >= 1
    # courses list carries counts
    lst = (await client.get("/courses", headers=user_a)).json()
    assert next(c for c in lst["items"] if c["id"] == cid)["counts"]["runs"] == 1

    # faculty cannot reach admin
    assert (await client.get("/admin/users", headers=user_a)).status_code == 403
    # promote a fresh user to admin directly in the DB
    admin_hdr = as_user(f"admin-{uuid.uuid4().hex[:6]}@test.edu")
    admin_me = (await client.get("/me", headers=admin_hdr)).json()
    from sqlalchemy import update

    from app.db.enums import AppRole
    from app.db.models import Profile
    from app.db.session import session_scope

    async with session_scope() as db:
        await db.execute(update(Profile).where(Profile.id == uuid.UUID(admin_me["id"])).values(role=AppRole.admin))
    users = (await client.get("/admin/users?page_size=100", headers=admin_hdr)).json()
    row = next(u for u in users["items"] if u["id"] == me["id"])
    assert row["courses"] >= 1 and row["runs"] >= 1
    runs = (await client.get("/admin/runs?module=exam_audit", headers=admin_hdr)).json()
    assert any(r["id"] == run["id"] and r["owner_email"] == me["email"] for r in runs["items"])
    usage = (await client.get("/admin/usage?group=user", headers=admin_hdr)).json()
    assert any(u["key"] == me["email"] and u["calls"] > 0 for u in usage)
    audits = (await client.get("/admin/department/exam-audits", headers=admin_hdr)).json()
    assert any(a["run_id"] == run["id"] for a in audits)
    assert (await client.get("/admin/department/attainment", headers=admin_hdr)).status_code == 200
    # admin is read-only on findings (SEC-009) but can read them
    f = (await client.get(f"/runs/{run['id']}/findings", headers=admin_hdr)).json()
    assert f and (await client.patch(f"/findings/{f[0]['id']}", json={"status": "accepted"}, headers=admin_hdr)).status_code == 403
    # disable + cannot self-disable
    r = await client.patch(f"/admin/users/{me['id']}", json={"is_active": False}, headers=admin_hdr)
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert (await client.get("/courses", headers=user_a)).status_code == 403
    await client.patch(f"/admin/users/{me['id']}", json={"is_active": True}, headers=admin_hdr)
    assert (await client.patch(f"/admin/users/{admin_me['id']}", json={"is_active": False}, headers=admin_hdr)).status_code == 422
    # demo reset seeds a demo course for the admin
    r = await client.post("/admin/demo/reset", headers=admin_hdr)
    assert r.status_code == 200 and r.json()["course_id"]
    r2 = await client.post("/admin/demo/reset", headers=admin_hdr)
    assert r2.status_code == 200 and r2.json()["course_id"] != r.json()["course_id"]


async def test_demo_seed_has_tier1_artefacts(client, user_a):
    r = await client.post("/demo/seed", headers=user_a)
    assert r.status_code == 200, r.text
    cid = r.json()["course_id"]
    arts = (await client.get(f"/courses/{cid}/artefacts", headers=user_a)).json()
    kinds = {a["kind"] for a in arts}
    assert kinds == {"question_paper", "syllabus", "marks_sheet", "rubric", "answer_set"}
    marks = next(a for a in arts if a["kind"] == "marks_sheet")
    assert marks["counts"]["students"] == 30
    courses = (await client.get("/courses?page_size=100", headers=user_a)).json()["items"]
    assert {c["code"] for c in courses} >= {"CSE 3103", "CSE 4101"}
    # every module runs on the demo data
    paper = next(a for a in arts if a["kind"] == "question_paper" and not a["label"].startswith("[DRAFT]"))
    run = await _start(client, user_a, cid, "attainment", {"marks_artefact_id": marks["id"], "paper_artefact_id": paper["id"]})
    assert run["status"] == "completed", run
    assert any(c["co_code"] == "CO6" and c["students"] == 30 for c in run["summary"]["cos"])
    rub = next(a for a in arts if a["kind"] == "rubric")
    ans = next(a for a in arts if a["kind"] == "answer_set")
    run = await _start(client, user_a, cid, "calibration", {"rubric_artefact_id": rub["id"], "answer_set_artefact_id": ans["id"]})
    assert run["status"] == "completed", run
    assert run["summary"]["divergent_answers"] >= 1
    syl = next(a for a in arts if a["kind"] == "syllabus")
    other = next(c for c in courses if c["code"] == "CSE 4101")
    run = await _start(client, user_a, cid, "syllabus_check", {"syllabus_artefact_id": syl["id"], "compare_course_ids": [other["id"]]})
    assert run["status"] == "completed", run
    assert run["summary"]["matrix"]
