from __future__ import annotations

from agent.multiagent.config import MultiAgentConfig
from agent.multiagent.contracts import OrchestratorRequest, OrchestratorRoute, SubagentResult
from agent.multiagent.orchestrator import MultiAgentOrchestrator


def _legacy_handler(session_id: str, message: str, name: str | None = None, correlation_id: str | None = None):
    return {
        "reply": f"legacy:{message}",
        "state": {"session_id": session_id},
    }


def _config() -> MultiAgentConfig:
    return MultiAgentConfig(
        enabled=True,
        openai_sdk_router_enabled=False,
        openai_sdk_model="gpt-4.1-mini",
        trace_path="data/test_multiagent_trace.jsonl",
        trace_enabled=False,
        allow_sensitive_actions=False,
    )


def test_orchestrator_routes_to_catalog_for_catalog_hint():
    orchestrator = MultiAgentOrchestrator(config=_config(), legacy_handler=_legacy_handler)

    req = OrchestratorRequest(session_id="s1", message="quero ver o catalogo de imoveis em Manaira")
    result = orchestrator.process(req)

    assert result.decision.route == OrchestratorRoute.CATALOG
    assert "reply" in result.payload


def test_orchestrator_handoff_to_legacy_on_catalog_failure():
    orchestrator = MultiAgentOrchestrator(config=_config(), legacy_handler=_legacy_handler)

    class _FailingCatalog:
        name = "catalog_subagent"

        def run(self, request: OrchestratorRequest) -> SubagentResult:
            return SubagentResult(
                payload={"reply": "catalog failed"},
                handled=False,
                reason="catalog_failed",
                requires_handoff=True,
            )

    orchestrator._catalog = _FailingCatalog()  # type: ignore[attr-defined]

    req = OrchestratorRequest(session_id="s1", message="catalogo de imoveis")
    result = orchestrator.process(req)

    assert result.decision.route == OrchestratorRoute.CATALOG
    assert result.payload["reply"].startswith("legacy:")
    assert len(result.handoffs) == 1
    assert result.handoffs[0].target == "legacy_triage_subagent"


def test_orchestrator_blocks_sensitive_message_by_default():
    orchestrator = MultiAgentOrchestrator(config=_config(), legacy_handler=_legacy_handler)

    req = OrchestratorRequest(session_id="s1", message="por favor, drop table leads")
    result = orchestrator.process(req)

    assert result.decision.route == OrchestratorRoute.SAFE_FALLBACK
    assert "seguranca" in result.payload["reply"].lower()

