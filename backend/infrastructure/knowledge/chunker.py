"""
[Fase 6 - 12.2] Chunker para documentos da base de conhecimento.

Estrategia:
  - Markdown: separa por secoes (`##` / `###`)
  - TXT/PDF: separa por paragrafos com sobreposicao
  - Preserva metadados operacionais do documento
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from infrastructure.knowledge.ingestor import DocumentInput


MIN_CHARS = 60
MAX_CHARS = 1200
OVERLAP_CHARS = 80


@dataclass
class Chunk:
    """Unidade de recuperacao da base de conhecimento."""

    chunk_id: str
    doc_id: str
    doc_type: str
    title: str
    section: str
    text: str
    tags: List[str] = field(default_factory=list)
    valid_until: Optional[str] = None
    is_public: bool = True
    access_level: str = "public"
    source_path: Optional[str] = None
    version: str = ""
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    updated_at: Optional[str] = None


def chunk_document(doc: DocumentInput) -> List[Chunk]:
    """Transforma um documento em chunks semanticamente coerentes."""
    content = (doc.content or "").strip()
    if not content:
        return []
    if _is_markdown(content):
        return _chunk_markdown(doc)
    return _chunk_plain(doc)


def _is_markdown(content: str) -> bool:
    return bool(re.search(r"^#{1,3}\s", content, re.MULTILINE))


def _chunk_markdown(doc: DocumentInput) -> List[Chunk]:
    content = re.sub(r"^---\n.*?\n---\n", "", doc.content, flags=re.DOTALL)
    section_pattern = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)
    parts = section_pattern.split(content)

    chunks: List[Chunk] = []
    current_section = "Resumo"
    buffer = ""
    idx = 0

    def flush() -> None:
        nonlocal buffer, idx
        text = buffer.strip()
        if len(text) < MIN_CHARS:
            buffer = ""
            return
        if len(text) <= MAX_CHARS:
            chunks.append(_build_chunk(doc, idx, current_section, text))
            idx += 1
            buffer = ""
            return
        for piece in _split_paragraphs(text):
            piece = piece.strip()
            if len(piece) < MIN_CHARS:
                continue
            chunks.append(_build_chunk(doc, idx, current_section, piece))
            idx += 1
        buffer = ""

    for part in parts:
        if section_pattern.match(part):
            flush()
            current_section = part.lstrip("#").strip() or "Resumo"
            continue
        buffer = f"{buffer}\n{part}".strip()
        if len(buffer) > MAX_CHARS:
            flush()

    flush()
    return chunks


def _chunk_plain(doc: DocumentInput) -> List[Chunk]:
    paragraphs = _split_paragraphs(doc.content)
    chunks: List[Chunk] = []
    buffer = ""
    idx = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        candidate = f"{buffer}\n\n{para}".strip() if buffer else para
        if len(candidate) <= MAX_CHARS:
            buffer = candidate
            continue

        if len(buffer) >= MIN_CHARS:
            chunks.append(_build_chunk(doc, idx, "", buffer))
            idx += 1
            overlap = buffer[-OVERLAP_CHARS:] if len(buffer) > OVERLAP_CHARS else buffer
            buffer = f"{overlap}\n\n{para}".strip()
        else:
            buffer = para

    if len(buffer.strip()) >= MIN_CHARS:
        chunks.append(_build_chunk(doc, idx, "", buffer.strip()))
    return chunks


def _build_chunk(doc: DocumentInput, idx: int, section: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=f"{doc.doc_id}#{idx}",
        doc_id=doc.doc_id,
        doc_type=doc.doc_type,
        title=doc.title,
        section=section or "Resumo",
        text=text.strip(),
        tags=list(doc.tags),
        valid_until=doc.valid_until,
        is_public=doc.is_public,
        access_level=doc.access_level,
        source_path=doc.source_path,
        version=doc.version,
        city=doc.city,
        neighborhood=doc.neighborhood,
        updated_at=doc.updated_at,
    )


def _split_paragraphs(text: str) -> List[str]:
    return re.split(r"\n{2,}", text)
