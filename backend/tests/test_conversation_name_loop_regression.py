import logging
from unittest.mock import patch

from agent import controller as controller_module
from agent import llm as llm_module
from agent import rules as rules_module
from agent.state import store as legacy_store
from application.conversation_orchestrator import ConversationOrchestrator, MessageInput
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


def _asks_for_name(reply: str) -> bool:
    normalized = (reply or "").lower()
    return ("como posso te chamar" in normalized) or ("seu nome" in normalized)


def test_boa_noite_then_single_word_name_advances(tmp_path, monkeypatch):
    orchestrator, repos = _build_orchestrator(tmp_path, monkeypatch)
    session_id = "sess_single_name"

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        first = _send(orchestrator, session_id, "boa noite")
        assert _asks_for_name(first["reply"])

        second = _send(orchestrator, session_id, "rougger")
        assert second["state"]["lead_profile"]["name"] == "Rougger"
        assert not _asks_for_name(second["reply"])
        assert second["state"]["last_question_key"] != "lead_name"

        lead = repos["leads"].get_by_session(session_id)
        assert lead is not None
        assert lead.name == "Rougger"


def test_prefixed_name_is_extracted_and_flow_advances(tmp_path, monkeypatch):
    orchestrator, _ = _build_orchestrator(tmp_path, monkeypatch)
    session_id = "sess_prefixed_name"

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        _send(orchestrator, session_id, "boa noite")
        second = _send(orchestrator, session_id, "meu nome é rouger")

    assert second["state"]["lead_profile"]["name"] == "Rouger"
    assert not _asks_for_name(second["reply"])
    assert second["state"]["last_question_key"] != "lead_name"


def test_resume_after_name_collection_does_not_reask_name(tmp_path, monkeypatch):
    orchestrator, _ = _build_orchestrator(tmp_path, monkeypatch)
    session_id = "sess_resume_name"

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        _send(orchestrator, session_id, "boa noite")
        _send(orchestrator, session_id, "rougger")

        # Simula processo novo: limpa store legada em memória e recria orquestrador.
        legacy_store.reset(session_id)
        resumed_orchestrator, resumed_repos = _build_orchestrator(tmp_path, monkeypatch)
        resumed = _send(resumed_orchestrator, session_id, "quero comprar")

    assert resumed["state"]["lead_profile"]["name"] == "Rougger"
    assert not _asks_for_name(resumed["reply"])
    lead = resumed_repos["leads"].get_by_session(session_id)
    assert lead is not None
    assert lead.name == "Rougger"


def test_rehydrate_with_existing_name_keeps_value(tmp_path, monkeypatch):
    orchestrator, repos = _build_orchestrator(tmp_path, monkeypatch)
    session_id = "sess_rehydrate_name"

    with patch("agent.tools.get_neighborhoods", return_value=["Manaira"]):
        _send(orchestrator, session_id, "boa noite")
        _send(orchestrator, session_id, "rougger")
        third = _send(orchestrator, session_id, "ok")

    assert third["state"]["lead_profile"]["name"] == "Rougger"
    lead = repos["leads"].get_by_session(session_id)
    assert lead is not None
    assert lead.name == "Rougger"


def test_corrupted_json_is_logged_and_quarantined(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(json_file, "STORE_DIR", tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    json_file._FILE_LOCKS.clear()

    corrupted = tmp_path / "leads.json"
    corrupted.write_text("{invalid json", encoding="utf-8")

    repo = json_file.JsonLeadRepository()
    with caplog.at_level(logging.ERROR):
        leads = repo.list_by_status(LeadStatus.NEW)

    assert leads == []
    assert any("json_store_load_error" in record.message for record in caplog.records)
    quarantined = list(tmp_path.glob("leads.json.corrupted-*"))
    assert quarantined, "Arquivo corrompido deve ser movido para quarentena"
