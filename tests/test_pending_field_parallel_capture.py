from __future__ import annotations

from unittest.mock import MagicMock, patch

from agent.controller import handle_message
from agent.presenter import build_summary_payload
from agent.state import SessionState, store


def _mock_decision() -> dict:
    return {
        "intent": None,
        "criteria": {},
        "extracted_updates": {},
        "handoff": {"should": False},
        "plan": {"action": "ASK", "message": ""},
    }


def _prime_buy_session_for_quality_gate(session_id: str) -> SessionState:
    state = store.get(session_id)
    state.intent = "comprar"
    state.set_triage_field("city", "Joao Pessoa", status="confirmed", source="user")
    state.set_triage_field("neighborhood", "Cabo Branco", status="confirmed", source="user")
    state.set_triage_field("property_type", "apartamento", status="confirmed", source="user")
    state.set_triage_field("bedrooms", 3, status="confirmed", source="user")
    state.set_triage_field("suites", 2, status="confirmed", source="user")
    state.set_triage_field("bathrooms_min", 3, status="confirmed", source="user")
    state.set_triage_field("parking", 2, status="confirmed", source="user")
    state.set_triage_field("budget_min", 700000, status="confirmed", source="user")
    state.set_triage_field("budget", 1000000, status="confirmed", source="user")
    state.set_triage_field("timeline", "30d", status="confirmed", source="user")
    state.set_triage_field("micro_location", "beira-mar", status="confirmed", source="user")
    state.set_triage_field("leisure_required", "yes", status="confirmed", source="user")
    return state


