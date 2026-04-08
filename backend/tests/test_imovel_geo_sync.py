import importlib
import os
import shutil
import sys
from pathlib import Path

from sqlalchemy import inspect

from services.geo_matching import enrich_imovel_payload, match_legacy_location


def test_geo_matching_covers_all_audit_statuses():
    exact = match_legacy_location(
        {
            "codigo": "10014",
            "titulo": "Leblon - RJ",
            "cidade": "Rio de Janeiro",
            "bairro": "Copacabana",
            "uf": "RJ",
        },
        source="legacy_audit",
        known_neighborhoods=["Copacabana", "Leblon"],
    )
    assert exact.status == "exato"
    assert exact.score == 100
    assert exact.canonical_city == "Rio de Janeiro"
    assert exact.canonical_bairro == "Copacabana"

    probable = match_legacy_location(
        {
            "codigo": "10162",
            "titulo": "Leblon - RJ",
            "cidade": "RJ",
            "bairro": "Leblon",
            "uf": "RJ",
        },
        source="legacy_audit",
        known_neighborhoods=["Copacabana", "Leblon"],
    )
    assert probable.status == "provavel"
    assert probable.score == 85
    assert probable.canonical_city == "Rio de Janeiro"
    assert probable.canonical_bairro == "Leblon"

    ambiguous = match_legacy_location(
        {
            "codigo": "10200",
            "titulo": "Cabo Branco - RJ",
            "cidade": "Rio de Janeiro",
            "bairro": "Cabo Branco",
            "uf": "RJ",
        },
        source="legacy_audit",
        known_neighborhoods=["Cabo Branco", "Cabo-Branco"],
    )
    assert ambiguous.status == "ambiguo"
    assert ambiguous.score == 45
    assert ambiguous.ambiguous_candidates == ["Cabo Branco", "Cabo-Branco"]

    not_found = match_legacy_location({}, source="legacy_audit", known_neighborhoods=[])
    assert not_found.status == "nao_encontrado"
    assert not_found.score == 0
    assert not_found.canonical_city is None
    assert not_found.canonical_bairro is None


def test_geo_enrich_extracts_map_query_and_precision():
    payload = {
        "codigo": "20001",
        "tipo_negocio": "venda",
        "titulo": "Apartamento em Copacabana",
        "descricao": "Descricao",
        "foto_url": "/imoveis-img/fallback.jpg",
        "area_m2": 75,
        "dependencias": False,
        "tem_elevadores": False,
        "bairro": "Copacabana",
        "cidade": "Rio de Janeiro",
    }
    raw = {
        "codigo": "20001",
        "titulo": "Copacabana - RJ",
        "bairro": "Copacabana",
        "cidade": "RJ",
        "uf": "RJ",
        "mapa_url": "https://maps.google.com.br/maps?q=Avenida Atlantica 1702 Copacabana Rio de Janeiro&output=embed",
    }
    enriched = enrich_imovel_payload(
        payload,
        source="legacy_audit",
        raw_row=raw,
        known_neighborhoods=["Copacabana"],
    )

    assert enriched["endereco_formatado"] == "Avenida Atlantica 1702 Copacabana Rio de Janeiro"
    assert enriched["logradouro"] == "Avenida Atlantica"
    assert enriched["numero"] == "1702"
    assert enriched["localizacao_precisao"] == "endereco_aprox"
    assert enriched["localizacao_status"] in {"exato", "provavel"}


def test_init_db_migrates_legacy_sqlite_and_persists_geo_fields(tmp_path):
    legacy_db = Path("data/imoveis.db").resolve()
    assert legacy_db.exists()

    db_path = tmp_path / "imoveis_legacy_copy.db"
    shutil.copyfile(legacy_db, db_path)

    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"

    try:
        for module_name in [
            "main",
            "db",
            "routes.imoveis",
            "models.imovel",
            "seeds.imoveis_seed",
        ]:
            sys.modules.pop(module_name, None)

        db = importlib.import_module("db")

        db.init_db()

        inspector = inspect(db.engine)
        columns = {column["name"] for column in inspector.get_columns("imoveis")}
        assert {"latitude", "longitude", "localizacao_origem", "localizacao_status", "localizacao_score"}.issubset(columns)

        with db.SessionLocal() as session:
            seed_row = session.query(importlib.import_module("models.imovel").Imovel).filter_by(codigo="7989").one()
            assert seed_row.localizacao_origem in {"legacy_audit", "curated_default"}
            assert seed_row.localizacao_status in {"exato", "provavel", "ambiguo", "nao_encontrado"}
            assert seed_row.localizacao_score is not None
            assert seed_row.bairro
            assert seed_row.cidade
            assert seed_row.localizacao_raw_bairro is not None
            assert seed_row.localizacao_raw_cidade is not None
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
