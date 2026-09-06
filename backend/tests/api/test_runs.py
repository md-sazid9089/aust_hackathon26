from __future__ import annotations

import json
import uuid

import pytest

from app.ai.providers.base import ProviderError
from tests.conftest import DRAFT_PAPER, OUTCOMES, PAST_PAPER, make_course, upload_text, wait_until_done


@pytest.fixture
async def workspace(client, user_a):
    course = await make_course(client, user_a)
    cos = (await client.put(f"/courses/{course['id']}/outcomes", json=OUTCOMES, headers=user_a)).json()
    draft = await upload_text(client, user_a, course["id"], kind="question_paper", label="Draft 2026", text=DRAFT_PAPER, declared=60)
    past = await upload_text(client, user_a, course["id"], kind="question_paper", label="Mid 2024", text=PAST_PAPER)
    return {"course": course, "cos": cos, "draft": draft, "past": past}


async def _run(client, headers, ws, **extra):
    body = {"module": "exam_audit", "inputs": {"draft_artefact_id": ws["draft"]["id"], "past_artefact_ids": [ws["past"]["id"]]}, **extra}
    r = await client.post(f"/courses/{ws['course']['id']}/runs", json=body, headers=headers)
    assert r.status_code == 202, r.text
    assert r.json()["status"] in ("queued", "analyzing")
    await wait_until_done()
    return (await client.get(f"/runs/{r.json()['id']}", headers=headers)).json()


async def test_exam_audit_end_to_end(client, user_a, workspace, mock_provider):
    run = await _run(client, user_a, workspace)
    assert run["status"] == "completed", run
    assert run["progress_pct"] == 100 and run["current_stage"] == "done" and run["model"] == "mock"
    s = run["summary"]
    assert s["questions"] == 9 and s["past_questions"] == 4
    assert s["marks_total"] == {"computed": 58.0, "declared": 60.0, "mismatch": True}
    assert len(s["mapping"]) == 9 and all(m["rationale"] for m in s["mapping"])
    findings = (await client.get(f"/runs/{run['id']}/findings", headers=user_a)).json()
    types = {f["type"] for f in findings}
    assert "marks_total_mismatch" in types
    assert "coverage_gap" in types  # CO6 (indexing) is never assessed
    assert "duplicate" in types  # 2(b) vs past 3(a), 1(a)/3(a) vs past 1(a)
    dup = next(f for f in findings if f["type"] == "duplicate")
    assert dup["evidence_snippet"] and dup["rationale"] and dup["provenance"]["model"] == "mock"
    assert findings[0]["severity"] == "high"  # sorted by severity
    # events backlog ends with done
    events = [json.loads(line[5:]) for line in (await client.get(f"/runs/{run['id']}/events", headers=user_a)).text.splitlines() if line.startswith("data:")]
    assert events[0]["stage"] == "queued" and events[-1] == {"status": "completed"}
    stages = [e.get("stage") for e in events]
    assert "map_and_bloom" in stages and "find_duplicates" in stages
    # questions now carry AI mapping + bloom
    qs = (await client.get(f"/artefacts/{workspace['draft']['id']}/questions", headers=user_a)).json()
    assert all(q["bloom_level"] for q in qs) and any(q["co_ids"] for q in qs)
    # run history
    hist = (await client.get(f"/courses/{workspace['course']['id']}/runs?module=exam_audit", headers=user_a)).json()
    assert hist["total"] == 1
    # llm calls happened for mapping and duplicates
    assert {c["purpose"] for c in mock_provider.calls} >= {"map_and_bloom", "confirm_duplicates"}


async def test_finding_decisions_and_export(client, user_a, user_b, workspace):
    run = await _run(client, user_a, workspace)
    findings = (await client.get(f"/runs/{run['id']}/findings", headers=user_a)).json()
    f0, f1 = findings[0], findings[1]
    r = await client.patch(f"/findings/{f0['id']}", json={"status": "accepted"}, headers=user_a)
    assert r.status_code == 200 and r.json()["status"] == "accepted" and r.json()["decided_at"]
    r = await client.patch(f"/findings/{f1['id']}", json={"status": "dismissed"}, headers=user_a)
    assert r.json()["status"] == "dismissed"
    r = await client.patch(f"/findings/{f1['id']}", json={"status": "open"}, headers=user_a)
    assert r.json()["status"] == "open" and r.json()["decided_at"] is None
    assert (await client.patch(f"/findings/{f0['id']}", json={"status": "bogus"}, headers=user_a)).status_code == 422
    # other user: 404 (no leak)
    assert (await client.patch(f"/findings/{f0['id']}", json={"status": "accepted"}, headers=user_b)).status_code == 404
    assert (await client.get(f"/runs/{run['id']}", headers=user_b)).status_code == 404
    assert (await client.get(f"/runs/{run['id']}/findings", headers=user_b)).status_code == 404
    accepted = (await client.get(f"/runs/{run['id']}/findings?status=accepted", headers=user_a)).json()
    assert [f["id"] for f in accepted] == [f0["id"]]
    r = await client.get(f"/runs/{run['id']}/export", headers=user_a)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/markdown")
    assert "attachment" in r.headers["content-disposition"]
    assert f0["title"] in r.text and f1["title"] not in r.text
    r = await client.get(f"/runs/{run['id']}/export?include=all", headers=user_a)
    assert f1["title"] in r.text
    r = await client.get(f"/runs/{run['id']}/export?format=pdf", headers=user_a)
    assert r.status_code == 503 and r.json()["error"]["code"] == "PDF_UNAVAILABLE"


