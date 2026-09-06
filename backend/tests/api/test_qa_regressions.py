"""Regression tests for defects found by the QA loop."""

from __future__ import annotations

import asyncio

from tests.conftest import DRAFT_PAPER, OUTCOMES, make_course, upload_text, wait_until_done


async def test_soft_deleted_course_hides_runs_and_findings(client, user_a):
    course = await make_course(client, user_a)
    await client.put(f"/courses/{course['id']}/outcomes", json=OUTCOMES, headers=user_a)
    draft = await upload_text(client, user_a, course["id"], kind="question_paper", label="D", text=DRAFT_PAPER)
    r = await client.post(f"/courses/{course['id']}/runs", json={"module": "exam_audit", "inputs": {"draft_artefact_id": draft["id"]}}, headers=user_a)
    rid = r.json()["id"]
    await wait_until_done()
    fid = (await client.get(f"/runs/{rid}/findings", headers=user_a)).json()[0]["id"]
    assert (await client.delete(f"/courses/{course['id']}", headers=user_a)).status_code == 204
    assert (await client.get(f"/runs/{rid}", headers=user_a)).status_code == 404
    assert (await client.get(f"/runs/{rid}/findings", headers=user_a)).status_code == 404
    assert (await client.get(f"/runs/{rid}/events", headers=user_a)).status_code == 404
    assert (await client.patch(f"/findings/{fid}", json={"status": "accepted"}, headers=user_a)).status_code == 404


async def test_idempotency_key_scoped_to_payload_and_race_safe(client, user_a):
    course = await make_course(client, user_a)
    await client.put(f"/courses/{course['id']}/outcomes", json=OUTCOMES, headers=user_a)
    draft = await upload_text(client, user_a, course["id"], kind="question_paper", label="D", text=DRAFT_PAPER)
    other = await upload_text(client, user_a, course["id"], kind="question_paper", label="O", text=DRAFT_PAPER)
    body = {"module": "exam_audit", "inputs": {"draft_artefact_id": draft["id"]}}
    h = {**user_a, "Idempotency-Key": "race-key"}
    results = await asyncio.gather(*(client.post(f"/courses/{course['id']}/runs", json=body, headers=h) for _ in range(5)))
    assert [r.status_code for r in results] == [202] * 5
    assert len({r.json()["id"] for r in results}) == 1
    # same key, different payload -> 409
    r = await client.post(f"/courses/{course['id']}/runs", json={"module": "exam_audit", "inputs": {"draft_artefact_id": other["id"]}}, headers=h)
    assert r.status_code == 409 and r.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    # same key, different course -> 409
    course2 = await make_course(client, user_a)
    r = await client.post(f"/courses/{course2['id']}/runs", json=body, headers=h)
    assert r.status_code == 409
    await wait_until_done()


async def test_unimplemented_module_rejected_before_input_validation(client, user_a):
    course = await make_course(client, user_a)
    r = await client.post(f"/courses/{course['id']}/runs", json={"module": "calibration", "inputs": {}}, headers=user_a)
    assert r.status_code == 422 and r.json()["error"]["code"] == "MODULE_NOT_IMPLEMENTED"
    assert "exam_audit" in r.json()["error"]["details"]["available"]


async def test_outcome_and_topic_codes_can_be_swapped(client, user_a):
    course = await make_course(client, user_a)
    cos = (await client.put(f"/courses/{course['id']}/outcomes", json=OUTCOMES[:2], headers=user_a)).json()
    swapped = [{"id": cos[0]["id"], "code": "CO2", "text": cos[0]["text"]}, {"id": cos[1]["id"], "code": "CO1", "text": cos[1]["text"]}]
    r = await client.put(f"/courses/{course['id']}/outcomes", json=swapped, headers=user_a)
    assert r.status_code == 200 and [c["code"] for c in r.json()] == ["CO2", "CO1"]
    ts = (await client.put(f"/courses/{course['id']}/topics", json=[{"code": "T-01", "title": "A topic"}, {"code": "T-02", "title": "B topic"}], headers=user_a)).json()
    r = await client.put(f"/courses/{course['id']}/topics", json=[{"id": ts[0]["id"], "code": "T-02", "title": "A topic"}, {"id": ts[1]["id"], "code": "T-01", "title": "B topic"}], headers=user_a)
    assert r.status_code == 200 and [t["code"] for t in r.json()] == ["T-02", "T-01"]


async def test_blank_values_and_like_metacharacters(client, user_a):
    course = await make_course(client, user_a, code="QA 100")
    assert (await client.patch(f"/courses/{course['id']}", json={"code": "   "}, headers=user_a)).status_code == 422
    draft = await upload_text(client, user_a, course["id"], kind="question_paper", label="D", text=DRAFT_PAPER)
    r = await client.put(f"/artefacts/{draft['id']}/questions", json=[{"number": "   ", "text": "Some question text", "marks": 1}], headers=user_a)
    assert r.status_code == 422
    assert (await client.get("/courses?q=%25", headers=user_a)).json()["total"] == 0
    assert (await client.get("/courses?q=______", headers=user_a)).json()["total"] == 0
    assert (await client.get("/courses?q=QA%20100", headers=user_a)).json()["total"] == 1
