from __future__ import annotations

import time
import uuid

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.deps import get_current_user
from app.main import create_app

SECRET = "test-secret-please-rotate"


def _token(sub: str, *, exp_delta: int = 3600, email: str = "f@aust.edu", secret: str = SECRET, aud: str = "authenticated") -> str:
    return jwt.encode({"sub": sub, "email": email, "aud": aud, "exp": int(time.time()) + exp_delta, "user_metadata": {"full_name": "Prof F"}}, secret, algorithm="HS256")


@pytest.fixture
async def sb_client(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "supabase")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    get_settings.cache_clear()
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as c:
        yield c
    get_settings.cache_clear()


async def test_supabase_mode_rejects_missing_invalid_expired(sb_client):
    assert (await sb_client.get("/me")).status_code == 401
    assert (await sb_client.get("/courses")).status_code == 401
    r = await sb_client.get("/me", headers={"Authorization": "Bearer nonsense"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHENTICATED"
    r = await sb_client.get("/me", headers={"Authorization": f"Bearer {_token(str(uuid.uuid4()), exp_delta=-10)}"})
    assert r.status_code == 401 and "expired" in r.json()["error"]["message"].lower()
    r = await sb_client.get("/me", headers={"Authorization": f"Bearer {_token(str(uuid.uuid4()), secret='wrong')}"})
    assert r.status_code == 401
    r = await sb_client.get("/me", headers={"Authorization": f"Bearer {_token(str(uuid.uuid4()), aud='other')}"})
    assert r.status_code == 401
    # dev header must be ignored in supabase mode
    assert (await sb_client.get("/me", headers={"X-Dev-User": "x@y.z"})).status_code == 401


async def test_supabase_mode_accepts_valid_token_and_query_param(sb_client):
    uid = str(uuid.uuid4())
    r = await sb_client.get("/me", headers={"Authorization": f"Bearer {_token(uid)}"})
    assert r.status_code == 200 and r.json()["id"] == uid and r.json()["full_name"] == "Prof F"
    r = await sb_client.get(f"/me?access_token={_token(uid)}")
    assert r.status_code == 200
    # health does not require auth
    assert (await sb_client.get("/health")).status_code == 200


async def test_inactive_user_forbidden(client, user_a):
    from sqlalchemy import update

    from app.db.models import Profile
    from app.db.session import session_scope

    email = user_a["X-Dev-User"]
    assert (await client.get("/me", headers=user_a)).status_code == 200
    async with session_scope() as db:
        await db.execute(update(Profile).where(Profile.email == email).values(is_active=False))
    r = await client.get("/me", headers=user_a)
    assert r.status_code == 403 and r.json()["error"]["code"] == "USER_INACTIVE"


async def test_rate_limit(monkeypatch, user_a):
    from app.deps import runs_rate_limit

    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    get_settings.cache_clear()
    runs_rate_limit._hits.clear()
    app = create_app()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as c:
            course = (await c.post("/courses", json={"code": "RL 1", "title": "Rate limit"}, headers=user_a)).json()
            codes = []
            for _ in range(11):
                r = await c.post(f"/courses/{course['id']}/runs", json={"module": "exam_audit", "inputs": {}}, headers=user_a)
                codes.append(r.status_code)
            assert codes[:10] == [422] * 10 and codes[10] == 429
            assert r.headers["retry-after"]
    finally:
        get_settings.cache_clear()
        runs_rate_limit._hits.clear()


def test_get_current_user_is_a_dependency():
    assert callable(get_current_user)
