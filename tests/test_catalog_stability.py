import os
from pathlib import Path

from fastapi.testclient import TestClient

TEST_DB_PATH = Path("data/test_catalog_stability.db").resolve()
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"

from db import init_db  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)


def test_health_and_catalog_endpoints_are_stable():
    init_db()

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json().get("service") == "agente_imobiliario_api"

    locacao = client.get("/imoveis/locacao?limit=50")
    venda = client.get("/imoveis/venda?limit=50")

    assert locacao.status_code == 200
    assert venda.status_code == 200

    locacao_items = locacao.json()
    venda_items = venda.json()

    assert len(locacao_items) > 0
    assert len(venda_items) > 0

    assert all(item["tipo_negocio"] == "locacao" for item in locacao_items)
    assert all(item["tipo_negocio"] == "venda" for item in venda_items)


def test_catalog_text_is_not_mojibake_and_filters_work():
    init_db()

    response = client.get("/imoveis?limit=200")
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0

    for item in items:
        text_block = " ".join(
            [
                item.get("titulo") or "",
                item.get("descricao") or "",
                item.get("bairro") or "",
                item.get("cidade") or "",
            ]
        )
        assert "Ã" not in text_block
        assert "�" not in text_block

    filtros = client.get("/imoveis/filtros")
    assert filtros.status_code == 200
    payload = filtros.json()
    assert isinstance(payload.get("bairros"), list)
    assert isinstance(payload.get("categorias"), list)


def test_catalog_empty_state_behavior_for_filters():
    init_db()

    empty = client.get("/imoveis/venda?bairro=BAIRRO_QUE_NAO_EXISTE_12345")
    assert empty.status_code == 200
    assert empty.json() == []
