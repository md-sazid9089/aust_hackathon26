from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import CallContext, structured_call
from app.ai.guard import wrap_untrusted
from app.artefacts.service import ArtefactService
from app.assistant import prompts as P
from app.assistant import tools
from app.assistant.schemas import ActionOut, AssistantPlan, ChatMessage, ChatResponse
from app.courses.service import CourseService
from app.db.enums import UsagePurpose
from app.db.models import Profile
from app.errors import ApiError
from app.logging import get_logger
from app.runs.service import RunService

log = get_logger(__name__)

MAX_ROUNDS = 4
MAX_HISTORY = 12


class AssistantService:
    def __init__(self, db: AsyncSession, user: Profile) -> None:
        self.db = db
        self.user = user

    async def _context(self, current_course_id: uuid.UUID | None, attachment: tools.Attachment | None) -> dict[str, Any]:
        rows, _ = await CourseService(self.db, self.user).list(q=None, page=1, page_size=50, sort="created_at:desc")
        ctx: dict[str, Any] = {
            "user": {"name": self.user.full_name, "role": self.user.role.value},
            "courses": [{"id": str(c.id), "code": c.code, "title": c.title} for c in rows],
            "current_course": None,
            "attachment": {"filename": attachment.filename, "size_bytes": len(attachment.data)} if attachment else None,
        }
        if current_course_id and any(c.id == current_course_id for c in rows):
            arts = await ArtefactService(self.db, self.user).list(current_course_id, kind=None, status=None)
            runs, _ = await RunService(self.db, self.user).list_for_course(current_course_id, module=None, status=None, page=1, page_size=5)
            course = next(c for c in rows if c.id == current_course_id)
            ctx["current_course"] = {
                "id": str(course.id), "code": course.code, "title": course.title,
                "artefacts": [tools._artefact_brief(a) for a in arts],
                "recent_runs": [{"id": str(r.id), "module": r.module.value, "status": r.status.value} for r in runs],
            }
        return ctx

    async def chat(
        self,
        *,
        message: str,
        history: list[ChatMessage],
        current_course_id: uuid.UUID | None,
        attachment: tools.Attachment | None,
    ) -> ChatResponse:
        env = tools.ToolEnv(db=self.db, user=self.user, attachment=attachment, current_course_id=current_course_id)
        context = await self._context(current_course_id, attachment)
        history = history[-MAX_HISTORY:]
        history_text = "\n".join(f"{m.role}: {m.content[:1500]}" for m in history) or "(none)"
        system = P.PLAN_SYSTEM.format(tools=tools.catalogue())
        results: list[dict[str, Any]] = []
        actions: list[ActionOut] = []
        navigate: str | None = None
        model: str | None = None
        ctx = CallContext(user_id=self.user.id)

        for round_no in range(MAX_ROUNDS):
            final_round = round_no == MAX_ROUNDS - 1
            user_prompt = P.PLAN_USER.format(
                context=json.dumps(context, ensure_ascii=False),
                history=history_text,
                message=wrap_untrusted(message, "user_message", max_chars=6000),
                results=json.dumps(results, ensure_ascii=False, default=str)[:20_000] or "[]",
            )
            if final_round:
                user_prompt += "\nThis is the last round: return an empty tool_calls list and the final reply."
            res = await structured_call(
                purpose="assistant_plan",
                usage_purpose=UsagePurpose.assistant,
                system=system,
                user=user_prompt,
                schema=AssistantPlan,
                ctx=ctx,
                db=self.db,
                context={
                    "message": message, "history": [m.model_dump() for m in history], "app": context,
                    "results": results, "final_round": final_round, "tools": list(tools.TOOLS),
                },
            )
            model = res.model or model
            plan = res.value
            if plan is None:
                if actions:
                    return ChatResponse(reply=self._fallback_reply(actions), actions=actions, navigate=navigate, model=model)
                raise ApiError("ASSISTANT_UNAVAILABLE", 503, "The assistant could not produce a response", {"error": res.error})
            assert isinstance(plan, AssistantPlan)
            if not plan.tool_calls or final_round:
                reply = plan.reply.strip() or self._fallback_reply(actions)
                return ChatResponse(reply=reply, actions=actions, navigate=navigate, model=model)
            for call in plan.tool_calls[:6]:
                try:
                    raw_args = json.loads(call.arguments or "{}")
                    if not isinstance(raw_args, dict):
                        raw_args = {}
                except json.JSONDecodeError:
                    raw_args = {}
                result = await tools.execute(env, call.tool, raw_args)
                log.info("assistant.tool", tool=call.tool, ok=result.ok)
                actions.append(ActionOut(tool=call.tool, status="ok" if result.ok else "error", summary=result.summary, data=result.data or None))
                results.append({"tool": call.tool, "arguments": raw_args, "ok": result.ok, "summary": result.summary, "data": result.data})
                if result.navigate:
                    navigate = result.navigate
                if not result.ok:
                    break  # let the planner see the error before continuing
        return ChatResponse(reply=self._fallback_reply(actions), actions=actions, navigate=navigate, model=model)

    @staticmethod
    def _fallback_reply(actions: list[ActionOut]) -> str:
        if not actions:
            return "I could not work out what to do. Try: “list my courses”, “seed the demo course”, or attach a question paper and say “analyze this for CSE 3103”."
        return "\n".join(f"- {'✅' if a.status == 'ok' else '⚠️'} {a.summary}" for a in actions)
