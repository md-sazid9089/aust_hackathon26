from __future__ import annotations

import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient

from app.errors import Unauthenticated

ASYMMETRIC_ALGS = ("ES256", "RS256")
LOCAL_ISSUER = "faculty-copilot"
LOCAL_AUDIENCE = "faculty-copilot"
LOCAL_ISS, LOCAL_AUD = LOCAL_ISSUER, LOCAL_AUDIENCE


def issue_local_jwt(
    *, user_id: uuid.UUID, email: str, role: str, secret: str, ttl_s: int
) -> tuple[str, int]:
    """Sign an HS256 token for AUTH_MODE=local. Returns (token, expires_at epoch seconds)."""
    now = int(datetime.now(UTC).timestamp())
    exp = now + ttl_s
    claims = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iss": LOCAL_ISSUER,
        "aud": LOCAL_AUDIENCE,
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(claims, secret, algorithm="HS256"), exp


def verify_local_jwt(token: str, *, secret: str) -> dict[str, Any]:
    """Verify a token issued by `issue_local_jwt` and return its claims."""
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience=LOCAL_AUDIENCE,
            issuer=LOCAL_ISSUER,
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise Unauthenticated("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise Unauthenticated("Invalid token") from exc


@lru_cache
def _jwks_client(jwks_url: str) -> PyJWKClient:
    # In-process key cache; PyJWKClient refetches when it meets an unknown kid.
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)


def verify_supabase_jwt(
    token: str, *, jwks_url: str | None = None, secret: str | None = None
) -> dict[str, Any]:
    """Verify a Supabase access token and return its claims (sub, email, ...).

    ES256/RS256 tokens (current Supabase default) are checked against the project JWKS;
    HS256 tokens (legacy projects) against the shared JWT secret.
    """
    try:
        alg = jwt.get_unverified_header(token).get("alg")
        if alg == "HS256":
            if not secret:
                raise Unauthenticated("HS256 token but SUPABASE_JWT_SECRET is not set")
            key: Any = secret
        elif alg in ASYMMETRIC_ALGS:
            if not jwks_url:
                raise Unauthenticated(f"{alg} token but SUPABASE_JWKS_URL is not set")
            key = _jwks_client(jwks_url).get_signing_key_from_jwt(token).key
        else:
            raise Unauthenticated("Unsupported token algorithm")
        claims = jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience="authenticated",
            options={"require": ["sub", "exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise Unauthenticated("Token expired") from exc
    except jwt.PyJWKClientError as exc:
        raise Unauthenticated("Unable to resolve signing key") from exc
    except jwt.InvalidTokenError as exc:
        raise Unauthenticated("Invalid token") from exc
    return claims
