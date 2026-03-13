"""Endpoints para cadastro e consulta de imoveis."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from db import get_db
from models.imovel import Imovel

router = APIRouter(prefix="/imoveis", tags=["imoveis"])
TipoNegocio = Literal["locacao", "venda"]


class ImovelBase(BaseModel):
    codigo: str = Field(..., min_length=3, max_length=20)
    tipo_negocio: TipoNegocio
    titulo: str = Field(..., min_length=5, max_length=180)
    descricao: str = Field(..., min_length=10, max_length=3000)
    foto_url: str = Field(..., min_length=10, max_length=500)

    valor_aluguel: Decimal | None = Field(default=None, ge=0)
    valor_compra: Decimal | None = Field(default=None, ge=0)
    condominio: Decimal | None = Field(default=None, ge=0)
    iptu: Decimal | None = Field(default=None, ge=0)

    area_m2: Decimal = Field(..., gt=0)
    numero_salas: int | None = Field(default=None, ge=0)
    numero_vagas: int | None = Field(default=None, ge=0)
    numero_quartos: int | None = Field(default=None, ge=0)
    numero_banheiros: int | None = Field(default=None, ge=0)
    numero_suites: int | None = Field(default=None, ge=0)

    dependencias: bool = False
    ano_construcao: int | None = Field(default=None, ge=1800, le=datetime.now().year + 1)
    numero_andares: int | None = Field(default=None, ge=0)
    tem_elevadores: bool = False

    bairro: str = Field(..., min_length=2, max_length=120)
    cidade: str = Field(..., min_length=2, max_length=120)

    @model_validator(mode="after")
    def _validate_pricing(self) -> "ImovelBase":
        if self.tipo_negocio == "locacao" and self.valor_aluguel is None:
            raise ValueError("Para locacao, informe valor_aluguel.")
        if self.tipo_negocio == "venda" and self.valor_compra is None:
            raise ValueError("Para venda, informe valor_compra.")
        return self


class ImovelCreate(ImovelBase):
    pass


class ImovelResponse(ImovelBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


def _query_by_tipo(db: Session, tipo: TipoNegocio, limit: int, offset: int) -> list[Imovel]:
    return (
        db.query(Imovel)
        .filter(Imovel.tipo_negocio == tipo)
        .order_by(Imovel.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("", response_model=ImovelResponse, status_code=status.HTTP_201_CREATED)
def criar_imovel(payload: ImovelCreate, db: Session = Depends(get_db)) -> Imovel:
    existente = db.query(Imovel).filter(Imovel.codigo == payload.codigo).first()
    if existente:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Codigo de imovel ja cadastrado")

    novo_imovel = Imovel(**payload.model_dump())
    db.add(novo_imovel)
    db.commit()
    db.refresh(novo_imovel)
    return novo_imovel


@router.get("", response_model=list[ImovelResponse])
def listar_imoveis(
    tipo: TipoNegocio | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Imovel]:
    query = db.query(Imovel)
    if tipo:
        query = query.filter(Imovel.tipo_negocio == tipo)
    return query.order_by(Imovel.id.desc()).offset(offset).limit(limit).all()


@router.get("/locacao", response_model=list[ImovelResponse])
def listar_locacao(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Imovel]:
    return _query_by_tipo(db=db, tipo="locacao", limit=limit, offset=offset)


@router.get("/venda", response_model=list[ImovelResponse])
def listar_venda(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Imovel]:
    return _query_by_tipo(db=db, tipo="venda", limit=limit, offset=offset)


@router.get("/codigo/{codigo}", response_model=ImovelResponse)
def obter_imovel_por_codigo(codigo: str, db: Session = Depends(get_db)) -> Imovel:
    imovel = db.query(Imovel).filter(Imovel.codigo == codigo).first()
    if imovel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imovel nao encontrado")
    return imovel


@router.get("/{imovel_id}", response_model=ImovelResponse)
def obter_imovel_por_id(imovel_id: int, db: Session = Depends(get_db)) -> Imovel:
    imovel = db.query(Imovel).filter(Imovel.id == imovel_id).first()
    if imovel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imovel nao encontrado")
    return imovel
