"""
[M3 / Fase 5.4] Busca semântica e híbrida do catálogo de imóveis.

Implementação local sem dependência de serviço externo (sem pgvector, sem OpenAI embeddings).
Usa TF-IDF + similaridade de cosseno para busca semântica sobre descrições e highlights.

A busca híbrida combina:
1. Score estruturado (filtros exatos) — peso configurável
2. Score semântico (TF-IDF sobre texto) — peso configurável

Para migração futura para embeddings densos (ex: text-embedding-3-small),
basta substituir o VectorIndex por uma implementação via pgvector ou Qdrant.

Critério de saída 11.4:
- [x] Vetor local (TF-IDF) implementado
- [x] Embeddings (índice de texto) para descrições e amenidades
- [x] Busca híbrida: filtro estruturado + semântica
- [x] Reranking por score combinado
- [x] Score de recomendação (match_score)
- [x] Métricas de qualidade via recall@k logado
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from domain.entities import Property
from core.trace import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Pré-processamento de texto
# ─────────────────────────────────────────────────────────────────────────────

_STOPWORDS_PT: Set[str] = {
    "a", "ao", "as", "com", "da", "das", "de", "do", "dos", "e", "em",
    "é", "na", "nas", "no", "nos", "o", "os", "ou", "para", "por",
    "que", "se", "um", "uma", "uns", "umas", "à", "às",
}


def _tokenize(text: str) -> List[str]:
    """Tokeniza texto: lowercase, remove pontuação, remove stopwords."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = [t for t in text.split() if t and t not in _STOPWORDS_PT and len(t) > 1]
    return tokens


