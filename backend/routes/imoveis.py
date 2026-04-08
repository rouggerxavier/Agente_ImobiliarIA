"""Endpoints para cadastro e consulta de imoveis."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db import get_db
from models.imovel import Imovel

router = APIRouter(prefix="/imoveis", tags=["imoveis"])
TipoNegocio = Literal["locacao", "venda"]
GeoMatchStatus = Literal["exato", "provavel", "ambiguo", "nao_encontrado"]
logger = logging.getLogger(__name__)


class ImovelBase(BaseModel):
    codigo: str = Field(..., min_length=3, max_length=20)
    tipo_negocio: TipoNegocio
    titulo: str = Field(..., min_length=5, max_length=180)
    descricao: str = Field(..., min_length=10, max_length=3000)
    foto_url: str = Field(..., min_length=10, max_length=500)
    categoria: str | None = Field(default=None, max_length=80)
    finalidade: str | None = Field(default=None, max_length=40)
    fonte_url: str | None = Field(default=None, max_length=500)
    video_url: str | None = Field(default=None, max_length=500)
    mapa_url: str | None = Field(default=None, max_length=500)

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
    uf: str | None = Field(default=None, max_length=8)
    endereco: str | None = Field(default=None, max_length=255)
    endereco_formatado: str | None = Field(default=None, max_length=255)
    logradouro: str | None = Field(default=None, max_length=180)
    numero: str | None = Field(default=None, max_length=40)
    complemento: str | None = Field(default=None, max_length=120)
    cep: str | None = Field(default=None, max_length=20)
    ponto_referencia: str | None = Field(default=None, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    localizacao_precisao: str | None = Field(default=None, max_length=24)
    localizacao_origem: str | None = Field(default=None, max_length=40)
    localizacao_status: GeoMatchStatus | None = Field(default=None)
    localizacao_score: int | None = Field(default=None, ge=0, le=100)
    localizacao_raw_bairro: str | None = Field(default=None, max_length=120)
    localizacao_raw_cidade: str | None = Field(default=None, max_length=120)
    localizacao_raw_uf: str | None = Field(default=None, max_length=8)

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


class ImovelFiltersResponse(BaseModel):
    bairros: list[str]
    categorias: list[str]
    finalidades: list[str]


def _log_catalog_event(event: str, *, status_code: int, started_at: float, count: int | None = None, **extra):
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    payload = {
        "event": event,
        "status": status_code,
        "elapsed_ms": elapsed_ms,
        "count": count,
        **extra,
    }
    logger.info("catalog_event=%s", payload)


def _apply_optional_filters(
    query,
    *,
    tipo_negocio: TipoNegocio | None = None,
    categoria: str | None = None,
    finalidade: str | None = None,
    bairro: str | None = None,
    cidade: str | None = None,
    dormitorios: int | None = None,
):
    if tipo_negocio:
        query = query.filter(Imovel.tipo_negocio == tipo_negocio)
    if categoria:
        query = query.filter(Imovel.categoria.ilike(categoria.strip()))
    if finalidade:
        query = query.filter(Imovel.finalidade.ilike(finalidade.strip()))
    if bairro:
        query = query.filter(Imovel.bairro.ilike(f"%{bairro.strip()}%"))
    if cidade:
        query = query.filter(Imovel.cidade.ilike(f"%{cidade.strip()}%"))
    if dormitorios is not None:
        query = query.filter(Imovel.numero_quartos >= dormitorios)
    return query


def _query_by_tipo(
    db: Session,
    tipo: TipoNegocio,
    limit: int,
    offset: int,
    categoria: str | None = None,
    bairro: str | None = None,
    dormitorios: int | None = None,
) -> list[Imovel]:
    query = db.query(Imovel).filter(Imovel.tipo_negocio == tipo)
    query = _apply_optional_filters(query, categoria=categoria, bairro=bairro, dormitorios=dormitorios)
    return query.order_by(Imovel.id.desc()).offset(offset).limit(limit).all()


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
    categoria: str | None = Query(default=None, max_length=80),
    finalidade: str | None = Query(default=None, max_length=40),
    bairro: str | None = Query(default=None, max_length=120),
    cidade: str | None = Query(default=None, max_length=120),
    dormitorios: int | None = Query(default=None, ge=0, le=20),
    limit: int = Query(default=24, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Imovel]:
    started_at = time.perf_counter()
    query = db.query(Imovel)
    query = _apply_optional_filters(
        query,
        tipo_negocio=tipo,
        categoria=categoria,
        finalidade=finalidade,
        bairro=bairro,
        cidade=cidade,
        dormitorios=dormitorios,
    )
    rows = query.order_by(Imovel.id.desc()).offset(offset).limit(limit).all()
    _log_catalog_event(
        "listar_imoveis",
        status_code=200,
        started_at=started_at,
        count=len(rows),
        tipo=tipo,
        categoria=categoria,
        finalidade=finalidade,
        bairro=bairro,
        cidade=cidade,
        dormitorios=dormitorios,
        limit=limit,
        offset=offset,
    )
    return rows


@router.get("/locacao", response_model=list[ImovelResponse])
def listar_locacao(
    categoria: str | None = Query(default=None, max_length=80),
    bairro: str | None = Query(default=None, max_length=120),
    dormitorios: int | None = Query(default=None, ge=0, le=20),
    limit: int = Query(default=24, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Imovel]:
    started_at = time.perf_counter()
    rows = _query_by_tipo(
        db=db,
        tipo="locacao",
        limit=limit,
        offset=offset,
        categoria=categoria,
        bairro=bairro,
        dormitorios=dormitorios,
    )
    _log_catalog_event(
        "listar_locacao",
        status_code=200,
        started_at=started_at,
        count=len(rows),
        categoria=categoria,
        bairro=bairro,
        dormitorios=dormitorios,
        limit=limit,
        offset=offset,
    )
    return rows


@router.get("/venda", response_model=list[ImovelResponse])
def listar_venda(
    categoria: str | None = Query(default=None, max_length=80),
    bairro: str | None = Query(default=None, max_length=120),
    dormitorios: int | None = Query(default=None, ge=0, le=20),
    limit: int = Query(default=24, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Imovel]:
    started_at = time.perf_counter()
    rows = _query_by_tipo(
        db=db,
        tipo="venda",
        limit=limit,
        offset=offset,
        categoria=categoria,
        bairro=bairro,
        dormitorios=dormitorios,
    )
    _log_catalog_event(
        "listar_venda",
        status_code=200,
        started_at=started_at,
        count=len(rows),
        categoria=categoria,
        bairro=bairro,
        dormitorios=dormitorios,
        limit=limit,
        offset=offset,
    )
    return rows


@router.get("/busca", response_model=list[ImovelResponse])
def buscar_imoveis(
    q: str | None = Query(default=None, min_length=1, max_length=200),
    codigo: str | None = Query(default=None, min_length=1, max_length=20),
    tipo_negocio: TipoNegocio | None = Query(default=None),
    categoria: str | None = Query(default=None, max_length=80),
    finalidade: str | None = Query(default=None, max_length=40),
    bairro: str | None = Query(default=None, max_length=120),
    cidade: str | None = Query(default=None, max_length=120),
    dormitorios: int | None = Query(default=None, ge=0, le=20),
    limit: int = Query(default=48, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Imovel]:
    started_at = time.perf_counter()
    query = db.query(Imovel)
    query = _apply_optional_filters(
        query,
        tipo_negocio=tipo_negocio,
        categoria=categoria,
        finalidade=finalidade,
        bairro=bairro,
        cidade=cidade,
        dormitorios=dormitorios,
    )

    if codigo:
        query = query.filter(Imovel.codigo.ilike(codigo.strip()))

    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Imovel.titulo.ilike(term),
                Imovel.bairro.ilike(term),
                Imovel.cidade.ilike(term),
                Imovel.codigo.ilike(term),
                Imovel.categoria.ilike(term),
                Imovel.descricao.ilike(term),
            )
        )

    rows = query.order_by(Imovel.id.desc()).offset(offset).limit(limit).all()
    _log_catalog_event(
        "buscar_imoveis",
        status_code=200,
        started_at=started_at,
        count=len(rows),
        q=q,
        codigo=codigo,
        tipo_negocio=tipo_negocio,
        categoria=categoria,
        finalidade=finalidade,
        bairro=bairro,
        cidade=cidade,
        dormitorios=dormitorios,
        limit=limit,
        offset=offset,
    )
    return rows


@router.get("/filtros", response_model=ImovelFiltersResponse)
def listar_filtros(db: Session = Depends(get_db)) -> ImovelFiltersResponse:
    started_at = time.perf_counter()
    bairros = (
        db.query(Imovel.bairro)
        .filter(Imovel.bairro.isnot(None))
        .group_by(Imovel.bairro)
        .order_by(func.lower(Imovel.bairro))
        .all()
    )
    categorias = (
        db.query(Imovel.categoria)
        .filter(Imovel.categoria.isnot(None))
        .group_by(Imovel.categoria)
        .order_by(func.lower(Imovel.categoria))
        .all()
    )
    finalidades = (
        db.query(Imovel.finalidade)
        .filter(Imovel.finalidade.isnot(None))
        .group_by(Imovel.finalidade)
        .order_by(func.lower(Imovel.finalidade))
        .all()
    )

    response = ImovelFiltersResponse(
        bairros=[item[0] for item in bairros if item[0]],
        categorias=[item[0] for item in categorias if item[0]],
        finalidades=[item[0] for item in finalidades if item[0]],
    )
    _log_catalog_event(
        "listar_filtros",
        status_code=200,
        started_at=started_at,
        count=len(response.bairros) + len(response.categorias) + len(response.finalidades),
    )
    return response


@router.get("/codigo/{codigo}", response_model=ImovelResponse)
def obter_imovel_por_codigo(codigo: str, db: Session = Depends(get_db)) -> Imovel:
    started_at = time.perf_counter()
    imovel = db.query(Imovel).filter(Imovel.codigo == codigo).first()
    if imovel is None:
        _log_catalog_event(
            "obter_imovel_por_codigo",
            status_code=404,
            started_at=started_at,
            codigo=codigo,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imovel nao encontrado")
    _log_catalog_event(
        "obter_imovel_por_codigo",
        status_code=200,
        started_at=started_at,
        count=1,
        codigo=codigo,
    )
    return imovel


@router.get("/{imovel_id:int}", response_model=ImovelResponse)
def obter_imovel_por_id(imovel_id: int, db: Session = Depends(get_db)) -> Imovel:
    started_at = time.perf_counter()
    imovel = db.query(Imovel).filter(Imovel.id == imovel_id).first()
    if imovel is None:
        _log_catalog_event(
            "obter_imovel_por_id",
            status_code=404,
            started_at=started_at,
            imovel_id=imovel_id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imovel nao encontrado")
    _log_catalog_event(
        "obter_imovel_por_id",
        status_code=200,
        started_at=started_at,
        count=1,
        imovel_id=imovel_id,
    )
    return imovel
