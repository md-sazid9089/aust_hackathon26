"""AUTH_MODE=local: email+password sign-in, HS256 JWT, role permission matrix, full faculty journey."""

from __future__ import annotations

import time
import uuid

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt import LOCAL_AUD, LOCAL_ISS
from app.auth.service import ensure_seed_users
from app.config import get_settings
from app.db.session import session_scope
from app.main import create_app
from tests.conftest import DRAFT_PAPER, OUTCOMES, PAST_PAPER, upload_text, wait_until_done

SECRET = "unit-test-jwt-secret-at-least-32-chars-long"
FACULTY = ("teacher@aust.edu", "Teacher#2026")
ADMIN = ("admin@aust.edu", "Admin#2026")


@pytest.fixture
async def local(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "local")
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("SEED_FACULTY_EMAIL", FACULTY[0])
    monkeypatch.setenv("SEED_FACULTY_PASSWORD", FACULTY[1])
    monkeypatch.setenv("SEED_ADMIN_EMAIL", ADMIN[0])
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", ADMIN[1])
    get_settings.cache_clear()
    async with session_scope() as db:  # lifespan does this in production
        await ensure_seed_users(db, get_settings())
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as c:
        yield c
    get_settings.cache_clear()


async def login(c: AsyncClient, creds: tuple[str, str]) -> tuple[dict[str, str], dict]:
    r = await c.post("/auth/login", json={"email": creds[0], "password": creds[1]})
    assert r.status_code == 200, r.text
    body = r.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body


