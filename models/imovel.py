"""Property ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Imovel(Base):
    """Representa um imovel com dados comerciais e estruturais."""

    __tablename__ = "imoveis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    tipo_negocio: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # locacao | venda

    titulo: Mapped[str] = mapped_column(String(180), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    foto_url: Mapped[str] = mapped_column(String(500), nullable=False)
    categoria: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    finalidade: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    fonte_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mapa_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    valor_aluguel: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    valor_compra: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    condominio: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    iptu: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    area_m2: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    numero_salas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_vagas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_quartos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_banheiros: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_suites: Mapped[int | None] = mapped_column(Integer, nullable=True)

    dependencias: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ano_construcao: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_andares: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tem_elevadores: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    bairro: Mapped[str] = mapped_column(String(120), nullable=False)
    cidade: Mapped[str] = mapped_column(String(120), nullable=False)
    uf: Mapped[str | None] = mapped_column(String(8), nullable=True)
    endereco: Mapped[str | None] = mapped_column(String(255), nullable=True)
    endereco_formatado: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logradouro: Mapped[str | None] = mapped_column(String(180), nullable=True)
    numero: Mapped[str | None] = mapped_column(String(40), nullable=True)
    complemento: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cep: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ponto_referencia: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    localizacao_precisao: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    localizacao_origem: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    localizacao_status: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    localizacao_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    localizacao_raw_bairro: Mapped[str | None] = mapped_column(String(120), nullable=True)
    localizacao_raw_cidade: Mapped[str | None] = mapped_column(String(120), nullable=True)
    localizacao_raw_uf: Mapped[str | None] = mapped_column(String(8), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
