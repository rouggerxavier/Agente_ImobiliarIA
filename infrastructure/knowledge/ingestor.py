"""
[Fase 6 - 12.2] Ingestor: carrega documentos e preserva metadados operacionais.

Suporta:
  - Markdown (.md)
  - Texto puro (.txt)
  - PDF (.pdf) quando `pypdf` ou `PyPDF2` estiver disponivel

Metadados suportados via frontmatter:
  - doc_type
  - valid_until
  - updated_at
  - tags
  - is_public
  - access_level
  - domain
  - city
  - neighborhood
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional


_FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
_KV_RE = re.compile(r"^([A-Za-z0-9_]+)\s*:\s*(.+)$")


@dataclass
class DocumentInput:
    """Documento pronto para indexacao no RAG."""

    doc_id: str
    title: str
    content: str
    doc_type: str
    source_path: Optional[str] = None
    source_url: Optional[str] = None
    valid_until: Optional[str] = None
    updated_at: Optional[str] = None
    version: str = ""
    tags: List[str] = field(default_factory=list)
    is_public: bool = True
    access_level: str = "public"  # public | internal | sensitive
    city: Optional[str] = None
    neighborhood: Optional[str] = None

    def __post_init__(self) -> None:
        self.doc_type = str(self.doc_type or "faq").strip().lower()
        self.access_level = _normalize_access_level(self.access_level, self.is_public)
        self.city = _normalize_location(self.city)
        self.neighborhood = _normalize_location(self.neighborhood)
        deduped_tags: List[str] = []
        seen = set()
        for tag in self.tags:
            normalized = _normalize_tag(tag)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped_tags.append(normalized)
        self.tags = deduped_tags
        if not self.version:
            self.version = _compute_version(self.content)


def load_file(path: str) -> Optional[DocumentInput]:
    """
    Carrega um arquivo e retorna um DocumentInput.

    Arquivos vazios ou formatos nao suportados retornam None.
    """
    file_path = Path(path)
    ext = file_path.suffix.lower()
    if ext not in {".md", ".txt", ".pdf"}:
        return None

    if ext == ".pdf":
        raw = _parse_pdf(file_path)
    else:
        try:
            raw = file_path.read_text(encoding="utf-8")
        except OSError:
            return None

    if not raw or not raw.strip():
        return None

    meta = {}
    content = raw
    if ext in {".md", ".txt"}:
        frontmatter = _FRONTMATTER_RE.match(raw.lstrip("\ufeff"))
        if frontmatter:
            meta = _parse_frontmatter(frontmatter.group(1))
            content = raw[frontmatter.end():]

    content = content.strip()
    if not content:
        return None

    title = _extract_title(content, file_path.stem.replace("_", " ").strip())
    doc_type = str(meta.get("doc_type") or _guess_type(file_path, meta)).strip().lower()
    is_public = _parse_bool(meta.get("is_public"), default=True)
    access_level = meta.get("access_level") or meta.get("permission") or meta.get("scope")

    tags = _parse_tags(meta.get("tags"))
    domain = meta.get("domain")
    if domain:
        tags.append(domain)
    if doc_type:
        tags.append(doc_type)
    if meta.get("topic"):
        tags.append(meta["topic"])
    if meta.get("city"):
        tags.append(meta["city"])
    if meta.get("neighborhood"):
        tags.append(meta["neighborhood"])

    return DocumentInput(
        doc_id=_path_to_id(file_path),
        title=title,
        content=content,
        doc_type=doc_type,
        source_path=str(file_path.as_posix()),
        valid_until=_clean_nullable(meta.get("valid_until")),
        updated_at=_clean_nullable(meta.get("updated_at")),
        tags=tags,
        is_public=is_public,
        access_level=str(access_level or "").strip().lower() or ("public" if is_public else "internal"),
        city=_clean_nullable(meta.get("city")),
        neighborhood=_clean_nullable(meta.get("neighborhood")),
    )


def load_directory(directory: str, recursive: bool = True) -> List[DocumentInput]:
    """Carrega todos os documentos suportados de um diretorio."""
    base = Path(directory)
    if not base.exists():
        return []

    docs: List[DocumentInput] = []
    for path in _iter_supported_files(base, recursive=recursive):
        doc = load_file(str(path))
        if doc is not None:
            docs.append(doc)
    return docs


def build_document(
    *,
    doc_id: str,
    title: str,
    content: str,
    doc_type: str,
    source_path: Optional[str] = None,
    valid_until: Optional[str] = None,
    updated_at: Optional[str] = None,
    tags: Optional[Iterable[str]] = None,
    is_public: bool = True,
    access_level: str = "public",
    city: Optional[str] = None,
    neighborhood: Optional[str] = None,
) -> DocumentInput:
    """Helper utilitario para testes e ingestao programatica."""
    return DocumentInput(
        doc_id=doc_id,
        title=title,
        content=content,
        doc_type=doc_type,
        source_path=source_path,
        valid_until=valid_until,
        updated_at=updated_at,
        tags=list(tags or []),
        is_public=is_public,
        access_level=access_level,
        city=city,
        neighborhood=neighborhood,
    )


def _iter_supported_files(base: Path, recursive: bool) -> Iterable[Path]:
    iterator = base.rglob("*") if recursive else base.glob("*")
    for path in sorted(iterator, key=lambda item: str(item).lower()):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.suffix.lower() not in {".md", ".txt", ".pdf"}:
            continue
        yield path


def _path_to_id(path: Path) -> str:
    base = path.with_suffix("").as_posix().replace("/", "_")
    return re.sub(r"[^A-Za-z0-9_]+", "_", base).strip("_").lower()


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        text = line.strip()
        if text.startswith("#"):
            return text.lstrip("#").strip() or fallback
    return fallback


def _parse_frontmatter(text: str) -> dict:
    parsed = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _KV_RE.match(line)
        if not match:
            continue
        parsed[match.group(1).strip().lower()] = match.group(2).strip()
    return parsed


def _parse_tags(value: Optional[str]) -> List[str]:
    if value is None:
        return []
    raw = str(value).strip()
    if not raw or raw in {"[]", "null", "None"}:
        return []
    raw = raw.strip("[]")
    return [item.strip().strip("'\"") for item in raw.split(",") if item.strip()]


def _normalize_tag(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", "_", normalized)


def _clean_nullable(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() in {"null", "none", "n/a"}:
        return None
    return cleaned


def _normalize_location(value: Optional[str]) -> Optional[str]:
    cleaned = _clean_nullable(value)
    if cleaned is None:
        return None
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = "".join(char for char in cleaned if not unicodedata.combining(char))
    cleaned = cleaned.replace("-", "_").replace(" ", "_")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.lower().strip("_")


def _normalize_access_level(value: str, is_public: bool) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"public", "internal", "sensitive"}:
        return normalized
    return "public" if is_public else "internal"


def _parse_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "sim", "yes", "y"}:
        return True
    if normalized in {"0", "false", "nao", "não", "no", "n"}:
        return False
    return default


def _guess_type(path: Path, meta: dict) -> str:
    normalized = path.as_posix().lower()
    topic = str(meta.get("topic") or "").lower()
    if "geo/" in normalized or meta.get("domain") == "geo":
        return "geo"
    if "financiamento" in normalized or "financiamento" in topic:
        return "financing"
    if "script" in normalized:
        return "script"
    if any(token in normalized for token in ["politica", "policy", "regras", "visita", "reserva"]):
        return "policy"
    if "objec" in normalized or "obje" in normalized:
        return "script"
    return "faq"


def _compute_version(content: str) -> str:
    return hashlib.sha1(content.encode("utf-8")).hexdigest()


def _parse_pdf(path: Path) -> Optional[str]:
    readers = []
    try:
        from pypdf import PdfReader  # type: ignore

        readers.append(PdfReader)
    except Exception:
        pass
    try:
        from PyPDF2 import PdfReader as PdfReaderLegacy  # type: ignore

        readers.append(PdfReaderLegacy)
    except Exception:
        pass

    for reader_cls in readers:
        try:
            reader = reader_cls(str(path))
            pages = []
            for page in getattr(reader, "pages", []):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text.strip())
            content = "\n\n".join(pages).strip()
            if content:
                return content
        except Exception:
            continue
    return None
