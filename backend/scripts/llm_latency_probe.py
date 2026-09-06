"""Time a small chat call against LLM_BASE_URL for several model aliases (diagnostic only)."""
from __future__ import annotations

import asyncio
import os
import sys
import time

import httpx

BASE = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8080/v1")
MODELS = sys.argv[1:] or ["auto", "fast", "quality", "pollinations/openai-fast"]
BODY = {
    "messages": [
        {"role": "system", "content": "Reply with ONE JSON object only."},
        {"role": "user", "content": 'Return {"ok": true, "n": 3}'},
    ],
    "temperature": 0,
    "max_tokens": 64,
}


async def probe(client: httpx.AsyncClient, model: str, fmt: dict | None) -> None:
    body = {**BODY, "model": model}
    if fmt:
        body["response_format"] = fmt
    t = time.perf_counter()
    try:
        r = await client.post(f"{BASE}/chat/completions", json=body, timeout=90)
        dt = time.perf_counter() - t
        content = (r.json().get("choices") or [{}])[0].get("message", {}).get("content", "")[:60] if r.status_code == 200 else r.text[:120]
        print(f"{model:28s} fmt={fmt['type'] if fmt else '-':12s} {r.status_code} {dt:6.2f}s  {content!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"{model:28s} fmt={fmt['type'] if fmt else '-':12s} ERR {time.perf_counter() - t:6.2f}s {exc}")


async def main() -> None:
    async with httpx.AsyncClient(headers={"Authorization": "Bearer x"}) as client:
        for m in MODELS:
            for fmt in (None, {"type": "json_object"}):
                await probe(client, m, fmt)


asyncio.run(main())
