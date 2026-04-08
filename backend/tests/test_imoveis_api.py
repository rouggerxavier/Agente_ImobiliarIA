import os
from pathlib import Path

from fastapi.testclient import TestClient


TEST_DB_PATH = Path("data/test_imoveis_api.db").resolve()
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402


client = TestClient(app)


def test_seed_endpoints_and_crud_by_codigo():
    init_db()

    locacao_resp = client.get("/imoveis/locacao")
    assert locacao_resp.status_code == 200
    locacao_items = locacao_resp.json()
    assert len(locacao_items) >= 1
    assert all(item["tipo_negocio"] == "locacao" for item in locacao_items)
    assert all(item.get("foto_url") for item in locacao_items)

    venda_resp = client.get("/imoveis/venda")
    assert venda_resp.status_code == 200
    venda_items = venda_resp.json()
    assert len(venda_items) >= 1
    assert all(item["tipo_negocio"] == "venda" for item in venda_items)
    assert all(item.get("foto_url") for item in venda_items)

    codigo_existente = locacao_items[0]["codigo"]
    detalhe_resp = client.get(f"/imoveis/codigo/{codigo_existente}")
    assert detalhe_resp.status_code == 200
    detalhe = detalhe_resp.json()
    assert detalhe["codigo"] == codigo_existente
    assert "descricao" in detalhe
    assert "condominio" in detalhe
    assert "iptu" in detalhe
    assert "tem_elevadores" in detalhe
    assert "foto_url" in detalhe
    assert "localizacao_status" in detalhe
    assert "localizacao_origem" in detalhe
    assert "localizacao_precisao" in detalhe
    assert "endereco_formatado" in detalhe

    novo = {
        "codigo": "99991",
        "tipo_negocio": "venda",
        "titulo": "Apartamento demo para venda",
        "descricao": "Descricao de teste para criar um novo imovel via API.",
        "foto_url": "https://picsum.photos/seed/apto-99991/1200/800",
        "valor_compra": "990000.00",
        "valor_aluguel": None,
        "condominio": "1200.00",
        "iptu": "330.00",
        "area_m2": "88.50",
        "numero_salas": 1,
        "numero_vagas": 1,
        "numero_quartos": 3,
        "numero_banheiros": 2,
        "numero_suites": 1,
        "dependencias": True,
        "ano_construcao": 2016,
        "numero_andares": 14,
        "tem_elevadores": True,
        "bairro": "Copacabana",
        "cidade": "Rio de Janeiro",
    }

    create_resp = client.post("/imoveis", json=novo)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["codigo"] == "99991"
    assert created["tipo_negocio"] == "venda"
    assert "localizacao_status" in created
    assert created["localizacao_status"] is None

    get_created = client.get("/imoveis/codigo/99991")
    assert get_created.status_code == 200
    assert get_created.json()["titulo"] == "Apartamento demo para venda"
