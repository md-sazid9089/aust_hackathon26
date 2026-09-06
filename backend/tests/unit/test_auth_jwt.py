from __future__ import annotations

import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt import PyJWK

from app.auth import jwt as auth_jwt
from app.errors import Unauthenticated

JWKS_URL = "https://example.supabase.co/auth/v1/.well-known/jwks.json"


@pytest.fixture
def es256(monkeypatch):
    priv = ec.generate_private_key(ec.SECP256R1())
    pub_jwk = PyJWK.from_dict(
        {**jwt.get_algorithm_by_name("ES256").to_jwk(priv.public_key(), as_dict=True), "kid": "k1"}
    )

    class FakeClient:
        def get_signing_key_from_jwt(self, token):
            if jwt.get_unverified_header(token).get("kid") != "k1":
                raise jwt.PyJWKClientError("unknown kid")
            return pub_jwk

    auth_jwt._jwks_client.cache_clear()
    monkeypatch.setattr(auth_jwt, "_jwks_client", lambda url: FakeClient())
    return priv


def _claims(**over):
    return {"sub": str(uuid.uuid4()), "aud": "authenticated", "exp": int(time.time()) + 600, **over}


def test_es256_token_verified_via_jwks(es256):
    token = jwt.encode(_claims(email="a@b.c"), es256, algorithm="ES256", headers={"kid": "k1"})
    claims = auth_jwt.verify_supabase_jwt(token, jwks_url=JWKS_URL)
    assert claims["email"] == "a@b.c"


def test_es256_unknown_kid_rejected(es256):
    token = jwt.encode(_claims(), es256, algorithm="ES256", headers={"kid": "other"})
    with pytest.raises(Unauthenticated):
        auth_jwt.verify_supabase_jwt(token, jwks_url=JWKS_URL)


def test_es256_without_jwks_url_rejected(es256):
    token = jwt.encode(_claims(), es256, algorithm="ES256", headers={"kid": "k1"})
    with pytest.raises(Unauthenticated):
        auth_jwt.verify_supabase_jwt(token, secret="s")


def test_hs256_still_supported_and_alg_none_rejected():
    token = jwt.encode(_claims(), "s", algorithm="HS256")
    assert "sub" in auth_jwt.verify_supabase_jwt(token, jwks_url=JWKS_URL, secret="s")
    with pytest.raises(Unauthenticated):
        auth_jwt.verify_supabase_jwt(token, jwks_url=JWKS_URL)  # no secret
    with pytest.raises(Unauthenticated):
        auth_jwt.verify_supabase_jwt(jwt.encode(_claims(), None, algorithm="none"), jwks_url=JWKS_URL, secret="s")
