"""Initial property seed data."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from models.imovel import Imovel


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


def seed_imoveis(db: Session) -> None:
    """Populate default properties and keep seeded records updated by code."""
    existing_by_code = {imovel.codigo: imovel for imovel in db.query(Imovel).all()}
    has_changes = False

    for payload in SEED_IMOVEIS:
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