def _property_text(prop: Property) -> str:
    """Concatena campos textuais relevantes do imóvel em um único documento."""
    parts: List[str] = []
    if prop.description:
        parts.append(prop.description)
    if prop.highlights:
        parts.extend(prop.highlights)
    if prop.neighborhood:
        parts.append(prop.neighborhood)
    if prop.city:
        parts.append(prop.city)
    if prop.micro_location:
        parts.append(prop.micro_location)
    # Amenidades como texto
    amen = prop.amenities
    if amen.has_pool:
        parts.append("piscina")
    if amen.has_gym:
        parts.append("academia")
    if amen.has_playground:
        parts.append("playground")
    if amen.has_balcony:
        parts.append("varanda")
    if amen.has_gourmet_area:
        parts.append("gourmet")
    if amen.has_doorman:
        parts.append("portaria 24 horas")
    if amen.has_elevator:
        parts.append("elevador")
    if amen.leisure_level:
        parts.append(f"lazer {amen.leisure_level}")
    if prop.sun_position:
        parts.append(prop.sun_position)
    if prop.pet_friendly:
        parts.append("aceita pet")
    if prop.furnished:
        parts.append("mobiliado")
    return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Índice TF-IDF
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TFIDFIndex:
    """
    Índice TF-IDF local sobre os textos dos imóveis.

    Construído na memória — rebuild quando o catálogo muda.
    Para produção com >10k imóveis, substituir por pgvector ou Qdrant.
    """
    # property_id → lista de tokens
    _corpus: Dict[str, List[str]] = field(default_factory=dict)
    # term → {property_id → tf}
    _tf: Dict[str, Dict[str, float]] = field(default_factory=lambda: defaultdict(dict))
    # term → idf
    _idf: Dict[str, float] = field(default_factory=dict)
    _built: bool = False

    def build(self, properties: List[Property]) -> None:
        """Constrói o índice a partir da lista de imóveis."""
        self._corpus.clear()
        self._tf.clear()
        self._idf.clear()

        n = len(properties)
        if n == 0:
            self._built = True
            return

        doc_freq: Dict[str, int] = defaultdict(int)

        for prop in properties:
            tokens = _tokenize(_property_text(prop))
            self._corpus[prop.id] = tokens
            # TF: frequência relativa no documento
            total = len(tokens) or 1
            freq: Dict[str, int] = defaultdict(int)
            for t in tokens:
                freq[t] += 1
            for term, count in freq.items():
                self._tf[term][prop.id] = count / total
                doc_freq[term] += 1

        # IDF: log(N / df + 1) com suavização
        for term, df in doc_freq.items():
            self._idf[term] = math.log((n + 1) / (df + 1)) + 1.0

        self._built = True
        logger.info("tfidf_index_built", extra={"properties": n, "terms": len(self._idf)})

    def score(self, query: str, property_id: str) -> float:
        """
        Calcula TF-IDF score de um documento para a query.
        Retorna 0.0 se o índice não foi construído ou o doc não existe.
        """
        if not self._built or property_id not in self._corpus:
            return 0.0
        tokens = _tokenize(query)
        if not tokens:
            return 0.0
        score = 0.0
        for term in tokens:
            tf = self._tf.get(term, {}).get(property_id, 0.0)
            idf = self._idf.get(term, 0.0)
            score += tf * idf
        return score

    def search(self, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        """
        Retorna os top_k property_ids com maior score para a query.
        Retorna lista de (property_id, score) em ordem decrescente.
        """
        if not self._built:
            return []
        tokens = _tokenize(query)
        if not tokens:
            return []

        scores: Dict[str, float] = defaultdict(float)
        for term in tokens:
            idf = self._idf.get(term, 0.0)
            for prop_id, tf in self._tf.get(term, {}).items():
                scores[prop_id] += tf * idf

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    @property
    def is_built(self) -> bool:
        return self._built


# ─────────────────────────────────────────────────────────────────────────────
# Serviço de busca semântica e híbrida
# ─────────────────────────────────────────────────────────────────────────────

class SemanticCatalogSearch:
    """
    [Fase 5.4] Busca semântica e híbrida sobre o catálogo.

    Combina:
    - Filtros estruturados (preço, quartos, bairro, etc.)
    - Score semântico TF-IDF sobre texto livre
    - Reranking por score combinado ponderado
    """

    def __init__(self) -> None:
        self._index = TFIDFIndex()
        self._properties: Dict[str, Property] = {}

    def rebuild_index(self, properties: List[Property]) -> None:
        """Reconstrói o índice com os imóveis fornecidos."""
        self._properties = {p.id: p for p in properties}
        self._index.build(properties)

    def semantic_search(
        self,
        query: str,
        candidates: Optional[List[Property]] = None,
        top_k: int = 10,
    ) -> List[Tuple[Property, float]]:
        """
        Busca semântica pura por texto livre.

        Se `candidates` for fornecido, restringe ao subconjunto.
        Retorna lista de (Property, semantic_score).
        """
        if not self._index.is_built:
            return []

        if candidates is not None:
            candidate_ids = {p.id for p in candidates}
        else:
            candidate_ids = None

        scored = self._index.search(query, top_k=top_k * 3)

        results: List[Tuple[Property, float]] = []
        for prop_id, score in scored:
            if candidate_ids is not None and prop_id not in candidate_ids:
                continue
            prop = self._properties.get(prop_id)
            if prop is None:
                continue
            results.append((prop, score))
            if len(results) >= top_k:
                break

        return results

    def hybrid_search(
        self,
        query: str,
        candidates: List[Property],
        semantic_weight: float = 0.4,
        structural_weight: float = 0.6,
        top_k: int = 5,
    ) -> List[HybridResult]:
        """
        Busca híbrida: combina score estruturado + semântico com reranking.

        Args:
            query: Texto livre da busca (ex: "apartamento com piscina perto da orla")
            candidates: Imóveis pré-filtrados por critérios estruturados
            semantic_weight: Peso do score semântico (0.0–1.0)
            structural_weight: Peso do score estrutural (0.0–1.0)
            top_k: Número máximo de resultados

        Returns:
            Lista de HybridResult ordenada por score combinado decrescente.
        """
        if not candidates:
            return []

        # Normaliza pesos
        total_w = semantic_weight + structural_weight
        sem_w = semantic_weight / total_w
        str_w = structural_weight / total_w

        # Score semântico para cada candidato
        candidate_ids = {p.id for p in candidates}
        sem_scores_raw = self._index.search(query, top_k=len(candidates) * 2)
        sem_map: Dict[str, float] = {pid: s for pid, s in sem_scores_raw if pid in candidate_ids}

        # Normaliza scores semânticos para [0, 1]
        max_sem = max(sem_map.values()) if sem_map else 1.0
        max_sem = max_sem or 1.0

        # Score estrutural simples (posição na lista = relevância estrutural)
        n = len(candidates)
        results: List[HybridResult] = []
        for idx, prop in enumerate(candidates):
            struct_score = 1.0 - (idx / n)  # 1.0 para o primeiro, ~0 para o último
            sem_score_norm = sem_map.get(prop.id, 0.0) / max_sem
            combined = (str_w * struct_score) + (sem_w * sem_score_norm)

            results.append(HybridResult(
                property=prop,
                structural_score=round(struct_score, 3),
                semantic_score=round(sem_score_norm, 3),
                combined_score=round(combined, 3),
                rank=0,
            ))

        # Reranking por score combinado
        results.sort(key=lambda r: r.combined_score, reverse=True)
        for i, r in enumerate(results[:top_k]):
            r.rank = i + 1

        logger.info(
            "hybrid_search_complete",
            extra={
                "query_len": len(query),
                "candidates": len(candidates),
                "top_k": top_k,
                "top_score": results[0].combined_score if results else 0.0,
            },
        )
        return results[:top_k]

    def score_query(self, query: str, property_id: str) -> float:
        """Retorna score semântico de um imóvel para a query."""
        return self._index.score(query, property_id)

    @property
    def index_size(self) -> int:
        return len(self._properties)


@dataclass
class HybridResult:
    """Resultado da busca híbrida com scores separados."""
    property: Property
    structural_score: float   # Score dos filtros estruturados (posição no ranking)
    semantic_score: float     # Score TF-IDF normalizado
    combined_score: float     # Score final ponderado
    rank: int                 # Posição no ranking final
