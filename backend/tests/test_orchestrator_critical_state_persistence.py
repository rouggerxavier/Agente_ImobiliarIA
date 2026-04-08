from unittest.mock import patch

from sqlalchemy import create_engine

from agent import controller as controller_module
from agent import llm as llm_module
from agent import rules as rules_module
from agent.state import store as legacy_store
from application.conversation_orchestrator import (
    ConversationOrchestrator,
    MessageInput,
    OrchestratorGraphState,
)
from domain.enums import Channel
from infrastructure.persistence import json_file
from infrastructure.persistence.session_state import SqlSessionStateRepository


class _StubAgent:
    def decide(self, message, state, neighborhoods=None, correlation_id=None):
        return (
            {
                "intent": None,
                "criteria": {},
                "extracted_updates": {},
                "handoff": {"should": False},
                "plan": {"action": "ASK", "message": ""},
            },
            False,
        )


def _build_orchestrator(tmp_path, monkeypatch):
    json_store = tmp_path / "json_store"
    state_db = tmp_path / "state_store.db"

    monkeypatch.setattr(json_file, "STORE_DIR", json_store)
    json_store.mkdir(parents=True, exist_ok=True)
    json_file._FILE_LOCKS.clear()
    monkeypatch.setattr(json_file, "load_properties", lambda: [])
    monkeypatch.setattr(json_file, "load_brokers", lambda path="data/agents.json": [])

    monkeypatch.setattr(llm_module, "USE_LLM", False, raising=False)
    monkeypatch.setattr(llm_module, "TRIAGE_ONLY", True, raising=False)
    monkeypatch.setattr(rules_module, "TRIAGE_ONLY", True, raising=False)
    monkeypatch.setattr(controller_module, "TRIAGE_ONLY", True, raising=False)
    monkeypatch.setattr(controller_module, "get_agent", lambda: _StubAgent())

    repos = json_file.create_persistent_repos()
    state_repo = SqlSessionStateRepository(engine=create_engine(f"sqlite:///{state_db}"))
    orchestrator = ConversationOrchestrator(
        lead_repo=repos["leads"],
        conversation_repo=repos["conversations"],
        message_repo=repos["messages"],
        decision_log_repo=repos["decision_logs"],
        event_repo=repos["events"],
        checkpoint_store=repos["checkpoints"],
        session_state_repo=state_repo,
    )
    return orchestrator, repos


def _send(orchestrator: ConversationOrchestrator, session_id: str, text: str) -> dict:
    return orchestrator.process_legacy_payload(
        MessageInput(
            session_id=session_id,
            message_text=text,
            channel=Channel.WEB,
        )
    )


def _asks_for_name(reply: str) -> bool:
    normalized = (reply or "").lower()
    return ("como posso te chamar" in normalized) or ("seu nome" in normalized)


def _rehydrate(orchestrator: ConversationOrchestrator, repos, session_id: str):
    lead = repos["leads"].get_by_session(session_id)
    assert lead is not None
    conversation = repos["conversations"].get_active_by_lead(lead.id)
    assert conversation is not None
    graph_state = OrchestratorGraphState(
        trace_id="trace-critical-state",
        lead_id=lead.id,
        conversation_id=conversation.id,
        channel=Channel.WEB,
        message_input=MessageInput(session_id=session_id, message_text="probe", channel=Channel.WEB),
    )
    return orchestrator._rehydrate_legacy_state(lead, conversation, graph_state)


