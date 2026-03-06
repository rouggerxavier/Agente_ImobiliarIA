"""
Testes de cenário para os casos de uso críticos do agente imobiliário.

Cobre:
  Cenário 1 — "libera aluguel por temporada" NÃO muda intent
  Cenário 2 — Resposta curta preenche slot pendente (bathrooms)
  Cenário 3 — QA interrupt retorna ao funil com pending_slot
  Cenário 4 — JSON truncado não derruba o fluxo
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from agent.state import store, SessionState
from agent.controller import handle_message
from agent.extractor import extract_criteria
from agent import llm as llm_module
from agent import rules as rules_module
from agent import controller as controller_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _triage_patches():
    """Garante que estamos sempre em modo triagem."""
    return [
        patch.object(llm_module, "TRIAGE_ONLY", True),
        patch.object(rules_module, "TRIAGE_ONLY", True),
        patch.object(controller_module, "TRIAGE_ONLY", True),
    ]


def _no_llm():
    return patch.object(llm_module, "USE_LLM", False)


# ---------------------------------------------------------------------------
# Cenário 1: "libera aluguel por temporada" NÃO muda intent
# ---------------------------------------------------------------------------

class TestCenario1TemporadaNaoMudaIntent:

    def test_extractor_temporada_nao_seta_intent_alugar(self):
        """Extrator: 'aluguel por temporada' não deve setar intent=alugar."""
        msg = "quero comprar um apto que libera aluguel por temporada"
        result = extract_criteria(msg, [])
        assert result.get("intent") == "comprar", (
            f"Expected intent=comprar, got {result.get('intent')!r}"
        )
        assert result.get("allows_short_term_rental") == "yes", (
            f"Expected allows_short_term_rental=yes, got {result.get('allows_short_term_rental')!r}"
        )

    def test_extractor_airbnb_nao_muda_intent(self):
        """Extrator: menção ao Airbnb não muda intent."""
        msg = "procuro apartamento para investir, precisa aceitar Airbnb"
        result = extract_criteria(msg, [])
        assert result.get("intent") in {"comprar", None}, (
            f"Airbnb não deve forçar intent=alugar, got {result.get('intent')!r}"
        )
        assert result.get("allows_short_term_rental") == "yes"

    def test_extractor_temporada_sem_intent_preserva(self):
        """Quando só fala 'temporada', intent não é definido."""
        msg = "apto com lazer que libera locação por temporada"
        result = extract_criteria(msg, [])
        # Sem "comprar" nem "alugar" explícito — intent pode ser None
        assert result.get("intent") != "alugar", (
            "'locação por temporada' não deve forçar intent=alugar"
        )
        assert result.get("allows_short_term_rental") == "yes"
        assert result.get("leisure_required") == "yes"

    def test_fluxo_completo_temporada_nao_muda_intent(self):
        """
        Fluxo conversacional:
          U1: quero comprar  → intent=comprar setado
          U2: apto 2 quartos 1 suite que libera aluguel por temporada e tem área de lazer
          Assert: intent ainda=comprar, allows_short_term_rental=yes, leisure=yes, bedrooms=2, suites=1
        """
        sid = "cenario1_temporada_intent"
        store.reset(sid)
        p1, p2, p3 = _triage_patches()

        with _no_llm(), p1, p2, p3:
            handle_message(sid, "quero comprar")
            handle_message(
                sid,
                "apto 2 quartos 1 suite que libera aluguel por temporada e tem área de lazer"
            )

        state = store.get(sid)
        assert state.intent == "comprar", f"Intent should remain 'comprar', got {state.intent!r}"
        assert state.triage_fields.get("allows_short_term_rental", {}).get("value") == "yes", (
            "allows_short_term_rental should be 'yes'"
        )
        assert state.triage_fields.get("leisure_required", {}).get("value") == "yes", (
            "leisure_required should be 'yes'"
        )
        assert state.criteria.bedrooms == 2, f"bedrooms should be 2, got {state.criteria.bedrooms}"
        assert state.criteria.suites == 1, f"suites should be 1, got {state.criteria.suites}"

    def test_proxima_pergunta_nao_inclui_lazer_ja_confirmado(self):
        """
        Quando lazer já foi confirmado na mensagem anterior,
        a próxima pergunta não deve ser sobre lazer.
        """
        from agent.rules import missing_critical_fields, next_best_question_key

        sid = "cenario1_lazer_nao_repete"
        store.reset(sid)
        state = store.get(sid)

        # Setar estado com lazer já confirmado
        state.intent = "comprar"
        state.set_criterion("city", "Joao Pessoa", status="confirmed")
        state.set_criterion("neighborhood", "Manaira", status="confirmed")
        state.set_criterion("property_type", "apartamento", status="confirmed")
        state.set_criterion("bedrooms", 2, status="confirmed")
        state.set_criterion("suites", 1, status="confirmed")
        state.set_criterion("leisure_required", "yes", status="confirmed")

        missing = missing_critical_fields(state)
        next_key = next_best_question_key(state)

        assert "leisure_required" not in missing, (
            f"leisure_required não deveria estar em missing: {missing}"
        )
        assert next_key != "leisure_required", (
            f"next question não deveria ser leisure_required, got {next_key!r}"
        )


# ---------------------------------------------------------------------------
# Cenário 2: Resposta curta preenche slot pendente
# ---------------------------------------------------------------------------

class TestCenario2RespostaCurtaSlotPendente:

    def test_numero_preenche_bathrooms_pending(self):
        """Quando bot perguntou banheiros e usuário responde '2', deve setar bathrooms_min=2."""
        sid = "cenario2_bathrooms_short"
        store.reset(sid)
        state = store.get(sid)
        state.last_question_key = "bathrooms_min"
        state.pending_field = "bathrooms_min"
        store.save(state)

        p1, p2, p3 = _triage_patches()
        with _no_llm(), p1, p2, p3:
            handle_message(sid, "2")

        state = store.get(sid)
        bf = state.triage_fields.get("bathrooms_min", {})
        assert bf.get("value") == 2, (
            f"bathrooms_min should be 2 after short reply '2', got {bf.get('value')!r}"
        )
        assert bf.get("status") == "confirmed"

    def test_numero_preenche_suites_pending(self):
        """Quando bot perguntou suítes e usuário responde '1', deve setar suites=1."""
        sid = "cenario2_suites_short"
        store.reset(sid)
        state = store.get(sid)
        state.last_question_key = "suites"
        state.pending_field = "suites"
        store.save(state)

        p1, p2, p3 = _triage_patches()
        with _no_llm(), p1, p2, p3:
            handle_message(sid, "1")

        state = store.get(sid)
        sf = state.triage_fields.get("suites", {})
        assert sf.get("value") == 1, f"suites should be 1, got {sf.get('value')!r}"

    def test_sim_preenche_leisure_pending(self):
        """Quando bot perguntou lazer e usuário responde 'sim', deve setar leisure_required=yes."""
        sid = "cenario2_leisure_sim"
        store.reset(sid)
        state = store.get(sid)
        state.last_question_key = "leisure_required"
        state.pending_field = "leisure_required"
        store.save(state)

        p1, p2, p3 = _triage_patches()
        with _no_llm(), p1, p2, p3:
            handle_message(sid, "sim")

        state = store.get(sid)
        lf = state.triage_fields.get("leisure_required", {})
        assert lf.get("value") == "yes", f"leisure_required should be 'yes', got {lf.get('value')!r}"

    def test_nao_preenche_leisure_pending(self):
        """Quando bot perguntou lazer e usuário responde 'não', deve setar leisure_required=no."""
        sid = "cenario2_leisure_nao"
        store.reset(sid)
        state = store.get(sid)
        state.last_question_key = "leisure_required"
        state.pending_field = "leisure_required"
        store.save(state)

        p1, p2, p3 = _triage_patches()
        with _no_llm(), p1, p2, p3:
            handle_message(sid, "não")

        state = store.get(sid)
        lf = state.triage_fields.get("leisure_required", {})
        assert lf.get("value") == "no", f"leisure_required should be 'no', got {lf.get('value')!r}"


# ---------------------------------------------------------------------------
# Cenário 3: QA interrupt e retorno ao funil
# ---------------------------------------------------------------------------

class TestCenario3QAInterrupt:

    def _setup_mid_triage(self, sid: str):
        """Prepara sessão a meio do funil (intent + city setados, faltam outros)."""
        store.reset(sid)
        state = store.get(sid)
        state.intent = "comprar"
        state.set_criterion("city", "Joao Pessoa", status="confirmed")
        state.set_criterion("neighborhood", "Manaira", status="confirmed")
        state.set_criterion("property_type", "apartamento", status="confirmed")
        store.save(state)
        return state

    def test_pet_question_mid_triage_returns_to_funnel(self):
        """
        Usuário no meio do funil pergunta 'aceita pet?'.
        Bot deve responder E voltar perguntando próximo campo.
        """
        sid = "cenario3_pet_interrupt"
        self._setup_mid_triage(sid)

        p1, p2, p3 = _triage_patches()
        with _no_llm(), p1, p2, p3:
            resp = handle_message(sid, "aceita pet?")

        reply = resp["reply"].lower()
        # Deve mencionar pet na resposta
        assert "pet" in reply, f"Resposta não mencionou pet: {reply!r}"
        # Deve retornar ao funil (mencionar "pra eu te indicar" ou fazer uma pergunta)
        assert ("pra eu te indicar" in reply or "?" in reply), (
            f"Resposta deve incluir retorno ao funil: {reply!r}"
        )

        # pending_slot deve estar setado
        state = store.get(sid)
        assert state.pending_field is not None, "pending_field deve estar setado após QA interrupt"

    def test_qa_interrupt_sets_pending_slot(self):
        """Após QA interrupt, pending_slot deve ser o próximo campo do funil."""
        from agent.rules import next_best_question_key, missing_critical_fields

        sid = "cenario3_pending_slot"
        self._setup_mid_triage(sid)

        p1, p2, p3 = _triage_patches()
        with _no_llm(), p1, p2, p3:
            handle_message(sid, "tem academia no condomínio?")

        state = store.get(sid)
        missing = missing_critical_fields(state)
        # pending_field deve ser um dos campos críticos faltantes
        if state.pending_field:
            assert state.pending_field in missing or state.pending_field in {
                "lead_name", "lead_phone", "leisure_level"
            }, (
                f"pending_field={state.pending_field!r} deveria ser campo do funil. "
                f"Missing: {missing}"
            )

    def test_faq_intent_returns_to_funnel_with_pending_slot(self):
        """FAQ intent real também deve retornar ao funil com pending_slot."""
        sid = "cenario3_faq_pending"
        self._setup_mid_triage(sid)

        # Força pergunta de banheiros pendente
        state = store.get(sid)
        state.set_criterion("bedrooms", 3, status="confirmed")
        store.save(state)

        p1, p2, p3 = _triage_patches()
        with _no_llm(), p1, p2, p3:
            resp = handle_message(sid, "como funciona o financiamento?")

        reply = resp["reply"]
        # Deve ter retorno ao funil
        assert "?" in reply or "pra eu" in reply.lower(), (
            f"Reply deve ter retorno ao funil: {reply!r}"
        )


# ---------------------------------------------------------------------------
# Cenário 4: JSON truncado não derruba o fluxo
# ---------------------------------------------------------------------------

class TestCenario4JSONTruncado:

    def test_repair_valid_json(self):
        """JSON válido não precisa de reparo."""
        from agent.llm import _repair_truncated_json
        result = _repair_truncated_json('{"intent": "comprar", "plan": {"action": "ASK"}}')
        assert result == {"intent": "comprar", "plan": {"action": "ASK"}}

    def test_repair_json_with_code_fence(self):
        """JSON dentro de ```json ... ``` é extraído e parseado."""
        from agent.llm import _repair_truncated_json
        raw = '```json\n{"decision": "ASK", "updates": []}\n```'
        result = _repair_truncated_json(raw)
        assert result is not None
        assert result.get("decision") == "ASK"

    def test_repair_truncated_closes_braces(self):
        """JSON truncado (sem fechamento) é reparado com best-effort."""
        from agent.llm import _repair_truncated_json
        truncated = '{"intent": "comprar", "plan": {"action": "ASK"'
        result = _repair_truncated_json(truncated)
        assert result is not None, "Deveria reparar JSON truncado"
        assert result.get("intent") == "comprar"

    def test_repair_returns_none_for_garbage(self):
        """Texto completamente inválido retorna None (sem exceção)."""
        from agent.llm import _repair_truncated_json
        result = _repair_truncated_json("este não é json de jeito nenhum !@#$")
        assert result is None

    def test_gemini_truncated_json_falls_back_gracefully(self):
        """
        Quando Gemini retorna JSON truncado, o fluxo NÃO deve lançar RuntimeError.
        Deve retornar resposta válida (fallback do funil determinístico).
        """
        sid = "cenario4_truncated_gemini"
        store.reset(sid)
        state = store.get(sid)
        state.intent = "comprar"
        state.set_criterion("city", "Joao Pessoa", status="confirmed")
        store.save(state)

        # Simula Gemini retornando JSON truncado que não pode ser reparado
        truncated_response = '{"intent": "comprar", "extracted_updates": {"bedrooms'

        p1, p2, p3 = _triage_patches()
        with (
            patch.object(llm_module, "LLM_PROVIDER", "gemini_native"),
            patch.object(llm_module, "USE_LLM", True),
            patch.object(llm_module, "LLM_API_KEY", "fake-key"),
            patch("agent.llm._call_gemini_native", return_value=truncated_response),
            p1, p2, p3
        ):
            try:
                resp = handle_message(sid, "quero 3 quartos")
                # Deve ter resposta (não crash)
                assert "reply" in resp, "Deve retornar reply mesmo com JSON truncado"
                assert resp["reply"], "Reply não pode ser vazio"
            except RuntimeError as e:
                pytest.fail(f"JSON truncado não deveria lançar RuntimeError: {e}")

    def test_empty_llm_result_falls_back_to_deterministic(self):
        """
        Quando LLM retorna {} (fallback de JSON inválido),
        o funil determinístico assume e faz a próxima pergunta.
        """
        sid = "cenario4_empty_result"
        store.reset(sid)
        state = store.get(sid)
        state.intent = "comprar"
        store.save(state)

        p1, p2, p3 = _triage_patches()
        # LLM retorna {} (como se fosse JSON inválido recuperado)
        with (
            patch.object(llm_module, "USE_LLM", True),
            patch.object(llm_module, "LLM_API_KEY", "fake"),
            patch("agent.llm.call_llm", return_value={}),
            p1, p2, p3
        ):
            resp = handle_message(sid, "estou procurando algo em João Pessoa")

        assert "reply" in resp
        assert resp["reply"], "Reply não pode ser vazio com fallback determinístico"


# ---------------------------------------------------------------------------
# Testes de integração: multi-slot extraction
# ---------------------------------------------------------------------------

class TestMultiSlotExtraction:

    def test_mensagem_rica_captura_multiplos_campos(self):
        """
        'apto 2 quartos 1 suite 2 vagas que tem piscina e academia'
        deve capturar: bedrooms=2, suites=1, parking=2, leisure_required=yes,
        leisure_features=['piscina', 'academia'].
        """
        msg = "apto 2 quartos 1 suite 2 vagas que tem piscina e academia"
        result = extract_criteria(msg, [])
        assert result.get("bedrooms") == 2
        assert result.get("suites") == 1
        assert result.get("parking") == 2
        assert result.get("leisure_required") == "yes"
        features = result.get("leisure_features") or []
        assert "piscina" in features
        assert "academia" in features

    def test_mensagem_com_temporada_e_lazer(self):
        """
        'apto que libera Airbnb e tem área de lazer'
        → allows_short_term_rental=yes, leisure_required=yes
        """
        msg = "apto que libera Airbnb e tem área de lazer"
        result = extract_criteria(msg, [])
        assert result.get("allows_short_term_rental") == "yes"
        assert result.get("leisure_required") == "yes"
        # Intent não deve ser setado (sem comprar/alugar explícito)
        assert result.get("intent") is None or result.get("intent") != "alugar"

    def test_leisure_feature_seta_leisure_required(self):
        """Menção de 'piscina' isolada já deve implicar leisure_required=yes."""
        msg = "preciso que tenha piscina no condomínio"
        result = extract_criteria(msg, [])
        assert result.get("leisure_required") == "yes"
        assert "piscina" in (result.get("leisure_features") or [])
