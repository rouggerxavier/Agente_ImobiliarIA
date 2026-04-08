from __future__ import annotations
import logging
import re
import unicodedata
from typing import Dict, Any, List, Tuple, Optional
import time

logger = logging.getLogger(__name__)
from .state import store, SessionState
from .ai_agent import get_agent
from . import tools
from .rules import (
    can_search_properties,
    missing_critical_fields,
    next_best_question,
    next_best_question_key,
    choose_question,
    QUESTION_BANK,
    PREFERENCE_ORDER,
)
from .dialogue import Plan
from .llm import TRIAGE_ONLY
from . import llm as llm_module
from .extractor import enrich_with_regex, resolve_city
from .presenter import (
    format_option,
    build_summary_payload,
    format_handoff_message,
)
from .scoring import compute_lead_score
from .persistence import persist_state
from . import persistence
from .router import route_lead
from .quality import compute_quality_score
from .knowledge_base import answer_question
try:
    from app import faq  # FastAPI deploy layout
except ImportError:
    import faq  # standalone / test layout


AFFIRMATIVE = {"sim", "s", "pode", "claro", "ok", "yes", "isso", "perfeito"}
NEGATIVE = {"nao", "nÃ£o", "n", "no", "negativo"}
BOOL_KEYS = {"pet", "furnished"}
GREETINGS = {"bom dia", "boa tarde", "boa noite", "olÃ¡", "ola", "oi", "e aÃ­", "eai"}
INTENT_KEYWORDS = {"comprar", "alugar", "investir"}
GENERIC_NAMES = {"ok", "ola", "olÃ¡", "oi", "hi", "hello", "tudo bem"}
_NAME_PREFIX_PATTERN = re.compile(
    r"^(?:meu\s+nome\s+(?:e|Ã©)|me\s+chamo|sou|eu\s+sou|aqui\s+(?:e|Ã©)|nome)\s+(.+)$",
    re.IGNORECASE,
)
_NON_NAME_FIRST_WORDS = {
    "comprar", "alugar", "quero", "queria", "procuro", "procurando", "busco",
    "apartamento", "casa", "cobertura", "studio", "sim", "nao", "nÃ£o", "ok",
    "bom", "boa", "oi", "ola", "olÃ¡", "eai", "tudo",
}

# Aviso inicial obrigatÃ³rio para contexto de triagem
_TRIAGE_PRE_NOTICE = (
    "Antes de seguir, te explico rapidinho: este atendimento funciona apenas para triagem. "
    "Vou anotar como vocÃª quer seu apartamento ou casa e, ao final, repasso tudo para um corretor, "
    "junto com seu nome e nÃºmero de WhatsApp, para ele entrar em contato. "
)
# SaudÃ£o inicial da Grankasa â€” pede o nome primeiro para personalizar o atendimento
_GRANKASA_GREETING = (
    "Bom dia! ðŸ˜Š Sou a assistente virtual da Grankasa, aqui pra te ajudar a encontrar o imÃ³vel ideal. "
    f"{_TRIAGE_PRE_NOTICE}"
    "Pra comeÃ§ar, como posso te chamar?"
)
_GRANKASA_GREETING_TARDE = (
    "Boa tarde! ðŸ˜Š Sou a assistente virtual da Grankasa, aqui pra te ajudar a encontrar o imÃ³vel ideal. "
    f"{_TRIAGE_PRE_NOTICE}"
    "Pra comeÃ§ar, como posso te chamar?"
)
_GRANKASA_GREETING_NOITE = (
    "Boa noite! ðŸ˜Š Sou a assistente virtual da Grankasa, aqui pra te ajudar a encontrar o imÃ³vel ideal. "
    f"{_TRIAGE_PRE_NOTICE}"
    "Pra comeÃ§ar, como posso te chamar?"
)
_GRANKASA_GREETING_NEUTRAL = (
    "OlÃ¡! ðŸ˜Š Sou a assistente virtual da Grankasa, aqui pra te ajudar a encontrar o imÃ³vel ideal. "
    f"{_TRIAGE_PRE_NOTICE}"
    "Pra comeÃ§ar, como posso te chamar?"
)


def _human_handoff(state: SessionState, reason: str) -> Dict[str, Any]:
    """Processa handoff para humano usando presenter para formatar mensagem."""
    state.human_handoff = True
    summary = {
        "session_id": state.session_id,
        "intent": state.intent,
        "criteria": state.criteria.__dict__,
        "last_suggestions": state.last_suggestions,
        "reason": reason,
        "lead_score": state.lead_score.__dict__,
    }
    reply = format_handoff_message(reason)
    return {
        "reply": reply,
        "handoff": tools.handoff_human(str(summary)),
        "state": state.to_public_dict(),
    }


def should_handoff_to_human(message: str, state: SessionState) -> Tuple[bool, str]:
    """
    Decide se deve transferir para humano usando anÃ¡lise de IA.
    """
    agent = get_agent()

    try:
        should_handoff, reason, urgency = agent.should_handoff(message, state)
        if should_handoff:
            logger.info("Handoff detectado: %s (urgÃªncia: %s)", reason, urgency)
        return should_handoff, reason
    except Exception as e:
        logger.warning("Erro na decisÃ£o de handoff, usando fallback do agent: %s", e)
        should_handoff, reason, _ = agent._handoff_fallback(message, state)
        return should_handoff, reason


