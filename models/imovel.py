"""Property ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class Imovel(Base):
    """Representa um imovel com dados comerciais e estruturais."""

    __tablename__ = "imoveis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    tipo_negocio: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # locacao | venda

    titulo: Mapped[str] = mapped_column(String(180), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    foto_url: Mapped[str] = mapped_column(String(500), nullable=False)

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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
