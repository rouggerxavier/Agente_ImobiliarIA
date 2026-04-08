from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from .geo_normalizer import location_key


logger = logging.getLogger(__name__)

_CACHE_LOCK = threading.Lock()
_CACHE_SIGNATURE: Optional[Tuple[Tuple[str, int, int], ...]] = None
_CACHE_DOCS: List["KnowledgeDoc"] = []
_CACHE_CHUNKS: List["KnowledgeChunk"] = []
_CACHE_CHUNKS_BY_DOMAIN: Dict[str, List["KnowledgeChunk"]] = {"institutional": [], "geo": []}
_CACHE_GEO_TOKENS: set[str] = set()

_EMBED_CACHE_LOCK = threading.Lock()
_EMBED_CACHE_LOADED = False
_EMBED_CACHE_DIRTY = False
_EMBED_CACHE: Dict[str, List[float]] = {}
_QUERY_EMBED_CACHE: Dict[str, List[float]] = {}
_EMBED_RUNTIME_DISABLED = False
_EMBED_CLIENT = None

_DOMAIN_ALLOWED = {"institutional", "geo"}
_STOPWORDS = {
    "a",
    "ao",
    "aos",
    "as",
    "com",
    "como",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "essa",
    "esse",
    "esta",
    "este",
    "isso",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "ou",
    "para",
    "por",
    "pra",
    "que",
    "se",
    "sem",
    "um",
    "uma",
}
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}

_TOPIC_ALIASES: Dict[str, Tuple[str, ...]] = {
    "financiamento": ("financiamento", "financiar", "banco", "fgts", "entrada", "juros", "parcel"),
    "custos": ("itbi", "cartorio", "registro", "escritura", "taxa", "cust"),
    "visita": ("visita", "agendar", "agenda", "horario"),
    "temporada": ("airbnb", "temporada", "short stay", "locacao por temporada"),
    "condominio": ("condominio", "pet", "mudanca", "reforma", "regra"),
    "processo_compra": ("proposta", "analise", "matricula", "escritura", "etapas", "passo"),
    "glossario": ("matricula", "averbacao", "onus", "habite", "laudemio", "termo"),
    "bairro_guide": ("bairro", "regiao", "orla", "praia", "familia", "valoriz"),
}
_GEO_HINT_TERMS = {
    "bairro",
    "regiao",
    "orla",
    "praia",
    "beira mar",
    "perto da praia",
    "intermares",
    "manaira",
    "tambau",
    "cabo branco",
    "bessa",
    "joao pessoa",
    "cabedelo",
    "bayeux",
    "santa rita",
}
_INSTITUTIONAL_HINT_TERMS = {
    "financiamento",
    "fgts",
    "itbi",
    "cartorio",
    "registro",
    "escritura",
    "documento",
    "documentacao",
    "prazo",
    "proposta",
    "reserva",
    "condominio",
    "visita",
    "sinal",
    "entrada",
}


@dataclass(frozen=True)
class KnowledgeMetadata:
    domain: str
    city: Optional[str]
    neighborhood: Optional[str]
    topic: str
    updated_at: str


@dataclass(frozen=True)
class KnowledgeDoc:
    doc_id: str
    path: str
    title: str
    body: str
    metadata: KnowledgeMetadata
    neighborhood_label: Optional[str]


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    doc_id: str
    path: str
    title: str
    section: str
    text: str
    metadata: KnowledgeMetadata
    tokens: Tuple[str, ...]


@dataclass(frozen=True)
class RetrievalHit:
    chunk: KnowledgeChunk
    score: float


def _strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _normalize_text(text: str) -> str:
    lowered = _strip_accents((text or "").lower())
    lowered = lowered.replace("_", " ").replace("-", " ")
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def _tokenize(text: str) -> Tuple[str, ...]:
    normalized = _normalize_text(text)
    raw = re.findall(r"[a-z0-9]+", normalized)
    return tuple(tok for tok in raw if len(tok) > 1 and tok not in _STOPWORDS)


