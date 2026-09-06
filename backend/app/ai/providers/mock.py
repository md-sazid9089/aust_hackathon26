from __future__ import annotations

import hashlib
import json
import math
import re
from collections import deque
from typing import Any

from app.ai.providers.base import AIProvider, ChatResult, EmbedResult, ProviderError

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on", "by", "is", "are", "be",
    "that", "this", "its", "it", "as", "at", "from", "each", "which", "what", "into", "your", "you",
    "given", "using", "use", "write", "state", "explain", "describe", "define", "list", "draw",
    "design", "compare", "distinguish", "briefly", "suitable", "example", "examples", "following",
    "than", "more", "least", "all", "any", "between", "two", "one", "system", "course", "students",
}

BLOOM_VERBS: dict[str, tuple[str, ...]] = {
    "remember": ("define", "list", "state", "name", "recall", "identify", "label", "recite"),
    "understand": ("explain", "describe", "compare", "distinguish", "summarize", "summarise", "interpret", "discuss", "outline", "classify"),
    "apply": ("write", "draw", "convert", "solve", "compute", "calculate", "implement", "apply", "construct", "translate", "demonstrate", "find"),
    "analyze": ("analyse", "analyze", "determine", "differentiate", "examine", "decompose", "normalise", "normalize", "derive", "investigate", "identify the"),
    "evaluate": ("evaluate", "justify", "assess", "critique", "recommend", "argue", "judge", "select"),
    "create": ("design", "propose", "develop", "formulate", "devise", "compose", "plan"),
}

EMBED_DIM = 256


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z][a-z0-9+\-]{2,}", text.lower()) if t not in STOPWORDS}


def hashed_embedding(text: str, dim: int = EMBED_DIM) -> list[float]:
    """Deterministic bag-of-words hashing vector; only for offline/mock mode."""
    vec = [0.0] * dim
    for tok in re.findall(r"[a-z][a-z0-9+\-]{2,}", text.lower()):
        if tok in STOPWORDS:
            continue
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)  # noqa: S324 - not security related
        vec[h % dim] += 1.0 if (h >> 8) % 2 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 6) for v in vec]


def guess_bloom(text: str) -> str:
    lowered = text.lower()
    first = lowered[:80]
    for level, verbs in BLOOM_VERBS.items():
        if any(first.startswith(v) or f" {v} " in f" {first} " for v in verbs):
            return level
    for level, verbs in BLOOM_VERBS.items():
        if any(v in lowered for v in verbs):
            return level
    return "understand"


def _overlap(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / math.sqrt(len(ta) * len(tb))


class MockProvider(AIProvider):
    """Deterministic, offline stand-in used for tests and the no-network demo fallback.

    It never fabricates content: outputs are simple lexical heuristics over the structured
    `context` that the caller built the prompt from. Tests may queue raw responses/exceptions.
    """

    name = "mock"

    def __init__(self) -> None:
        self._queued: dict[str, deque[str | Exception]] = {}
        self.calls: list[dict[str, Any]] = []

    # --- test hooks -------------------------------------------------------
    def queue(self, purpose: str, response: str | Exception) -> None:
        self._queued.setdefault(purpose, deque()).append(response)

    def reset(self) -> None:
        self._queued.clear()
        self.calls.clear()

    # --- provider API -----------------------------------------------------
    async def chat_json(
        self,
        *,
        purpose: str,
        system: str,
        user: str,
        json_schema: dict[str, Any],
        schema_name: str,
        model: str | None = None,
        temperature: float = 0.0,
        timeout_s: float = 60.0,
        context: dict[str, Any] | None = None,
    ) -> ChatResult:
        self.calls.append({"purpose": purpose, "schema": schema_name})
        q = self._queued.get(purpose)
        if q:
            item = q.popleft()
            if isinstance(item, Exception):
                raise item
            return ChatResult(content=item, model="mock", tokens_in=0, tokens_out=0)
        ctx = context or {}
        handler = getattr(self, f"_h_{purpose}", None)
        if handler is None:
            raise ProviderError(f"Mock provider has no handler for purpose '{purpose}'", retryable=False)
        return ChatResult(content=json.dumps(handler(ctx)), model="mock", tokens_in=0, tokens_out=0)

    async def embed(self, texts: list[str], *, timeout_s: float = 60.0) -> EmbedResult:
        return EmbedResult(vectors=[hashed_embedding(t) for t in texts], model="mock-hash-256", tokens_in=0)

    # --- heuristic handlers (keyed by purpose) ----------------------------
    def _h_extract_questions(self, ctx: dict[str, Any]) -> dict[str, Any]:
        from app.artefacts.parsers import split_questions_heuristic

        items = split_questions_heuristic(ctx.get("text", ""))
        return {"questions": items, "notes": "heuristic split (mock provider)"}

    def _h_extract_syllabus(self, ctx: dict[str, Any]) -> dict[str, Any]:
        from app.artefacts.parsers import split_topics_heuristic

        return {"topics": split_topics_heuristic(ctx.get("text", "")), "notes": "heuristic split (mock provider)"}

    def _h_map_and_bloom(self, ctx: dict[str, Any]) -> dict[str, Any]:
        cos = ctx.get("outcomes", [])
        topics = ctx.get("topics", [])
        items = []
        for q in ctx.get("questions", []):
            co_scores = sorted(((_overlap(q["text"], c["text"]), c["code"]) for c in cos), reverse=True)
            topic_scores = sorted(((_overlap(q["text"], t["title"]), t["code"]) for t in topics), reverse=True)
            best_co = [code for s, code in co_scores[:1] if s >= 0.15]
            best_topics = [code for s, code in topic_scores[:1] if s >= 0.15]
            conf = round(min(1.0, co_scores[0][0] * 2), 3) if co_scores and best_co else 0.0
            items.append(
                {
                    "number": q["number"],
                    "co_codes": best_co,
                    "topic_codes": best_topics,
                    "bloom_level": guess_bloom(q["text"]),
                    "confidence": conf,
                    "rationale": (
                        f"Lexical overlap with {best_co[0]} ({co_scores[0][0]:.2f})" if best_co
                        else "No outcome shares enough vocabulary with this question"
                    ) + f"; verb pattern suggests Bloom '{guess_bloom(q['text'])}'.",
                }
            )
        return {"items": items}

    def _h_confirm_duplicates(self, ctx: dict[str, Any]) -> dict[str, Any]:
        out = []
        for pair in ctx.get("pairs", []):
            ov = _overlap(pair["draft_text"], pair["other_text"])
            dup = ov >= 0.6 or float(pair.get("similarity", 0)) >= 0.9
            out.append(
                {
                    "draft_number": pair["draft_number"],
                    "other_question_id": pair["other_question_id"],
                    "is_duplicate": dup,
                    "rationale": f"Token overlap {ov:.2f}; vector similarity {float(pair.get('similarity', 0)):.2f}. "
                    + ("Both ask for the same task on the same concept." if dup else "Shared vocabulary but the task differs."),
                }
            )
        return {"items": out}
