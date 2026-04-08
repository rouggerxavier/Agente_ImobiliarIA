from unittest.mock import patch

from agent import controller as controller_module
from agent import llm as llm_module
from agent import rules as rules_module
from agent.state import store as legacy_store
from application.conversation_orchestrator import (
    ConversationOrchestrator,
    MessageInput,
    OrchestratorGraphState,
)
from domain.enums import Channel, LeadStatus
from infrastructure.persistence import json_file


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
    monkeypatch.setattr(json_file, "STORE_DIR", tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    json_file._FILE_LOCKS.clear()
    monkeypatch.setattr(json_file, "load_properties", lambda: [])
    monkeypatch.setattr(json_file, "load_brokers", lambda path="data/agents.json": [])

    monkeypatch.setattr(llm_module, "USE_LLM", False, raising=False)
    monkeypatch.setattr(llm_module, "TRIAGE_ONLY", True, raising=False)
    monkeypatch.setattr(rules_module, "TRIAGE_ONLY", True, raising=False)
    monkeypatch.setattr(controller_module, "TRIAGE_ONLY", True, raising=False)
    monkeypatch.setattr(controller_module, "get_agent", lambda: _StubAgent())

    repos = json_file.create_persistent_repos()
    orchestrator = ConversationOrchestrator(
        lead_repo=repos["leads"],
        conversation_repo=repos["conversations"],
        message_repo=repos["messages"],
        decision_log_repo=repos["decision_logs"],
        event_repo=repos["events"],
        checkpoint_store=repos["checkpoints"],
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


def _rehydrate(orchestrator: ConversationOrchestrator, repos, session_id: str):
    lead = repos["leads"].get_by_session(session_id)
    assert lead is not None
    conversation = repos["conversations"].get_active_by_lead(lead.id)
    assert conversation is not None
    graph_state = OrchestratorGraphState(
        trace_id="trace-bridge-test",
        lead_id=lead.id,
        conversation_id=conversation.id,
        channel=Channel.WEB,
        message_input=MessageInput(session_id=session_id, message_text="rehydrate_probe", channel=Channel.WEB),
    )
    return orchestrator._rehydrate_legacy_state(lead, conversation, graph_state)


def test_multiple_messages_same_session_preserve_legacy_runtime_state(tmp_path, monkeypatch):
    orchestrator, _ = _build_orchestrator(tmp_path, monkeypatch)
    session_id = "bridge_no_reset"
    legacy_store.reset(session_id)

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        _send(orchestrator, session_id, "boa noite")
        state = legacy_store.get(session_id)
        state.engagement_notes.append("sentinel_runtime")
        state.pending_field = "budget"
        state.last_question_key = "budget"
        if "budget" not in state.asked_questions:
            state.asked_questions.append("budget")

        _send(orchestrator, session_id, "rougger")

    state_after = legacy_store.get(session_id)
    assert "sentinel_runtime" in state_after.engagement_notes
    assert state_after.lead_profile.get("name") == "Rougger"


def test_rehydrate_keeps_valid_pending_and_last_question(tmp_path, monkeypatch):
    orchestrator, repos = _build_orchestrator(tmp_path, monkeypatch)
    session_id = "bridge_keep_pending"
    legacy_store.reset(session_id)

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        _send(orchestrator, session_id, "boa noite")

    state = legacy_store.get(session_id)
    state.pending_field = "budget"
    state.last_question_key = "budget"
    if "budget" not in state.asked_questions:
        state.asked_questions.append("budget")

    rehydrated = _rehydrate(orchestrator, repos, session_id)
    assert rehydrated.pending_field == "budget"
    assert rehydrated.last_question_key == "budget"
    assert "budget" in rehydrated.asked_questions


def test_rehydrate_non_destructive_conflict_resolution_prefers_legacy_runtime(tmp_path, monkeypatch):
    orchestrator, repos = _build_orchestrator(tmp_path, monkeypatch)
    session_id = "bridge_conflict_city"
    legacy_store.reset(session_id)

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        _send(orchestrator, session_id, "oi")

    state = legacy_store.get(session_id)
    state.set_criterion("city", "Cabedelo", status="confirmed", source="user")

    lead = repos["leads"].get_by_session(session_id)
    assert lead is not None
    lead.preferences.city = "Joao Pessoa"
    repos["leads"].save(lead)

    rehydrated = _rehydrate(orchestrator, repos, session_id)
    assert rehydrated.criteria.city == "Cabedelo"


def test_saved_name_is_not_lost_on_rehydrate(tmp_path, monkeypatch):
    orchestrator, repos = _build_orchestrator(tmp_path, monkeypatch)
    session_id = "bridge_keep_name"
    legacy_store.reset(session_id)

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        _send(orchestrator, session_id, "oi")

    state = legacy_store.get(session_id)
    state.lead_profile["name"] = "Alice Runtime"
    lead = repos["leads"].get_by_session(session_id)
    assert lead is not None
    lead.name = "Alice Persisted"
    repos["leads"].save(lead)

    rehydrated = _rehydrate(orchestrator, repos, session_id)
    assert rehydrated.lead_profile["name"] == "Alice Runtime"


def test_saved_phone_is_not_lost_on_rehydrate(tmp_path, monkeypatch):
    orchestrator, repos = _build_orchestrator(tmp_path, monkeypatch)
    session_id = "bridge_keep_phone"
    legacy_store.reset(session_id)

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        _send(orchestrator, session_id, "oi")

    state = legacy_store.get(session_id)
    state.lead_profile["phone"] = "83999990000"
    lead = repos["leads"].get_by_session(session_id)
    assert lead is not None
    lead.phone = "83911112222"
    repos["leads"].save(lead)

    rehydrated = _rehydrate(orchestrator, repos, session_id)
    assert rehydrated.lead_profile["phone"] == "83999990000"


def test_pending_field_other_than_name_phone_remains_consistent(tmp_path, monkeypatch):
    orchestrator, repos = _build_orchestrator(tmp_path, monkeypatch)
    session_id = "bridge_pending_other_field"
    legacy_store.reset(session_id)

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        _send(orchestrator, session_id, "oi")

    state = legacy_store.get(session_id)
    state.pending_field = "neighborhood"
    state.last_question_key = "neighborhood"
    if "neighborhood" not in state.asked_questions:
        state.asked_questions.append("neighborhood")

    rehydrated = _rehydrate(orchestrator, repos, session_id)
    assert rehydrated.pending_field == "neighborhood"
    assert rehydrated.last_question_key == "neighborhood"


def test_resume_does_not_reopen_completed_triage(tmp_path, monkeypatch):
    orchestrator, repos = _build_orchestrator(tmp_path, monkeypatch)
    session_id = "bridge_resume_completed"
    legacy_store.reset(session_id)

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        _send(orchestrator, session_id, "boa noite")

    lead = repos["leads"].get_by_session(session_id)
    assert lead is not None
    lead.status = LeadStatus.QUALIFIED
    repos["leads"].save(lead)

    state = legacy_store.get(session_id)
    state.completed = False

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        resumed = _send(orchestrator, session_id, "oi de novo")

    reply_lower = resumed["reply"].lower()
    assert "perfil" in reply_lower and "registrado" in reply_lower
    assert resumed["state"]["completed"] is True
