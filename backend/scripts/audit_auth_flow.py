"""Live audit of the sign-in → every-page flow against a running backend (not a pytest file).

Usage: .venv/bin/python scripts/audit_auth_flow.py [base_url]
"""

from __future__ import annotations

import sys
import time

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001") + "/api/v1"
FACULTY = ("teacher@aust.edu", "Teacher#2026")
ADMIN = ("admin@aust.edu", "Admin#2026")

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, info: str = "") -> None:
    results.append((name, ok, info))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {info}")


def login(c: httpx.Client, creds) -> tuple[dict, dict]:
    r = c.post("/auth/login", json={"email": creds[0], "password": creds[1]})
    check(f"login {creds[0]}", r.status_code == 200, f"{r.status_code}")
    body = r.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]


with httpx.Client(base_url=BASE, timeout=60) as c:
    check("health (public)", c.get("/health").status_code == 200)
    check("permissions catalog (public)", c.get("/auth/permissions").status_code == 200)
    check("no token → 401 /me", c.get("/me").status_code == 401)
    check("no token → 401 /courses", c.get("/courses").status_code == 401)
    check("wrong password → 401", c.post("/auth/login", json={"email": FACULTY[0], "password": "nope"}).status_code == 401)
    check("no sign-up route", c.post("/auth/signup", json={}).status_code in (404, 405))

    fac, fac_me = login(c, FACULTY)
    adm, adm_me = login(c, ADMIN)
    check("faculty dashboards", "admin" not in fac_me["dashboards"] and "exam_audit" in fac_me["dashboards"], str(fac_me["dashboards"]))
    check("admin dashboards", {"admin", "admin_department"} <= set(adm_me["dashboards"]), str(adm_me["dashboards"]))

    # /  course list
    check("page / (courses) faculty", c.get("/courses", headers=fac).status_code == 200)
    check("page / (courses) admin", c.get("/courses", headers=adm).status_code == 200)

    # demo seed → course workspace
    r = c.post("/demo/seed", headers=fac)
    check("demo seed faculty", r.status_code == 200, r.text[:80])
    cid = r.json()["course_id"]
    check("demo seed admin → 403", c.post("/demo/seed", headers=adm).status_code == 403)

    # /courses/:id  tabs
    for tab in ("", "/outcomes", "/co-po-map", "/topics", "/artefacts", "/runs"):
        check(f"page /courses/:id{tab} faculty", c.get(f"/courses/{cid}{tab}", headers=fac).status_code == 200)
    check("page /courses/:id admin (other owner) → 404", c.get(f"/courses/{cid}", headers=adm).status_code == 404)
    check("program outcomes", c.get("/program-outcomes", headers=fac).status_code == 200)

    # exam-audit/new
    arts = c.get(f"/courses/{cid}/artefacts", headers=fac).json()
    papers = [a for a in arts if a["kind"] == "question_paper" and a["status"] == "done"]
    draft = next((a for a in papers if "draft" in a["label"].lower()), papers[-1])
    past = [a["id"] for a in papers if a["id"] != draft["id"]]
    check("questions visible", c.get(f"/artefacts/{draft['id']}/questions", headers=fac).status_code == 200)
    r = c.post(f"/courses/{cid}/runs", json={"module": "exam_audit", "inputs": {"draft_artefact_id": draft["id"], "past_artefact_ids": past}}, headers=fac)
    check("exam-audit run start faculty", r.status_code == 202, r.text[:120])
    run_id = r.json()["id"]
    check("run start admin → 403", c.post(f"/courses/{cid}/runs", json={"module": "exam_audit", "inputs": {"draft_artefact_id": draft["id"], "past_artefact_ids": []}}, headers=adm).status_code == 403)

    # SSE with ?access_token= (EventSource can't set headers)
    tok = fac["Authorization"].split()[1]
    with c.stream("GET", f"/runs/{run_id}/events?access_token={tok}", timeout=60) as s:
        got_done = False
        for line in s.iter_lines():
            if line.startswith("event: done"):
                got_done = True
                break
        check("SSE events via access_token", got_done)

    # exam-audit/:runId
    for _ in range(30):
        run = c.get(f"/runs/{run_id}", headers=fac).json()
        if run["status"] in ("completed", "partial", "failed"):
            break
        time.sleep(1)
    check("run finished", run["status"] in ("completed", "partial"), run["status"])
    findings = c.get(f"/runs/{run_id}/findings", headers=fac).json()
    check("findings listed", len(findings) > 0, f"{len(findings)} findings")
    fid = findings[0]["id"]
    check("faculty accept finding", c.patch(f"/findings/{fid}", json={"status": "accepted"}, headers=fac).status_code == 200)
    check("admin decide finding → 403", c.patch(f"/findings/{fid}", json={"status": "dismissed"}, headers=adm).status_code == 403)
    check("export accepted findings", c.get(f"/runs/{run_id}/export", headers=fac).status_code == 200)
    check("logout", c.post("/auth/logout", headers=fac).status_code == 204)

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