def _short_reply_updates(message: str, state: SessionState) -> Dict[str, Dict[str, Any]]:
    """
    Interpreta respostas curtas como confirmaÃ§Ã£o do Ãºltimo campo.
    """
    msg = message.strip().lower()
    updates: Dict[str, Dict[str, Any]] = {}
    lk = state.last_question_key
    if not lk:
        return updates

    is_yes = msg in AFFIRMATIVE
    is_no = msg in NEGATIVE
    is_indifferent = any(kw in msg for kw in ["tanto faz", "indiferente", "qualquer", "nao importa", "nÃ£o importa"])

    # Detecta "indiferente" para qualquer campo
    if is_indifferent:
        if lk in {"suites", "bathrooms_min", "micro_location", "leisure_required", "leisure_level", "floor_pref", "sun_pref", "pet", "furnished"}:
            updates[lk] = {"value": "indifferent", "status": "confirmed", "source": "user", "raw_text": message}
            return updates

    if lk in BOOL_KEYS and (is_yes or is_no):
        updates[lk] = {"value": True if is_yes else False, "status": "confirmed", "source": "user"}
        return updates

    # NOVO: SuÃ­tes (aceita nÃºmeros ou "nenhuma")
    if lk == "suites":
        import re
        # PadrÃµes: "1", "2", "nenhuma", "0"
        match = re.search(r"(\d+)", msg)
        if match:
            updates["suites"] = {"value": int(match.group(1)), "status": "confirmed", "source": "user", "raw_text": message}
            return updates
        if "nenhuma" in msg or "sem" in msg or "zero" in msg:
            updates["suites"] = {"value": 0, "status": "confirmed", "source": "user", "raw_text": message}
            return updates

    # NOVO: Banheiros
    if lk == "bathrooms_min":
        import re
        match = re.search(r"(\d+)", msg)
        if match:
            updates["bathrooms_min"] = {"value": int(match.group(1)), "status": "confirmed", "source": "user", "raw_text": message}
            return updates

    # NOVO: Micro-location (praia)
    if lk == "micro_location":
        if "beira" in msg or "frente" in msg:
            updates["micro_location"] = {"value": "beira-mar", "status": "confirmed", "source": "user", "raw_text": message}
            return updates
        if "1 quadra" in msg or "uma quadra" in msg:
            updates["micro_location"] = {"value": "1_quadra", "status": "confirmed", "source": "user", "raw_text": message}
            return updates
        if "2" in msg or "3" in msg or "duas" in msg or "tres" in msg:
            updates["micro_location"] = {"value": "2-3_quadras", "status": "confirmed", "source": "user", "raw_text": message}
            return updates

    # NOVO: Leisure required
    if lk == "leisure_required":
        _yes_leisure = is_yes or any(kw in msg for kw in {"queria", "quero", "precisa", "preciso", "sim precisa", "sim queria", "importante", "essencial"})
        _no_leisure = is_no or any(kw in msg for kw in {"nao precisa", "nÃ£o precisa", "nao preciso", "nÃ£o preciso", "sem lazer", "nao e essencial", "nÃ£o Ã© essencial"})
        if _yes_leisure:
            updates["leisure_required"] = {"value": "yes", "status": "confirmed", "source": "user", "raw_text": message}
            return updates
        if _no_leisure:
            updates["leisure_required"] = {"value": "no", "status": "confirmed", "source": "user", "raw_text": message}
            return updates

    # NOVO: Leisure level
    if lk == "leisure_level":
        if "complet" in msg or "tudo" in msg:
            updates["leisure_level"] = {"value": "full", "status": "confirmed", "source": "user", "raw_text": message}
            return updates
        if "simples" in msg or "basico" in msg or "bÃ¡sico" in msg:
            updates["leisure_level"] = {"value": "simple", "status": "confirmed", "source": "user", "raw_text": message}
            return updates
        if "ok" in msg or "razoavel" in msg or "medio" in msg or "mÃ©dio" in msg:
            updates["leisure_level"] = {"value": "ok", "status": "confirmed", "source": "user", "raw_text": message}
            return updates

    # NOVO: Floor preference
    if lk == "floor_pref":
        if "alto" in msg:
            updates["floor_pref"] = {"value": "alto", "status": "confirmed", "source": "user", "raw_text": message}
            return updates
        if "baixo" in msg:
            updates["floor_pref"] = {"value": "baixo", "status": "confirmed", "source": "user", "raw_text": message}
            return updates
        if "medio" in msg or "mÃ©dio" in msg:
            updates["floor_pref"] = {"value": "medio", "status": "confirmed", "source": "user", "raw_text": message}
            return updates

    # NOVO: Sun preference
    if lk == "sun_pref":
        if "nascente" in msg or "manha" in msg or "manhÃ£" in msg:
            updates["sun_pref"] = {"value": "nascente", "status": "confirmed", "source": "user", "raw_text": message}
            return updates
        if "poente" in msg or "tarde" in msg:
            updates["sun_pref"] = {"value": "poente", "status": "confirmed", "source": "user", "raw_text": message}
            return updates
    if lk == "lead_name":
        candidate = _extract_name_candidate(message)
        if candidate:
            updates["lead_name"] = {"value": candidate, "status": "confirmed", "source": "user", "raw_text": message}
            return updates

    if lk == "lead_phone":
        # Captura nÃºmero de telefone â€” qualquer resposta que tenha dÃ­gitos suficientes
        digits = "".join(ch for ch in message if ch.isdigit())
        if len(digits) >= 8:
            updates["lead_phone"] = {"value": message.strip(), "status": "confirmed", "source": "user", "raw_text": message}
            return updates

    # NOVO: payment_type (financiamento, FGTS, Ã  vista, consÃ³rcio)
    if lk == "payment_type":
        if any(kw in msg for kw in {"financ", "financiamento", "financiar"}):
            updates["payment_type"] = {"value": "financiamento", "status": "confirmed", "source": "user", "raw_text": message}
            return updates
        if "fgts" in msg:
            updates["payment_type"] = {"value": "fgts", "status": "confirmed", "source": "user", "raw_text": message}
            return updates
        if any(kw in msg for kw in {"a vista", "Ã  vista", "avista", "dinheiro", "cash"}):
            updates["payment_type"] = {"value": "a_vista", "status": "confirmed", "source": "user", "raw_text": message}
            return updates
        if any(kw in msg for kw in {"consorcio", "consÃ³rcio"}):
            updates["payment_type"] = {"value": "consorcio", "status": "confirmed", "source": "user", "raw_text": message}
            return updates

    # NOVO: condo_max (valor mÃ¡ximo de condomÃ­nio)
    if lk == "condo_max":
        import re
        match = re.search(r"(\d[\d.,]*)", msg)
        if match:
            raw = match.group(1).replace(".", "").replace(",", "")
            try:
                val = int(raw)
                updates["condo_max"] = {"value": val, "status": "confirmed", "source": "user", "raw_text": message}
                return updates
            except ValueError:
                pass

    # NOVO: allows_short_term_rental
    if lk == "allows_short_term_rental":
        if is_yes or any(kw in msg for kw in {"permite", "aceita", "libera", "sim", "airbnb", "temporada"}):
            updates["allows_short_term_rental"] = {"value": "yes", "status": "confirmed", "source": "user", "raw_text": message}
            return updates
        if is_no or any(kw in msg for kw in {"nao permite", "nÃ£o permite", "nao aceita", "nÃ£o aceita", "nao libera", "nÃ£o libera"}):
            updates["allows_short_term_rental"] = {"value": "no", "status": "confirmed", "source": "user", "raw_text": message}
            return updates

    # Requisitos extras: qualquer texto livre Ã© aceito; "nÃ£o" / "nada" / "tÃ¡ bom" encerra sem salvar
    if lk == "extra_requirements":
        _skip_phrases = {"nao", "nÃ£o", "nada", "ta bom", "tÃ¡ bom", "tudo certo", "nao tenho", "nÃ£o tenho", "sem mais", "nao tem mais", "nÃ£o tem mais", "nao faltou", "nÃ£o faltou"}
        if msg in _skip_phrases or msg.startswith("nao ") or msg.startswith("nÃ£o "):
            # UsuÃ¡rio nÃ£o tem requisitos extras â€” marca campo como "none" (sem info) para nÃ£o perguntar de novo
            updates["extra_requirements"] = {"value": "none", "status": "confirmed", "source": "user", "raw_text": message}
        elif len(message.strip()) >= 3:
            updates["extra_requirements"] = {"value": message.strip(), "status": "confirmed", "source": "user", "raw_text": message}
        return updates

    if lk in {"intent", "operation"}:
        if any(token in msg for token in {"comprar", "compra"}):
            updates["intent"] = {"value": "comprar", "status": "confirmed", "source": "user"}
            return updates
        if any(token in msg for token in {"alugar", "aluguel"}):
            updates["intent"] = {"value": "alugar", "status": "confirmed", "source": "user"}
            return updates
        if is_yes and state.intent:
            updates["intent"] = {"value": state.intent, "status": "confirmed", "source": "user"}
            return updates

    if lk == "intent_stage":
        stage = None
        inferred_timeline = None

        if any(token in msg for token in {"olhando", "pesquis", "sÃ³ olhando", "so olhando", "curioso", "sem pressa"}):
            stage = "researching"
            # Pesquisando sem pressa â†’ timeline mais longo (3-6 meses)
            inferred_timeline = "6m"
        elif any(token in msg for token in {"visita", "visitar", "marcar", "agendar", "agenda", "prÃ³ximas semanas", "proximas semanas", "rÃ¡pido", "rapido", "pronto", "urgente"}):
            stage = "ready_to_visit"
            # Pronto para visitar â†’ timeline curto (30 dias)
            inferred_timeline = "30d"
        elif "negoci" in msg:
            stage = "negotiating"
            # Negociando â†’ timeline imediato
            inferred_timeline = "30d"

        if stage:
            updates["intent_stage"] = {"value": stage, "status": "confirmed", "source": "user"}
            # Infere timeline baseado no intent_stage
            if inferred_timeline and not state.criteria.timeline:
                updates["timeline"] = {"value": inferred_timeline, "status": "inferred", "source": "intent_stage"}
            return updates

    return updates


