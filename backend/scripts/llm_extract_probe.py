"""Time the real extraction prompt end-to-end per model alias (diagnostic only). Usage: python scripts/llm_extract_probe.py fast auto"""
from __future__ import annotations

import asyncio
import sys
import time

from app.ai.client import CallContext, structured_call
from app.ai.guard import wrap_untrusted
from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.config import get_settings
from app.db.enums import UsagePurpose
from app.extraction import prompts as P
from app.extraction.schemas import ExtractedQuestions, ExtractedTopics

PAPER = """Ahsanullah University of Science and Technology
CSE 3101 Database Systems — Semester Final, Fall 2025      Time: 3 hours   Full marks: 70
Answer any FIVE of the following SIX questions.

1. (a) Define functional dependency. Explain Armstrong's axioms with examples.        [6]
   (b) Consider relation R(A,B,C,D,E) with FDs {A->B, BC->D, D->E}. Find all candidate keys.   [8]
2. (a) What is the difference between 3NF and BCNF? Give an example that is in 3NF but not BCNF.   [7]
   (b) Decompose the relation in Q1(b) into BCNF. Is the decomposition dependency preserving?   [7]
3. (a) Explain the ACID properties of a transaction.   [6]
   (b) Draw the state diagram of a transaction and explain each state.   [8]
4. Write SQL queries for the following on tables Student(id, name, dept), Enrol(sid, cid, grade), Course(cid, title, credits):
   (i) Names of students who took every course offered by 'CSE'.   [5]
   (ii) For each department, the average grade of its students.   [5]
   (iii) Courses with no enrolments.   [4]
5. (a) Compare B+ tree and hash indexing.   [7]
   (b) A B+ tree of order 4 receives keys 10, 20, 5, 6, 12, 30, 7, 17 in that order. Show the tree after each insertion.   [7]
6. (a) Explain two-phase locking and show why it guarantees conflict serializability.   [7]
   (b) What is a deadlock? Describe wait-die and wound-wait schemes.   [7]
"""

SYLLABUS = """CSE 3101 Database Systems — Course Outline
Week 1: Introduction to DBMS, data models, three-schema architecture
Week 2-3: ER modelling, ER to relational mapping
Week 4: Relational algebra and calculus
Week 5-6: SQL: DDL, DML, joins, subqueries, views
Week 7: Functional dependencies and normalisation (1NF-BCNF)
Week 8: Mid-term
Week 9: Storage and file organisation
Week 10: Indexing: B+ trees, hashing
Week 11: Query processing and optimisation
Week 12: Transactions, ACID, concurrency control
Week 13: Recovery
Grading: attendance 10%, quizzes 20%, mid 20%, final 50%. Textbook: Silberschatz et al.
"""


async def run(model: str) -> None:
    s = get_settings()
    prov = OpenAICompatibleProvider(base_url=s.llm_base_url, api_key=s.llm_api_key or "x", model=model, embed_model=s.embed_model)
    for name, system, user, schema in (
        ("questions", P.EXTRACT_QUESTIONS_SYSTEM, P.EXTRACT_QUESTIONS_USER.format(document=wrap_untrusted(PAPER, "paper")), ExtractedQuestions),
        ("syllabus", P.EXTRACT_SYLLABUS_SYSTEM, P.EXTRACT_SYLLABUS_USER.format(document=wrap_untrusted(SYLLABUS, "syllabus")), ExtractedTopics),
    ):
        t = time.perf_counter()
        res = await structured_call(purpose=f"extract_{name}", usage_purpose=UsagePurpose.extraction, system=system, user=user, schema=schema, ctx=CallContext(), provider=prov)
        dt = time.perf_counter() - t
        n = len(getattr(res.value, "questions", getattr(res.value, "topics", []))) if res.value else 0
        print(f"{model:10s} {name:9s} {dt:6.1f}s attempts={res.attempts} mode={res.response_mode} items={n} err={res.error} warn={res.warnings}")
    await prov.aclose()


async def main() -> None:
    for m in sys.argv[1:] or ["fast", "auto"]:
        await run(m)


asyncio.run(main())