def test_restart_preserves_pending_name_phone_and_intent_stage(tmp_path, monkeypatch):
    session_id = "critical_restart_resume"
    legacy_store.reset(session_id)
    orchestrator, repos = _build_orchestrator(tmp_path, monkeypatch)

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        _send(orchestrator, session_id, "boa noite")

    state = legacy_store.get(session_id)
    state.lead_profile["name"] = "Rougger"
    state.lead_profile["phone"] = "83999990000"
    state.intent_stage = "ready_to_visit"
    state.pending_field = "budget"
    state.last_question_key = "budget"
    state.field_ask_count["budget"] = 2
    if "budget" not in state.asked_questions:
        state.asked_questions.append("budget")

    lead = repos["leads"].get_by_session(session_id)
    assert lead is not None
    conversation = repos["conversations"].get_active_by_lead(lead.id)
    assert conversation is not None
    orchestrator._persist_critical_state_snapshot(
        session_id=session_id,
        legacy_state=state,
        lead_id=lead.id,
        conversation_id=conversation.id,
        trace_id="trace-manual-persist",
    )

    legacy_store.reset(session_id)
    resumed_orchestrator, resumed_repos = _build_orchestrator(tmp_path, monkeypatch)
    resumed_state = _rehydrate(resumed_orchestrator, resumed_repos, session_id)

    assert resumed_state.lead_profile["name"] == "Rougger"
    assert resumed_state.lead_profile["phone"] == "83999990000"
    assert resumed_state.intent_stage == "ready_to_visit"
    assert resumed_state.pending_field == "budget"
    assert resumed_state.last_question_key == "budget"
    assert resumed_state.field_ask_count.get("budget") == 2


def test_rehydrate_merge_runtime_wins_over_persisted_snapshot(tmp_path, monkeypatch):
    session_id = "critical_runtime_precedence"
    legacy_store.reset(session_id)
    orchestrator, repos = _build_orchestrator(tmp_path, monkeypatch)

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        _send(orchestrator, session_id, "oi")

    persisted_state = legacy_store.get(session_id)
    persisted_state.set_criterion("city", "Joao Pessoa", status="confirmed", source="persisted")
    lead = repos["leads"].get_by_session(session_id)
    assert lead is not None
    conversation = repos["conversations"].get_active_by_lead(lead.id)
    assert conversation is not None
    orchestrator._persist_critical_state_snapshot(
        session_id=session_id,
        legacy_state=persisted_state,
        lead_id=lead.id,
        conversation_id=conversation.id,
        trace_id="trace-persisted-city",
    )

    runtime_state = legacy_store.get(session_id)
    runtime_state.set_criterion("city", "Cabedelo", status="confirmed", source="runtime")

    rehydrated = _rehydrate(orchestrator, repos, session_id)
    assert rehydrated.criteria.city == "Cabedelo"


def test_restart_does_not_lose_pending_question_context(tmp_path, monkeypatch):
    session_id = "critical_pending_after_restart"
    legacy_store.reset(session_id)
    orchestrator, _ = _build_orchestrator(tmp_path, monkeypatch)

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        first = _send(orchestrator, session_id, "boa noite")

    assert _asks_for_name(first["reply"])

    legacy_store.reset(session_id)
    resumed_orchestrator, resumed_repos = _build_orchestrator(tmp_path, monkeypatch)
    resumed_state = _rehydrate(resumed_orchestrator, resumed_repos, session_id)

    assert resumed_state.last_question_key == "lead_name"
    assert resumed_state.pending_field == "lead_name"


def test_handoff_and_completed_flags_survive_restart(tmp_path, monkeypatch):
    session_id = "critical_handoff_resume"
    legacy_store.reset(session_id)
    orchestrator, repos = _build_orchestrator(tmp_path, monkeypatch)

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        _send(orchestrator, session_id, "oi")

    state = legacy_store.get(session_id)
    state.human_handoff = True
    state.completed = True

    lead = repos["leads"].get_by_session(session_id)
    assert lead is not None
    conversation = repos["conversations"].get_active_by_lead(lead.id)
    assert conversation is not None
    orchestrator._persist_critical_state_snapshot(
        session_id=session_id,
        legacy_state=state,
        lead_id=lead.id,
        conversation_id=conversation.id,
        trace_id="trace-handoff",
    )

    legacy_store.reset(session_id)
    resumed_orchestrator, resumed_repos = _build_orchestrator(tmp_path, monkeypatch)
    resumed_state = _rehydrate(resumed_orchestrator, resumed_repos, session_id)

    assert resumed_state.human_handoff is True
    assert resumed_state.completed is True