_QA_INTERRUPT_STARTERS = {
    "como", "quanto", "pode", "aceita", "tem", "vocÃªs", "voces",
    "qual", "quais", "quando", "onde", "por que", "porque",
    "Ã© possivel", "e possivel", "dÃ¡ pra", "da pra", "posso",
}


def _is_qa_interrupt(message: str) -> bool:
    """
    Detecta se a mensagem Ã© uma pergunta de QA (interrupÃ§Ã£o do funil).
    CritÃ©rios: contÃ©m '?' OU comeÃ§a com palavra interrogativa tÃ­pica.
    """
    msg = message.strip().lower()
    if "?" in msg:
        return True
    first_word = msg.split()[0] if msg.split() else ""
    return first_word in _QA_INTERRUPT_STARTERS


def _qa_answer_generic(message: str) -> Optional[str]:
    """
    Resposta genÃ©rica curta para perguntas QA nÃ£o cobertas pelo FAQ.
    Retorna None se nÃ£o conseguir responder.
    """
    low = message.lower()
    if "pet" in low or "animal" in low or "cachorro" in low or "gato" in low:
        return "ImÃ³veis pet-friendly existem! Vou anotar essa preferÃªncia pra filtrar as opÃ§Ãµes."
    if "vaga" in low or "garagem" in low or "estacion" in low:
        return "Garagem depende de cada imÃ³vel â€” vou considerar isso nos filtros quando buscarmos."
    if "condomin" in low or "taxa" in low:
        return "O valor do condomÃ­nio varia por imÃ³vel. Posso te mostrar opÃ§Ãµes com condomÃ­nio dentro de um teto, se quiser."
    if "mobiliado" in low or "movel" in low or "mÃ³vel" in low:
        return "Temos imÃ³veis mobiliados e sem mobÃ­lia. Vou anotar sua preferÃªncia."
    if "financ" in low or "fgts" in low:
        return "Financiamento e FGTS sÃ£o possÃ­veis dependendo do imÃ³vel e do banco. Um corretor pode te orientar melhor."
    if "piscina" in low or "academia" in low or "lazer" in low:
        return "Ãrea de lazer (piscina, academia, etc.) estÃ¡ disponÃ­vel em vÃ¡rios condomÃ­nios â€” anotei isso nos seus critÃ©rios."
    return None


def _qa_answer_from_knowledge(message: str, state: SessionState, domain: Optional[str] = None) -> Optional[str]:
    kb = answer_question(
        message,
        city=state.criteria.city,
        neighborhood=state.criteria.neighborhood,
        domain=domain,
        top_k=3,
    )
    if not kb:
        return None
    sources = kb.get("sources", [])
    if not sources:
        return kb["answer"]
    return kb["answer"] + "\n\nFontes internas: " + " | ".join(sources[:3])


def _extract_update_value(payload: Any) -> Any:
    if isinstance(payload, dict):
        return payload.get("value")
    return payload