async def test_login_rejects_bad_credentials_and_no_signup(local):
    r = await local.post("/auth/login", json={"email": FACULTY[0], "password": "wrong"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHENTICATED"
    r = await local.post("/auth/login", json={"email": "nobody@aust.edu", "password": "whatever"})
    assert r.status_code == 401  # same error: no account enumeration
    assert (await local.post("/auth/login", json={"email": "not-an-email", "password": "x"})).status_code == 422
    assert (await local.post("/auth/signup", json={})).status_code in (404, 405)
    # unauthenticated access to protected routes
    assert (await local.get("/me")).status_code == 401
    assert (await local.get("/courses")).status_code == 401
    assert (await local.get("/me", headers={"X-Dev-User": "x@y.z"})).status_code == 401  # dev header ignored
    assert (await local.get("/health")).status_code == 200
    assert (await local.get("/auth/permissions")).status_code == 200


async def test_login_issues_jwt_with_role_and_me_reports_permissions(local):
    headers, body = await login(local, FACULTY)
    claims = jwt.decode(body["access_token"], SECRET, algorithms=["HS256"], audience=LOCAL_AUD, issuer=LOCAL_ISS)
    assert claims["role"] == "faculty" and claims["email"] == FACULTY[0] and claims["exp"] == body["expires_at"]
    assert body["user"]["role"] == "faculty"
    me = (await local.get("/me", headers=headers)).json()
    assert me["email"] == FACULTY[0]
    assert "findings:decide" in me["permissions"] and "admin" not in me["dashboards"]
    assert set(me["dashboards"]) >= {"courses", "course_workspace", "exam_audit", "overview"}
    # SSE-style query param works too
    assert (await local.get(f"/me?access_token={body['access_token']}")).status_code == 200
    assert (await local.post("/auth/logout", headers=headers)).status_code == 204

    _, admin_body = await login(local, ADMIN)
    assert admin_body["user"]["role"] == "admin"
    assert {"admin", "admin_department"} <= set(admin_body["user"]["dashboards"])
    assert "findings:decide" not in admin_body["user"]["permissions"]


async def test_tampered_expired_and_foreign_tokens_rejected(local):
    headers, body = await login(local, FACULTY)
    sub = jwt.decode(body["access_token"], options={"verify_signature": False})["sub"]

    def mk(**over):
        c = {"sub": sub, "email": FACULTY[0], "role": "faculty", "iss": LOCAL_ISS, "aud": LOCAL_AUD, "iat": int(time.time()), "exp": int(time.time()) + 600}
        c.update(over)
        return jwt.encode(c, over.pop("_secret", SECRET), algorithm="HS256")

    assert (await local.get("/me", headers={"Authorization": f"Bearer {mk(exp=int(time.time()) - 5)}"})).status_code == 401
    assert (await local.get("/me", headers={"Authorization": f"Bearer {mk(_secret='another-secret-another-secret-12345')}"})).status_code == 401
    assert (await local.get("/me", headers={"Authorization": f"Bearer {mk(aud='authenticated')}"})).status_code == 401
    assert (await local.get("/me", headers={"Authorization": f"Bearer {mk(sub=str(uuid.uuid4()))}"})).status_code == 401  # unknown user, no auto-provision
    # role claim is informational: permissions come from the DB role, so escalating it does nothing
    r = await local.get("/me", headers={"Authorization": f"Bearer {mk(role='admin')}"})
    assert r.status_code == 200 and r.json()["role"] == "faculty"


async def test_permission_catalog_matches_table(local):
    cat = (await local.get("/auth/permissions")).json()
    roles = {r["role"]: r for r in cat["roles"]}
    assert "dashboard:admin" in roles["admin"]["permissions"] and "dashboard:admin" not in roles["faculty"]["permissions"]
    assert "findings:decide" in roles["faculty"]["permissions"] and "findings:decide" not in roles["admin"]["permissions"]
    from sqlalchemy import select

    from app.db.models import RolePermission

    async with session_scope() as db:
        rows = {(r.role.value, r.permission) for r in (await db.execute(select(RolePermission))).scalars()}
    expected = {(r, p) for r, d in roles.items() for p in d["permissions"]}
    assert rows == expected


async def test_admin_is_read_only(local):
    admin, _ = await login(local, ADMIN)
    r = await local.post("/courses", json={"code": "CSE 9999", "title": "x"}, headers=admin)
    assert r.status_code == 403 and r.json()["error"]["code"] == "PERMISSION_DENIED"
    assert (await local.post("/demo/seed", headers=admin)).status_code == 403
    assert (await local.get("/courses", headers=admin)).status_code == 200  # reads are fine


async def test_faculty_full_journey_with_jwt(local):
    """Sign in → workspace → outcomes → upload → confirm → run → findings → decide → export."""
    fac, _ = await login(local, FACULTY)
    admin, _ = await login(local, ADMIN)

    course = (await local.post("/courses", json={"code": f"CSE {uuid.uuid4().int % 9000 + 1000}", "title": "Database Systems"}, headers=fac)).json()
    cid = course["id"]
    assert (await local.put(f"/courses/{cid}/outcomes", json=OUTCOMES, headers=fac)).status_code == 200
    past = await upload_text(local, fac, cid, kind="question_paper", label="Mid 2024", text=PAST_PAPER)
    draft = await upload_text(local, fac, cid, kind="question_paper", label="Final draft", text=DRAFT_PAPER, declared=60)
    assert past["status"] == "done" and draft["status"] == "done"
    qs = (await local.get(f"/artefacts/{draft['id']}/questions", headers=fac)).json()
    assert len(qs) >= 8
    assert (await local.put(f"/artefacts/{draft['id']}/questions", json=[{k: q[k] for k in ("id", "number", "text", "marks")} for q in qs], headers=fac)).status_code == 200

    r = await local.post(f"/courses/{cid}/runs", json={"module": "exam_audit", "inputs": {"draft_artefact_id": draft["id"], "past_artefact_ids": [past["id"]]}}, headers=fac)
    assert r.status_code == 202, r.text
    run_id = r.json()["id"]
    await wait_until_done()
    run = (await local.get(f"/runs/{run_id}", headers=fac)).json()
    assert run["status"] in ("completed", "partial"), run
    findings = (await local.get(f"/runs/{run_id}/findings", headers=fac)).json()
    assert findings
    fid = findings[0]["id"]
    assert (await local.patch(f"/findings/{fid}", json={"status": "accepted"}, headers=fac)).status_code == 200
    r = await local.get(f"/runs/{run_id}/export", headers=fac)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/markdown")

    # Admin: cannot decide findings (SEC-009); cannot see another owner's course (404, ownership scoping)
    assert (await local.patch(f"/findings/{fid}", json={"status": "dismissed"}, headers=admin)).status_code == 403
    assert (await local.get(f"/courses/{cid}", headers=admin)).status_code == 404

    # change password then old token still valid until expiry, new password logs in
    r = await local.post("/auth/change-password", json={"current_password": FACULTY[1], "new_password": "NewTeacher#2026"}, headers=fac)
    assert r.status_code == 204
    assert (await local.post("/auth/login", json={"email": FACULTY[0], "password": FACULTY[1]})).status_code == 401
    assert (await local.post("/auth/login", json={"email": FACULTY[0], "password": "NewTeacher#2026"})).status_code == 200
    # restore for other tests
    async with session_scope() as db:
        await ensure_seed_users(db, get_settings())
