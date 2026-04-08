from __future__ import annotations

from typing import Callable, Dict, Any

from ..contracts import OrchestratorRequest, SubagentResult


class LegacyTriageSubagent:
    name = "legacy_triage_subagent"

    def __init__(self, legacy_handler: Callable[[str, str, str | None, str | None], Dict[str, Any]]):
        self._legacy_handler = legacy_handler

    def run(self, request: OrchestratorRequest) -> SubagentResult:
        try:
            payload = self._legacy_handler(
                request.session_id,
                request.message,
                name=request.name,
                correlation_id=request.correlation_id,
            )
            return SubagentResult(payload=payload, handled=True, reason="legacy_triage")
        except Exception as exc:
            return SubagentResult(
                payload={"reply": "Desculpe, nao consegui processar agora. Tente novamente em instantes."},
                handled=False,
                reason=f"legacy_triage_failed:{exc}",
            )

