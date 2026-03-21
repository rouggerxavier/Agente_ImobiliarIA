"""Initial property seed data."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy.orm import Session

from models.imovel import Imovel
from services.geo_matching import enrich_imovel_payload

logger = logging.getLogger(__name__)


SEED_IMOVEIS = [
    {
        "codigo": "7989",
        "tipo_negocio": "locacao",
        "titulo": "Apartamento em Copacabana para locação",
        "descricao": (
            "Apartamento residencial em Copacabana com planta bem distribuída, "
            "boa iluminação e acesso rápido ao comércio da região."
        ),
        "foto_url": "/imoveis-img/locacao-01.jpg",
        "valor_aluguel": Decimal("4000.00"),
        "valor_compra": None,
        "condominio": Decimal("1043.00"),
        "iptu": Decimal("315.00"),
        "area_m2": Decimal("85.00"),
        "numero_salas": 1,
        "numero_vagas": 1,
        "numero_quartos": 3,
        "numero_banheiros": 2,
        "numero_suites": 1,
        "dependencias": True,
        "ano_construcao": 2006,
        "numero_andares": 10,
        "tem_elevadores": True,
        "bairro": "Copacabana",
        "cidade": "Rio de Janeiro",
    },
    {
        "codigo": "8012",
        "tipo_negocio": "locacao",
        "titulo": "Apartamento no Leblon para locação",
        "descricao": (
            "Imóvel residencial no Leblon, ideal para famílias que buscam localização "
            "nobre, conforto interno e mobilidade na Zona Sul."
        ),
        "foto_url": "/imoveis-img/locacao-02.jpg",
        "valor_aluguel": Decimal("7900.00"),
        "valor_compra": None,
        "condominio": Decimal("1570.00"),
        "iptu": Decimal("900.00"),
        "area_m2": Decimal("95.00"),
        "numero_salas": 1,
        "numero_vagas": 1,
        "numero_quartos": 3,
        "numero_banheiros": 3,
        "numero_suites": 1,
        "dependencias": True,
        "ano_construcao": 2010,
        "numero_andares": 12,
        "tem_elevadores": True,
        "bairro": "Leblon",
        "cidade": "Rio de Janeiro",
    },
    {
        "codigo": "8345",
        "tipo_negocio": "locacao",
        "titulo": "Apartamento em Copacabana para locação",
        "descricao": (
            "Apartamento amplo em Copacabana, próximo a serviços e com planta funcional "
            "para rotina de moradia e home office."
        ),
        "foto_url": "/imoveis-img/locacao-03.jpg",
        "valor_aluguel": Decimal("6500.00"),
        "valor_compra": None,
        "condominio": Decimal("1800.00"),
        "iptu": Decimal("726.49"),
        "area_m2": Decimal("100.00"),
        "numero_salas": 1,
        "numero_vagas": 1,
        "numero_quartos": 3,
        "numero_banheiros": 2,
        "numero_suites": 1,
        "dependencias": True,
        "ano_construcao": 2009,
        "numero_andares": 12,
        "tem_elevadores": True,
        "bairro": "Copacabana",
        "cidade": "Rio de Janeiro",
    },
    {
        "codigo": "8124",
        "tipo_negocio": "locacao",
        "titulo": "Apartamento em Ipanema para locação",
        "descricao": (
            "Apartamento com varanda em Ipanema, ambientes integrados e boa circulação "
            "de ar, ideal para quem deseja morar próximo à praia."
        ),
        "foto_url": "/imoveis-img/locacao-04.jpg",
        "valor_aluguel": Decimal("9800.00"),
        "valor_compra": None,
        "condominio": Decimal("2100.00"),
        "iptu": Decimal("1110.00"),
        "area_m2": Decimal("110.00"),
        "numero_salas": 2,
        "numero_vagas": 1,
        "numero_quartos": 3,
        "numero_banheiros": 3,
        "numero_suites": 1,
        "dependencias": True,
        "ano_construcao": 2013,
        "numero_andares": 14,
        "tem_elevadores": True,
        "bairro": "Ipanema",
        "cidade": "Rio de Janeiro",
    },
    {
        "codigo": "8450",
        "tipo_negocio": "locacao",
        "titulo": "Apartamento em Botafogo para locação",
        "descricao": (
            "Imóvel em Botafogo com planta inteligente, excelente para casal ou família "
            "pequena, perto de metrô e comércio."
        ),
        "foto_url": "/imoveis-img/locacao-05.jpg",
        "valor_aluguel": Decimal("5200.00"),
        "valor_compra": None,
        "condominio": Decimal("1200.00"),
        "iptu": Decimal("420.00"),
        "area_m2": Decimal("78.00"),
        "numero_salas": 1,
        "numero_vagas": 1,
        "numero_quartos": 2,
        "numero_banheiros": 2,
        "numero_suites": 1,
        "dependencias": False,
        "ano_construcao": 2008,
        "numero_andares": 11,
        "tem_elevadores": True,
        "bairro": "Botafogo",
        "cidade": "Rio de Janeiro",
    },
    {
        "codigo": "8906",
        "tipo_negocio": "venda",
        "titulo": "Apartamento em Copacabana para venda",
        "descricao": (
            "Apartamento para venda em Copacabana com boa relação custo-benefício, "
            "layout versátil e proximidade da praia."
        ),
        "foto_url": "/imoveis-img/venda-01.jpg",
        "valor_aluguel": None,
        "valor_compra": Decimal("630000.00"),
        "condominio": Decimal("1150.00"),
        "iptu": Decimal("250.00"),
        "area_m2": Decimal("70.00"),
        "numero_salas": 1,
        "numero_vagas": 1,
        "numero_quartos": 2,
        "numero_banheiros": 2,
        "numero_suites": 1,
        "dependencias": False,
        "ano_construcao": 2004,
        "numero_andares": 9,
        "tem_elevadores": True,
        "bairro": "Copacabana",
        "cidade": "Rio de Janeiro",
    },
    {
        "codigo": "7197",
        "tipo_negocio": "venda",
        "titulo": "Studio em Copacabana para venda",
        "descricao": (
            "Studio reformado em Copacabana para investimento ou moradia, com "
            "condomínio tradicional e acesso fácil ao transporte."
        ),
        "foto_url": "/imoveis-img/venda-02.jpg",
        "valor_aluguel": None,
        "valor_compra": Decimal("450000.00"),
        "condominio": Decimal("900.00"),
        "iptu": Decimal("124.00"),
        "area_m2": Decimal("32.00"),
        "numero_salas": 1,
        "numero_vagas": 0,
        "numero_quartos": 1,
        "numero_banheiros": 1,
        "numero_suites": 0,
        "dependencias": False,
        "ano_construcao": 1998,
        "numero_andares": 8,
        "tem_elevadores": True,
        "bairro": "Copacabana",
        "cidade": "Rio de Janeiro",
    },
    {
        "codigo": "9021",
        "tipo_negocio": "venda",
        "titulo": "Apartamento na Barra da Tijuca para venda",
        "descricao": (
            "Apartamento moderno na Barra da Tijuca com varanda gourmet e "
            "infraestrutura completa no condomínio."
        ),
        "foto_url": "/imoveis-img/venda-03.jpg",
        "valor_aluguel": None,
        "valor_compra": Decimal("1250000.00"),
        "condominio": Decimal("2100.00"),
        "iptu": Decimal("510.00"),
        "area_m2": Decimal("120.00"),
        "numero_salas": 2,
        "numero_vagas": 2,
        "numero_quartos": 3,
        "numero_banheiros": 3,
        "numero_suites": 1,
        "dependencias": True,
        "ano_construcao": 2018,
        "numero_andares": 16,
        "tem_elevadores": True,
        "bairro": "Barra da Tijuca",
        "cidade": "Rio de Janeiro",
    },
    {
        "codigo": "9108",
        "tipo_negocio": "venda",
        "titulo": "Cobertura em Ipanema para venda",
        "descricao": (
            "Cobertura duplex em Ipanema com área externa e vista livre, "
            "projeto ideal para quem busca espaço e exclusividade."
        ),
        "foto_url": "/imoveis-img/venda-04.jpg",
        "valor_aluguel": None,
        "valor_compra": Decimal("2500000.00"),
        "condominio": Decimal("3400.00"),
        "iptu": Decimal("1200.00"),
        "area_m2": Decimal("180.00"),
        "numero_salas": 2,
        "numero_vagas": 2,
        "numero_quartos": 4,
        "numero_banheiros": 4,
        "numero_suites": 2,
        "dependencias": True,
        "ano_construcao": 2012,
        "numero_andares": 18,
        "tem_elevadores": True,
        "bairro": "Ipanema",
        "cidade": "Rio de Janeiro",
    },
    {
        "codigo": "9254",
        "tipo_negocio": "venda",
        "titulo": "Apartamento em Botafogo para venda",
        "descricao": (
            "Apartamento residencial em Botafogo com metragem equilibrada, "
            "boa ventilação e fácil acesso a serviços."
        ),
        "foto_url": "/imoveis-img/venda-05.jpg",
        "valor_aluguel": None,
        "valor_compra": Decimal("870000.00"),
        "condominio": Decimal("1300.00"),
        "iptu": Decimal("380.00"),
        "area_m2": Decimal("86.00"),
        "numero_salas": 1,
        "numero_vagas": 1,
        "numero_quartos": 2,
        "numero_banheiros": 2,
        "numero_suites": 1,
        "dependencias": True,
        "ano_construcao": 2011,
        "numero_andares": 13,
        "tem_elevadores": True,
        "bairro": "Botafogo",
        "cidade": "Rio de Janeiro",
    },
]


KNOWN_NEIGHBORHOODS = tuple(sorted({seed["bairro"] for seed in SEED_IMOVEIS if seed.get("bairro")}))


_ENRICHED_FILE = Path(__file__).resolve().parents[1] / "data" / "grankasa_catalog_enriched.json"
_AUDIT_FILE = Path(__file__).resolve().parents[1] / "data" / "grankasa_catalog_audit.json"
_CATEGORY_TO_FINALIDADE = {
    "loja": "COMERCIAL",
    "sala": "COMERCIAL",
    "salas/conjuntos": "COMERCIAL",
    "predio": "COMERCIAL",
    "casa comercial": "COMERCIAL",
}
_ALLOWED_FINALIDADES = {"COMERCIAL", "MISTO", "RESIDENCIAL"}
_CURRENT_YEAR = datetime.now().year


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    if "Ã" in value or "Â" in value:
        try:
            value = value.encode("latin1").decode("utf-8")
        except (UnicodeError, AttributeError):
            pass
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", value).strip()


def _to_decimal_currency(value: str | None) -> Decimal | None:
    if not value:
        return None
    cleaned = (
        value.replace("R$", "")
        .replace(".", "")
        .replace(",", ".")
        .replace(" ", "")
        .replace("\xa0", "")
        .strip()
    )
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _to_int(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    match = re.search(r"-?\d+", str(value))
    if not match:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


def _normalize_year(value: int | None) -> int | None:
    if value is None:
        return None
    if 1800 <= value <= _CURRENT_YEAR + 1:
        return value

    # Some legacy rows may carry an extra trailing zero (e.g., 19880).
    if value > 9999 and value % 10 == 0:
        trimmed = value // 10
        if 1800 <= trimmed <= _CURRENT_YEAR + 1:
            return trimmed
    return None


def _to_bool(value: str | bool | None, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = _normalize_text(str(value)).lower()
    if normalized in {"sim", "true", "1", "yes"}:
        return True
    if normalized in {"nao", "false", "0", "no"}:
        return False
    return default


def _guess_bairro(titulo: str) -> str:
    clean_title = _normalize_text(titulo)
    if " - " in clean_title:
        return clean_title.split(" - ", 1)[0].strip() or "Rio de Janeiro"
    return clean_title or "Rio de Janeiro"


def _safe_area(quartos: int | None) -> Decimal:
    if quartos is None:
        return Decimal("65.00")
    if quartos <= 1:
        return Decimal("48.00")
    if quartos == 2:
        return Decimal("75.00")
    if quartos == 3:
        return Decimal("105.00")
    return Decimal("140.00")


def _normalize_categoria(tipo: str | None) -> str | None:
    categoria = _normalize_text(tipo)
    if not categoria:
        return None
    return categoria.title()


def _normalize_cidade(value: str | None) -> str:
    city = _normalize_text(value)
    if not city:
        return "Rio de Janeiro"
    if city.lower() in {"rj", "rio", "rio de janeiro - rj"}:
        return "Rio de Janeiro"
    return city


def _normalize_finalidade(value: str | None, categoria: str | None) -> str:
    raw = _normalize_text(value).upper()
    if raw in _ALLOWED_FINALIDADES:
        return raw

    categoria_key = _normalize_text(categoria).lower()
    if categoria_key in _CATEGORY_TO_FINALIDADE:
        return _CATEGORY_TO_FINALIDADE[categoria_key]

    return "RESIDENCIAL"


def _build_seed_from_audit_file() -> list[dict]:
    source_file = _ENRICHED_FILE if _ENRICHED_FILE.exists() else _AUDIT_FILE
    if not source_file.exists():
        return []

    try:
        raw_items = json.loads(source_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    normalized: list[dict] = []
    seen_codes: set[str] = set()

    for item in raw_items:
        codigo = _normalize_text(str(item.get("codigo") or ""))
        if not codigo or codigo in seen_codes:
            continue

        origem = _normalize_text(item.get("origem_listagem"))
        tipo_negocio = "locacao" if origem == "locacao" else "venda"

        titulo_raw = _normalize_text(item.get("titulo"))
        bairro = _normalize_text(item.get("bairro")) or _guess_bairro(titulo_raw)
        cidade = _normalize_cidade(item.get("cidade"))
        categoria = _normalize_categoria(item.get("tipo"))
        finalidade = _normalize_finalidade(item.get("finalidade"), categoria)

        quartos = _to_int(item.get("quartos")) or 0
        suites = _to_int(item.get("suites")) or 0
        banheiros = _to_int(item.get("banheiros")) or 0
        vagas = _to_int(item.get("vagas")) or 0
        area = _to_int(item.get("area"))
        salas = _to_int(item.get("salas"))
        ano_construcao = _normalize_year(_to_int(item.get("ano_construcao")))
        numero_andares = _to_int(item.get("numero_andares"))
        elevadores = _to_bool(item.get("elevadores"), default=False)
        dependencias = _to_bool(item.get("dependencias"), default=False)

        preco = _to_decimal_currency(item.get("preco"))
        valor_aluguel = preco if tipo_negocio == "locacao" else None
        valor_compra = preco if tipo_negocio == "venda" else None
        condominio = _to_decimal_currency(item.get("condominio")) or Decimal("0.00")
        iptu = _to_decimal_currency(item.get("iptu")) or Decimal("0.00")

        foto_url = _normalize_text(item.get("imagem"))
        if not foto_url or "logo.png" in foto_url.lower():
            foto_url = "/imoveis-img/fallback.jpg"

        tipo_label = categoria or "Imovel"
        titulo = f"{tipo_label} em {bairro}"
        descricao_longa = _normalize_text(item.get("descricao_longa"))
        descricao = descricao_longa or (
            f"{tipo_label} localizado em {bairro}, {cidade}. "
            "Dados importados de auditoria para aproximar o catalogo ao site de referencia."
        )

        normalized_item = {
            "codigo": codigo,
            "tipo_negocio": tipo_negocio,
            "titulo": titulo[:180],
            "descricao": descricao[:3000],
            "foto_url": foto_url,
            "categoria": categoria,
            "finalidade": finalidade,
            "fonte_url": _normalize_text(item.get("url_detalhada")) or None,
            "video_url": _normalize_text(item.get("video_url")) or None,
            "mapa_url": _normalize_text(item.get("mapa_url")) or None,
            "valor_aluguel": valor_aluguel,
            "valor_compra": valor_compra,
            "condominio": condominio,
            "iptu": iptu,
            "area_m2": Decimal(str(area)) if area and area > 0 else _safe_area(quartos),
            "numero_salas": salas,
            "numero_vagas": vagas,
            "numero_quartos": quartos,
            "numero_banheiros": banheiros,
            "numero_suites": suites,
            "dependencias": dependencias,
            "ano_construcao": ano_construcao,
            "numero_andares": numero_andares,
            "tem_elevadores": elevadores,
            "bairro": bairro[:120] or "Rio de Janeiro",
            "cidade": cidade[:120] or "Rio de Janeiro",
        }
        normalized.append(
            enrich_imovel_payload(
                normalized_item,
                source="legacy_audit",
                raw_row=item,
                known_neighborhoods=KNOWN_NEIGHBORHOODS,
            )
        )
        seen_codes.add(codigo)

    return normalized


def _ensure_minimum_catalog_balance(payload: list[dict]) -> list[dict]:
    """Guarantee at least one listing for each business type."""
    has_locacao = any(item.get("tipo_negocio") == "locacao" for item in payload)
    has_venda = any(item.get("tipo_negocio") == "venda" for item in payload)

    if has_locacao and has_venda:
        return payload

    complement = []
    for seed in SEED_IMOVEIS:
        tipo = seed.get("tipo_negocio")
        if tipo == "locacao" and has_locacao:
            continue
        if tipo == "venda" and has_venda:
            continue
        complement.append(
            enrich_imovel_payload(
                seed,
                source="curated_default",
                raw_row=seed,
                known_neighborhoods=KNOWN_NEIGHBORHOODS,
            )
        )
        if tipo == "locacao":
            has_locacao = True
        if tipo == "venda":
            has_venda = True
        if has_locacao and has_venda:
            break

    return payload + complement


def _effective_seed_payload() -> tuple[list[dict], str]:
    """Use audited catalog when available, fallback to curated default seed."""
    from_audit = _build_seed_from_audit_file()
    if from_audit:
        return _ensure_minimum_catalog_balance(from_audit), "legacy_audit"

    curated = [
        enrich_imovel_payload(
            payload,
            source="curated_default",
            raw_row=payload,
            known_neighborhoods=KNOWN_NEIGHBORHOODS,
        )
        for payload in SEED_IMOVEIS
    ]
    return _ensure_minimum_catalog_balance(curated), "curated_default"


def seed_imoveis(db: Session) -> None:
    """Populate default properties and keep seeded records updated by code."""
    seed_payload, seed_source = _effective_seed_payload()
    existing_by_code = {imovel.codigo: imovel for imovel in db.query(Imovel).all()}
    has_changes = False

    for payload in seed_payload:
        existing = existing_by_code.get(payload["codigo"])

        if existing is None:
            db.add(Imovel(**payload))
            has_changes = True
            continue

        for field, value in payload.items():
            if getattr(existing, field) != value:
                setattr(existing, field, value)
                has_changes = True

    if has_changes:
        db.commit()

    logger.info(
        "seed_imoveis source=%s records=%d db_records=%d changes=%s",
        seed_source,
        len(seed_payload),
        len(existing_by_code),
        has_changes,
    )
