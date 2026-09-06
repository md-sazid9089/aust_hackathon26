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
    "appropriate", "required", "information", "techniques", "strategies", "statements", "purpose",
    "main", "type", "types", "major", "fundamental", "concepts", "involving", "retrieve", "showing",
    "containing", "exceeds", "exceed", "having", "find", "names", "name", "plan", "workload",
}


def _stem(tok: str) -> str:
    if tok.endswith("ies") and len(tok) > 4:
        return tok[:-3] + "y"
    if tok.endswith("es") and len(tok) > 4 and tok[-3] in "sxz":
        return tok[:-2]
    if tok.endswith("s") and not tok.endswith("ss") and len(tok) > 3:
        return tok[:-1]
    return tok

BLOOM_VERBS: dict[str, tuple[str, ...]] = {
    "remember": ("define", "list", "state", "name", "recall", "identify", "label", "recite"),
    "understand": ("explain", "describe", "compare", "distinguish", "summarize", "summarise", "interpret", "discuss", "outline", "classify"),
    "apply": ("write", "draw", "convert", "solve", "compute", "calculate", "implement", "apply", "construct", "translate", "demonstrate", "find"),
    "analyze": ("analyse", "analyze", "determine", "differentiate", "examine", "decompose", "normalise", "normalize", "derive", "investigate", "identify the"),
    "evaluate": ("evaluate", "justify", "assess", "critique", "recommend", "argue", "judge", "select"),
    "create": ("design", "propose", "develop", "formulate", "devise", "compose", "plan"),
}

EMBED_DIM = 256


SYNONYMS = {"query": "sql", "average": "aggregate", "group": "aggregate", "having": "aggregate",
            "count": "aggregate", "sum": "aggregate", "3nf": "bcnf", "normalize": "normalise", "locking": "concurrency"}


def tokens(text: str) -> set[str]:
    raw = re.findall(r"[a-z0-9][a-z0-9+]{1,}", text.lower())
    return {SYNONYMS.get(_stem(t), _stem(t)) for t in raw if t not in STOPWORDS and len(t) > 2}


