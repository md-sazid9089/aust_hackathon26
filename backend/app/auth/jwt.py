from __future__ import annotations

from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient

from app.errors import Unauthenticated

ASYMMETRIC_ALGS = ("ES256", "RS256")


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
