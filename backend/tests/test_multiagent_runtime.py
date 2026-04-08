from __future__ import annotations

from agent import runtime
from agent.multiagent.contracts import OrchestratorDecision, OrchestratorResult, OrchestratorRoute


def test_runtime_uses_legacy_when_multiagent_disabled(monkeypatch):
    monkeypatch.setenv("MULTIAGENT_ENABLED", "false")

    def _fake_legacy(session_id, message, name=None, correlation_id=None):
        return {"reply": "legacy_path", "state": {"session_id": session_id}}

    monkeypatch.setattr(runtime, "legacy_handle_message", _fake_legacy)

    result = runtime.handle_message("sid-1", "ola")
    assert result["reply"] == "legacy_path"


def test_runtime_fallbacks_to_legacy_if_orchestrator_crashes(monkeypatch):
    monkeypatch.setenv("MULTIAGENT_ENABLED", "true")

    def _fake_legacy(session_id, message, name=None, correlation_id=None):
        return {"reply": "legacy_fallback", "state": {"session_id": session_id}}

    class _BoomOrchestrator:
        def __init__(self, *args, **kwargs):
            pass

        def process(self, request):
            raise RuntimeError("boom")

    monkeypatch.setattr(runtime, "legacy_handle_message", _fake_legacy)
    monkeypatch.setattr(runtime, "MultiAgentOrchestrator", _BoomOrchestrator)

    result = runtime.handle_message("sid-2", "catalogo")
    assert result["reply"] == "legacy_fallback"


def test_runtime_exposes_orchestration_metadata(monkeypatch):
    monkeypatch.setenv("MULTIAGENT_ENABLED", "true")

    def _fake_legacy(session_id, message, name=None, correlation_id=None):
        return {"reply": "legacy", "state": {"session_id": session_id}}

    class _StubOrchestrator:
        def __init__(self, *args, **kwargs):
            pass

        def process(self, request):
            return OrchestratorResult(
                payload={"reply": "from_orchestrator"},
                decision=OrchestratorDecision(
                    route=OrchestratorRoute.KNOWLEDGE,
                    reason="stub",
                    delegated_to="knowledge_subagent",
                    used_openai_sdk_router=False,
                ),
                handoffs=[],
                tool_calls=[],
            )

    monkeypatch.setattr(runtime, "legacy_handle_message", _fake_legacy)
    monkeypatch.setattr(runtime, "MultiAgentOrchestrator", _StubOrchestrator)

    result = runtime.handle_message("sid-3", "duvida sobre itbi?")
    assert result["reply"] == "from_orchestrator"
    assert result["orchestration"]["route"] == "knowledge"

