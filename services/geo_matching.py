"""Geo matching helpers for legacy property data."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Literal, Mapping, Sequence
from urllib.parse import parse_qs, unquote, urlparse

from agent.geo_normalizer import canonical_city, canonical_neighborhood, location_key

logger = logging.getLogger(__name__)

GeoMatchStatus = Literal["exato", "provavel", "ambiguo", "nao_encontrado"]

_CITY_ALIASES = {
    "rj": "Rio de Janeiro",
    "rio": "Rio de Janeiro",
    "rio de janeiro": "Rio de Janeiro",
    "rio de janeiro rj": "Rio de Janeiro",
    "rio de janeiro - rj": "Rio de Janeiro",
}

_TITLE_NEIGHBORHOOD_PATTERNS = (
    re.compile(
        r"\bem\s+(.+?)(?:\s+(?:para|com|no|na|de|do|da|vista|andar|reformado|mobiliado)\b|$)",
        re.IGNORECASE,
    ),
    re.compile(r"^(.+?)\s*-\s*[A-Za-z]{2}$", re.IGNORECASE),
)


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _truncate(value: str | None, max_length: int | None = None) -> str | None:
    if value is None or max_length is None:
        return value
    return value[:max_length]


def _unique_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _normal_city(value: str | None) -> str | None:
    if not value:
        return None
    key = location_key(value)
    if not key:
        return None
    if key in _CITY_ALIASES:
        return _CITY_ALIASES[key]
    canonical = canonical_city(value)
    if canonical:
        return canonical
    return value.strip()


def _title_city_and_bairro(title: str | None) -> tuple[str | None, str | None]:
    if not title:
        return None, None
    clean = _clean(title)
    if not clean:
        return None, None

    for pattern in _TITLE_NEIGHBORHOOD_PATTERNS:
        match = pattern.search(clean)
        if not match:
            continue
        candidate = _clean(match.group(1))
        if not candidate:
            continue
        if pattern is _TITLE_NEIGHBORHOOD_PATTERNS[1]:
            suffix = _clean(clean.rsplit(" - ", 1)[-1])
            city = _normal_city(suffix)
            if city:
                return city, candidate
        return None, candidate
    return None, None


def _matching_neighborhood_candidates(value: str | None, known: Sequence[str] | None) -> list[str]:
    if not value or not known:
        return []
    key = location_key(value)
    candidates = [item.strip() for item in known if item and location_key(item) == key]
    return _unique_preserve_order(candidates)


def _extract_map_query_text(mapa_url: str | None) -> str | None:
    clean_url = _clean(mapa_url)
    if not clean_url:
        return None
    try:
        parsed = urlparse(clean_url)
    except ValueError:
        return None
    params = parse_qs(parsed.query)
    query = params.get("q", [None])[0]
    if query:
        return _clean(unquote(query))
    return None


def _extract_coordinates_from_text(text: str | None) -> tuple[float | None, float | None]:
    if not text:
        return None, None

    # Accept both comma and dot decimals, with optional spaces.
    match = re.search(r"(-?\d{1,2}[.,]\d+)\s*,\s*(-?\d{1,3}[.,]\d+)", text)
    if not match:
        return None, None

    lat_raw = match.group(1).replace(",", ".")
    lon_raw = match.group(2).replace(",", ".")

    try:
        lat = float(Decimal(lat_raw))
        lon = float(Decimal(lon_raw))
    except (InvalidOperation, ValueError):
        return None, None

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, None
    return lat, lon


def _extract_street_and_number(text: str | None) -> tuple[str | None, str | None]:
    if not text:
        return None, None
    clean = text.strip()
    match = re.search(r"\b(\d{1,6}[A-Za-z]?)\b", clean)
    if not match:
        return clean, None
    number = match.group(1)
    street = clean[: match.start()].strip(" ,.-")
    if not street:
        return clean, number
    return street, number


def _infer_precision(
    *,
    map_query_text: str | None,
    canonical_city: str | None,
    canonical_bairro: str | None,
    latitude: float | None,
    longitude: float | None,
    status: GeoMatchStatus,
) -> str:
    if latitude is not None and longitude is not None:
        return "coordenadas"
    if map_query_text:
        return "endereco_aprox"
    if canonical_city and canonical_bairro and status in {"exato", "provavel"}:
        return "bairro_cidade"
    if canonical_city or canonical_bairro:
        return "parcial"
    return "indisponivel"


@dataclass(slots=True)
class GeoMatchResult:
    """Audit-friendly geo match result for a property row."""

    origem: str
    status: GeoMatchStatus
    score: int
    raw_city: str | None
    raw_bairro: str | None
    raw_uf: str | None
    canonical_city: str | None
    canonical_bairro: str | None
    reasons: list[str] = field(default_factory=list)
    ambiguous_candidates: list[str] = field(default_factory=list)

    def to_model_fields(self) -> dict[str, Any]:
        return {
            "localizacao_origem": self.origem,
            "localizacao_status": self.status,
            "localizacao_score": self.score,
            "localizacao_raw_cidade": self.raw_city,
            "localizacao_raw_bairro": self.raw_bairro,
            "localizacao_raw_uf": self.raw_uf,
            "latitude": None,
            "longitude": None,
        }

    def as_log_payload(self) -> dict[str, Any]:
        return {
            "origem": self.origem,
            "status": self.status,
            "score": self.score,
            "raw_city": self.raw_city,
            "raw_bairro": self.raw_bairro,
            "raw_uf": self.raw_uf,
            "canonical_city": self.canonical_city,
            "canonical_bairro": self.canonical_bairro,
            "reasons": self.reasons,
            "ambiguous_candidates": self.ambiguous_candidates,
        }


def match_legacy_location(
    row: Mapping[str, Any],
    *,
    source: str,
    known_neighborhoods: Sequence[str] | None = None,
) -> GeoMatchResult:
    """Match and score a legacy location row in an audit-friendly way."""

    raw_city = _clean(row.get("cidade"))
    raw_bairro = _clean(row.get("bairro"))
    raw_uf = _clean(row.get("uf"))
    raw_title = _clean(row.get("titulo"))

    reasons: list[str] = []
    ambiguous_candidates: list[str] = []

    city_from_title, bairro_from_title = _title_city_and_bairro(raw_title)
    city = None

    if raw_city:
        city = _normal_city(raw_city)
        if city and location_key(city) != location_key(raw_city):
            reasons.append("city_normalized")
    if not city and raw_uf:
        city = _normal_city(raw_uf)
        if city:
            reasons.append("city_inferred_from_uf")
    if not city and city_from_title:
        city = city_from_title
        reasons.append("city_inferred_from_title")
    if city is None and raw_title:
        reasons.append("city_not_resolved")

    bairro = None
    if raw_bairro:
        candidates = _matching_neighborhood_candidates(raw_bairro, known_neighborhoods)
        if len(candidates) > 1:
            ambiguous_candidates = candidates
        bairro = canonical_neighborhood(raw_bairro, known=known_neighborhoods) or raw_bairro.strip()
        if bairro and location_key(bairro) != location_key(raw_bairro):
            reasons.append("bairro_normalized")
    if not bairro and bairro_from_title:
        bairro = canonical_neighborhood(bairro_from_title, known=known_neighborhoods) or bairro_from_title.strip()
        reasons.append("bairro_inferred_from_title")
    if bairro is None and raw_title:
        reasons.append("bairro_not_resolved")

    if raw_city and raw_uf and city and city_from_title is None:
        city_from_uf = _normal_city(raw_uf)
        if city_from_uf and location_key(city_from_uf) != location_key(city):
            reasons.append("city_conflict_with_uf")
            return GeoMatchResult(
                origem=source,
                status="ambiguo",
                score=40,
                raw_city=raw_city,
                raw_bairro=raw_bairro,
                raw_uf=raw_uf,
                canonical_city=city,
                canonical_bairro=bairro,
                reasons=reasons or ["city_conflict_with_uf"],
                ambiguous_candidates=ambiguous_candidates,
            )

    if ambiguous_candidates:
        reasons.append("bairro_ambiguous_candidates")
        return GeoMatchResult(
            origem=source,
            status="ambiguo",
            score=45,
            raw_city=raw_city,
            raw_bairro=raw_bairro,
            raw_uf=raw_uf,
            canonical_city=city,
            canonical_bairro=bairro,
            reasons=reasons,
            ambiguous_candidates=ambiguous_candidates,
        )

    city_is_exact = bool(raw_city and city and location_key(raw_city) == location_key(city))
    bairro_is_exact = bool(raw_bairro and bairro and location_key(raw_bairro) == location_key(bairro))

    if city and bairro:
        used_fallback = not city_is_exact or not bairro_is_exact
        status: GeoMatchStatus = "provavel" if used_fallback else "exato"
        score = 100 if status == "exato" else 85
        if status == "exato":
            reasons.append("exact_match")
        else:
            reasons.append("probable_match")
        result = GeoMatchResult(
            origem=source,
            status=status,
            score=score,
            raw_city=raw_city,
            raw_bairro=raw_bairro,
            raw_uf=raw_uf,
            canonical_city=city,
            canonical_bairro=bairro,
            reasons=reasons,
        )
        logger.debug("geo_match=%s", result.as_log_payload())
        return result

    if city or bairro:
        reasons.append("partial_match")
        result = GeoMatchResult(
            origem=source,
            status="provavel",
            score=70,
            raw_city=raw_city,
            raw_bairro=raw_bairro,
            raw_uf=raw_uf,
            canonical_city=city,
            canonical_bairro=bairro,
            reasons=reasons,
        )
        logger.debug("geo_match=%s", result.as_log_payload())
        return result

    result = GeoMatchResult(
        origem=source,
        status="nao_encontrado",
        score=0,
        raw_city=raw_city,
        raw_bairro=raw_bairro,
        raw_uf=raw_uf,
        canonical_city=None,
        canonical_bairro=None,
        reasons=reasons or ["location_not_found"],
    )
    logger.debug("geo_match=%s", result.as_log_payload())
    return result


def enrich_imovel_payload(
    payload: Mapping[str, Any],
    *,
    source: str,
    raw_row: Mapping[str, Any] | None = None,
    known_neighborhoods: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Attach geo audit fields to a property payload."""

    source_row = raw_row or payload
    result = match_legacy_location(source_row, source=source, known_neighborhoods=known_neighborhoods)
    enriched = dict(payload)
    raw_map_url = _clean(source_row.get("mapa_url"))
    map_query_text = _extract_map_query_text(raw_map_url)
    latitude, longitude = _extract_coordinates_from_text(map_query_text)
    street, number = _extract_street_and_number(map_query_text)
    precision = _infer_precision(
        map_query_text=map_query_text,
        canonical_city=result.canonical_city,
        canonical_bairro=result.canonical_bairro,
        latitude=latitude,
        longitude=longitude,
        status=result.status,
    )

    if result.canonical_city:
        enriched["cidade"] = _truncate(result.canonical_city, 120)
    if result.canonical_bairro:
        enriched["bairro"] = _truncate(result.canonical_bairro, 120)
    if raw_map_url:
        enriched["mapa_url"] = _truncate(raw_map_url, 500)

    enriched.update(result.to_model_fields())
    enriched["uf"] = _truncate(_clean(source_row.get("uf")), 8)
    enriched["endereco"] = _truncate(street, 255)
    enriched["endereco_formatado"] = _truncate(map_query_text, 255)
    enriched["logradouro"] = _truncate(street, 180)
    enriched["numero"] = _truncate(number, 40)
    enriched["complemento"] = None
    enriched["cep"] = None
    enriched["ponto_referencia"] = None
    enriched["latitude"] = latitude
    enriched["longitude"] = longitude
    enriched["localizacao_precisao"] = precision
    logger.debug(
        "geo_payload_enriched codigo=%s payload=%s",
        enriched.get("codigo"),
        result.as_log_payload(),
    )
    return enriched
