from __future__ import annotations

from typing import Any

import jwt

from app.errors import Unauthenticated


def verify_supabase_jwt(token: str, secret: str) -> dict[str, Any]:
    """Verify an HS256 Supabase access token and return its claims (sub, email, ...)."""
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"require": ["sub", "exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise Unauthenticated("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise Unauthenticated("Invalid token") from exc
    return claims