async def test_run_validation_errors(client, user_a, workspace):
    cid = workspace["course"]["id"]
    ok_inputs = {"draft_artefact_id": workspace["draft"]["id"], "past_artefact_ids": []}
    # exam_audit inputs are not valid attainment inputs
    r = await client.post(f"/courses/{cid}/runs", json={"module": "attainment", "inputs": ok_inputs}, headers=user_a)
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    r = await client.post(f"/courses/{cid}/runs", json={"module": "exam_audit", "inputs": {}}, headers=user_a)
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    r = await client.post(f"/courses/{cid}/runs", json={"module": "exam_audit", "inputs": {"draft_artefact_id": str(uuid.uuid4())}}, headers=user_a)
    assert r.status_code == 404 and r.json()["error"]["code"] == "ARTEFACT_NOT_FOUND"
    r = await client.post(f"/courses/{cid}/runs", json={"module": "exam_audit", "inputs": {**ok_inputs, "past_artefact_ids": [workspace["draft"]["id"]]}}, headers=user_a)
    assert r.status_code == 422
    r = await client.post(f"/courses/{cid}/runs", json={"module": "exam_audit", "inputs": ok_inputs, "params": {"dup_threshold": 2}}, headers=user_a)
    assert r.status_code == 422
    # syllabus artefact is not a question paper
    syl = await upload_text(client, user_a, cid, kind="syllabus", label="S", text="Week 1: Intro to databases\nWeek 2: SQL")
    r = await client.post(f"/courses/{cid}/runs", json={"module": "exam_audit", "inputs": {"draft_artefact_id": syl["id"]}}, headers=user_a)
    assert r.status_code == 422
    # course without outcomes
    empty = await make_course(client, user_a)
    d = await upload_text(client, user_a, empty["id"], kind="question_paper", label="D", text=DRAFT_PAPER)
    r = await client.post(f"/courses/{empty['id']}/runs", json={"module": "exam_audit", "inputs": {"draft_artefact_id": d["id"]}}, headers=user_a)
    assert r.status_code == 409 and r.json()["error"]["code"] == "COURSE_HAS_NO_OUTCOMES"
    # artefact from another course
    r = await client.post(f"/courses/{cid}/runs", json={"module": "exam_audit", "inputs": {"draft_artefact_id": d["id"]}}, headers=user_a)
    assert r.status_code == 404
    assert (await client.get(f"/runs/{uuid.uuid4()}", headers=user_a)).status_code == 404


async def test_idempotency_key_returns_same_run(client, user_a, workspace):
    body = {"module": "exam_audit", "inputs": {"draft_artefact_id": workspace["draft"]["id"]}}
    h = {**user_a, "Idempotency-Key": "k-1"}
    r1 = await client.post(f"/courses/{workspace['course']['id']}/runs", json=body, headers=h)
    r2 = await client.post(f"/courses/{workspace['course']['id']}/runs", json=body, headers=h)
    assert r1.status_code == 202 and r2.status_code == 202 and r1.json()["id"] == r2.json()["id"]
    await wait_until_done()
    assert (await client.get(f"/courses/{workspace['course']['id']}/runs", headers=user_a)).json()["total"] == 1


async def test_llm_failure_yields_partial_run_with_deterministic_findings(client, user_a, workspace, mock_provider):
    for _ in range(4):
        mock_provider.queue("map_and_bloom", ProviderError("timeout"))
    run = await _run(client, user_a, workspace)
    assert run["status"] == "partial"
    assert "AI mapping unavailable" in run["error"]
    findings = (await client.get(f"/runs/{run['id']}/findings", headers=user_a)).json()
    types = {f["type"] for f in findings}
    assert "marks_total_mismatch" in types and "coverage_gap" in types  # deterministic stages still ran
    assert all(f["type"] == "coverage_gap" for f in findings if f["target_kind"] == "course_outcome")
    warnings = [json.loads(l[5:]) for l in (await client.get(f"/runs/{run['id']}/events", headers=user_a)).text.splitlines() if l.startswith("data:") and '"warning"' in l]
    assert warnings


