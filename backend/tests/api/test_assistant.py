from __future__ import annotations

import io
import json

from tests.conftest import DRAFT_PAPER, OUTCOMES, PAST_PAPER, make_course, upload_text, wait_until_done


async def _chat(client, headers, message, *, course_id=None, history=None, file=None):
    data = {"message": message}
    if course_id:
        data["course_id"] = course_id
    if history is not None:
        data["history"] = json.dumps(history)
    files = {"file": file} if file else None
    r = await client.post("/assistant/chat", data=data, files=files, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def test_help_and_list_courses(client, user_a):
    out = await _chat(client, user_a, "What can you do?")
    assert out["actions"] == [] and "Exam Paper Audit" in out["reply"]
    course = await make_course(client, user_a, code="CSE 4101")
    out = await _chat(client, user_a, "list my courses")
    assert out["actions"][0]["tool"] == "list_courses" and out["actions"][0]["status"] == "ok"
    assert "CSE 4101" in out["reply"] and out["navigate"] == "/courses"
    assert course["id"] in json.dumps(out["actions"][0]["data"])


async def test_create_course_via_chat(client, user_a):
    out = await _chat(client, user_a, "create course CSE 4201 Compiler Design")
    act = out["actions"][0]
    assert act["tool"] == "create_course" and act["status"] == "ok"
    assert out["navigate"].startswith("/courses/")
    r = await client.get("/courses", headers=user_a)
    assert any(c["code"] == "CSE 4201" and c["title"] == "Compiler Design" for c in r.json()["items"])


async def test_attachment_upload_analyze_and_decide(client, user_a):
    course = await make_course(client, user_a, code="CSE 3103")
    await client.put(f"/courses/{course['id']}/outcomes", json=OUTCOMES, headers=user_a)
    await upload_text(client, user_a, course["id"], kind="question_paper", label="Mid 2024", text=PAST_PAPER)
    await wait_until_done()

    # no course named and several exist → clarifying question, file not consumed
    await make_course(client, user_a, code="CSE 1101")
    out = await _chat(client, user_a, "analyze this paper", file=("draft.txt", io.BytesIO(DRAFT_PAPER.encode()), "text/plain"))
    assert out["actions"] == [] and "Which course" in out["reply"]

    out = await _chat(client, user_a, "analyze this exam paper for CSE 3103", file=("draft.txt", io.BytesIO(DRAFT_PAPER.encode()), "text/plain"))
    act = out["actions"][0]
    assert act["tool"] == "analyze_attachment" and act["status"] == "ok", act
    assert act["data"]["artefact"]["kind"] == "question_paper" and act["data"]["artefact"]["status"] == "done"
    assert act["data"]["run"]["status"] == "completed"
    types = {f["type"] for f in act["data"]["findings"]}
    assert {"coverage_gap", "duplicate"} <= types  # no declared total → no marks_total_mismatch
    assert "Findings" in out["reply"] and "COVERAGE GAP" in out["reply"].upper()
    assert out["navigate"].startswith(f"/courses/{course['id']}/exam-audit/")
    run_id = act["data"]["run"]["id"]

    # artefact really stored and visible via the normal API
    arts = (await client.get(f"/courses/{course['id']}/artefacts", headers=user_a)).json()
    assert any(a["label"] == "draft" and a["status"] == "done" for a in arts)

    # accept all coverage-gap findings from the course page context
    out = await _chat(client, user_a, "accept all coverage gap findings", course_id=course["id"])
    act = out["actions"][0]
    assert act["tool"] == "decide_findings" and act["status"] == "ok"
    findings = (await client.get(f"/runs/{run_id}/findings", headers=user_a)).json()
    gaps = [f for f in findings if f["type"] == "coverage_gap"]
    assert gaps and all(f["status"] == "accepted" for f in gaps)
    assert all(f["status"] == "open" for f in findings if f["type"] != "coverage_gap")

    out = await _chat(client, user_a, f"export report {run_id}")
    assert out["actions"][0]["tool"] == "export_run" and "markdown" in out["reply"]


async def test_upload_only_stores_without_run(client, user_a):
    course = await make_course(client, user_a, code="CSE 2201")
    out = await _chat(client, user_a, "upload this syllabus", course_id=course["id"], file=("syllabus.txt", io.BytesIO(("Course outline\n" + "\n".join(f"Week {i}: Topic {i} of the module" for i in range(1, 8))).encode()), "text/plain"))
    act = out["actions"][0]
    assert act["tool"] == "upload_attachment" and act["status"] == "ok", act
    assert act["data"]["artefact"]["kind"] == "syllabus"
    runs = (await client.get(f"/courses/{course['id']}/runs", headers=user_a)).json()
    assert runs["total"] == 0


async def test_isolation_other_users_course(client, user_a, user_b):
    course = await make_course(client, user_a, code="CSE 3301")
    out = await _chat(client, user_b, f"show me the overview of course {course['id']}")
    act = out["actions"][0]
    assert act["status"] == "error" and "COURSE_NOT_FOUND" in act["summary"]


async def test_bad_history_rejected(client, user_a):
    r = await client.post("/assistant/chat", data={"message": "hi", "history": "not-json"}, headers=user_a)
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