def test_reasks_pending_field_and_captures_short_term_preference() -> None:
    session_id = "test_pending_field_parallel_capture"
    state = _prime_buy_session_for_quality_gate(session_id)
    state.pending_field = "condo_max"
    state.last_question_key = "condo_max"
    state.field_ask_count["condo_max"] = 1
    state.asked_questions.append("condo_max")
    state.quality_gate_turns = 1

    with patch("agent.tools.get_neighborhoods", return_value=["Cabo Branco", "Manaira", "Bessa"]):
        with patch("agent.controller.get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.decide.return_value = (_mock_decision(), False)
            mock_get_agent.return_value = mock_agent

            result = handle_message(
                session_id=session_id,
                message="eu quero que o predio permita locacao por temporada",
                name="Teste",
            )

    reply_low = result["reply"].lower()
    assert "temporada" in reply_low
    assert "teto de" in reply_low or "mensal" in reply_low

    updated = store.get(session_id)
    assert updated.triage_fields.get("allows_short_term_rental", {}).get("value") == "yes"
    assert updated.pending_field == "condo_max"
    assert updated.field_ask_count.get("condo_max") == 2
    assert updated.quality_gate_turns == 1

    store.reset(session_id)


def test_summary_includes_short_term_rental_preference() -> None:
    state = SessionState(session_id="test_summary_short_term")
    state.lead_profile["name"] = "Rougger"
    state.intent = "comprar"
    state.set_triage_field("city", "Joao Pessoa", status="confirmed", source="user")
    state.set_triage_field("neighborhood", "Cabo Branco", status="confirmed", source="user")
    state.set_triage_field("property_type", "apartamento", status="confirmed", source="user")
    state.set_triage_field("bedrooms", 3, status="confirmed", source="user")
    state.set_triage_field("parking", 2, status="confirmed", source="user")
    state.set_triage_field("budget", 1000000, status="confirmed", source="user")
    state.set_triage_field("timeline", "30d", status="confirmed", source="user")
    state.set_triage_field("micro_location", "beira-mar", status="confirmed", source="user")
    state.set_triage_field("allows_short_term_rental", "yes", status="confirmed", source="user")

    summary = build_summary_payload(state, assigned_agent={"name": "Joao Silva"})
    assert "temporada" in summary["text"].lower()
    assert "permit" in summary["text"].lower()


def test_summary_includes_payment_type_and_condo_max() -> None:
    """Testa que payment_type e condo_max aparecem no resumo."""
    state = SessionState(session_id="test_summary_payment_condo")
    state.lead_profile["name"] = "Maria"
    state.intent = "comprar"
    state.set_triage_field("city", "Joao Pessoa", status="confirmed", source="user")
    state.set_triage_field("neighborhood", "Manaira", status="confirmed", source="user")
    state.set_triage_field("property_type", "apartamento", status="confirmed", source="user")
    state.set_triage_field("bedrooms", 3, status="confirmed", source="user")
    state.set_triage_field("parking", 1, status="confirmed", source="user")
    state.set_triage_field("budget", 800000, status="confirmed", source="user")
    state.set_triage_field("timeline", "3m", status="confirmed", source="user")
    state.set_triage_field("condo_max", 1500, status="confirmed", source="user")
    state.set_triage_field("payment_type", "financiamento", status="confirmed", source="user")

    summary = build_summary_payload(state, assigned_agent={"name": "Joao Silva"})
    text = summary["text"].lower()
    assert "1.500" in text or "1500" in text, f"condo_max não aparece no resumo: {summary['text']}"
    assert "financiamento" in text, f"payment_type não aparece no resumo: {summary['text']}"


def test_quality_gate_reasks_unanswered_gap() -> None:
    """Quando o usuário desvia do gap do quality gate, o gap deve ser re-perguntado."""
    session_id = "test_qg_reask_unanswered"
    state = _prime_buy_session_for_quality_gate(session_id)
    state.pending_field = "condo_max"
    state.last_question_key = "condo_max"
    state._quality_gate_pending_field = "condo_max"
    state.field_ask_count["condo_max"] = 1
    state.asked_questions.append("condo_max")
    state.quality_gate_turns = 0  # Ainda não contou como turn efetivo

    with patch("agent.tools.get_neighborhoods", return_value=["Cabo Branco", "Manaira"]):
        with patch("agent.controller.get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.decide.return_value = (_mock_decision(), False)
            mock_get_agent.return_value = mock_agent

            # Responde com info paralela em vez de responder condo_max
            result = handle_message(
                session_id=session_id,
                message="eu quero que o predio permita locacao por temporada",
                name="Teste",
            )

    updated = store.get(session_id)
    # allows_short_term_rental deve ter sido capturado
    assert updated.criteria.allows_short_term_rental == "yes"
    # quality_gate_turns NÃO deve ter incrementado (gap não foi respondido)
    assert updated.quality_gate_turns == 0, f"quality_gate_turns={updated.quality_gate_turns}, deveria ser 0"
    # pending_field ainda é condo_max (re-perguntou)
    assert updated.pending_field == "condo_max"

    store.reset(session_id)


def test_quality_gate_increments_when_gap_answered() -> None:
    """Quando o gap é respondido, quality_gate_turns deve incrementar."""
    session_id = "test_qg_increment_answered"
    state = _prime_buy_session_for_quality_gate(session_id)
    state.pending_field = "condo_max"
    state.last_question_key = "condo_max"
    state._quality_gate_pending_field = "condo_max"
    state.field_ask_count["condo_max"] = 1
    state.asked_questions.append("condo_max")
    state.quality_gate_turns = 0

    with patch("agent.tools.get_neighborhoods", return_value=["Cabo Branco", "Manaira"]):
        with patch("agent.controller.get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.decide.return_value = (_mock_decision(), False)
            mock_get_agent.return_value = mock_agent

            # Responde o condo_max
            result = handle_message(
                session_id=session_id,
                message="1500 reais",
                name="Teste",
            )

    updated = store.get(session_id)
    # condo_max deve ter sido preenchido
    assert updated.criteria.condo_max == 1500, f"condo_max={updated.criteria.condo_max}"
    # quality_gate_turns DEVE ter incrementado (gap foi respondido)
    assert updated.quality_gate_turns == 1, f"quality_gate_turns={updated.quality_gate_turns}, deveria ser 1"

    store.reset(session_id)


def test_payment_type_extraction() -> None:
    """Testa que financiamento é capturado pelo extractor."""
    from agent.extractor import extract_criteria
    result = extract_criteria("financiamento", [])
    assert result.get("payment_type") == "financiamento"

    result2 = extract_criteria("quero pagar à vista", [])
    assert result2.get("payment_type") == "a_vista"

    result3 = extract_criteria("vou usar o FGTS", [])
    assert result3.get("payment_type") == "fgts"