def _root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _knowledge_dir() -> Path:
    return _root_dir() / "knowledge"


def _scan_markdown_files() -> List[Path]:
    base = _knowledge_dir()
    if not base.exists():
        return []
    files = [p for p in base.rglob("*.md") if p.name.lower() != "readme.md"]
    return sorted(files, key=lambda p: str(p).lower())


def _compute_signature(files: Iterable[Path]) -> Tuple[Tuple[str, int, int], ...]:
    out: List[Tuple[str, int, int]] = []
    for p in files:
        st = p.stat()
        out.append((str(p), st.st_mtime_ns, st.st_size))
    return tuple(out)


def _parse_frontmatter(raw: str) -> Tuple[Dict[str, str], str]:
    raw = raw.lstrip("\ufeff")
    pattern = r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n?(.*)$"
    match = re.match(pattern, raw, flags=re.DOTALL)
    if not match:
        return {}, raw
    front = match.group(1)
    body = match.group(2)
    meta: Dict[str, str] = {}
    for line in front.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip().lower()] = val.strip()
    return meta, body


def _none_if_null(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    val = value.strip()
    if not val:
        return None
    if val.lower() in {"null", "none", "n/a"}:
        return None
    return val


def _normalize_meta(raw_meta: Dict[str, str], path: Path) -> KnowledgeMetadata:
    parts_norm = [_normalize_text(p) for p in path.parts]
    inferred_domain = "geo" if "geo" in parts_norm else "institutional"
    domain = (raw_meta.get("domain") or inferred_domain).strip().lower()
    if domain not in _DOMAIN_ALLOWED:
        domain = inferred_domain

    city = _none_if_null(raw_meta.get("city"))
    neighborhood = _none_if_null(raw_meta.get("neighborhood"))
    topic = (raw_meta.get("topic") or "general").strip().lower()
    updated_at = (raw_meta.get("updated_at") or "1970-01-01").strip()

    if city:
        city = location_key(city).replace(" ", "_")
    if neighborhood:
        neighborhood = location_key(neighborhood).replace(" ", "_")

    return KnowledgeMetadata(
        domain=domain,
        city=city,
        neighborhood=neighborhood,
        topic=topic,
        updated_at=updated_at,
    )


def _extract_title(body: str, fallback: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def _clean_heading_for_label(title: str) -> str:
    cleaned = title.strip()
    cleaned = re.sub(
        r"\s+\((joao pessoa|cabedelo|bayeux|santa rita)\)\s*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def _derive_neighborhood_label(title: str, metadata: KnowledgeMetadata) -> Optional[str]:
    if metadata.domain != "geo" or not metadata.neighborhood:
        return None
    label = _clean_heading_for_label(title)
    if label:
        return label
    return metadata.neighborhood.replace("_", " ").title()


def _split_sections(body: str) -> List[Tuple[str, str]]:
    sections: List[Tuple[str, str]] = []
    cur_title = "Resumo"
    cur_lines: List[str] = []

    for line in body.splitlines():
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            text = "\n".join(cur_lines).strip()
            if text:
                sections.append((cur_title, text))
            cur_title = line[3:].strip() or "Resumo"
            cur_lines = []
            continue
        cur_lines.append(line)

    tail = "\n".join(cur_lines).strip()
    if tail:
        sections.append((cur_title, tail))
    return sections


def _chunk_section_text(section: str, text: str, max_chars: int = 700) -> List[Tuple[str, str]]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if not blocks:
        return []

    out: List[Tuple[str, str]] = []
    cur: List[str] = []
    cur_size = 0
    for block in blocks:
        block_len = len(block)
        if cur and cur_size + block_len + 2 > max_chars:
            out.append((section, "\n\n".join(cur)))
            cur = [block]
            cur_size = block_len
        else:
            cur.append(block)
            cur_size += block_len + (2 if cur else 0)
    if cur:
        out.append((section, "\n\n".join(cur)))
    return out


def _build_geo_token_index(docs: List[KnowledgeDoc]) -> set[str]:
    names: set[str] = set()
    for doc in docs:
        if doc.metadata.domain != "geo":
            continue
        if doc.metadata.city:
            names.add(doc.metadata.city.replace("_", " "))
        if doc.metadata.neighborhood:
            names.add(doc.metadata.neighborhood.replace("_", " "))
    tokens: set[str] = set()
    for name in names:
        normalized = _normalize_text(name)
        if not normalized:
            continue
        tokens.add(normalized)
        for tok in normalized.split():
            if len(tok) > 2:
                tokens.add(tok)
    return tokens


def _build_index() -> Tuple[List[KnowledgeDoc], List[KnowledgeChunk], Dict[str, List[KnowledgeChunk]]]:
    files = _scan_markdown_files()
    docs: List[KnowledgeDoc] = []
    chunks: List[KnowledgeChunk] = []
    chunks_by_domain: Dict[str, List[KnowledgeChunk]] = {"institutional": [], "geo": []}

    for i, path in enumerate(files, start=1):
        raw = path.read_text(encoding="utf-8")
        raw_meta, body = _parse_frontmatter(raw)
        metadata = _normalize_meta(raw_meta, path)
        title = _extract_title(body, path.stem.replace("_", " ").title())
        neighborhood_label = _derive_neighborhood_label(title, metadata)

        rel_path = os.path.relpath(path, _root_dir()).replace("\\", "/")
        doc = KnowledgeDoc(
            doc_id=f"doc_{i:04d}",
            path=rel_path,
            title=title,
            body=body,
            metadata=metadata,
            neighborhood_label=neighborhood_label,
        )
        docs.append(doc)

        sections = _split_sections(body)
        if not sections:
            sections = [("Resumo", body.strip())]

        chunk_counter = 0
        for section_title, section_text in sections:
            for _, text_block in _chunk_section_text(section_title, section_text):
                chunk_counter += 1
                tokens = _tokenize(f"{doc.title} {section_title} {text_block} {metadata.topic}")
                if not tokens:
                    continue
                chunk = KnowledgeChunk(
                    chunk_id=f"{doc.doc_id}_c{chunk_counter:02d}",
                    doc_id=doc.doc_id,
                    path=doc.path,
                    title=doc.title,
                    section=section_title,
                    text=text_block,
                    metadata=metadata,
                    tokens=tokens,
                )
                chunks.append(chunk)
                if metadata.domain in chunks_by_domain:
                    chunks_by_domain[metadata.domain].append(chunk)

    return docs, chunks, chunks_by_domain


def ensure_loaded() -> None:
    global _CACHE_SIGNATURE, _CACHE_DOCS, _CACHE_CHUNKS, _CACHE_CHUNKS_BY_DOMAIN, _CACHE_GEO_TOKENS
    files = _scan_markdown_files()
    signature = _compute_signature(files)
    with _CACHE_LOCK:
        if signature == _CACHE_SIGNATURE:
            return
        docs, chunks, chunks_by_domain = _build_index()
        _CACHE_DOCS = docs
        _CACHE_CHUNKS = chunks
        _CACHE_CHUNKS_BY_DOMAIN = chunks_by_domain
        _CACHE_GEO_TOKENS = _build_geo_token_index(docs)
        _CACHE_SIGNATURE = signature


def list_geo_neighborhoods() -> List[str]:
    ensure_loaded()
    labels: Dict[str, str] = {}
    for doc in _CACHE_DOCS:
        if doc.metadata.domain != "geo" or not doc.metadata.neighborhood:
            continue
        label = doc.neighborhood_label or doc.metadata.neighborhood.replace("_", " ").title()
        key = _normalize_text(label)
        if not key:
            continue
        prev = labels.get(key)
        if not prev:
            labels[key] = label
            continue
        prev_has_non_ascii = any(ord(ch) > 127 for ch in prev)
        new_has_non_ascii = any(ord(ch) > 127 for ch in label)
        if new_has_non_ascii and not prev_has_non_ascii:
            labels[key] = label
    return [labels[k] for k in sorted(labels.keys())]


def _passes_filters(chunk: KnowledgeChunk, filters: Dict[str, Any]) -> bool:
    domain = filters.get("domain")
    if domain and chunk.metadata.domain != str(domain).lower():
        return False

    city = filters.get("city")
    if city:
        city_key = location_key(str(city)).replace(" ", "_")
        if chunk.metadata.city and chunk.metadata.city != city_key:
            return False

    neighborhood = filters.get("neighborhood")
    if neighborhood:
        n_key = location_key(str(neighborhood)).replace(" ", "_")
        if chunk.metadata.neighborhood and chunk.metadata.neighborhood != n_key:
            return False

    topic = filters.get("topic")
    if topic:
        if chunk.metadata.topic != str(topic).strip().lower():
            return False
    return True


def _env_bool(name: str, default: Optional[bool] = None) -> Optional[bool]:
    raw = os.getenv(name)
    if raw is None:
        return default
    val = raw.strip().lower()
    if val in _TRUE_VALUES:
        return True
    if val in _FALSE_VALUES:
        return False
    return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _should_use_embeddings() -> bool:
    flag = _env_bool("KNOWLEDGE_EMBEDDINGS_ENABLED", None)
    if flag is False:
        return False
    if flag is True:
        return bool(os.getenv("OPENAI_API_KEY"))
    return bool(os.getenv("OPENAI_API_KEY"))


def _embedding_model() -> str:
    return os.getenv("KNOWLEDGE_EMBED_MODEL", os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"))


def _embedding_cache_path() -> Path:
    configured = os.getenv("KNOWLEDGE_EMBED_CACHE_PATH", "").strip()
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            path = _root_dir() / path
        return path
    return _root_dir() / "data" / "knowledge_embeddings_cache.json"


def _load_embed_cache() -> None:
    global _EMBED_CACHE_LOADED, _EMBED_CACHE
    with _EMBED_CACHE_LOCK:
        if _EMBED_CACHE_LOADED:
            return
        path = _embedding_cache_path()
        if not path.exists():
            _EMBED_CACHE = {}
            _EMBED_CACHE_LOADED = True
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                parsed: Dict[str, List[float]] = {}
                for key, vec in payload.items():
                    if not isinstance(key, str) or not isinstance(vec, list):
                        continue
                    try:
                        parsed[key] = [float(v) for v in vec]
                    except (TypeError, ValueError):
                        continue
                _EMBED_CACHE = parsed
            else:
                _EMBED_CACHE = {}
        except Exception:
            logger.warning("Falha ao carregar cache de embeddings; seguindo sem cache persistido.")
            _EMBED_CACHE = {}
        _EMBED_CACHE_LOADED = True


def _save_embed_cache_if_dirty() -> None:
    global _EMBED_CACHE_DIRTY
    with _EMBED_CACHE_LOCK:
        if not _EMBED_CACHE_DIRTY:
            return
        path = _embedding_cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(_EMBED_CACHE, ensure_ascii=True), encoding="utf-8")
        tmp.replace(path)
        _EMBED_CACHE_DIRTY = False


def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _chunk_cache_key(chunk: KnowledgeChunk, model: str) -> str:
    return f"{model}:chunk:{chunk.chunk_id}:{_hash_text(chunk.text)}"


def _query_cache_key(query: str, model: str) -> str:
    return f"{model}:query:{_hash_text(query)}"


def _get_embed_client():
    global _EMBED_CLIENT, _EMBED_RUNTIME_DISABLED
    if _EMBED_RUNTIME_DISABLED:
        return None
    if _EMBED_CLIENT is not None:
        return _EMBED_CLIENT
    if not _should_use_embeddings():
        return None

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except Exception:
        logger.warning("Biblioteca OpenAI indisponivel para embeddings; usando apenas lexical.")
        _EMBED_RUNTIME_DISABLED = True
        return None

    try:
        _EMBED_CLIENT = OpenAI(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
        return _EMBED_CLIENT
    except Exception as exc:
        logger.warning("Falha ao iniciar cliente de embeddings: %s", exc)
        _EMBED_RUNTIME_DISABLED = True
        return None


def _request_embedding(text: str, model: str) -> Optional[List[float]]:
    global _EMBED_RUNTIME_DISABLED
    client = _get_embed_client()
    if client is None:
        return None
    try:
        response = client.embeddings.create(model=model, input=text)
        data = getattr(response, "data", None) or []
        if not data:
            return None
        first = data[0]
        embedding = getattr(first, "embedding", None)
        if embedding is None and isinstance(first, dict):
            embedding = first.get("embedding")
        if not isinstance(embedding, list):
            return None
        return [float(v) for v in embedding]
    except Exception as exc:
        logger.warning("Embeddings indisponiveis neste runtime; fallback para lexical. erro=%s", exc)
        _EMBED_RUNTIME_DISABLED = True
        return None


def _get_query_embedding(query_norm: str, model: str) -> Optional[List[float]]:
    key = _query_cache_key(query_norm, model)
    cached = _QUERY_EMBED_CACHE.get(key)
    if cached is not None:
        return cached
    vector = _request_embedding(query_norm, model)
    if vector:
        _QUERY_EMBED_CACHE[key] = vector
    return vector


def _get_chunk_embedding(chunk: KnowledgeChunk, model: str) -> Optional[List[float]]:
    global _EMBED_CACHE_DIRTY
    _load_embed_cache()
    key = _chunk_cache_key(chunk, model)
    with _EMBED_CACHE_LOCK:
        cached = _EMBED_CACHE.get(key)
    if cached is not None:
        return cached

    vector = _request_embedding(chunk.text, model)
    if vector is None:
        return None

    with _EMBED_CACHE_LOCK:
        _EMBED_CACHE[key] = vector
        _EMBED_CACHE_DIRTY = True
    return vector


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for va, vb in zip(a, b):
        dot += va * vb
        norm_a += va * va
        norm_b += vb * vb
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def _infer_topic_hint(query_norm: str) -> Optional[str]:
    best_topic = None
    best_score = 0
    for topic, aliases in _TOPIC_ALIASES.items():
        score = 0
        for alias in aliases:
            if alias in query_norm:
                score += 1
        if score > best_score:
            best_score = score
            best_topic = topic
    return best_topic


def _infer_domain_hint(query_norm: str) -> Optional[str]:
    geo_score = 0
    institutional_score = 0

    for term in _GEO_HINT_TERMS:
        if term in query_norm:
            geo_score += 1
    for term in _INSTITUTIONAL_HINT_TERMS:
        if term in query_norm:
            institutional_score += 1

    for token in _CACHE_GEO_TOKENS:
        if token and token in query_norm:
            geo_score += 1

    if geo_score >= institutional_score + 1 and geo_score > 0:
        return "geo"
    if institutional_score >= geo_score + 1 and institutional_score > 0:
        return "institutional"
    return None


def _lexical_score(q_tokens: set[str], query_norm: str, chunk: KnowledgeChunk) -> float:
    if not q_tokens:
        return 0.0
    chunk_tokens = set(chunk.tokens)
    overlap = q_tokens.intersection(chunk_tokens)
    if not overlap:
        return 0.0

    score = float(len(overlap))
    score += len(overlap) / max(len(q_tokens), 1)

    if chunk.metadata.topic and chunk.metadata.topic in query_norm:
        score += 1.5
    if chunk.metadata.neighborhood and chunk.metadata.neighborhood.replace("_", " ") in query_norm:
        score += 2.0
    if chunk.metadata.city and chunk.metadata.city.replace("_", " ") in query_norm:
        score += 1.0
    return score


def _metadata_boost(
    query_norm: str,
    chunk: KnowledgeChunk,
    *,
    topic_hint: Optional[str],
    domain_hint: Optional[str],
) -> float:
    boost = 0.0
    if chunk.metadata.topic and chunk.metadata.topic in query_norm:
        boost += 0.16
    if topic_hint and chunk.metadata.topic == topic_hint:
        boost += 0.36
    if domain_hint and chunk.metadata.domain == domain_hint:
        boost += 0.10
    if chunk.metadata.neighborhood and chunk.metadata.neighborhood.replace("_", " ") in query_norm:
        boost += 0.40
    if chunk.metadata.city and chunk.metadata.city.replace("_", " ") in query_norm:
        boost += 0.20
    return boost


def _candidate_chunks(filters: Dict[str, Any]) -> List[KnowledgeChunk]:
    domain = str(filters.get("domain") or "").lower()
    base = _CACHE_CHUNKS_BY_DOMAIN.get(domain, _CACHE_CHUNKS)
    out: List[KnowledgeChunk] = []
    for chunk in base:
        if _passes_filters(chunk, filters):
            out.append(chunk)
    return out


def _semantic_candidate_order(
    candidates: List[KnowledgeChunk],
    lexical_scores: Dict[str, float],
    topic_hint: Optional[str],
) -> List[KnowledgeChunk]:
    max_candidates = max(1, _env_int("KNOWLEDGE_SEMANTIC_CANDIDATES", 120))

    def rank(chunk: KnowledgeChunk) -> float:
        score = lexical_scores.get(chunk.chunk_id, 0.0)
        if topic_hint and chunk.metadata.topic == topic_hint:
            score += 1.0
        if chunk.metadata.domain == "geo" and chunk.metadata.neighborhood:
            score += 0.2
        return score

    ordered = sorted(candidates, key=rank, reverse=True)
    return ordered[:max_candidates]


def _semantic_scores(
    query_norm: str,
    candidates: List[KnowledgeChunk],
    lexical_scores: Dict[str, float],
    topic_hint: Optional[str],
) -> Dict[str, float]:
    if not _should_use_embeddings() or _EMBED_RUNTIME_DISABLED:
        return {}
    model = _embedding_model()
    query_vector = _get_query_embedding(query_norm, model)
    if not query_vector:
        return {}

    ordered = _semantic_candidate_order(candidates, lexical_scores, topic_hint)
    scores: Dict[str, float] = {}
    for chunk in ordered:
        vector = _get_chunk_embedding(chunk, model)
        if not vector:
            continue
        sim = _cosine_similarity(query_vector, vector)
        normalized = max(0.0, min(1.0, (sim + 1.0) / 2.0))
        scores[chunk.chunk_id] = normalized

    _save_embed_cache_if_dirty()
    return scores


def retrieve_hybrid(query: str, top_k: int = 3, filters: Optional[Dict[str, Any]] = None) -> List[RetrievalHit]:
    ensure_loaded()
    if not query.strip():
        return []

    active_filters = dict(filters or {})
    query_norm = _normalize_text(query)
    q_tokens = set(_tokenize(query))

    domain_hint = None
    if not active_filters.get("domain"):
        domain_hint = _infer_domain_hint(query_norm)
        if domain_hint:
            active_filters["domain"] = domain_hint

    candidates = _candidate_chunks(active_filters)
    if not candidates:
        return []

    lexical_scores: Dict[str, float] = {}
    max_lexical = 0.0
    for chunk in candidates:
        score = _lexical_score(q_tokens, query_norm, chunk)
        lexical_scores[chunk.chunk_id] = score
        if score > max_lexical:
            max_lexical = score

    topic_hint = _infer_topic_hint(query_norm)
    semantic_scores = _semantic_scores(query_norm, candidates, lexical_scores, topic_hint)

    lexical_weight = _env_float("KNOWLEDGE_LEXICAL_WEIGHT", 0.65)
    semantic_weight = _env_float("KNOWLEDGE_SEMANTIC_WEIGHT", 0.35)
    if not semantic_scores:
        lexical_weight = 1.0
        semantic_weight = 0.0
    total_weight = lexical_weight + semantic_weight
    if total_weight <= 0.0:
        lexical_weight = 1.0
        semantic_weight = 0.0
        total_weight = 1.0
    lexical_weight /= total_weight
    semantic_weight /= total_weight

    hits: List[RetrievalHit] = []
    for chunk in candidates:
        lex_raw = lexical_scores.get(chunk.chunk_id, 0.0)
        lex_norm = (lex_raw / max_lexical) if max_lexical > 0 else 0.0
        sem_norm = semantic_scores.get(chunk.chunk_id, 0.0)
        boost = _metadata_boost(
            query_norm,
            chunk,
            topic_hint=topic_hint,
            domain_hint=domain_hint,
        )
        score = lexical_weight * lex_norm + semantic_weight * sem_norm + boost
        if lex_raw <= 0.0 and sem_norm <= 0.0 and boost <= 0.0:
            continue
        hits.append(RetrievalHit(chunk=chunk, score=score))

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[: max(1, top_k)]


def retrieve(query: str, top_k: int = 3, filters: Optional[Dict[str, Any]] = None) -> List[RetrievalHit]:
    return retrieve_hybrid(query, top_k=top_k, filters=filters)


def _short_text(text: str, max_len: int = 300) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_len:
        return compact
    truncated = compact[:max_len].rstrip()
    return truncated + "..."


def _filter_variants(base_filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    variants: List[Dict[str, Any]] = [dict(base_filters)]
    if "topic" in base_filters:
        relaxed = dict(base_filters)
        relaxed.pop("topic", None)
        variants.append(relaxed)
    if "neighborhood" in base_filters:
        relaxed = dict(base_filters)
        relaxed.pop("neighborhood", None)
        variants.append(relaxed)
    if "city" in base_filters:
        relaxed = dict(base_filters)
        relaxed.pop("city", None)
        variants.append(relaxed)

    seen = set()
    deduped: List[Dict[str, Any]] = []
    for item in variants:
        key = tuple(sorted((k, str(v)) for k, v in item.items()))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def answer_question(
    query: str,
    *,
    city: Optional[str] = None,
    neighborhood: Optional[str] = None,
    domain: Optional[str] = None,
    topic: Optional[str] = None,
    top_k: int = 3,
) -> Optional[Dict[str, Any]]:
    filters: Dict[str, Any] = {}
    if domain:
        filters["domain"] = domain
    if city:
        filters["city"] = city
    if neighborhood:
        filters["neighborhood"] = neighborhood
    if topic:
        filters["topic"] = topic

    hits: List[RetrievalHit] = []
    for variant in _filter_variants(filters):
        hits = retrieve_hybrid(query, top_k=top_k, filters=variant)
        if hits:
            break
    if not hits:
        hits = retrieve_hybrid(query, top_k=top_k, filters=None)
    if not hits:
        return None

    main = hits[0].chunk
    answer = _short_text(main.text, max_len=340)
    answer = f"Em geral, {answer[0].lower() + answer[1:]}" if answer else answer
    if answer and not answer.endswith("."):
        answer += "."
    answer += " Isso pode variar; confirmamos no caso concreto."

    refs: List[str] = []
    seen = set()
    for hit in hits:
        c = hit.chunk
        ref = f"{c.path}#{c.section}"
        if ref in seen:
            continue
        seen.add(ref)
        refs.append(ref)
        if len(refs) == 3:
            break

    return {
        "answer": answer,
        "sources": refs,
        "domain": main.metadata.domain,
        "topic": main.metadata.topic,
    }
