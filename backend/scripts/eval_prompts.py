"""Offline eval of the AI prompts against the human-labelled seed questions.

Runs the real `structured_call` path (prompts, schemas, response-mode ladder) against any
OpenAI-compatible endpoint and scores it. No DB, no server.

  LLM_PROVIDER=openai_compatible LLM_BASE_URL=http://127.0.0.1:8080/v1 LLM_API_KEY=x LLM_MODEL=auto \
      .venv/bin/python scripts/eval_prompts.py [--models auto,quality] [--json out.json]

Metrics (per model):
  extraction   question count recall/precision by label, total-marks exact
  mapping      CO exact-match, Bloom exact, Bloom within ±1, evidence_quote verbatim rate, mean |conf - correct|
  duplicates   on the labelled near-duplicate pairs: precision/recall of level in {identical, paraphrase}
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("LLM_PROVIDER", "openai_compatible")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "data" / "seed-data"
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.client import CallContext, build_provider, structured_call  # noqa: E402
from app.ai.guard import wrap_untrusted  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db.enums import BLOOM_ORDER, BloomLevel, UsagePurpose  # noqa: E402
from app.extraction import prompts as EP  # noqa: E402
from app.extraction.schemas import ExtractedQuestions  # noqa: E402
from app.modules.exam_audit import prompts as MP  # noqa: E402
from app.modules.exam_audit.graph import quote_is_verbatim  # noqa: E402
from app.modules.exam_audit.schemas import DUPLICATE_LEVELS, ConfirmDuplicatesOut, MapAndBloomOut  # noqa: E402

BLOOM_BY_ID = {"L1": "remember", "L2": "understand", "L3": "apply", "L4": "analyze", "L5": "evaluate", "L6": "create"}


def load_gold():
    qs = json.load(open(SEED / "questions.json"))
    cos = json.load(open(SEED / "course_outcomes.json"))
    topics = json.load(open(SEED / "syllabus_topics.json"))
    papers = {p["paper_id"]: p for p in json.load(open(SEED / "question_papers.json"))}
    return qs, cos, topics, papers


def paper_text(paper, questions):
    lines = [paper.get("title", ""), ""]
    for q in questions:
        lines.append(f"{q['display_label']} {q['text']} [{q['marks']}]")
    return "\n".join(lines)


async def eval_extraction(provider, paper, questions):
    text = paper_text(paper, questions)
    res = await structured_call(
        purpose="extract_questions", usage_purpose=UsagePurpose.extraction, system=EP.EXTRACT_QUESTIONS_SYSTEM,
        user=EP.EXTRACT_QUESTIONS_USER.format(document=wrap_untrusted(text, "paper")), schema=ExtractedQuestions,
        ctx=CallContext(), provider=provider,
    )
    if res.value is None:
        return {"ok": False, "error": res.error, "mode": res.response_mode}
    got = {"".join(q.number.split()).lower(): q for q in res.value.questions}
    want = {q["display_label"].replace(" ", "").lower(): q for q in questions}
    hit = set(got) & set(want)
    marks_ok = sum(1 for k in hit if abs(float(got[k].marks) - float(want[k]["marks"])) < 0.01)
    return {
        "ok": True, "mode": res.response_mode, "attempts": res.attempts, "repaired": res.repaired,
        "recall": round(len(hit) / len(want), 3), "precision": round(len(hit) / max(1, len(got)), 3),
        "marks_exact": round(marks_ok / max(1, len(hit)), 3),
        "total_marks_exact": abs(sum(float(q.marks) for q in res.value.questions) - sum(q["marks"] for q in questions)) < 0.01,
        "missing": sorted(set(want) - set(got)), "extra": sorted(set(got) - set(want)),
    }


async def eval_mapping(provider, questions, cos, topics):
    outcomes_txt = "\n".join(f"- {c['code']}: {c['statement']}" for c in cos)
    topics_txt = "\n".join(f"- {t['topic_id']}: {t.get('title') or t.get('name')}" for t in topics) or "- (none provided)"
    labelled = [q for q in questions if q.get("co_id") and q.get("bloom_id")]
    rows, verbatim, conf_err = [], 0, []
    for i in range(0, len(labelled), 15):
        batch = labelled[i : i + 15]
        qtxt = "\n".join(f"{q['display_label']} :: {wrap_untrusted(q['text'], f'q{q['display_label']}', 2000)}" for q in batch)
        res = await structured_call(
            purpose="map_and_bloom", usage_purpose=UsagePurpose.exam_audit, system=MP.MAP_AND_BLOOM_SYSTEM,
            user=MP.MAP_AND_BLOOM_USER.format(outcomes=outcomes_txt, topics=topics_txt, questions=qtxt),
            schema=MapAndBloomOut, ctx=CallContext(), provider=provider,
        )
        if res.value is None:
            return {"ok": False, "error": res.error, "mode": res.response_mode}
        by_num = {"".join(it.number.split()).lower(): it for it in res.value.items}
        for q in batch:
            it = by_num.get(q["display_label"].replace(" ", "").lower())
            if it is None:
                rows.append({"q": q["display_label"], "missing": True})
                continue
            gold_bloom = BLOOM_BY_ID[q["bloom_id"]]
            co_ok = q["co_id"] in it.co_codes
            bloom_dist = abs(BLOOM_ORDER[BloomLevel(it.bloom_level)] - BLOOM_ORDER[BloomLevel(gold_bloom)])
            vb = quote_is_verbatim(it.evidence_quote, q["text"])
            verbatim += vb
            conf_err.append(abs(it.confidence - (1.0 if co_ok else 0.0)))
            rows.append({"q": q["display_label"], "co_ok": co_ok, "got_co": it.co_codes, "gold_co": q["co_id"],
                         "bloom_ok": bloom_dist == 0, "bloom_dist": bloom_dist, "got_bloom": it.bloom_level.value, "gold_bloom": gold_bloom,
                         "evidence_verbatim": vb, "confidence": it.confidence})
    scored = [r for r in rows if not r.get("missing")]
    n = max(1, len(scored))
    return {
        "ok": True, "n": len(scored), "missing": len(rows) - len(scored),
        "co_exact": round(sum(r["co_ok"] for r in scored) / n, 3),
        "bloom_exact": round(sum(r["bloom_ok"] for r in scored) / n, 3),
        "bloom_within_1": round(sum(r["bloom_dist"] <= 1 for r in scored) / n, 3),
        "evidence_verbatim_rate": round(verbatim / n, 3),
        "confidence_mae": round(sum(conf_err) / max(1, len(conf_err)), 3),
        "rows": rows,
    }


# Hand-labelled pairs from the seed set: (draft label, other label, expected duplicate?)
DUP_GOLD = [
    ("QP-2026-DRAFT-01", "2(a)", "QP-2024-MID-01", "1(a)", True),   # physical vs logical independence, reworded
    ("QP-2026-DRAFT-01", "2(b)", "QP-2025-FIN-01", "1(b)", True),   # ER diagram, same scenario
    ("QP-2026-DRAFT-01", "1(a)", "QP-2024-MID-01", "2(a)", False),  # same topic, different task
    ("QP-2026-DRAFT-01", "4(a)", "QP-2025-FIN-01", "3(a)", False),
]


async def eval_duplicates(provider, questions):
    idx = {(q["paper_id"], q["display_label"]): q for q in questions}
    pairs = [(idx.get((a, b)), idx.get((c, d)), exp) for a, b, c, d, exp in DUP_GOLD]
    pairs = [(x, y, e) for x, y, e in pairs if x and y]
    if not pairs:
        return {"ok": False, "error": "no gold pairs matched the seed set"}
    txt = "\n\n".join(
        f"PAIR draft_number={d['display_label']} other_question_id=P{i}\nDRAFT: {wrap_untrusted(d['text'], 'draft', 2000)}\nOTHER: {wrap_untrusted(o['text'], 'other', 2000)}"
        for i, (d, o, _) in enumerate(pairs)
    )
    res = await structured_call(
        purpose="confirm_duplicates", usage_purpose=UsagePurpose.exam_audit, system=MP.CONFIRM_DUPLICATES_SYSTEM,
        user=MP.CONFIRM_DUPLICATES_USER.format(pairs=txt), schema=ConfirmDuplicatesOut, ctx=CallContext(), provider=provider,
    )
    if res.value is None:
        return {"ok": False, "error": res.error}
    got = {v.other_question_id: v for v in res.value.items}
    tp = fp = fn = 0
    rows = []
    for i, (d, o, exp) in enumerate(pairs):
        v = got.get(f"P{i}")
        pred = bool(v and v.level in DUPLICATE_LEVELS)
        tp += pred and exp
        fp += pred and not exp
        fn += (not pred) and exp
        rows.append({"draft": d["display_label"], "other": o["display_label"], "expected": exp, "level": v.level if v else None})
    return {"ok": True, "precision": round(tp / max(1, tp + fp), 3), "recall": round(tp / max(1, tp + fn), 3), "rows": rows}


async def run(models: list[str]) -> dict:
    qs, cos, topics, papers = load_gold()
    by_paper: dict[str, list] = {}
    for q in qs:
        by_paper.setdefault(q["paper_id"], []).append(q)
    report: dict = {"models": {}}
    for model in models:
        os.environ["LLM_MODEL"] = model
        get_settings.cache_clear()
        provider = build_provider(get_settings())
        t0 = time.perf_counter()
        ext = {pid: await eval_extraction(provider, papers[pid], qlist) for pid, qlist in by_paper.items()}
        mapping = await eval_mapping(provider, qs, cos, topics)
        dups = await eval_duplicates(provider, qs)
        await provider.aclose()
        report["models"][model] = {"seconds": round(time.perf_counter() - t0, 1), "extraction": ext, "mapping": mapping, "duplicates": dups}
        m = mapping if mapping.get("ok") else {}
        e_ok = [e for e in ext.values() if e.get("ok")]
        print(
            f"\n== {model} ({report['models'][model]['seconds']}s) mode={m.get('mode') or (e_ok[0]['mode'] if e_ok else '?')}\n"
            f"extraction: recall={[e['recall'] for e in e_ok]} precision={[e['precision'] for e in e_ok]} marks_exact={[e['marks_exact'] for e in e_ok]} failed={len(ext) - len(e_ok)}\n"
            f"mapping:    n={m.get('n')} co_exact={m.get('co_exact')} bloom_exact={m.get('bloom_exact')} bloom_±1={m.get('bloom_within_1')} "
            f"evidence_verbatim={m.get('evidence_verbatim_rate')} conf_mae={m.get('confidence_mae')} err={mapping.get('error')}\n"
            f"duplicates: precision={dups.get('precision')} recall={dups.get('recall')} err={dups.get('error')}"
        )
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=os.environ.get("LLM_MODEL", "auto"))
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    rep = asyncio.run(run([m.strip() for m in a.models.split(",") if m.strip()]))
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=2, default=str))
        print(f"\nwrote {a.json}")