def _normalize_text_for_match(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(normalized.lower().split())


def _extract_name_candidate(message: str) -> Optional[str]:
    text = " ".join(str(message or "").strip().split())
    if not text:
        return None

    candidate = text
    intro_match = _NAME_PREFIX_PATTERN.match(text)
    if intro_match:
        candidate = intro_match.group(1).strip()
    else:
        normalized_text = _normalize_text_for_match(text)
        normalized_intro_match = re.match(r"^(?:meu nome e|me chamo|sou|eu sou|aqui e|nome)\s+(.+)$", normalized_text)
        if normalized_intro_match:
            candidate = normalized_intro_match.group(1).strip()
    candidate = candidate.strip(" .,!?:;\"'")
    if not candidate:
        return None

    normalized = _normalize_text_for_match(candidate)
    if not normalized:
        return None
    if any(char.isdigit() for char in normalized):
        return None
    if any(token in normalized for token in ("http://", "https://", "@", "/")):
        return None

    words = normalized.split()
    if not words or len(words) > 4:
        return None
    if words[0] in _NON_NAME_FIRST_WORDS:
        return None
    normalized_generic_names = {_normalize_text_for_match(name) for name in GENERIC_NAMES}
    if normalized in normalized_generic_names:
        return None

    normalized_greetings = {_normalize_text_for_match(greeting) for greeting in GREETINGS}
    if normalized in normalized_greetings:
        return None

    return candidate.title()


def _extract_name_update(message: str, state: SessionState) -> Dict[str, Dict[str, Any]]:
    if _is_valid_name(state.lead_profile.get("name")):
        return {}
    candidate = _extract_name_candidate(message)
    if not candidate:
        return {}
    return {
        "lead_name": {
            "value": candidate,
            "status": "confirmed",
            "source": "user",
            "raw_text": message,
        }
    }


def _field_has_value(state: SessionState, key: Optional[str]) -> bool:
    if not key:
        return False
    if key in {"intent", "operation"}:
        return bool(state.intent)
    if key in {"lead_name", "name"}:
        return bool((state.lead_profile.get("name") or "").strip())
    if key in {"lead_phone", "phone"}:
        return bool((state.lead_profile.get("phone") or "").strip())

    if hasattr(state.criteria, key):
        val = getattr(state.criteria, key)
    else:
        val = state.triage_fields.get(key, {}).get("value")
    return val is not None and str(val).strip() != ""


def _parallel_update_ack(extracted_updates: Dict[str, Any], pending_field: Optional[str]) -> Optional[str]:
    """
    Gera confirmaÃ§Ã£o curta quando usuÃ¡rio traz preferÃªncia paralela
    enquanto ainda falta responder o campo pendente.
    """
    if not extracted_updates:
        return None

    short_term_keys = {"allows_short_term_rental", "airbnb_allowed", "short_term_rental_allowed"}
    for key in short_term_keys:
        if key == pending_field or key not in extracted_updates:
            continue
        val = _extract_update_value(extracted_updates.get(key))
        if isinstance(val, str):
            norm = val.strip().lower()
            if norm == "yes":
                return "Perfeito, anotei que vocÃª quer condomÃ­nio que permita locaÃ§Ã£o por temporada (Airbnb)."
            if norm == "no":
                return "Perfeito, anotei que vocÃª prefere condomÃ­nio que nÃ£o permita locaÃ§Ã£o por temporada."

    return None


def _avoid_repeat_question(state: SessionState, proposed_key: Optional[str]) -> Optional[str]:
    if not proposed_key:
        return proposed_key
    if proposed_key == "city" and not state.criteria.city:
        return proposed_key
    if state.last_question_key and state.last_question_key == proposed_key:
        missing = missing_critical_fields(state)
        for key in missing:
            if key != proposed_key and key not in state.asked_questions:
                return key
    return proposed_key


def _question_text_for_key(key: Optional[str], state: SessionState) -> str:
    if not key:
        return "Como posso ajudar?"
    question = choose_question(key, state)
    if question:
        return _personalize_question(question, state)
    base = QUESTION_BANK.get(key, ["Pode me dar mais detalhes?"])[0]
    return _personalize_question(base, state)


def _personalize_question(question: str, state: SessionState) -> str:
    """Insere o nome da pessoa na pergunta quando disponÃ­vel, de forma natural."""
    first_name = _get_first_name(state)
    if not first_name:
        return question
    # Evita adicionar o nome se jÃ¡ estÃ¡ na pergunta
    if first_name.lower() in question.lower():
        return question
    # Adiciona o nome de forma natural usando template estÃ¡vel por pergunta
    templates = [
        f"{first_name}, {question[0].lower()}{question[1:]}",
        f"E {first_name}, {question[0].lower()}{question[1:]}",
        f"{question.rstrip('?')}, {first_name}?",
    ]
    idx = hash(question) % len(templates)
    return templates[idx]


def _prepend_greeting_if_needed(message: str, reply: str, state: SessionState = None) -> str:
    """
    Adiciona cumprimento ao inÃ­cio da resposta apenas no primeiro turno.

    Args:
        message: Mensagem do usuÃ¡rio
        reply: Resposta do bot
        state: Estado da sessÃ£o (para verificar se Ã© primeiro turno)

    Returns:
        Resposta com ou sem cumprimento
    """
    # SÃ³ adiciona cumprimento no primeiro turno (evita "Bom dia!" no meio da conversa)
    if state and state.message_index > 1:
        return reply

    low = message.lower()
    if any(g in low for g in GREETINGS):
        if not reply.lower().startswith(("bom dia", "boa tarde", "boa noite", "oi", "olÃ¡", "ola")):
            if "tarde" in low:
                return "Boa tarde! " + reply
            elif "noite" in low:
                return "Boa noite! " + reply
            return "Bom dia! " + reply
    return reply


def _should_reset_session(state: SessionState, message: str) -> bool:
    low = message.lower()
    has_greeting = any(g in low for g in GREETINGS)
    has_intent_keyword = any(k in low for k in INTENT_KEYWORDS)
    completed = getattr(state, "completed", False)
    stale = (state.last_activity_at and (time.time() - state.last_activity_at) > 3 * 3600)
    return (completed and has_greeting and has_intent_keyword) or stale


def _is_valid_name(name: Optional[str]) -> bool:
    if not name:
        return False
    cleaned = str(name).strip().lower()
    if cleaned in GENERIC_NAMES or len(cleaned) < 3:
        return False
    return True


def _get_first_name(state: SessionState) -> Optional[str]:
    name = state.lead_profile.get("name")
    if not _is_valid_name(name):
        return None
    return str(name).strip().split()[0].capitalize()


def _format_budget(value: int) -> str:
    """Formata valor monetÃ¡rio em PT-BR (ex: R$ 800.000)."""
    if value >= 1_000_000:
        # Formato milhÃµes
        milhoes = value / 1_000_000
        if milhoes == int(milhoes):
            return f"R$ {int(milhoes)} milhÃ£o" if milhoes == 1 else f"R$ {int(milhoes)} milhÃµes"
        else:
            return f"R$ {milhoes:.1f} milhÃµes"
    else:
        # Formato com pontos
        return f"R$ {value:,.0f}".replace(",", ".")


def _format_budget_conflict_message(key: str, prev_val: Any, new_val: Any, state: SessionState) -> str:
    """
    Gera mensagem de conflito especÃ­fica para budget, considerando ranges.
    """
    if key in {"budget", "budget_max"}:
        # Verificar se jÃ¡ existe budget_min definido
        budget_min = state.criteria.budget_min
        if budget_min and new_val and new_val < budget_min:
            # Conflito real: novo mÃ¡ximo Ã© menor que o mÃ­nimo existente
            return (
                f"Aqui ficou registrado que seu orÃ§amento mÃ­nimo Ã© {_format_budget(budget_min)} "
                f"e mÃ¡ximo {_format_budget(prev_val)}. Agora vocÃª disse {_format_budget(new_val)}. "
                f"Isso fica fora da faixa. Pode confirmar qual Ã© o orÃ§amento correto?"
            )
        else:
            return (
                f"Aqui ficou registrado orÃ§amento mÃ¡ximo de {_format_budget(prev_val)} "
                f"nesta conversa. Agora vocÃª disse {_format_budget(new_val)}. Qual vale?"
            )
    elif key == "budget_min":
        # Verificar se jÃ¡ existe budget_max definido
        budget_max = state.criteria.budget
        if budget_max and new_val and new_val > budget_max:
            # Conflito real: novo mÃ­nimo Ã© maior que o mÃ¡ximo existente
            return (
                f"Aqui ficou registrado que seu orÃ§amento mÃ¡ximo Ã© {_format_budget(budget_max)} "
                f"e mÃ­nimo {_format_budget(prev_val)}. Agora vocÃª disse {_format_budget(new_val)}. "
                f"Isso fica fora da faixa. Pode confirmar qual Ã© o orÃ§amento correto?"
            )
        else:
            return (
                f"Aqui ficou registrado orÃ§amento mÃ­nimo de {_format_budget(prev_val)} "
                f"nesta conversa. Agora vocÃª disse {_format_budget(new_val)}. Qual vale?"
            )
    else:
        # Conflito genÃ©rico (nÃ£o-budget)
        return (
            f"Aqui ficou registrado {prev_val} nesta conversa. "
            f"Agora vocÃª disse {new_val}. Qual vale?"
        )


def handle_message(session_id: str, message: str, name: str | None = None, correlation_id: str | None = None) -> Dict[str, Any]:
    """
    Processa mensagem do cliente (mÃ¡x 1 chamada LLM).
    """
    agent = get_agent()
    state = store.get(session_id)
    # Reset heurÃ­stico para nova conversa apÃ³s conclusÃ£o
    if _should_reset_session(state, message):
        preserved_profile = state.lead_profile.copy()
        logger.info("SESSION_RESET reason=completed_or_stale correlation=%s", correlation_id)
        store.reset(session_id)
        state = store.get(session_id)
        state.lead_profile.update(preserved_profile)

    # Evita duplicar conclusÃ£o/persistÃªncia se jÃ¡ finalizado
    if state.completed:
        reply = "Seu perfil jÃ¡ foi registrado! Um corretor da Grankasa vai entrar em contato com vocÃª em breve ðŸ˜Š"
        return {"reply": reply, "state": state.to_public_dict()}

    # Controle de turnos/atividade
    state.set_current_turn(state.message_index + 1)
    triage_only = TRIAGE_ONLY

    low_msg = message.lower()
    if any(k in low_msg for k in ["baixar o preco", "baixar o preÃ§o", "desconto", "negociar", "negociaÃ§Ã£o", "negociacao"]):
        return _human_handoff(state, reason="negociacao")

    if name and not state.lead_profile.get("name"):
        state.lead_profile["name"] = name
        state.lead_name = name

    state.history.append({"role": "user", "text": message})

    # Detecta confusÃ£o/pedido de esclarecimento ANTES de processar normalmente
    from .confusion_detector import (
        detect_confusion,
        generate_clarification_response,
        should_offer_options,
        format_options_message,
        is_answering_field
    )

    confusion_info = detect_confusion(message, state)

    # Se detectou confusÃ£o e temos um campo pendente
    if confusion_info and confusion_info.get("is_confused"):
        field = confusion_info.get("field")

        # LÃª contador atual (jÃ¡ foi incrementado quando o bot fez a pergunta)
        if field:
            ask_count = state.field_ask_count.get(field, 0)

            # Se jÃ¡ tentou 3+ vezes (pergunta inicial + 2 confusÃµes), oferece opÃ§Ãµes mÃºltipla escolha
            should_offer, options = should_offer_options(field, ask_count)

            if should_offer and options:
                # Oferece opÃ§Ãµes estruturadas
                reply = format_options_message(field, options)
                state.awaiting_clarification = False  # Resetando apÃ³s oferecer opÃ§Ãµes
                state.history.append({"role": "assistant", "text": reply})
                return {"reply": reply, "state": state.to_public_dict()}
            else:
                # Gera explicaÃ§Ã£o do termo/campo
                explanation = generate_clarification_response(confusion_info, state)
                state.awaiting_clarification = True
                state.last_user_confusion_signal = message
                state.history.append({"role": "assistant", "text": explanation})
                return {"reply": explanation, "state": state.to_public_dict()}

    # Se estava aguardando clarificaÃ§Ã£o e agora respondeu, limpa flag
    if state.awaiting_clarification:
        # Verifica se a resposta atual parece ser uma resposta vÃ¡lida ao campo
        if state.pending_field and is_answering_field(message, state.pending_field):
            state.awaiting_clarification = False
            state.last_user_confusion_signal = None

    # === EXTRACT-FIRST: Extraction sempre ocorre antes de decidir prÃ³xima aÃ§Ã£o ===
    # Isso garante que o state Ã© atualizado mesmo se LLM falhar

    # 1. HeurÃ­stica para respostas curtas (sim/nÃ£o)
    user_short_updates = _short_reply_updates(message, state)

    # 2. ExtraÃ§Ã£o via regex (sempre determinÃ­stico)
    neighborhoods = tools.get_neighborhoods()
    extracted_updates = enrich_with_regex(message, state, {}, known_neighborhoods=neighborhoods)

    # 3. Override de intent se explÃ­cito
    low_msg = message.lower()
    override_phrase = "na verdade" in low_msg or "corrig" in low_msg
    override_intent = None
    if override_phrase:
        if "comprar" in low_msg:
            override_intent = "comprar"
        elif "alugar" in low_msg or "aluguel" in low_msg:
            override_intent = "alugar"

    # 4. Resolve cidade explÃ­cita
    explicit_city = resolve_city(message, state)
    if explicit_city:
        extracted_updates["city"] = {
            "value": explicit_city,
            "status": "override",
            "source": "user",
            "raw_text": message,
        }

    # 5. Merge updates: short replies
    if user_short_updates:
        extracted_updates.update(user_short_updates)

    # 6. Captura de nome independente do contexto da pergunta.
    # Evita loop quando o estado Ã© reidratado sem `last_question_key`.
    if "lead_name" not in extracted_updates:
        extracted_updates.update(_extract_name_update(message, state))

    # 7. Normaliza neighborhood
    if "neighborhood" in extracted_updates:
        nb = extracted_updates["neighborhood"]
        if isinstance(nb, dict):
            nb["status"] = "confirmed"
            nb["source"] = nb.get("source", "user")
            nb["raw_text"] = nb.get("raw_text") or message

    # 8. Aplica updates extraÃ­dos ANTES de chamar LLM
    conflicts, conflict_values = state.apply_updates(extracted_updates)

    # === DECISÃƒO (LLM ou fallback) ===
    # Agora que extraction jÃ¡ ocorreu, podemos decidir prÃ³xima aÃ§Ã£o
    try:
        decision, used_llm = agent.decide(message, state, neighborhoods, correlation_id=correlation_id)
    except Exception as llm_exc:
        # Importar LLMUnavailableError aqui para evitar circular import
        from .llm import LLMUnavailableError

        # Se LLM ficou indisponÃ­vel (503/429/timeout), degraded mode foi ativado
        if isinstance(llm_exc, LLMUnavailableError):
            logger.warning("DEGRADED_MODE: LLM indisponÃ­vel: %s. Usando fallback determinÃ­stico.", llm_exc.error_type)
            # state.llm_degraded jÃ¡ foi setado por llm_decide()
            # Usar fallback completo
            from .llm import _get_fallback_decision
            decision = _get_fallback_decision(message, agent._build_state_summary(state, neighborhoods), TRIAGE_ONLY)
            decision["degraded_mode"] = True
            decision["degraded_reason"] = llm_exc.error_type
            used_llm = False
        else:
            # Outro erro inesperado, re-raise
            raise

    new_intent = decision.get("intent")
    extracted = decision.get("criteria", {}) or {}
    # extracted_updates jÃ¡ foi aplicado acima (extract-first)
    # Merge com o que veio do LLM se houver novos
    llm_extracted_updates = decision.get("extracted_updates") or {k: {"value": v, "status": "confirmed"} for k, v in extracted.items()}
    if llm_extracted_updates:
        # Merge com os jÃ¡ extraÃ­dos (priorizar user-confirmed sobre LLM-inferred)
        for key, val in llm_extracted_updates.items():
            if key not in extracted_updates:
                extracted_updates[key] = val

    handoff_info = decision.get("handoff", {})
    plan_info = decision.get("plan", {})
    fallback_reason = decision.get("fallback_reason")
    degraded_mode = decision.get("degraded_mode", False)

    if fallback_reason:
        state.fallback_reason = fallback_reason

    # Atualiza/override intent
    if override_intent and state.intent and override_intent != state.intent:
        state.intent = override_intent
        logger.info("Intent overridden: %s", override_intent)
    if new_intent and not state.intent:
        state.intent = new_intent
        logger.info("Intent: %s", new_intent)

    if extracted:
        logger.debug("CritÃ©rios extraÃ­dos: %s", extracted)

    faq_intent = faq.detect_faq_intent(message)

    # SaÃ­da da Grankasa no primeiro turno: saudÃ£o pura (mensagem Ã© sÃ³ cumprimento, sem dado imobiliÃ¡rio)
    if state.message_index == 1 and not faq_intent:
        low = message.lower()
        keywords = {"comprar", "alugar", "ap", "apartamento", "casa", "bairro", "cidade", "visitar", "orc", "budget", "r$", "vaga", "quarto", "mil"}
        has_digits = any(ch.isdigit() for ch in low)
        criteria_empty = all(v is None for v in state.criteria.__dict__.values())
        is_pure_greeting = criteria_empty and not state.intent and not has_digits and not any(k in low for k in keywords)
        if is_pure_greeting:
            # Escolhe a saudÃ£o certa pelo horÃ¡rio da mensagem
            if "tarde" in low:
                greeting_reply = _GRANKASA_GREETING_TARDE
            elif "noite" in low:
                greeting_reply = _GRANKASA_GREETING_NOITE
            elif "dia" in low:
                greeting_reply = _GRANKASA_GREETING
            else:
                greeting_reply = _GRANKASA_GREETING_NEUTRAL
            state.last_question_key = "lead_name"
            state.pending_field = "lead_name"
            state.field_ask_count["lead_name"] = state.field_ask_count.get("lead_name", 0) + 1
            state.last_bot_utterance = greeting_reply
            if "lead_name" not in state.asked_questions:
                state.asked_questions.append("lead_name")
            state.history.append({"role": "assistant", "text": greeting_reply})
            return {"reply": greeting_reply, "state": state.to_public_dict()}

    # Aplica lead scoring a cada mensagem
    score = compute_lead_score(state)
    state.lead_score.temperature = score["temperature"]
    state.lead_score.score = score["score"]
    state.lead_score.reasons = score["reasons"]
    _temp_icon = {"hot": "ðŸ”´ HOT", "warm": "ðŸŸ¡ WARM", "cold": "ðŸ”µ COLD"}.get(score['temperature'], score['temperature'].upper())
    _bar_fill = min(10, score['score'] // 10)
    _bar = "â–ˆ" * _bar_fill + "â–‘" * (10 - _bar_fill)
    _reasons_str = ", ".join(score['reasons']) if score['reasons'] else "nenhum"
    logger.info("â–¶ LEAD  %s [%s] %d/100 â€” %s  (correlation=%s)", _temp_icon, _bar, score['score'], _reasons_str, correlation_id)

    # Aplica quality scoring
    quality = compute_quality_score(state)
    _completeness_pct = int(quality['completeness'] * 100)
    _comp_fill = min(10, _completeness_pct // 10)
    _comp_bar = "â–ˆ" * _comp_fill + "â–‘" * (10 - _comp_fill)
    _grade_icon = {"A": "â­â­â­", "B": "â­â­", "C": "â­", "D": "â—‹â—‹â—‹"}.get(quality['grade'], "?")
    logger.info("â–¶ QUAL  Nota %s %s [%s] %d%% completo | score=%d  (correlation=%s)", quality['grade'], _grade_icon, _comp_bar, _completeness_pct, quality['score'], correlation_id)

    # Handoff (regras IA + decisÃ£o)
    if handoff_info.get("should"):
        reason = handoff_info.get("reason", "outro")
        logger.info("Handoff: %s", reason)
        return _human_handoff(state, reason=reason)

    # === TRIAGEM ONLY ===
    if triage_only:
        if conflicts:
            key = conflicts[0]
            vals = conflict_values.get(key, {})
            prev_val = vals.get("previous") if vals else state.triage_fields.get(key, {}).get("value")
            new_val = vals.get("new") if vals else extracted_updates.get(key, {}).get("value")

            # Usar mensagem formatada especÃ­fica para budget ou genÃ©rica
            question = _format_budget_conflict_message(key, prev_val, new_val, state)

            state.last_question_key = key
            state.pending_field = key
            state.field_ask_count[key] = state.field_ask_count.get(key, 0) + 1
            state.last_bot_utterance = question
            if key not in state.asked_questions:
                state.asked_questions.append(key)
            state.history.append({"role": "assistant", "text": question})
            return {"reply": question, "state": state.to_public_dict()}

        # FAQ antes de seguir o funil
        faq_intent = faq.detect_faq_intent(message)
        if faq_intent:
            faq_reply = faq.answer_faq(faq_intent, state, message)
            missing = missing_critical_fields(state)
            if missing:
                next_key = next_best_question_key(state)
                next_key = _avoid_repeat_question(state, next_key)
                if next_key == "neighborhood" and not state.criteria.city:
                    next_key = "city"
                follow_up = _question_text_for_key(next_key, state)
                combined = f"{faq_reply}\n\nAgora, pra eu te indicar opÃ§Ãµes certas: {follow_up}"
                state.last_question_key = next_key
                state.pending_field = next_key
                state.field_ask_count[next_key] = state.field_ask_count.get(next_key, 0) + 1
                state.last_bot_utterance = combined
                if next_key and next_key not in state.asked_questions:
                    state.asked_questions.append(next_key)
                state.history.append({"role": "assistant", "text": combined})
                return {"reply": combined, "state": state.to_public_dict()}
            state.history.append({"role": "assistant", "text": faq_reply})
            return {"reply": faq_reply, "state": state.to_public_dict()}

        # QA interrupt genÃ©rico: pergunta no meio do funil nÃ£o coberta pelo FAQ
        if _is_qa_interrupt(message) and state.intent:
            qa_answer = _qa_answer_generic(message)
            if not qa_answer:
                qa_answer = _qa_answer_from_knowledge(message, state)
            if qa_answer:
                missing = missing_critical_fields(state)
                if missing:
                    next_key = next_best_question_key(state)
                    next_key = _avoid_repeat_question(state, next_key)
                    if next_key == "neighborhood" and not state.criteria.city:
                        next_key = "city"
                    follow_up = _question_text_for_key(next_key, state)
                    combined = f"{qa_answer}\n\nAgora, pra eu te indicar opÃ§Ãµes certas: {follow_up}"
                    state.last_question_key = next_key
                    state.pending_field = next_key
                    state.field_ask_count[next_key] = state.field_ask_count.get(next_key, 0) + 1
                    state.last_bot_utterance = combined
                    if next_key and next_key not in state.asked_questions:
                        state.asked_questions.append(next_key)
                    state.history.append({"role": "assistant", "text": combined})
                    return {"reply": combined, "state": state.to_public_dict()}
                state.history.append({"role": "assistant", "text": qa_answer})
                return {"reply": qa_answer, "state": state.to_public_dict()}

        # 0. Pede nome primeiro apenas quando o usuÃ¡rio ainda nÃ£o trouxe
        # sinais claros de busca imobiliÃ¡ria (evita bloquear perguntas crÃ­ticas).
        has_any_criteria = any(v is not None for v in state.criteria.__dict__.values())
        has_meaningful_updates = any(
            _extract_update_value(payload) is not None for payload in extracted_updates.values()
        )
        should_name_gate_first = not state.intent and not has_any_criteria and not has_meaningful_updates

        if (
            should_name_gate_first
            and not _is_valid_name(state.lead_profile.get("name"))
            and "lead_name" not in state.asked_questions
        ):
            name_q_base = choose_question("lead_name", state) or "Antes de comeÃ§ar, como posso te chamar?"
            name_q = f"{_TRIAGE_PRE_NOTICE}{name_q_base}"
            state.last_question_key = "lead_name"
            state.pending_field = "lead_name"
            state.field_ask_count["lead_name"] = state.field_ask_count.get("lead_name", 0) + 1
            state.last_bot_utterance = name_q
            state.asked_questions.append("lead_name")
            reply = _prepend_greeting_if_needed(message, name_q, state)
            state.history.append({"role": "assistant", "text": reply})
            return {"reply": reply, "state": state.to_public_dict()}

        missing = missing_critical_fields(state)
        if missing:
            next_key = next_best_question_key(state)
            next_key = _avoid_repeat_question(state, next_key)
            if next_key == "neighborhood" and not state.criteria.city:
                next_key = "city"
            question = _question_text_for_key(next_key, state)
            state.last_question_key = next_key
            state.pending_field = next_key  # Rastreia campo sendo coletado
            state.field_ask_count[next_key] = state.field_ask_count.get(next_key, 0) + 1  # Incrementa contador
            state.last_bot_utterance = question  # Salva pergunta do bot
            if next_key and next_key not in state.asked_questions:
                state.asked_questions.append(next_key)

            reply = _prepend_greeting_if_needed(message, question, state)
            if state.fallback_reason:
                reply = f"Vou seguir no modo simples: {reply}"
            state.history.append({"role": "assistant", "text": reply})
            return {"reply": reply, "state": state.to_public_dict()}

        # Campo pendente sem resposta: se o usuÃ¡rio trouxe outra preferÃªncia Ãºtil,
        # confirma o que foi capturado e repete a pergunta pendente (uma vez).
        from .quality_gate import should_handoff, next_question_from_quality_gaps, detect_field_refusal, mark_field_refusal

        pending_field = state.pending_field
        pending_unanswered = pending_field and not _field_has_value(state, pending_field)
        has_parallel_updates = any(
            key != pending_field and _extract_update_value(payload) is not None
            for key, payload in extracted_updates.items()
        )

        if pending_unanswered and has_parallel_updates and not detect_field_refusal(message):
            ask_count = state.field_ask_count.get(pending_field, 0)
            if ask_count < 2:
                question = _question_text_for_key(pending_field, state)
                ack = _parallel_update_ack(extracted_updates, pending_field)
                reply = f"{ack}\n\n{question}" if ack else question

                state.last_question_key = pending_field
                state.pending_field = pending_field
                state.field_ask_count[pending_field] = ask_count + 1
                state.last_bot_utterance = reply
                if pending_field not in state.asked_questions:
                    state.asked_questions.append(pending_field)
                state.history.append({"role": "assistant", "text": reply})
                logger.info("PENDING_FIELD reasked: %s (ask_count=%d)", pending_field, state.field_ask_count[pending_field])
                return {"reply": reply, "state": state.to_public_dict()}

        # === QUALITY GATE ===
        # Verifica se quality_score permite handoff
        quality = compute_quality_score(state)

        # Detectar recusa antes de aplicar gate
        if detect_field_refusal(message) and state.last_question_key:
            mark_field_refusal(state, state.last_question_key)

        # Se o gap pendente (quality gate anterior) NÃƒO foi respondido,
        # reconhecer info paralela e re-perguntar o gap
        prev_qg_field = getattr(state, '_quality_gate_pending_field', None)
        if prev_qg_field and not _field_has_value(state, prev_qg_field):
            # O gap anterior nÃ£o foi respondido â€” NÃƒO contar como turn efetivo
            # Se houve updates paralelos, reconhecer + re-perguntar
            if has_parallel_updates and not detect_field_refusal(message):
                ask_count = state.field_ask_count.get(prev_qg_field, 0)
                if ask_count < 3:  # AtÃ© 3 tentativas para quality gate gaps
                    question = _question_text_for_key(prev_qg_field, state)
                    ack = _parallel_update_ack(extracted_updates, prev_qg_field)
                    reply = f"{ack}\n\n{question}" if ack else question
                    state.last_question_key = prev_qg_field
                    state.pending_field = prev_qg_field
                    state._quality_gate_pending_field = prev_qg_field
                    state.field_ask_count[prev_qg_field] = ask_count + 1
                    state.last_bot_utterance = reply
                    state.history.append({"role": "assistant", "text": reply})
                    logger.info("QUALITY_GATE re-ask unanswered gap: %s (ask_count=%d)", prev_qg_field, state.field_ask_count[prev_qg_field])
                    return {"reply": reply, "state": state.to_public_dict()}
        elif prev_qg_field and _field_has_value(state, prev_qg_field):
            # O gap anterior FOI respondido â€” agora sim conta como turn efetivo
            state.quality_gate_turns += 1
            state._quality_gate_pending_field = None

        if not should_handoff(state, quality):
            # Quality gate bloqueou handoff - fazer pergunta cirÃºrgica
            next_key = next_question_from_quality_gaps(state, quality)
            if next_key:
                if not prev_qg_field:
                    # Primeira pergunta de quality gate â€” conta como turn
                    state.quality_gate_turns += 1
                question = _question_text_for_key(next_key, state)
                state.last_question_key = next_key
                state.pending_field = next_key  # Rastreia campo sendo coletado
                state._quality_gate_pending_field = next_key  # Rastreia gap do quality gate
                state.field_ask_count[next_key] = state.field_ask_count.get(next_key, 0) + 1
                state.last_bot_utterance = question
                if next_key not in state.asked_questions:
                    state.asked_questions.append(next_key)

                # Contexto: avisar que estÃ¡ quase pronto mas falta um detalhe
                if state.quality_gate_turns == 1:
                    question = f"Quase lÃ¡! SÃ³ preciso de mais um detalhe: {question}"

                reply = _prepend_greeting_if_needed(message, question, state)
                state.history.append({"role": "assistant", "text": reply})
                logger.info("QUALITY_GATE pergunta de gap: %s (turn %d/3)", next_key, state.quality_gate_turns)
                return {"reply": reply, "state": state.to_public_dict()}
            else:
                # Sem perguntas disponÃ­veis, permitir handoff mesmo com score baixo
                logger.info("QUALITY_GATE sem perguntas disponÃ­veis, permitindo handoff com grade=%s", quality.get('grade'))

        # Triagem concluÃ­da (sem campos missing ou quality gate passou)
        # 1. Pergunta aberta sobre requisitos extras (uma Ãºnica vez)
        if "extra_requirements" not in state.asked_questions:
            first_name = _get_first_name(state)
            raw_extra_q = choose_question("extra_requirements", state) or "Ficou faltando alguma coisa? Algum detalhe ou exigÃªncia importante que eu ainda nÃ£o perguntei? (ou diga 'nÃ£o' se estiver tudo certo)"
            extra_q = f"{first_name}, {raw_extra_q[0].lower()}{raw_extra_q[1:]}" if first_name else raw_extra_q
            state.last_question_key = "extra_requirements"
            state.pending_field = "extra_requirements"
            state.field_ask_count["extra_requirements"] = state.field_ask_count.get("extra_requirements", 0) + 1
            state.last_bot_utterance = extra_q
            state.asked_questions.append("extra_requirements")
            state.history.append({"role": "assistant", "text": extra_q})
            persist_state(state)
            return {"reply": extra_q, "state": state.to_public_dict()}

        # 2. Pede telefone para fechar â€” Ã© o encerramento da conversa
        if not state.lead_profile.get("phone"):
            first_name = _get_first_name(state)
            if first_name:
                phone_q = f"Perfeito, {first_name}! Pra eu passar seu perfil pro corretor, me manda seu nÃºmero de WhatsApp?"
            else:
                phone_q = "Perfeito! Pra eu passar seu perfil pro corretor, me manda seu nÃºmero de WhatsApp?"
            state.last_question_key = "lead_phone"
            state.pending_field = "lead_phone"
            state.field_ask_count["lead_phone"] = state.field_ask_count.get("lead_phone", 0) + 1
            state.last_bot_utterance = phone_q
            if "lead_phone" not in state.asked_questions:
                state.asked_questions.append("lead_phone")
            state.history.append({"role": "assistant", "text": phone_q})
            return {"reply": phone_q, "state": state.to_public_dict()}

        # === SLA POLICY ===
        # Classificar lead e determinar aÃ§Ã£o SLA antes do roteamento
        from .sla import (
            classify_lead,
            compute_sla_action,
            should_emit_hot_event,
            build_hot_lead_event,
        )

        lead_score_value = state.lead_score.score
        lead_class = classify_lead(lead_score_value, state)
        quality = compute_quality_score(state)
        sla_action = compute_sla_action(lead_class, quality.get("grade"), state)

        # Atualizar estado com classificaÃ§Ã£o SLA
        state.lead_class = lead_class
        state.sla = sla_action["sla_type"]

        logger.info("SLA lead_class=%s score=%s sla=%s priority=%s correlation=%s", lead_class, lead_score_value, state.sla, sla_action['priority'], correlation_id)

        # Roteamento (com priority se HOT)
        routing_result = route_lead(state, correlation_id=correlation_id, priority=sla_action["priority"])
        assigned_agent_info = None

        if routing_result:
            assigned_agent_info = {
                "id": routing_result.agent_id,
                "name": routing_result.agent_name,
                "whatsapp": routing_result.whatsapp if tools.EXPOSE_AGENT_CONTACT else None,
                "score": routing_result.score,
                "reasons": routing_result.reasons,
                "fallback": routing_result.fallback
            }

        # Gera summary com informaÃ§Ã£o do corretor atribuÃ­do
        summary = build_summary_payload(state, assigned_agent=assigned_agent_info)
        summary["payload"]["lead_score"] = state.lead_score.__dict__
        summary["payload"]["quality_score"] = quality
        summary["payload"]["lead_class"] = lead_class
        summary["payload"]["sla"] = state.sla

        if assigned_agent_info:
            summary["payload"]["assigned_agent"] = assigned_agent_info
            summary["payload"]["routing"] = {
                "strategy": routing_result.strategy,
                "evaluated_agents_count": routing_result.evaluated_agents_count,
                "priority": sla_action["priority"]
            }

        state.completed = True
        persist_state(state)

        # PersistÃªncia pipeline expandida
        import uuid
        lead_id = uuid.uuid4().hex
        now_ts = time.time()
        completed_at = now_ts
        created_at = state.last_activity_at or now_ts
        lead_record = {
            "lead_id": lead_id,
            "session_id": state.session_id,
            "created_at": created_at,
            "completed_at": completed_at,
            "lead_profile": state.lead_profile,
            "criteria": state.criteria.__dict__,
            "triage_fields": state.triage_fields,
            "lead_score": state.lead_score.__dict__,
            "quality_score": quality,
            "assigned_agent": assigned_agent_info,
            "lead_class": lead_class,
            "sla": state.sla,
            "priority": sla_action["priority"],
            "last_action": f"{lead_class.lower()}_handoff",
            "flags": {
                "is_completed": True,
                "is_hot": lead_class == "HOT",
                "needs_followup": quality.get("grade") != "A",
                "llm_degraded": state.llm_degraded,  # Circuit breaker ativo durante sessÃ£o
            },
            "llm_status": {
                "degraded": state.llm_degraded,
                "last_error": state.llm_last_error,
                "degraded_until": state.llm_degraded_until_ts,
            } if state.llm_degraded else None,
        }
        persistence.append_lead(lead_record)
        if state.lead_profile.get("name"):
            persistence.update_lead_index(state.lead_profile["name"], lead_id)

        # Emitir evento HOT_LEAD com proteÃ§Ã£o contra duplicata
        if should_emit_hot_event(state, lead_class):
            event = build_hot_lead_event(
                lead_id=lead_id,
                session_state=state,
                lead_score=lead_score_value,
                quality_grade=quality.get("grade"),
                assigned_agent=assigned_agent_info,
                timestamp=completed_at
            )
            logger.info("NOTIFY HOT_LEAD lead_id=%s name=%s score=%s correlation=%s", lead_id, state.lead_profile.get('name'), lead_score_value, correlation_id)
            persistence.append_event(event)
            state.hot_lead_emitted = True

        # Mensagem final para o cliente: resumo humanizado completo (dados + contato fictÃ­cio)
        # O summary["text"] jÃ¡ foi gerado por build_summary_payload com todos os dados
        reply = summary["text"]
        state.history.append({"role": "assistant", "text": reply})
        return {
            "reply": reply,
            "state": state.to_public_dict(),
            "summary": summary["payload"],
            "handoff": tools.handoff_human(str(summary["payload"]))
        }

    # FAQ para fluxo normal
    if faq_intent:
        faq_reply = faq.answer_faq(faq_intent, state, message)
        missing = missing_critical_fields(state)
        if missing:
            next_key = next_best_question_key(state)
            next_key = _avoid_repeat_question(state, next_key)
            if next_key == "neighborhood" and not state.criteria.city:
                next_key = "city"
            follow_up = _question_text_for_key(next_key, state)
            combined = f"{faq_reply}\n\nSÃ³ pra eu te ajudar melhor: {follow_up}"
            state.last_question_key = next_key
            if next_key and next_key not in state.asked_questions:
                state.asked_questions.append(next_key)
            state.history.append({"role": "assistant", "text": combined})
            return {"reply": combined, "state": state.to_public_dict()}
        state.history.append({"role": "assistant", "text": faq_reply})
        return {"reply": faq_reply, "state": state.to_public_dict()}

    # === FLUXO NORMAL (nÃ£o usado neste MVP, mas mantido) ===
    plan = Plan(
        action=plan_info.get("action", "ASK"),
        message=plan_info.get("message", ""),
        question_key=plan_info.get("question_key"),
        question=plan_info.get("question") or plan_info.get("message"),
        filters=plan_info.get("filters", {}),
        handoff_reason=plan_info.get("handoff_reason"),
        state_updates=plan_info.get("state_updates", {}),
        reasoning=plan_info.get("reasoning")
    )

    logger.info("Plano: %s - %s", plan.action, plan.reasoning or plan.message[:50])

    if plan.action not in {"ASK", "SEARCH", "LIST", "REFINE", "SCHEDULE", "HANDOFF", "ANSWER_GENERAL", "CLARIFY", "TRIAGE_SUMMARY"}:
        plan.action = "ASK"

    if plan.action in {"SEARCH", "LIST"} and not can_search_properties(state):
        missing = missing_critical_fields(state)
        if missing:
            plan.action = "ASK"
            plan.message = choose_question(missing[0], state) or "Pode me dizer a cidade e o orÃ§amento?"

    updates = plan.state_updates or {}
    if "intent" in updates and updates["intent"]:
        state.intent = updates["intent"]
    criteria_updates = updates.get("criteria") or {}
    for key, value in criteria_updates.items():
        if value is not None:
            state.set_criterion(key, value, status="confirmed")

    if plan.action == "HANDOFF" and plan.handoff_reason:
        return _human_handoff(state, reason=plan.handoff_reason)

    if plan.action in {"ASK", "REFINE", "CLARIFY"}:
        qkey = _avoid_repeat_question(state, plan.question_key or state.last_question_key)
        if qkey == "neighborhood" and not state.criteria.city:
            qkey = "city"
        if qkey and choose_question(qkey, state):
            reply = choose_question(qkey, state)
        else:
            reply = plan.question or plan.message or "Como posso ajudar?"
        if state.fallback_reason:
            reply = f"Vou seguir no modo simples: {reply}"
        state.last_question_key = qkey or plan.question_key or state.last_question_key
        if state.last_question_key and state.last_question_key not in state.asked_questions:
            state.asked_questions.append(state.last_question_key)
        state.history.append({"role": "assistant", "text": reply})
        return {"reply": reply, "state": state.to_public_dict()}

    if plan.action == "ANSWER_GENERAL":
        reply = plan.message or "Como posso ajudar?"
        state.history.append({"role": "assistant", "text": reply})
        return {"reply": reply, "state": state.to_public_dict()}

    if plan.action in {"SEARCH", "LIST"}:
        filters = plan.filters or {
            "city": state.criteria.city,
            "neighborhood": state.criteria.neighborhood,
            "property_type": state.criteria.property_type,
            "bedrooms": state.criteria.bedrooms,
            "pet": state.criteria.pet,
            "furnished": state.criteria.furnished,
            "budget": state.criteria.budget,
        }

        results = tools.search_properties(filters, intent=state.intent)
        if not results:
            reply = "NÃ£o encontrei opÃ§Ãµes com esses filtros. Posso aumentar o orÃ§amento em ~10% ou considerar bairros vizinhos?"
            state.history.append({"role": "assistant", "text": reply})
            return {"reply": reply, "state": state.to_public_dict()}

        state.last_suggestions = [r.get("id") for r in results]
        lines: List[str] = []
        for idx, prop in enumerate(results, start=1):
            lines.append(format_option(idx, state.intent, prop))

        prefix = plan.message or ("Encontrei estas opÃ§Ãµes:" if len(lines) > 1 else "Achei esta opÃ§Ã£o:")
        footer = "Quer agendar visita ou refinar (bairro/quartos/orÃ§amento)?"
        reply = prefix + "\n" + "\n".join(lines) + "\n" + footer
        state.stage = "apresentou_opcoes"
        state.history.append({"role": "assistant", "text": reply})
        return {"reply": reply, "state": state.to_public_dict(), "properties": state.last_suggestions}

    if plan.action == "SCHEDULE":
        reply = plan.message or "Posso agendar uma visita. Qual horÃ¡rio prefere?"
        state.history.append({"role": "assistant", "text": reply})
        return {"reply": reply, "state": state.to_public_dict()}

    question = choose_question(next_best_question_key(state) or "", state) or plan.message or "Como posso ajudar? Prefere alugar ou comprar?"
    state.history.append({"role": "assistant", "text": question})
    return {"reply": question, "state": state.to_public_dict()}

