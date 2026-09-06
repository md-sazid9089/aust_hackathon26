from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

# PBKDF2-HMAC-SHA256 from the standard library: no native wheel needed on Python 3.14.
_ALG = "pbkdf2_sha256"
_ITERATIONS = 600_000  # OWASP 2023 recommendation for PBKDF2-HMAC-SHA256
_SALT_BYTES = 16


def hash_password(password: str, *, iterations: int = _ITERATIONS) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"{_ALG}${iterations}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        alg, iters, salt_b64, digest_b64 = encoded.split("$")
        if alg != _ALG:
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iters))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()
