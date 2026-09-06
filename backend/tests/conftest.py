from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

TEST_DB = Path(__file__).parent / f".test-{os.getpid()}.db"  # per-process: concurrent pytest runs must not share a file

os.environ.update(
    {
        "ENV": "test",
        "DATABASE_URL": f"sqlite+aiosqlite:///{TEST_DB}",
        "AUTH_MODE": "dev",
        "LLM_PROVIDER": "mock",
        "RATE_LIMIT_ENABLED": "false",
        "STORAGE_DIR": str(Path(__file__).parent / f".test_storage-{os.getpid()}"),
        "MAX_UPLOAD_MB": "1",
        "LLM_MAX_RETRIES": "1",
    }
)

from app.ai.client import set_provider  # noqa: E402
from app.ai.providers.mock import MockProvider  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db.models import Base  # noqa: E402
from app.db.session import get_engine, reset_engine  # noqa: E402
from app.extraction.service import wait_for_extractions  # noqa: E402
from app.main import create_app  # noqa: E402
from app.runs.orchestrator import orchestrator  # noqa: E402


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session", autouse=True)
async def _database():
    get_settings.cache_clear()
    reset_engine()
    if TEST_DB.exists():
        TEST_DB.unlink()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    from app.auth.service import sync_role_permissions
    from app.db.session import session_scope
    from app.demo.service import ensure_program_outcomes

    async with session_scope() as db:  # lifespan is not run by ASGITransport
        await ensure_program_outcomes(db)
        await sync_role_permissions(db)
    yield
    await engine.dispose()
    import shutil

    if TEST_DB.exists():
        TEST_DB.unlink()
    shutil.rmtree(Path(__file__).parent / f".test_storage-{os.getpid()}", ignore_errors=True)


@pytest.fixture(autouse=True)
def mock_provider() -> MockProvider:
    provider = MockProvider()
    set_provider(provider)
    yield provider
    provider.reset()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as c:
        yield c
    await orchestrator.wait_all()
    await wait_for_extractions()


def as_user(email: str) -> dict[str, str]:
    return {"X-Dev-User": email}


@pytest.fixture
def user_a() -> dict[str, str]:
    return as_user(f"a-{uuid.uuid4().hex[:8]}@test.edu")


@pytest.fixture
def user_b() -> dict[str, str]:
    return as_user(f"b-{uuid.uuid4().hex[:8]}@test.edu")


async def wait_until_done() -> None:
    await wait_for_extractions()
    await orchestrator.wait_all()


async def make_course(client: AsyncClient, headers: dict, code: str | None = None) -> dict:
    r = await client.post("/courses", json={"code": code or f"CSE {uuid.uuid4().int % 9000 + 1000}", "title": "Database Systems"}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


OUTCOMES = [
    {"code": "CO1", "text": "Explain fundamental database concepts, DBMS architecture and data independence.", "bloom_level": "understand", "weight": 15},
    {"code": "CO2", "text": "Design entity-relationship models and translate them into relational schemas.", "bloom_level": "apply", "weight": 20},
    {"code": "CO3", "text": "Write SQL queries including joins, aggregate functions, GROUP BY and HAVING.", "bloom_level": "apply", "weight": 20},
    {"code": "CO4", "text": "Analyse functional dependencies, candidate keys and normalise relations.", "bloom_level": "analyze", "weight": 20},
    {"code": "CO5", "text": "Evaluate transaction concurrency control and recovery techniques.", "bloom_level": "evaluate", "weight": 15},
    {"code": "CO6", "text": "Evaluate indexing and query optimisation strategies.", "bloom_level": "evaluate", "weight": 10},
]

DRAFT_PAPER = """Final Examination (DRAFT)
Total marks: 60
1(a) Define data independence and explain its two types with examples. [6]
1(b) List and describe the main responsibilities of a database administrator. [6]
2(a) Draw an ER diagram for an online course-registration system showing entities, attributes and relationships. [6]
2(b) Write an SQL query to list the names of the employees whose salary exceeds the average salary. [7]
3(a) Explain physical versus logical data independence with a suitable example. [6]
3(b) Given R(A,B,C,D,E) with F = {AB->C, C->D, D->E}, find the candidate keys and normalise to 3NF. [10]
4(a) Write an SQL query using GROUP BY and HAVING to find departments having more than five employees. [7]
4(b) Define a transaction and state the ACID properties of a transaction. [5]
5 Briefly explain the purpose of the database log file. [5]
"""

PAST_PAPER = """Mid Term Examination, Spring 2024
1(a) Distinguish between physical data independence and logical data independence with a suitable example for each. [5]
1(b) Explain the three-schema architecture of a DBMS and state the purpose of each level. [5]
2(a) Draw an ER diagram for a hospital management system containing at least four entities. [8]
3(a) Write an SQL query to list the names of the employees who earn more than the average salary. [7]
"""


async def upload_text(client: AsyncClient, headers: dict, course_id: str, *, kind: str, label: str, text: str, declared: float | None = None) -> dict:
    data = {"kind": kind, "label": label, "text": text}
    if declared is not None:
        data["declared_total_marks"] = str(declared)
    r = await client.post(f"/courses/{course_id}/artefacts", data=data, headers=headers)
    assert r.status_code == 202, r.text
    await wait_until_done()
    return (await client.get(f"/artefacts/{r.json()['id']}", headers=headers)).json()
