from __future__ import annotations

import unicodedata
from enum import Enum, auto
from typing import Optional

from agent.knowledge_base import answer_question
from agent.state import SessionState


def _norm(text: str) -> str:
    txt = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in txt if not unicodedata.combining(ch))


class FAQIntent(Enum):
    FINANCIAMENTO = auto()
    FGTS = auto()
    DOCUMENTOS = auto()
    TAXAS = auto()
    PRAZO = auto()
    NEGOCIACAO = auto()
    VISITA = auto()
    STATUS = auto()


KEYWORDS = {
    FAQIntent.FINANCIAMENTO: ["financiamento", "financiar", "banco", "entrada", "parcelar", "financia"],
    FAQIntent.FGTS: ["fgts", "fundo de garantia"],
    FAQIntent.DOCUMENTOS: ["escritura", "registro", "documentos", "cartorio", "regularizado", "habite-se", "habite se"],
    FAQIntent.TAXAS: ["itbi", "cartorio", "taxa", "custos", "condominio", "impostos", "escritura e registro"],
    FAQIntent.PRAZO: ["quanto tempo", "prazo", "demora", "leva quanto", "quando entrega", "chaves"],
    FAQIntent.NEGOCIACAO: ["negociar", "negociacao", "desconto", "abaixa", "aceita proposta"],
    FAQIntent.VISITA: ["visitar", "agendar", "visita", "conhecer", "ver o imovel", "ver o imovel"],
    FAQIntent.STATUS: ["e agora", "proximo passo", "quando", "vai chamar", "corretor", "atendimento", "ja tem opcoes", "me manda opcoes"],
}

QUESTION_CUES = ("?", "como ", "quanto", "pode", "aceita", "precisa", "quando")

INTENT_TOPIC_MAP = {
    FAQIntent.FINANCIAMENTO: "financiamento",
    FAQIntent.FGTS: "financiamento",
    FAQIntent.DOCUMENTOS: "glossario",
    FAQIntent.TAXAS: "custos",
    FAQIntent.PRAZO: "processo_compra",
    FAQIntent.VISITA: "visita",
    FAQIntent.NEGOCIACAO: "processo_compra",
}

INTENT_PREFIX = {
    FAQIntent.FINANCIAMENTO: "Sobre financiamento, ",
    FAQIntent.FGTS: "Sobre FGTS, ",
    FAQIntent.DOCUMENTOS: "Sobre documentacao, ",
    FAQIntent.TAXAS: "Sobre custos e taxas, ",
    FAQIntent.PRAZO: "Sobre prazo, ",
    FAQIntent.VISITA: "Sobre visita, ",
    FAQIntent.NEGOCIACAO: "Sobre negociacao, ",
}


def detect_faq_intent(user_text: str) -> Optional[FAQIntent]:
    if not user_text:
        return None
    norm = _norm(user_text.strip())
    has_question_form = ("?" in user_text) or any(norm.startswith(cue) for cue in QUESTION_CUES)
    if not has_question_form:
        return None

    # Avoid false positives on budget ranges.
    if any(token in norm for token in ["milhao", "mil ", "k"]) and "-" in norm:
        return None

    for intent, kws in KEYWORDS.items():
        for kw in kws:
            if kw in norm:
                return intent
    return None


def _format_sources(sources: list[str]) -> str:
    if not sources:
        return ""
    return "\n\nFontes internas: " + " | ".join(sources[:3])


def answer_faq(intent: FAQIntent, state: SessionState, user_text: Optional[str] = None) -> str:
    intent_op = state.intent

    # Layer 1: answer through knowledge base before static fallback.
    if user_text and intent != FAQIntent.STATUS:
        topic = INTENT_TOPIC_MAP.get(intent)
        kb = answer_question(
            user_text,
            city=state.criteria.city,
            neighborhood=state.criteria.neighborhood,
            domain="institutional",
            topic=topic,
            top_k=3,
        )
        if kb:
            answer = kb["answer"]
            prefix = INTENT_PREFIX.get(intent, "")
            if prefix and not _norm(answer).startswith(_norm(prefix)):
                answer = prefix + answer
            return answer + _format_sources(kb.get("sources", []))

    if intent == FAQIntent.FINANCIAMENTO:
        extra = ""
        if intent_op == "comprar":
            extra = " Voce pretende pagar a vista ou financiamento?"
        return (
            "Muitos imoveis aceitam financiamento, mas depende do imovel e da documentacao. "
            "O corretor confirma no seu caso." + extra
        )

    if intent == FAQIntent.FGTS:
        return (
            "Geralmente da para usar FGTS na compra se o perfil e o imovel estiverem dentro das regras. "
            "Recomendo validar com seu banco e o corretor confirma no seu caso."
        )

    if intent == FAQIntent.DOCUMENTOS:
        return (
            "O ideal e o imovel estar regularizado: matricula sem onus, habite-se e documentos do vendedor ok. "
            "Quando enviarmos opcoes, o corretor verifica tudo isso para voce."
        )

    if intent == FAQIntent.TAXAS:
        return (
            "Alem do valor do imovel, costuma haver custos de impostos/registro/cartorio e condominio quando existir. "
            "O corretor passa uma estimativa conforme o imovel e a cidade."
        )

    if intent == FAQIntent.PRAZO:
        return (
            "O tempo varia conforme documentacao e, se for financiamento, tambem do banco. "
            "Para visitas, o corretor agenda rapido dentro dos horarios que voce preferir."
        )

    if intent == FAQIntent.NEGOCIACAO:
        return (
            "Desconto depende do vendedor e do imovel. "
            "O corretor negocia e orienta a melhor proposta, sem prometer nada fora do perfil."
        )

    if intent == FAQIntent.VISITA:
        return (
            "Depois de alinhar seu perfil, o corretor agenda a visita. "
            "Me diz os dias/horarios que funcionam melhor e ele confirma."
        )

    if intent == FAQIntent.STATUS:
        missing = []
        from agent.rules import missing_critical_fields

        pending = missing_critical_fields(state)
        if pending:
            # Highlight 1-2 pending fields.
            missing = pending[:2]
            campos = " e ".join(missing)
            return f"Ja estou cuidando disso. So preciso confirmar {campos} pra te passar pro corretor."
        if state.completed:
            return "Ja repassei seu perfil para um corretor, ele te chama por aqui em seguida."
        return "Quase la! Estou finalizando seu perfil e ja conecto voce a um corretor."

    return "Posso ajudar nisso, mas o corretor confirma no seu caso."