def hashed_embedding(text: str, dim: int = EMBED_DIM) -> list[float]:
    """Deterministic bag-of-words hashing vector; only for offline/mock mode."""
    vec = [0.0] * dim
    for tok in tokens(text):
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
            best_co = [code for s, code in co_scores[:1] if s >= 0.12]
            best_topics = [code for s, code in topic_scores[:1] if s >= 0.12]
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

    # --- assistant planner (keyword intents; offline stand-in for the LLM agent) ---
    def _h_assistant_plan(self, ctx: dict[str, Any]) -> dict[str, Any]:
        from app.ai.providers.mock_assistant import plan

        return plan(ctx)

    # --- Tier-1 extraction handlers --------------------------------------------
    def _h_extract_rubric(self, ctx: dict[str, Any]) -> dict[str, Any]:
        from app.artefacts.parsers import split_rubric_heuristic

        return {"criteria": split_rubric_heuristic(ctx.get("text", "")), "notes": "heuristic split (mock provider)"}

    def _h_extract_answers(self, ctx: dict[str, Any]) -> dict[str, Any]:
        from app.artefacts.parsers import split_answers_heuristic

        items = split_answers_heuristic(ctx.get("text", ""))
        for a in items:
            a["question_ref"] = a.get("question_ref") or ""
        return {"answers": items, "notes": "heuristic split (mock provider)"}

    # --- Tier-1 module handlers ---------------------------------------------------
    def _h_explain_attainment(self, ctx: dict[str, Any]) -> dict[str, Any]:
        items = []
        for co in ctx.get("cos", []):
            if co.get("met"):
                continue
            weak = ", ".join(f"Q{q}" for q in co.get("weak_questions", [])[:3]) or "the mapped questions"
            items.append(
                {
                    "co_code": co["code"],
                    "explanation": (
                        f"{co['attained_pct']:.0f}% of students reached the threshold on {co['code']} against a target of "
                        f"{co['target_pct']:.0f}%. Scores were lowest on {weak}, which carry most of this outcome's marks."
                    ),
                    "actions": [
                        f"Add a formative exercise on '{co['text'][:60]}' before the next assessment.",
                        f"Review {weak} for wording or difficulty that exceeds the intended Bloom level.",
                        "Re-teach the concept with a worked example and re-assess with a short quiz.",
                    ],
                }
            )
        return {"items": items}

    def _h_relate_topics(self, ctx: dict[str, Any]) -> dict[str, Any]:
        this_num = _course_number(ctx.get("course_code", ""))
        items = []
        for p in ctx.get("pairs", []):
            sim = float(p.get("similarity", 0))
            ov = _overlap(p["topic_a"], p["topic_b"])
            other_num = _course_number(p.get("course_code", ""))
            if sim >= 0.7 or ov >= 0.5:
                rel, why = "overlap", f"Both topics share core vocabulary (overlap {max(sim, ov):.2f})."
            elif other_num and this_num and other_num < this_num and (sim >= 0.45 or ov >= 0.3):
                rel, why = "prerequisite", f"'{p['topic_b']}' in the earlier course {p['course_code']} introduces what '{p['topic_a']}' builds on."
            else:
                rel, why = "distinct", "Related vocabulary but different learning focus."
            items.append(
                {
                    "topic_a": p["topic_a"], "topic_b": p["topic_b"], "course_code": p["course_code"], "relation": rel, "rationale": why,
                    "suggestion": (
                        f"Reference {p['course_code']} coverage and shift depth toward application rather than re-teaching." if rel == "overlap"
                        else (f"State {p['course_code']} as a prerequisite or add a short recap." if rel == "prerequisite" else "")
                    ),
                }
            )
        return {"items": items}

    def _h_explain_divergence(self, ctx: dict[str, Any]) -> dict[str, Any]:
        items = []
        for it in ctx.get("items", []):
            scores = it.get("scores", {})
            hi = max(scores, key=scores.get) if scores else "?"
            lo = min(scores, key=scores.get) if scores else "?"
            items.append(
                {
                    "answer_id": it["answer_id"], "criterion_code": it["criterion_code"],
                    "explanation": (
                        f"Grader {hi} awarded {scores.get(hi, 0):g} while grader {lo} awarded {scores.get(lo, 0):g} on {it['criterion_code']} "
                        f"(max {it.get('max_score', 0):g}). The descriptor '{it.get('criterion_text', '')[:70]}' leaves room to reward the end result "
                        "versus the justification shown; agree which evidence counts before re-marking."
                    ),
                }
            )
        return {"items": items}

    def _h_prescore_answers(self, ctx: dict[str, Any]) -> dict[str, Any]:
        criteria = ctx.get("criteria", [])
        items = []
        for a in ctx.get("answers", []):
            scores = []
            for c in criteria:
                ref = c["text"] + " " + " ".join(lv.get("descriptor", "") for lv in c.get("levels", []))
                ov = _overlap(a["text"], ref)
                raw = min(1.0, ov * 2.5) * float(c["max_score"])
                levels = sorted({float(lv["score"]) for lv in c.get("levels", [])} | {0.0, float(c["max_score"])})
                score = min(levels, key=lambda s: abs(s - raw))
                scores.append({"criterion_code": c["code"], "score": score, "rationale": f"Lexical overlap {ov:.2f} with the criterion descriptors; nearest band {score:g}/{float(c['max_score']):g}."})
            items.append({"answer_id": a["answer_id"], "scores": scores})
        return {"items": items}

    def _h_propose_rubric_v2(self, ctx: dict[str, Any]) -> dict[str, Any]:
        items = []
        for c in ctx.get("criteria", []):
            mx = float(c["max_score"])
            items.append(
                {
                    "criterion_code": c["code"],
                    "proposed_text": f"{c['text']} — award marks only for evidence shown in the script (state what counts as evidence).",
                    "proposed_levels": [
                        {"label": f"{mx:g}", "score": mx, "descriptor": "Complete and explicitly justified."},
                        {"label": f"{mx / 2:g}", "score": round(mx / 2, 1), "descriptor": "Partially correct or correct result without justification."},
                        {"label": "0", "score": 0.0, "descriptor": "Missing or incorrect."},
                    ],
                    "rationale": f"Graders diverged by {float(c.get('mean_divergence', 0)):.1f} marks on average; the bands above make the evidence requirement explicit.",
                }
            )
        return {"items": items}

    def _h_suggest_questions(self, ctx: dict[str, Any]) -> dict[str, Any]:
        items = []
        stems = {"remember": "Define", "understand": "Explain", "apply": "Apply", "analyze": "Analyse", "evaluate": "Evaluate", "create": "Design"}
        for co in ctx.get("cos", []):
            level = co.get("bloom_level") or "apply"
            items.append(
                {
                    "co_code": co["code"],
                    "question": f"{stems.get(level, 'Explain')} — with reference to a concrete scenario — {co['text'][0].lower() + co['text'][1:].rstrip('.')}.",
                    "marks": 10,
                    "bloom_level": level,
                    "rationale": f"Targets {co['code']} directly at its intended Bloom level '{level}'; no current question assesses it.",
                }
            )
        return {"items": items}


def _course_number(code: str) -> int:
    m = re.search(r"(\d{3,4})", code or "")
    return int(m.group(1)) if m else 0
