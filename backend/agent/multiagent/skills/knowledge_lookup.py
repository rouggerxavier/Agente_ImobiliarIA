from __future__ import annotations

from agent.knowledge_base import answer_question
from agent.state import store

from .base import SkillContext, SkillResult


class KnowledgeLookupSkill:
    name = "knowledge_lookup"

    def run(self, context: SkillContext) -> SkillResult:
        try:
            state = store.get(context.session_id)
            city = state.criteria.city
            neighborhood = state.criteria.neighborhood
            result = answer_question(
                context.message,
                city=city,
                neighborhood=neighborhood,
                top_k=3,
            )
            if not result:
                return SkillResult(success=False, error="knowledge_not_found")
            return SkillResult(success=True, data=result)
        except Exception as exc:
            return SkillResult(success=False, error=f"knowledge_lookup_failed:{exc}")

