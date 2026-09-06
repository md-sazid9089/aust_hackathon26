from __future__ import annotations

import uuid

from tests.conftest import OUTCOMES, make_course


async def test_health_and_docs(client):
    assert (await client.get("/health")).json() == {"status": "ok"}
    r = await client.get("/readyz")
    assert r.status_code == 200 and r.json()["db"] == "ok" and r.json()["llm"] == "mock"
    assert (await client.get("http://test/docs")).status_code == 200
    assert (await client.get("http://test/redoc")).status_code == 200
    spec = (await client.get("/openapi.json")).json()
    assert "/api/v1/courses/{course_id}/runs" in spec["paths"]


async def test_me_and_request_id(client, user_a):
    r = await client.get("/me", headers=user_a)
    assert r.status_code == 200 and r.json()["role"] == "faculty"
    assert r.headers["x-request-id"]
    r = await client.get("/me", headers={**user_a, "X-Request-Id": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"


async def test_error_envelope_on_404_and_422(client, user_a):
    r = await client.get(f"/courses/{uuid.uuid4()}", headers=user_a)
    assert r.status_code == 404
    body = r.json()["error"]
    assert body["code"] == "COURSE_NOT_FOUND" and body["request_id"]
    r = await client.post("/courses", json={"code": "X", "title": ""}, headers=user_a)
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert r.json()["error"]["details"]["errors"]


async def test_course_crud_and_isolation(client, user_a, user_b):
    course = await make_course(client, user_a, code="cse 3103")
    assert course["code"] == "CSE 3103"
    r = await client.post("/courses", json={"code": "CSE 3103", "title": "dup"}, headers=user_a)
    assert r.status_code == 409 and r.json()["error"]["code"] == "COURSE_CODE_EXISTS"
    # other user cannot see it
    assert (await client.get(f"/courses/{course['id']}", headers=user_b)).status_code == 404
    assert (await client.patch(f"/courses/{course['id']}", json={"title": "xx"}, headers=user_b)).status_code == 404
    lst = (await client.get("/courses?q=3103", headers=user_a)).json()
    assert lst["total"] == 1 and lst["items"][0]["id"] == course["id"]
    assert (await client.get("/courses", headers=user_b)).json()["total"] == 0
    r = await client.patch(f"/courses/{course['id']}", json={"title": "Renamed"}, headers=user_a)
    assert r.json()["title"] == "Renamed"
    got = (await client.get(f"/courses/{course['id']}", headers=user_a)).json()
    assert got["counts"] == {"artefacts": 0, "runs": 0, "outcomes": 0}
    assert (await client.delete(f"/courses/{course['id']}", headers=user_a)).status_code == 204
    assert (await client.get(f"/courses/{course['id']}", headers=user_a)).status_code == 404
    # code reusable after soft delete
    assert (await client.post("/courses", json={"code": "CSE 3103", "title": "again"}, headers=user_a)).status_code == 201


async def test_outcomes_replace_all_and_co_po_map(client, user_a):
    course = await make_course(client, user_a)
    cid = course["id"]
    r = await client.put(f"/courses/{cid}/outcomes", json=OUTCOMES, headers=user_a)
    assert r.status_code == 200 and [c["code"] for c in r.json()] == [o["code"] for o in OUTCOMES]
    cos = r.json()
    # update one, drop one, add one
    body = [{"id": cos[0]["id"], "code": "CO1", "text": "Updated text here", "weight": 5}] + [
        {"id": c["id"], "code": c["code"], "text": c["text"], "weight": c["weight"]} for c in cos[1:5]
    ] + [{"code": "CO7", "text": "Brand new outcome text"}]
    r = await client.put(f"/courses/{cid}/outcomes", json=body, headers=user_a)
    assert r.status_code == 200
    codes = [c["code"] for c in r.json()]
    assert "CO6" not in codes and "CO7" in codes and r.json()[0]["text"] == "Updated text here"
    # duplicate codes rejected
    r = await client.put(f"/courses/{cid}/outcomes", json=[{"code": "CO1", "text": "aaa"}, {"code": "co1", "text": "bbb"}], headers=user_a)
    assert r.status_code == 422
    # unknown id rejected
    r = await client.put(f"/courses/{cid}/outcomes", json=[{"id": str(uuid.uuid4()), "code": "CO9", "text": "zzz"}], headers=user_a)
    assert r.status_code == 422
    pos = (await client.get("/program-outcomes", headers=user_a)).json()
    assert len(pos) == 12
    cos = (await client.get(f"/courses/{cid}/outcomes", headers=user_a)).json()
    cells = [{"co_id": cos[0]["id"], "po_id": pos[0]["id"], "strength": 3}]
    r = await client.put(f"/courses/{cid}/co-po-map", json=cells, headers=user_a)
    assert r.status_code == 200 and r.json()[0]["strength"] == 3
    r = await client.put(f"/courses/{cid}/co-po-map", json=[{"co_id": str(uuid.uuid4()), "po_id": pos[0]["id"], "strength": 1}], headers=user_a)
    assert r.status_code == 422
    r = await client.put(f"/courses/{cid}/co-po-map", json=[{**cells[0], "strength": 4}], headers=user_a)
    assert r.status_code == 422


async def test_topics_replace_all(client, user_a):
    course = await make_course(client, user_a)
    r = await client.put(f"/courses/{course['id']}/topics", json=[{"code": "T-01", "title": "Intro"}, {"code": "T-02", "title": "ER model"}], headers=user_a)
    assert r.status_code == 200 and len(r.json()) == 2
    t1 = r.json()[0]
    r = await client.put(f"/courses/{course['id']}/topics", json=[{"id": t1["id"], "code": "T-01", "title": "Intro (edited)"}], headers=user_a)
    assert [t["title"] for t in r.json()] == ["Intro (edited)"]
