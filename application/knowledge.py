"""
[M4] Conhecimento / RAG — base de conhecimento operacional.

Casos de uso:
- AnswerOperationalQuestion: busca em FAQ, políticas, scripts
- IngestDocument: indexa documento na base de conhecimento
- CheckGroundedness: valida se resposta está ancorada no contexto

Fase atual: usa knowledge_base.py legado como adaptador.
Fase 6 do roadmap: implementar RAG com embeddings + pgvector.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.trace import get_logger

logger = get_logger(__name__)


@dataclass
class KnowledgeResult:
    """Resultado de uma consulta à base de conhecimento."""
    answer: str
    sources: List[str] = field(default_factory=list)
    confidence: float = 0.0        # 0.0 → 1.0
    is_grounded: bool = True       # Resposta está ancorada em fonte?
    retrieved_chunks: List[str] = field(default_factory=list)
    domain: Optional[str] = None   # Ex: "faq", "pricing", "financing"


@dataclass
class DocumentInput:
    """Documento para ingestão na base de conhecimento."""
    title: str
    content: str                   # Texto já extraído (PDF → texto)
    doc_type: str                  # faq | policy | script | property_info
    source_url: Optional[str] = None
    valid_until: Optional[str] = None   # Data de validade do documento
    tags: List[str] = field(default_factory=list)
    is_public: bool = True         # Pode ser retornado ao cliente?


class KnowledgeService:
    """
    [M4] Serviço de base de conhecimento e RAG.

    Fase atual: delega ao knowledge_base.py legado.
    Fase 6: será substituído por pipeline com embeddings + pgvector.
    """

    def __init__(self, legacy_kb=None) -> None:
        """
        legacy_kb: instância de agent.knowledge_base (bridge para legado).
        Será None quando a implementação real de RAG estiver pronta.
        """
        self._legacy_kb = legacy_kb

    # ─────────────────────────────────────────────────────────────────────────
    # Resposta operacional
    # ─────────────────────────────────────────────────────────────────────────

    def answer(
        self,
        question: str,
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
        domain: Optional[str] = None,
        top_k: int = 3,
    ) -> Optional[KnowledgeResult]:
        """
        Responde pergunta operacional usando a base de conhecimento.

        Retorna None se não houver resposta suficientemente confiante.
        """
        # Bridge para legado
        if self._legacy_kb:
            try:
                result = self._legacy_kb.answer_question(
                    question,
                    city=city,
                    neighborhood=neighborhood,
                    domain=domain,
                    top_k=top_k,
                )
                if result:
                    logger.info(
                        "knowledge_answer_found",
                        extra={"domain": domain, "question_preview": question[:100]},
                    )
                    return KnowledgeResult(
                        answer=result.get("answer", ""),
                        sources=result.get("sources", []),
                        confidence=result.get("confidence", 0.7),
                        is_grounded=True,
                        domain=domain,
                    )
            except Exception as e:
                logger.warning("knowledge_legacy_error", extra={"error": str(e)})

        logger.info(
            "knowledge_no_answer",
            extra={"question_preview": question[:100], "domain": domain},
        )
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Verificação de groundedness
    # ─────────────────────────────────────────────────────────────────────────

    def check_groundedness(self, answer: str, context_chunks: List[str]) -> bool:
        """
        Verifica se a resposta está ancorada no contexto recuperado.

        Fase atual: heurística simples por sobreposição de termos.
        Fase 6: LLM-as-judge com prompt especializado.
        """
        if not context_chunks:
            return False

        answer_words = set(answer.lower().split())
        for chunk in context_chunks:
            chunk_words = set(chunk.lower().split())
            overlap = len(answer_words & chunk_words)
            if overlap >= 5:  # threshold mínimo
                return True

        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Ingestão (Fase 6)
    # ─────────────────────────────────────────────────────────────────────────

    def ingest_document(self, doc: DocumentInput) -> str:
        """
        Indexa documento na base de conhecimento.

        Fase atual: não implementado (Fase 6 do roadmap).
        Retorna ID do documento indexado.
        """
        logger.info(
            "knowledge_ingest_requested",
            extra={"title": doc.title, "doc_type": doc.doc_type},
        )
        raise NotImplementedError(
            "Ingestão de documentos será implementada na Fase 6 (RAG comercial). "
            "Por enquanto, use os arquivos estáticos em knowledge/."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Detecção de tipo de pergunta
    # ─────────────────────────────────────────────────────────────────────────

    def classify_question(self, question: str) -> str:
        """
        Classifica o tipo de pergunta para rotear ao módulo correto.

        Retorna: "catalog" | "faq" | "financing" | "policy" | "other"
        """
        q = question.lower()
        catalog_keywords = {"imóvel", "imovel", "apartamento", "casa", "preço", "preco", "bairro", "disponível"}
        financing_keywords = {"financiamento", "fgts", "parcela", "entrada", "banco", "caixa", "minha casa"}
        faq_keywords = {"como", "quando", "documentos", "visita", "processo", "funciona", "aceita", "permite"}

        if any(k in q for k in catalog_keywords):
            return "catalog"
        if any(k in q for k in financing_keywords):
            return "financing"
        if any(k in q for k in faq_keywords):
            return "faq"
        return "other"
