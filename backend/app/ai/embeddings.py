from __future__ import annotations

import math
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import CallContext, get_provider
from app.ai.providers.base import AIProvider, ProviderError
from app.config import get_settings
from app.db.enums import UsagePurpose
from app.db.models import UsageLog
from app.logging import get_logger

log = get_logger(__name__)
BATCH = 64


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


async def embed_texts(
    texts: list[str],
    *,
    ctx: CallContext,
    db: AsyncSession | None = None,
    provider: AIProvider | None = None,
) -> tuple[list[list[float]], str] | None:
    """Embed in batches; returns (vectors, model) or None when the provider fails (caller degrades)."""
    provider = provider or get_provider()
    settings = get_settings()
    vectors: list[list[float]] = []
    model = settings.embed_model
    for i in range(0, len(texts), BATCH):
        chunk = texts[i : i + BATCH]
        started = time.perf_counter()
        try:
            res = await provider.embed(chunk, timeout_s=settings.llm_timeout_s)
        except ProviderError as exc:
            log.warning("embed.failed", error=str(exc))
            if db is not None:
                db.add(UsageLog(user_id=ctx.user_id, run_id=ctx.run_id, purpose=UsagePurpose.embedding,
                                model=model, status="failed",
                                latency_ms=int((time.perf_counter() - started) * 1000)))
            return None
        model = res.model
        vectors.extend(res.vectors)
        if db is not None:
            db.add(UsageLog(user_id=ctx.user_id, run_id=ctx.run_id, purpose=UsagePurpose.embedding,
                            model=model, tokens_in=res.tokens_in, status="ok",
                            latency_ms=int((time.perf_counter() - started) * 1000)))
    return vectors, model
