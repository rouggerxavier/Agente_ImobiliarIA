"""
[M3 / Fase 5.2] Pipeline de ingestão do catálogo de imóveis.

Responsabilidades:
- Importar imóveis a partir de dicts (JSON, CSV, API externa)
- Validar qualidade mínima antes de publicar
- Normalizar bairros, cidades e tipos
- Detectar e tratar duplicidades via external_ref
- Atualização incremental (upsert)
- Arquivamento de imóveis removidos de uma carga completa
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from domain.entities import Property, PropertyAmenities
from domain.enums import PropertyPurpose, PropertyStatus, PropertyType
from domain.repositories import PropertyRepository
from core.trace import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Normalização de valores canônicos
# ─────────────────────────────────────────────────────────────────────────────

_PROPERTY_TYPE_MAP: Dict[str, PropertyType] = {
    "apartamento": PropertyType.APARTMENT,
    "apto": PropertyType.APARTMENT,
    "ap": PropertyType.APARTMENT,
    "flat": PropertyType.APARTMENT,
    "casa": PropertyType.HOUSE,
    "sobrado": PropertyType.HOUSE,
    "cobertura": PropertyType.PENTHOUSE,
    "penthouse": PropertyType.PENTHOUSE,
    "studio": PropertyType.STUDIO,
    "kitnet": PropertyType.STUDIO,
    "loft": PropertyType.STUDIO,
    "comercial": PropertyType.COMMERCIAL,
    "sala": PropertyType.COMMERCIAL,
    "loja": PropertyType.COMMERCIAL,
    "galpão": PropertyType.COMMERCIAL,
    "terreno": PropertyType.LAND,
    "lote": PropertyType.LAND,
    "chácara": PropertyType.RURAL,
    "rural": PropertyType.RURAL,
    "sítio": PropertyType.RURAL,
}

_CITY_NORMALIZATION: Dict[str, str] = {
    "joao pessoa": "João Pessoa",
    "joão pessoa": "João Pessoa",
    "jp": "João Pessoa",
    "cabedelo": "Cabedelo",
    "bayeux": "Bayeux",
    "santa rita": "Santa Rita",
    "conde": "Conde",
    "pitimbu": "Pitimbu",
    "campina grande": "Campina Grande",
}


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def normalize_city(raw: str) -> str:
    """Normaliza nome de cidade para forma canônica."""
    key = raw.strip().lower()
    return _CITY_NORMALIZATION.get(key, raw.strip().title())


def normalize_property_type(raw: str) -> PropertyType:
    """Normaliza tipo de imóvel para enum canônico."""
    key = str(raw or "").strip().lower()
    return _PROPERTY_TYPE_MAP.get(key, PropertyType.APARTMENT)


def normalize_purpose(item: Dict[str, Any]) -> PropertyPurpose:
    """Infere finalidade (venda/aluguel/ambos) a partir dos campos do dict."""
    raw_purpose = str(item.get("finalidade") or item.get("purpose") or "").lower()
    if "venda" in raw_purpose and "aluguel" in raw_purpose:
        return PropertyPurpose.BOTH
    if "venda" in raw_purpose or "compra" in raw_purpose or "sale" in raw_purpose:
        return PropertyPurpose.SALE
    if "aluguel" in raw_purpose or "locacao" in raw_purpose or "locação" in raw_purpose or "rent" in raw_purpose:
        return PropertyPurpose.RENT

    # Infere pelos preços quando finalidade não está explícita
    sale_price = _to_int(_first_present(item.get("preco_venda"), item.get("price"))) or 0
    rent_price = _to_int(_first_present(item.get("preco_aluguel"), item.get("rent_price"))) or 0
    if sale_price and rent_price:
        return PropertyPurpose.BOTH
    if rent_price:
        return PropertyPurpose.RENT
    return PropertyPurpose.SALE


# ─────────────────────────────────────────────────────────────────────────────
# Validação de qualidade
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def validate_property_data(item: Dict[str, Any]) -> ValidationResult:
    """
    Valida qualidade mínima do registro antes de publicar.
    Errors bloqueiam a ingestão; warnings apenas logam.
    """
    errors: List[str] = []
    warnings: List[str] = []

    city = item.get("cidade") or item.get("city") or ""
    if not city:
        errors.append("Campo obrigatório ausente: cidade")

    prop_type = item.get("tipo") or item.get("tipo_imovel") or item.get("property_type") or ""
    if not prop_type:
        errors.append("Campo obrigatório ausente: tipo")

    sale_price = _to_int(_first_present(item.get("preco_venda"), item.get("price"))) or 0
    rent_price = _to_int(_first_present(item.get("preco_aluguel"), item.get("rent_price"))) or 0
    if not sale_price and not rent_price:
        warnings.append("Imóvel sem preço definido — não aparecerá em buscas por orçamento")

    neighborhood = item.get("bairro") or item.get("neighborhood") or ""
    if not neighborhood:
        warnings.append("Bairro ausente — busca por bairro não funcionará")

    if sale_price and sale_price < 10_000:
        warnings.append(f"Preço de venda suspeito: R$ {sale_price:,.0f}")

    if rent_price and rent_price < 200:
        warnings.append(f"Preço de aluguel suspeito: R$ {rent_price:,.0f}")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


# ─────────────────────────────────────────────────────────────────────────────
# Conversão de dict raw → entidade Property
# ─────────────────────────────────────────────────────────────────────────────

def dict_to_property(item: Dict[str, Any]) -> Property:
    """Converte dict raw (qualquer origem) para entidade Property."""
    external_ref = str(_first_present(item.get("id"), item.get("codigo"), item.get("external_ref")) or "")
    city = normalize_city(str(_first_present(item.get("cidade"), item.get("city")) or ""))
    neighborhood = str(_first_present(item.get("bairro"), item.get("neighborhood")) or "")
    prop_type = normalize_property_type(
        _first_present(item.get("tipo"), item.get("tipo_imovel"), item.get("property_type")) or ""
    )
    purpose = normalize_purpose(item)

    amenities_raw = item.get("amenidades") or item.get("amenities") or {}
    if isinstance(amenities_raw, list):
        # Lista de strings — ex: ["piscina", "academia"]
        amen_dict: Dict[str, bool] = {}
        for tag in amenities_raw:
            tag_l = tag.lower()
            if "piscina" in tag_l or "pool" in tag_l:
                amen_dict["has_pool"] = True
            elif "academia" in tag_l or "gym" in tag_l:
                amen_dict["has_gym"] = True
            elif "playground" in tag_l:
                amen_dict["has_playground"] = True
            elif "salão" in tag_l or "party" in tag_l:
                amen_dict["has_party_room"] = True
            elif "gourmet" in tag_l:
                amen_dict["has_gourmet_area"] = True
            elif "sauna" in tag_l:
                amen_dict["has_sauna"] = True
            elif "portaria" in tag_l or "doorman" in tag_l:
                amen_dict["has_doorman"] = True
            elif "elevador" in tag_l or "elevator" in tag_l:
                amen_dict["has_elevator"] = True
            elif "varanda" in tag_l or "balcony" in tag_l:
                amen_dict["has_balcony"] = True
            elif "vista" in tag_l or "view" in tag_l:
                amen_dict["has_view"] = True
        amenities = PropertyAmenities(**amen_dict)
    elif isinstance(amenities_raw, dict):
        amenities = PropertyAmenities(**{k: v for k, v in amenities_raw.items() if k in PropertyAmenities.model_fields})
    else:
        amenities = PropertyAmenities(
            has_pool=bool(_first_present(item.get("piscina"), item.get("has_pool"))),
            has_gym=bool(_first_present(item.get("academia"), item.get("has_gym"))),
            has_playground=bool(_first_present(item.get("playground"), item.get("has_playground"))),
            has_party_room=bool(_first_present(item.get("salao_festas"), item.get("has_party_room"))),
            has_gourmet_area=bool(_first_present(item.get("gourmet"), item.get("has_gourmet_area"))),
            has_sauna=bool(_first_present(item.get("sauna"), item.get("has_sauna"))),
            has_doorman=bool(_first_present(item.get("portaria"), item.get("has_doorman"))),
            has_elevator=bool(_first_present(item.get("elevador"), item.get("has_elevator"))),
            has_balcony=bool(_first_present(item.get("varanda"), item.get("has_balcony"))),
            has_view=bool(_first_present(item.get("vista"), item.get("has_view"))),
        )

    title = _first_present(item.get("titulo"), item.get("title")) or ""
    description = _first_present(item.get("descricao"), item.get("descricao_curta"), item.get("description")) or ""

    return Property(
        external_ref=external_ref or None,
        city=city,
        neighborhood=neighborhood,
        address=_first_present(item.get("endereco"), item.get("address")),
        micro_location=_first_present(item.get("micro_location"), item.get("localizacao_micro")),
        property_type=prop_type,
        purpose=purpose,
        area_m2=_to_float(_first_present(item.get("area_m2"), item.get("area"))),
        bedrooms=_to_int(_first_present(item.get("quartos"), item.get("bedrooms"))),
        suites=_to_int(item.get("suites")),
        bathrooms=_to_int(_first_present(item.get("banheiros"), item.get("bathrooms"))),
        parking=_to_int(_first_present(item.get("vagas"), item.get("parking"))),
        floor=_to_int(_first_present(item.get("andar"), item.get("floor"))),
        total_floors=_to_int(_first_present(item.get("total_andares"), item.get("total_floors"))),
        price=_to_int(_first_present(item.get("preco_venda"), item.get("price"))),
        rent_price=_to_int(_first_present(item.get("preco_aluguel"), item.get("rent_price"))),
        condo_fee=_to_int(_first_present(item.get("condominio"), item.get("condo_fee"))),
        iptu_annual=_to_int(_first_present(item.get("iptu"), item.get("iptu_annual"))),
        furnished=_to_bool(_first_present(item.get("mobiliado"), item.get("furnished"))),
        pet_friendly=_to_bool(_first_present(item.get("aceita_pet"), item.get("pet_friendly"))),
        allows_short_term_rental=_to_bool(_first_present(item.get("permite_temporada"), item.get("allows_short_term_rental"))),
        sun_position=_first_present(item.get("sol"), item.get("sun_position")),
        amenities=amenities,
        description=description or None,
        highlights=[title] if title else [],
        status=PropertyStatus.AVAILABLE,
        broker_id=str(_first_present(item.get("corretor_id"), item.get("broker_id")) or "") or None,
        internal_notes=_first_present(item.get("observacoes_internas"), item.get("internal_notes")),
        cost_price=_to_int(_first_present(item.get("preco_custo"), item.get("cost_price"))),
        owner_name=_first_present(item.get("proprietario"), item.get("owner_name")),
        owner_phone=_first_present(item.get("telefone_proprietario"), item.get("owner_phone")),
        commission_pct=_to_float(_first_present(item.get("comissao_pct"), item.get("commission_pct"))),
    )


def _to_int(value: Any) -> Optional[int]:
    number = _to_float(value)
    return int(round(number)) if number is not None else None


def _to_float(value: Any) -> Optional[float]:
    if value in (None, "", "null"):
        return None
    try:
        if isinstance(value, bool):
            return float(int(value))
        if isinstance(value, (int, float)):
            return float(value)
        normalized = str(value).strip()
        normalized = normalized.replace("R$", "").replace("r$", "").replace(" ", "")
        normalized = normalized.replace("\u00A0", "")
        if "," in normalized and "." in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        elif "," in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        elif normalized.count(".") > 1:
            normalized = normalized.replace(".", "")
        elif normalized.count(".") == 1:
            left, right = normalized.split(".")
            if right.isdigit() and len(right) == 3:
                normalized = left + right
        return float(normalized)
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> Optional[bool]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "sim", "yes", "s")


# ─────────────────────────────────────────────────────────────────────────────
# Resultado de ingestão
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class IngestionReport:
    total_input: int = 0
    ingested: int = 0
    updated: int = 0
    skipped_invalid: int = 0
    skipped_duplicate: int = 0
    archived: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Serviço de ingestão
# ─────────────────────────────────────────────────────────────────────────────

class CatalogIngestionService:
    """
    [Fase 5.2] Pipeline de ingestão do catálogo.

    Suporta:
    - Importação via lista de dicts (JSON já parseado)
    - Importação via string JSON
    - Importação via string CSV
    - Upsert por external_ref (deduplicação)
    - Validação de qualidade antes de publicar
    - Normalização de campos
    - Arquivamento de imóveis ausentes da carga completa
    """

    def __init__(self, property_repo: PropertyRepository) -> None:
        self._repo = property_repo

    # ─── Entrada pública ───────────────────────────────────────────────────

    def ingest_dicts(
        self,
        items: Iterable[Dict[str, Any]],
        full_replace: bool = False,
    ) -> IngestionReport:
        """
        Ingere imóveis a partir de lista de dicts.

        Se full_replace=True, arquiva imóveis ativos que não estejam
        nos external_refs da carga (útil para sincronização completa).
        """
        report = IngestionReport()
        ingested_refs: List[str] = []

        for item in items:
            report.total_input += 1
            result = self._ingest_one(item, report)
            if result:
                ingested_refs.append(result)

        if full_replace:
            archived = self._archive_missing(ingested_refs)
            report.archived = archived

        logger.info(
            "catalog_ingestion_complete",
            extra={
                "total": report.total_input,
                "ingested": report.ingested,
                "updated": report.updated,
                "skipped_invalid": report.skipped_invalid,
                "archived": report.archived,
            },
        )
        return report

    def ingest_json_string(self, json_str: str, full_replace: bool = False) -> IngestionReport:
        """Ingere imóveis a partir de string JSON (array)."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            report = IngestionReport(total_input=0)
            report.errors.append(f"JSON inválido: {e}")
            return report
        if not isinstance(data, list):
            report = IngestionReport(total_input=0)
            report.errors.append("JSON deve ser um array de objetos")
            return report
        return self.ingest_dicts(data, full_replace=full_replace)

    def ingest_csv_string(self, csv_str: str, full_replace: bool = False) -> IngestionReport:
        """Ingere imóveis a partir de string CSV (primeira linha = cabeçalho)."""
        reader = csv.DictReader(io.StringIO(csv_str))
        return self.ingest_dicts(list(reader), full_replace=full_replace)

    # ─── Lógica interna ────────────────────────────────────────────────────

    def _ingest_one(self, item: Dict[str, Any], report: IngestionReport) -> Optional[str]:
        """Processa um único item. Retorna external_ref se bem-sucedido."""
        validation = validate_property_data(item)
        if not validation.valid:
            report.skipped_invalid += 1
            for err in validation.errors:
                report.errors.append(err)
            return None

        for warn in validation.warnings:
            report.warnings.append(warn)

        prop = dict_to_property(item)

        # Deduplicação por external_ref
        if prop.external_ref:
            existing = self._find_by_external_ref(prop.external_ref)
            if existing:
                # Atualiza preservando o id interno
                prop_updated = prop.model_copy(update={"id": existing.id, "created_at": existing.created_at})
                self._repo.save(prop_updated)
                report.updated += 1
                return prop.external_ref

        self._repo.save(prop)
        report.ingested += 1
        return prop.external_ref or prop.id

    def _find_by_external_ref(self, external_ref: str) -> Optional[Property]:
        """Busca imóvel existente pelo código externo."""
        # Busca todo o catálogo, inclusive imóveis arquivados, para permitir reativação via upsert.
        candidates = self._repo.search(status=None, limit=100000)
        for p in candidates:
            if p.external_ref == external_ref:
                return p
        return None

    def _archive_missing(self, present_refs: List[str]) -> int:
        """Arquiva imóveis disponíveis cujos external_refs não estão na carga."""
        present_set = set(present_refs)
        all_available = self._repo.search(status=PropertyStatus.AVAILABLE, limit=9999)
        archived = 0
        for prop in all_available:
            if prop.external_ref and prop.external_ref not in present_set:
                prop.status = PropertyStatus.OFF_MARKET
                prop.unavailable_reason = "Removido da carga de sincronização"
                prop.unavailable_since = datetime.utcnow()
                self._repo.save(prop)
                archived += 1
                logger.info("property_auto_archived", extra={"external_ref": prop.external_ref})
        return archived