async def test_invalid_llm_output_is_retried_then_partial(client, user_a, workspace, mock_provider):
    mock_provider.queue("map_and_bloom", "{ not json")
    mock_provider.queue("map_and_bloom", json.dumps({"items": [{"number": "1(a)", "co_codes": ["CO1"]}]}))  # schema violation (missing required fields)
    run = await _run(client, user_a, workspace)
    assert run["status"] == "partial"
    assert sum(1 for c in mock_provider.calls if c["purpose"] == "map_and_bloom") == 2


async def test_unknown_codes_from_llm_are_dropped(client, user_a, workspace, mock_provider):
    items = [{"number": n, "co_codes": ["CO99"], "topic_codes": ["T-77"], "bloom_level": "apply", "confidence": 0.9, "evidence_quote": "x", "rationale": "x"} for n in ["1(a)", "1(b)", "2(a)", "2(b)", "3(a)", "3(b)", "4(a)", "4(b)", "5"]]
    mock_provider.queue("map_and_bloom", json.dumps({"items": items}))
    run = await _run(client, user_a, workspace)
    assert run["status"] == "partial" and "Dropped unknown" in run["error"]
    findings = (await client.get(f"/runs/{run['id']}/findings", headers=user_a)).json()
    assert sum(1 for f in findings if f["type"] == "coverage_gap") == 6  # nothing mapped -> all COs uncovered
    assert sum(1 for f in findings if f["type"] == "untagged_question") == 9


async def test_faculty_mapping_wins_over_ai(client, user_a, workspace, mock_provider):
    qs = (await client.get(f"/artefacts/{workspace['draft']['id']}/questions", headers=user_a)).json()
    q5 = next(q for q in qs if q["number"] == "5")
    co6 = next(c for c in workspace["cos"] if c["code"] == "CO6")
    await client.put(f"/artefacts/{workspace['draft']['id']}/questions/co-map", json=[{"question_id": q5["id"], "co_ids": [co6["id"]]}], headers=user_a)
    run = await _run(client, user_a, workspace)
    m5 = next(m for m in run["summary"]["mapping"] if m["number"] == "5")
    assert m5["co_codes"] == ["CO6"] and m5["source"] == "faculty"
    assert not any(f["type"] == "coverage_gap" and f["target_label"] == "CO6" for f in (await client.get(f"/runs/{run['id']}/findings", headers=user_a)).json())


async def test_artefact_in_use_after_completed_run(client, user_a, workspace):
    run = await _run(client, user_a, workspace)
    assert run["status"] == "completed"
    r = await client.delete(f"/artefacts/{workspace['draft']['id']}", headers=user_a)
    assert r.status_code == 409 and r.json()["error"]["code"] == "ARTEFACT_IN_USE"
    r = await client.post(f"/artefacts/{workspace['draft']['id']}/reextract", headers=user_a)
    assert r.status_code == 409


async def test_demo_seed_idempotent_and_runnable(client, user_a):
    r = await client.post("/demo/seed", headers=user_a)
    assert r.status_code == 200 and r.json()["created"] is True
    cid = r.json()["course_id"]
    r2 = await client.post("/demo/seed", headers=user_a)
    assert r2.json()["created"] is False and r2.json()["course_id"] == cid
    course = (await client.get(f"/courses/{cid}", headers=user_a)).json()
    assert course["is_demo"] and course["counts"] == {"artefacts": 7, "runs": 0, "outcomes": 6}  # 3 papers + syllabus + marks + rubric + answers
    arts = (await client.get(f"/courses/{cid}/artefacts", headers=user_a)).json()
    papers = [a for a in arts if a["kind"] == "question_paper"]
    draft = next(a for a in papers if a["label"].startswith("[DRAFT]"))
    past = [a["id"] for a in papers if a["id"] != draft["id"]]
    r = await client.post(f"/courses/{cid}/runs", json={"module": "exam_audit", "inputs": {"draft_artefact_id": draft["id"], "past_artefact_ids": past}}, headers=user_a)
    assert r.status_code == 202
    await wait_until_done()
    run = (await client.get(f"/runs/{r.json()['id']}", headers=user_a)).json()
    assert run["status"] == "completed", run["error"]
    s = run["summary"]
    assert s["marks_total"]["computed"] == 58 and s["marks_total"]["declared"] == 60
    findings = (await client.get(f"/runs/{run['id']}/findings", headers=user_a)).json()
    types = {f["type"] for f in findings}
    assert {"marks_total_mismatch", "coverage_gap", "duplicate"} <= types
    assert any(f["type"] == "coverage_gap" and f["target_label"] == "CO6" for f in findings)  # planted flaw PF-01
