from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ArtefactKind, ExtractionStatus, RunStatus
from app.db.models import Artefact, Question, QuestionCoMap, QuestionTopicMap, Run, RunInput, Topic


class ArtefactRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, artefact_id: uuid.UUID) -> Artefact | None:
        return await self.db.get(Artefact, artefact_id)

    async def list(
        self, course_id: uuid.UUID, *, kind: ArtefactKind | None, status: ExtractionStatus | None
    ) -> list[Artefact]:
        stmt = select(Artefact).where(Artefact.course_id == course_id)
        if kind:
            stmt = stmt.where(Artefact.kind == kind)
        if status:
            stmt = stmt.where(Artefact.status == status)
        stmt = stmt.order_by(Artefact.created_at.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def counts(self, artefact_id: uuid.UUID) -> dict[str, int]:
        q = (await self.db.execute(select(func.count()).where(Question.artefact_id == artefact_id))).scalar_one()
        t = (await self.db.execute(select(func.count()).where(Topic.source_artefact_id == artefact_id))).scalar_one()
        return {"questions": q, "topics": t}

    async def questions(self, artefact_id: uuid.UUID) -> list[Question]:
        stmt = (
            select(Question)
            .where(Question.artefact_id == artefact_id)
            .options(selectinload(Question.co_links), selectinload(Question.topic_links))
            .order_by(Question.sort_order, Question.number)
            .execution_options(populate_existing=True)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def delete_questions(self, ids: list[uuid.UUID]) -> None:
        if ids:
            await self.db.execute(delete(QuestionCoMap).where(QuestionCoMap.question_id.in_(ids)))
            await self.db.execute(delete(QuestionTopicMap).where(QuestionTopicMap.question_id.in_(ids)))
            await self.db.execute(delete(Question).where(Question.id.in_(ids)))

    async def replace_co_map(self, question_ids: list[uuid.UUID], rows: list[QuestionCoMap]) -> None:
        if question_ids:
            await self.db.execute(delete(QuestionCoMap).where(QuestionCoMap.question_id.in_(question_ids)))
        self.db.add_all(rows)

    async def referenced_by_runs(self, artefact_id: uuid.UUID, *, completed_only: bool) -> int:
        stmt = select(func.count()).select_from(RunInput).where(RunInput.artefact_id == artefact_id)
        if completed_only:
            stmt = stmt.join(Run, Run.id == RunInput.run_id).where(
                Run.status.in_([RunStatus.completed, RunStatus.partial])
            )
        return (await self.db.execute(stmt)).scalar_one()

    async def delete_run_inputs(self, artefact_id: uuid.UUID) -> None:
        await self.db.execute(delete(RunInput).where(RunInput.artefact_id == artefact_id))

    async def clear_children(self, artefact: Artefact) -> None:
        ids = [q.id for q in await self.questions(artefact.id)]
        await self.delete_questions(ids)
        if artefact.kind == ArtefactKind.syllabus:
            topic_ids = list(
                (await self.db.execute(select(Topic.id).where(Topic.source_artefact_id == artefact.id))).scalars()
            )
            if topic_ids:
                await self.db.execute(delete(QuestionTopicMap).where(QuestionTopicMap.topic_id.in_(topic_ids)))
                await self.db.execute(delete(Topic).where(Topic.id.in_(topic_ids)))
