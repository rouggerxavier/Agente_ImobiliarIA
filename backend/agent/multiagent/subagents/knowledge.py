from __future__ import annotations

from ..contracts import OrchestratorRequest, SubagentResult
from ..skills import KnowledgeLookupSkill, SkillContext


class KnowledgeSubagent:
    name = "knowledge_subagent"

    def __init__(self) -> None:
        self._skill = KnowledgeLookupSkill()

    def run(self, request: OrchestratorRequest) -> SubagentResult:
        result = self._skill.run(
            SkillContext(
                session_id=request.session_id,
                message=request.message,
                correlation_id=request.correlation_id,
            )
        )

        if not result.success:
            return SubagentResult(
                payload={
                    "reply": "Nao consegui responder com base na base de conhecimento. Vou seguir com a triagem padrao.",
                    "knowledge_error": result.error,
                },
                handled=False,
                reason=result.error or "knowledge_skill_failed",
                requires_handoff=True,
            )

        answer = result.data.get("answer") or "Encontrei informacoes relevantes e posso detalhar melhor se quiser."
        payload = {
            "reply": answer,
            "knowledge": {
                "domain": result.data.get("domain"),
                "topic": result.data.get("topic"),
                "sources": result.data.get("sources") or [],
            },
        }
        return SubagentResult(payload=payload, handled=True, reason="knowledge_answer")

