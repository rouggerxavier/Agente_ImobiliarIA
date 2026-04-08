"""
[Fase 6 - 12.3] Motor local de recuperacao com TF-IDF + reranking leve.

Sem dependencias externas:
  - indexacao por chunks
  - busca lexical vetorizada por TF-IDF
  - filtros por tipo de documento, permissao e validade
  - reranking por cobertura e metadados
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Iterable, List, Optional, Set

from infrastructure.knowledge.chunker import Chunk, chunk_document
from infrastructure.knowledge.ingestor import DocumentInput


_STOPWORDS_PT: Set[str] = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos",
    "e", "em", "essa", "esse", "esta", "este", "isso", "na", "nas", "no",
    "nos", "o", "os", "ou", "para", "por", "pra", "que", "se", "sem",
    "um", "uma", "uns", "umas", "à", "às", "é", "são", "foi", "ser",
}


@dataclass
class RetrievedChunk:
    """Chunk recuperado com scores de suporte."""

    chunk: Chunk
    score: float
    rank: int
    lexical_score: float = 0.0
    coverage_score: float = 0.0


@dataclass
class RetrievalResult:
    """Resultado de busca no indice."""

    chunks: List[RetrievedChunk] = field(default_factory=list)
    query_tokens: List[str] = field(default_factory=list)
    total_indexed: int = 0
    filters_applied: Dict[str, str] = field(default_factory=dict)

    @property
    def texts(self) -> List[str]:
        return [item.chunk.text for item in self.chunks]

    @property
    def sources(self) -> List[str]:
        refs: List[str] = []
        for item in self.chunks:
            path = item.chunk.source_path or item.chunk.doc_id
            refs.append(f"{path}#{item.chunk.section}")
        return refs


class RAGIndex:
    """Indice em memoria com TF-IDF sobre chunks do corpus."""

    def __init__(self) -> None:
        self._documents: Dict[str, DocumentInput] = {}
        self._chunks: List[Chunk] = []
        self._chunk_vectors: List[Dict[str, float]] = []
        self._chunk_norms: List[float] = []
        self._idf: Dict[str, float] = {}
        self._token_sets: List[Set[str]] = []
        self._known_locations: Set[str] = set()
        self._built = False

    def replace_documents(self, docs: Iterable[DocumentInput]) -> None:
        self._documents = {doc.doc_id: doc for doc in docs}
        self._rebuild()

    def add_documents(self, docs: Iterable[DocumentInput]) -> None:
        for doc in docs:
            self._documents[doc.doc_id] = doc
        self._rebuild()

    def upsert_document(self, doc: DocumentInput) -> None:
        self._documents[doc.doc_id] = doc
        self._rebuild()

    def remove_document(self, doc_id: str) -> None:
        self._documents.pop(doc_id, None)
        self._rebuild()

    def doc_ids(self) -> List[str]:
        return sorted(self._documents.keys())

    @property
    def size(self) -> int:
        return len(self._chunks)

    @property
    def known_locations(self) -> Set[str]:
        return set(self._known_locations)

    def search(
        self,
        query: str,
        top_k: int = 3,
        *,
        doc_type_filter: Optional[str] = None,
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
        require_public: bool = True,
        access_level: Optional[str] = None,
        today: Optional[date] = None,
        tags: Optional[Iterable[str]] = None,
    ) -> RetrievalResult:
        if not self._built or not self._chunks or not (query or "").strip():
            return RetrievalResult(total_indexed=len(self._chunks))

        today = today or date.today()
        query_tokens = _tokenize(query)
        if not query_tokens:
            return RetrievalResult(total_indexed=len(self._chunks))

        active_tags = {_normalize_meta_value(tag) for tag in (tags or []) if _normalize_meta_value(tag)}
        filters: Dict[str, str] = {}
        if doc_type_filter:
            filters["doc_type"] = doc_type_filter
        if city:
            filters["city"] = city
        if neighborhood:
            filters["neighborhood"] = neighborhood
        if require_public:
            filters["public"] = "true"
        if access_level:
            filters["access_level"] = access_level

        q_vector, q_norm = self._query_vector(query_tokens)
        scored: List[tuple[float, float, int]] = []
        for idx, chunk in enumerate(self._chunks):
            if not _matches_filters(
                chunk,
                doc_type_filter=doc_type_filter,
                city=city,
                neighborhood=neighborhood,
                require_public=require_public,
                access_level=access_level,
                today=today,
                tags=active_tags,
            ):
                continue
            lexical = _cosine_similarity(q_vector, q_norm, self._chunk_vectors[idx], self._chunk_norms[idx])
            coverage = _coverage_score(set(query_tokens), self._token_sets[idx])
            boost = _metadata_boost(chunk, city=city, neighborhood=neighborhood, query_tokens=set(query_tokens))
            score = lexical + (coverage * 0.25) + boost
            if score <= 0:
                continue
            scored.append((score, coverage, idx))

        scored.sort(key=lambda item: item[0], reverse=True)
        results: List[RetrievedChunk] = []
        for rank, (score, coverage, idx) in enumerate(scored[: max(1, top_k)], start=1):
            lexical = _cosine_similarity(q_vector, q_norm, self._chunk_vectors[idx], self._chunk_norms[idx])
            results.append(
                RetrievedChunk(
                    chunk=self._chunks[idx],
                    score=round(score, 4),
                    rank=rank,
                    lexical_score=round(lexical, 4),
                    coverage_score=round(coverage, 4),
                )
            )
        return RetrievalResult(
            chunks=results,
            query_tokens=query_tokens,
            total_indexed=len(self._chunks),
            filters_applied=filters,
        )

    def _rebuild(self) -> None:
        self._chunks = []
        for doc in self._documents.values():
            self._chunks.extend(chunk_document(doc))

        token_lists = [_tokenize(_chunk_text_for_index(chunk)) for chunk in self._chunks]
        self._token_sets = [set(tokens) for tokens in token_lists]
        df: Dict[str, int] = defaultdict(int)
        for tokens in self._token_sets:
            for token in tokens:
                df[token] += 1

        total_docs = max(len(self._chunks), 1)
        self._idf = {
            token: math.log((1 + total_docs) / (1 + freq)) + 1.0
            for token, freq in df.items()
        }

        self._chunk_vectors = []
        self._chunk_norms = []
        for tokens in token_lists:
            tf = Counter(tokens)
            total_terms = max(sum(tf.values()), 1)
            vector = {
                token: (count / total_terms) * self._idf.get(token, 0.0)
                for token, count in tf.items()
            }
            norm = math.sqrt(sum(weight * weight for weight in vector.values()))
            self._chunk_vectors.append(vector)
            self._chunk_norms.append(norm)

        locations: Set[str] = set()
        for chunk in self._chunks:
            for candidate in (chunk.city, chunk.neighborhood):
                normalized = _normalize_meta_value(candidate)
                if normalized:
                    locations.add(normalized.replace("_", " "))
        self._known_locations = locations
        self._built = True

    def _query_vector(self, query_tokens: List[str]) -> tuple[Dict[str, float], float]:
        tf = Counter(query_tokens)
        total_terms = max(sum(tf.values()), 1)
        vector = {
            token: (count / total_terms) * self._idf.get(token, 0.0)
            for token, count in tf.items()
            if token in self._idf
        }
        norm = math.sqrt(sum(weight * weight for weight in vector.values()))
        return vector, norm


def _chunk_text_for_index(chunk: Chunk) -> str:
    parts = [
        chunk.doc_type,
        chunk.title,
        chunk.section,
        chunk.text,
        " ".join(chunk.tags or []),
        chunk.city or "",
        chunk.neighborhood or "",
    ]
    return " ".join(part for part in parts if part)


def _tokenize(text: str) -> List[str]:
    normalized = unicodedata.normalize("NFKD", (text or "").lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    return [token for token in normalized.split() if len(token) > 1 and token not in _STOPWORDS_PT]


def _coverage_score(query_tokens: Set[str], chunk_tokens: Set[str]) -> float:
    if not query_tokens or not chunk_tokens:
        return 0.0
    return len(query_tokens & chunk_tokens) / max(len(query_tokens), 1)


def _cosine_similarity(
    left: Dict[str, float],
    left_norm: float,
    right: Dict[str, float],
    right_norm: float,
) -> float:
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    dot = 0.0
    if len(left) > len(right):
        left, right = right, left
    for token, weight in left.items():
        dot += weight * right.get(token, 0.0)
    return dot / (left_norm * right_norm)


def _normalize_meta_value(value: Optional[str]) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKD", str(value).strip().lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.replace(" ", "_").replace("-", "_")
    return re.sub(r"_+", "_", normalized).strip("_")


def _matches_filters(
    chunk: Chunk,
    *,
    doc_type_filter: Optional[str],
    city: Optional[str],
    neighborhood: Optional[str],
    require_public: bool,
    access_level: Optional[str],
    today: date,
    tags: Set[str],
) -> bool:
    if doc_type_filter and chunk.doc_type != str(doc_type_filter).strip().lower():
        return False
    if require_public and not chunk.is_public:
        return False
    if access_level and chunk.access_level != str(access_level).strip().lower():
        return False
    if city and _normalize_meta_value(chunk.city) != _normalize_meta_value(city):
        return False
    if neighborhood and _normalize_meta_value(chunk.neighborhood) != _normalize_meta_value(neighborhood):
        return False
    if chunk.valid_until:
        try:
            if date.fromisoformat(chunk.valid_until) < today:
                return False
        except ValueError:
            pass
    if tags:
        chunk_tags = {_normalize_meta_value(tag) for tag in chunk.tags or []}
        if not tags.issubset(chunk_tags):
            return False
    return True


def _metadata_boost(
    chunk: Chunk,
    *,
    city: Optional[str],
    neighborhood: Optional[str],
    query_tokens: Set[str],
) -> float:
    boost = 0.0
    section = _normalize_meta_value(chunk.section)
    if city and _normalize_meta_value(chunk.city) == _normalize_meta_value(city):
        boost += 0.08
    if neighborhood and _normalize_meta_value(chunk.neighborhood) == _normalize_meta_value(neighborhood):
        boost += 0.12
    chunk_tags = {_normalize_meta_value(tag) for tag in chunk.tags or []}
    if query_tokens & chunk_tags:
        boost += 0.05
    if section in {"resumo", "analise", "perfil"}:
        boost += 0.06
    if section in {"aviso", "como_responder_no_atendimento"}:
        boost -= 0.05
    return boost
