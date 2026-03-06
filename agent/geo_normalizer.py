from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Optional


CITY_ALIASES = {
    "joao pessoa": "Joao Pessoa",
    "jp": "Joao Pessoa",
    "cabedelo": "Cabedelo",
    "bayeux": "Bayeux",
    "santa rita": "Santa Rita",
    "campina grande": "Campina Grande",
    "recife": "Recife",
    "natal": "Natal",
}

_LOWER_TOKENS = {"da", "de", "do", "das", "dos", "e"}


def strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def location_key(text: str | None) -> str:
    normalized = strip_accents((text or "").lower())
    normalized = normalized.replace("_", " ").replace("-", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def has_non_ascii(text: str) -> bool:
    return any(ord(ch) > 127 for ch in text)


def _title_case_pt(text: str) -> str:
    words = [w for w in location_key(text).split(" ") if w]
    out = []
    for idx, word in enumerate(words):
        if idx > 0 and word in _LOWER_TOKENS:
            out.append(word)
        else:
            out.append(word.capitalize())
    return " ".join(out)


def preferred_label(existing: Optional[str], candidate: str) -> str:
    if not existing:
        return candidate
    if has_non_ascii(candidate) and not has_non_ascii(existing):
        return candidate
    if has_non_ascii(existing) and not has_non_ascii(candidate):
        return existing
    if existing.islower() and not candidate.islower():
        return candidate
    return existing


def canonical_city(value: str | None) -> Optional[str]:
    key = location_key(value)
    if not key:
        return None
    return CITY_ALIASES.get(key) or _title_case_pt(key)


def canonical_neighborhood(value: str | None, known: Optional[Iterable[str]] = None) -> Optional[str]:
    key = location_key(value)
    if not key:
        return None
    if known:
        choice: Optional[str] = None
        for item in known:
            raw = str(item or "").strip()
            if not raw:
                continue
            if location_key(raw) == key:
                choice = preferred_label(choice, raw)
        if choice:
            return choice
    return _title_case_pt(key)

