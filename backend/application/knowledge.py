"""
[M4] Conhecimento / RAG - pipeline operacional da fase 6.

Responsabilidades:
  - ingerir documentos da base de conhecimento
  - classificar perguntas operacionais vs catalogo
  - recuperar contexto via TF-IDF
  - bloquear respostas quando a evidencia for insuficiente
  - formatar resposta com fontes rastreaveis
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from core.trace import get_logger
from infrastructure.knowledge import DocumentInput, RAGIndex, RetrievalResult, build_document, load_directory

logger = get_logger(__name__)


DEFAULT_KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", "knowledge"))
MIN_CONFIDENCE = max(0.15, float(os.getenv("KNOWLEDGE_MIN_CONFIDENCE", "0.30")))
MIN_GROUNDED_OVERLAP = max(2, int(os.getenv("KNOWLEDGE_MIN_GROUNDED_OVERLAP", "4")))


@dataclass
class KnowledgeResult:
    """Resultado consolidado de uma consulta a base operacional."""

    answer: str
    sources: List[str] = field(default_factory=list)
    confidence: float = 0.0
    is_grounded: bool = True
    retrieved_chunks: List[str] = field(default_factory=list)
    domain: Optional[str] = None
    prompt_context: List[str] = field(default_factory=list)
    blocked_reason: Optional[str] = None
    question_type: Optional[str] = None

    @property
    def reply_text(self) -> str:
        if not self.sources:
            return self.answer
        return f"{self.answer}\n\nFontes internas: {' | '.join(self.sources[:3])}"


class KnowledgeService:
    """Servico RAG local, sem dependencia do legado."""

    def __init__(
        self,
        *,
        index: Optional[RAGIndex] = None,
        knowledge_dir: Path | str = DEFAULT_KNOWLEDGE_DIR,
        auto_load: bool = True,
        require_public_default: bool = True,
    ) -> None:
        self._index = index or RAGIndex()
        self._knowledge_dir = Path(knowledge_dir)
        self._require_public_default = require_public_default
        if auto_load:
            self.refresh_index()

    @property
    def index(self) -> RAGIndex:
        return self._index

    def refresh_index(self) -> int:
        """Recarrega todo o corpus do diretorio configurado."""
        docs = load_directory(str(self._knowledge_dir), recursive=True)
        self._index.replace_documents(docs)
        logger.info(
            "knowledge_index_refreshed",
            extra={"documents": len(docs), "chunks": self._index.size, "directory": str(self._knowledge_dir)},
        )
        return len(docs)

    def ingest_document(self, doc: DocumentInput) -> str:
        """Faz upsert de um documento no indice."""
        self._index.upsert_document(doc)
        logger.info(
            "knowledge_document_ingested",
            extra={"doc_id": doc.doc_id, "doc_type": doc.doc_type, "access_level": doc.access_level},
        )
        return doc.doc_id

    def ingest_text(
        self,
        *,
        doc_id: str,
        title: str,
        content: str,
        doc_type: str,
        tags: Optional[List[str]] = None,
        is_public: bool = True,
        access_level: str = "public",
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
    ) -> str:
        """Helper para ingestao programatica e testes."""
        return self.ingest_document(
            build_document(
                doc_id=doc_id,
                title=title,
                content=content,
                doc_type=doc_type,
                tags=tags or [],
                is_public=is_public,
                access_level=access_level,
                city=city,
                neighborhood=neighborhood,
            )
        )

    def remove_document(self, doc_id: str) -> None:
        self._index.remove_document(doc_id)
        logger.info("knowledge_document_removed", extra={"doc_id": doc_id})

    def answer(
        self,
        question: str,
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
        domain: Optional[str] = None,
        top_k: int = 3,
        require_public: Optional[bool] = None,
    ) -> Optional[KnowledgeResult]:
        """
        Responde pergunta operacional usando o indice local.

        Retorna None quando:
          - a pergunta e de catalogo/imovel
          - nao ha contexto suficiente
          - a resposta nao passa no groundedness check
        """
        if not question or not question.strip():
            return None

        question_type = self.classify_question(question)
        if question_type == "catalog":
            return None

        require_public = self._require_public_default if require_public is None else require_public
        retrieval = self._search_with_relaxation(
            question,
            question_type=question_type,
            domain=domain,
            city=city,
            neighborhood=neighborhood,
            top_k=top_k,
            require_public=require_public,
        )
        if not retrieval.chunks:
            logger.info("knowledge_no_answer", extra={"question_preview": question[:100], "question_type": question_type})
            return None

        confidence = self._estimate_confidence(retrieval)
        prompt_context = self._build_prompt_context(retrieval)
        answer = self._compose_answer(question_type, retrieval)
        grounded = self.check_groundedness(answer, retrieval.texts)

        if confidence < MIN_CONFIDENCE or not grounded:
            logger.info(
                "knowledge_blocked",
                extra={
                    "question_preview": question[:100],
                    "question_type": question_type,
                    "confidence": confidence,
                    "grounded": grounded,
                },
            )
            return None

        logger.info(
            "knowledge_answer_found",
            extra={
                "question_preview": question[:100],
                "question_type": question_type,
                "confidence": confidence,
                "sources": retrieval.sources[:3],
            },
        )
        return KnowledgeResult(
            answer=answer,
            sources=retrieval.sources[:3],
            confidence=confidence,
            is_grounded=grounded,
            retrieved_chunks=retrieval.texts,
            domain=question_type,
            prompt_context=prompt_context,
            question_type=question_type,
        )

    def check_groundedness(self, answer: str, context_chunks: List[str]) -> bool:
        """Heuristica simples: a resposta precisa reutilizar termos da evidencia."""
        if not answer or not context_chunks:
            return False
        answer_tokens = set(_meaningful_tokens(answer))
        if not answer_tokens:
            return False
        context_tokens = set()
        for chunk in context_chunks:
            context_tokens.update(_meaningful_tokens(chunk))
        overlap = answer_tokens & context_tokens
        return len(overlap) >= MIN_GROUNDED_OVERLAP

    def classify_question(self, question: str) -> str:
        """
        Classifica a pergunta para evitar conflito entre RAG e catalogo.

        Retorna:
          catalog | financing | policy | geo | faq | other
        """
        normalized = _normalize_text(question)
        if not normalized:
            return "other"

        if any(token in normalized for token in _CATALOG_TERMS):
            return "catalog"
        if any(token in normalized for token in _FINANCING_TERMS):
            return "financing"
        if any(token in normalized for token in _POLICY_TERMS):
            return "policy"
        if any(token in normalized for token in _GEO_TERMS):
            return "geo"
        for location in self._index.known_locations:
            if location and location in normalized:
                return "geo"
        if any(token in normalized for token in _FAQ_TERMS) or "?" in question:
            return "faq"
        return "other"

    def requires_operational_knowledge(self, question: str) -> bool:
        return self.classify_question(question) in {"financing", "policy", "geo", "faq"}

    def _search_with_relaxation(
        self,
        question: str,
        *,
        question_type: str,
        domain: Optional[str],
        city: Optional[str],
        neighborhood: Optional[str],
        top_k: int,
        require_public: bool,
    ) -> RetrievalResult:
        doc_type = self._resolve_doc_type_filter(question_type=question_type, domain=domain)
        attempts = [
            {"doc_type_filter": doc_type, "city": city, "neighborhood": neighborhood},
            {"doc_type_filter": doc_type, "city": city, "neighborhood": None},
            {"doc_type_filter": doc_type, "city": None, "neighborhood": None},
            {"doc_type_filter": None, "city": city, "neighborhood": neighborhood},
            {"doc_type_filter": None, "city": None, "neighborhood": None},
        ]

        for filters in attempts:
            result = self._index.search(
                question,
                top_k=top_k,
                doc_type_filter=filters["doc_type_filter"],
                city=filters["city"],
                neighborhood=filters["neighborhood"],
                require_public=require_public,
            )
            if result.chunks:
                return result
        return RetrievalResult(total_indexed=self._index.size)

    def _resolve_doc_type_filter(self, *, question_type: str, domain: Optional[str]) -> Optional[str]:
        explicit = str(domain or "").strip().lower()
        if explicit in {"policy", "financing", "geo", "script"}:
            return explicit
        if explicit == "faq" and question_type in {"faq", "other"}:
            return "faq"
        if explicit == "institutional":
            return None
        mapping = {
            "financing": "financing",
            "policy": "policy",
            "geo": "geo",
            "faq": "faq",
        }
        return mapping.get(question_type)

    def _estimate_confidence(self, retrieval: RetrievalResult) -> float:
        if not retrieval.chunks:
            return 0.0
        top = retrieval.chunks[0]
        base = min(1.0, top.score)
        if len(retrieval.chunks) == 1:
            return round(min(1.0, base + 0.12), 3)
        gap = max(top.score - retrieval.chunks[1].score, 0.0)
        return round(min(1.0, base + min(gap, 0.2) + 0.08), 3)

    def _build_prompt_context(self, retrieval: RetrievalResult) -> List[str]:
        context: List[str] = []
        for item in retrieval.chunks[:3]:
            source = item.chunk.source_path or item.chunk.doc_id
            context.append(f"[{source}#{item.chunk.section}] {item.chunk.text}")
        return context

    def _compose_answer(self, question_type: str, retrieval: RetrievalResult) -> str:
        ordered = sorted(retrieval.chunks, key=lambda item: _section_priority(item.chunk.section))
        primary = ordered[0].chunk
        secondary = ordered[1].chunk if len(ordered) > 1 else None

        first = _compress_text(primary.text, max_sentences=2, max_chars=260)
        parts = [first]
        if secondary is not None:
            second = _compress_text(secondary.text, max_sentences=1, max_chars=140)
            if second and second not in first:
                parts.append(second)

        answer = " ".join(part for part in parts if part).strip()
        if not answer:
            answer = "Nao encontrei contexto suficiente para responder com seguranca."
        prefix = {
            "financing": "Sobre financiamento, ",
            "policy": "Pela politica e processos internos, ",
            "geo": "Sobre a regiao, ",
            "faq": "Pelo que temos na base, ",
        }.get(question_type, "")
        if prefix:
            answer = prefix + answer[0].lower() + answer[1:] if answer else prefix.strip()
        if not answer.endswith("."):
            answer += "."
        if "caso concreto" not in answer.lower():
            answer += " Isso pode variar; confirmamos no caso concreto."
        return answer


_CATALOG_TERMS = {
    "apartamento", "casa", "studio", "cobertura", "imovel disponivel",
    "imovel", "imóvel", "quero comprar", "quero alugar", "manda opcoes",
    "me mostra", "tem algum", "tem algo", "quantos quartos", "orcamento",
    "orçamento", "preco do imovel", "preço do imóvel",
}
_FINANCING_TERMS = {
    "financiamento", "financiar", "fgts", "entrada", "banco", "parcela",
    "juros", "credito", "crédito", "itbi", "cartorio", "cartório",
}
_POLICY_TERMS = {
    "documentos", "escritura", "registro", "visita", "reserva", "proposta",
    "condominio", "condomínio", "regras", "prazo", "processo", "atendimento",
    "aceita", "permite", "temporada", "airbnb",
}
_GEO_TERMS = {
    "bairro", "regiao", "região", "praia", "orla", "familia", "família",
    "morar", "investir", "vale a pena", "localizacao", "localização",
}
_FAQ_TERMS = {
    "como", "quando", "quanto tempo", "pode", "qual", "quais", "o que",
}
_MEANINGLESS_TERMS = {
    "isso", "essa", "esse", "sobre", "geral", "base", "caso", "concreto",
    "variar", "confirmamos", "temos", "pela", "pelas", "que", "para",
}


def _normalize_text(text: str) -> str:
    lowered = unicodedata.normalize("NFKD", (text or "").lower())
    lowered = "".join(char for char in lowered if not unicodedata.combining(char))
    lowered = re.sub(r"[^\w\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _meaningful_tokens(text: str) -> List[str]:
    return [
        token
        for token in _normalize_text(text).split()
        if len(token) > 2 and token not in _MEANINGLESS_TERMS
    ]


def _compress_text(text: str, *, max_sentences: int, max_chars: int) -> str:
    compact = re.sub(r"\s+", " ", (text or "").strip())
    compact = re.sub(r"^[-*]\s+", "", compact)
    compact = re.sub(r"\s[-*]\s+", " ", compact)
    if not compact:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", compact)
    selected = " ".join(sentences[:max_sentences]).strip()
    if len(selected) > max_chars:
        selected = selected[: max_chars - 3].rstrip() + "..."
    return selected


def _section_priority(section: str) -> int:
    normalized = _normalize_text(section).replace(" ", "_")
    if normalized in {"resumo", "analise", "perfil"}:
        return 0
    if normalized in {"tempo_medio_de_tramitacao", "prazo", "o_que_normalmente_e_avaliado"}:
        return 1
    if normalized in {"como_responder_no_atendimento"}:
        return 2
    if normalized in {"aviso"}:
        return 3
    return 1
