from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import requests
from sqlalchemy.orm import Session

from agent.multiagent.observability import emit_trace_event, log_structured
from db import SessionLocal
from models.imovel import Imovel
from services.geo_matching import enrich_imovel_payload

logger = logging.getLogger(__name__)


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip().lower()


def _extract_map_url_from_html(raw_html: str) -> str | None:
    match = re.search(r'<iframe[^>]+src="([^"]*maps\.google[^"]*)"', raw_html, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


@dataclass(slots=True)
class GeoPipelineConfig:
    legacy_catalog_path: Path = Path("data/grankasa_catalog_enriched.json")
    trace_path: Path = Path("data/geo_localizacao_trace.jsonl")
    report_path: Path = Path("docs/evidencias/geolocalizacao_auditoria.json")
    screenshot_report_path: Path = Path("docs/evidencias/geolocalizacao_screenshots.json")
    fetch_missing_map_url: bool = True
    persist_probable_matches: bool = False
    http_timeout_seconds: float = 10.0


@dataclass(slots=True)
class LegacyDiscoveryResult:
    items: list[dict[str, Any]]
    by_codigo: dict[str, dict[str, Any]]
    fetched_map_updates: int = 0


@dataclass(slots=True)
class MatchRecord:
    codigo: str
    imovel_id: int
    match_status: str
    match_score: int
    legacy_codigo: str | None = None
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PersistenceResult:
    updated: int
    skipped: int
    corrected: int


@dataclass(slots=True)
class ValidationRecord:
    codigo: str
    match_status: str
    match_score: int
    migration_status: str
    render_status: str
    e2e_status: str
    screenshot_path: str | None
    observacoes: str | None


class LegacyDiscoverySubagent:
    name = "legacy_discovery_subagent"

    def run(self, config: GeoPipelineConfig) -> LegacyDiscoveryResult:
        if not config.legacy_catalog_path.exists():
            raise FileNotFoundError(f"Legacy catalog file not found: {config.legacy_catalog_path}")

        payload = json.loads(config.legacy_catalog_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Legacy catalog payload must be a list of records.")

        fetched_map_updates = 0
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                )
            }
        )

        for item in payload:
            if item.get("mapa_url"):
                continue
            if not config.fetch_missing_map_url:
                continue
            detail_url = item.get("url_detalhada")
            if not detail_url:
                continue
            try:
                response = session.get(detail_url, timeout=config.http_timeout_seconds)
                response.raise_for_status()
                map_url = _extract_map_url_from_html(response.text)
                if map_url:
                    item["mapa_url"] = map_url
                    fetched_map_updates += 1
            except requests.RequestException:
                continue

        by_codigo = {
            str(item.get("codigo")).strip(): item
            for item in payload
            if str(item.get("codigo") or "").strip()
        }
        return LegacyDiscoveryResult(items=payload, by_codigo=by_codigo, fetched_map_updates=fetched_map_updates)


class MatchingSubagent:
    name = "matching_subagent"

    def _score_similarity(self, imovel: Imovel, row: dict[str, Any]) -> int:
        score = 0
        if _normalize(imovel.bairro) == _normalize(row.get("bairro")):
            score += 35
        if _normalize(imovel.cidade) in {_normalize(row.get("cidade")), "rio de janeiro"}:
            score += 20
        if _normalize(imovel.tipo_negocio) in {_normalize(row.get("origem_listagem")), _normalize(row.get("finalidade"))}:
            score += 15
        title_ratio = SequenceMatcher(None, _normalize(imovel.titulo), _normalize(row.get("titulo"))).ratio()
        score += int(title_ratio * 30)
        return min(score, 99)

    def run(self, discovery: LegacyDiscoveryResult, db: Session) -> list[MatchRecord]:
        properties = db.query(Imovel).order_by(Imovel.id.asc()).all()
        matches: list[MatchRecord] = []

        for imovel in properties:
            codigo = (imovel.codigo or "").strip()
            if codigo and codigo in discovery.by_codigo:
                matches.append(
                    MatchRecord(
                        codigo=codigo,
                        imovel_id=imovel.id,
                        match_status="exato",
                        match_score=100,
                        legacy_codigo=codigo,
                        reasons=["codigo_exato"],
                    )
                )
                continue

            scored: list[tuple[int, dict[str, Any]]] = []
            for row in discovery.items:
                scored.append((self._score_similarity(imovel, row), row))
            scored.sort(key=lambda item: item[0], reverse=True)

            if not scored or scored[0][0] < 60:
                matches.append(
                    MatchRecord(
                        codigo=codigo,
                        imovel_id=imovel.id,
                        match_status="nao_encontrado",
                        match_score=0,
                        reasons=["sem_candidato_confiavel"],
                    )
                )
                continue

            top_score, top_row = scored[0]
            second_score = scored[1][0] if len(scored) > 1 else -1
            if top_score - second_score < 8:
                matches.append(
                    MatchRecord(
                        codigo=codigo,
                        imovel_id=imovel.id,
                        match_status="ambiguo",
                        match_score=top_score,
                        legacy_codigo=str(top_row.get("codigo") or ""),
                        reasons=["empate_semantico"],
                    )
                )
                continue

            matches.append(
                MatchRecord(
                    codigo=codigo,
                    imovel_id=imovel.id,
                    match_status="provavel",
                    match_score=top_score,
                    legacy_codigo=str(top_row.get("codigo") or ""),
                    reasons=["similaridade_titulo_bairro"],
                )
            )

        return matches


class PersistenceSubagent:
    name = "persistence_subagent"

    def run(
        self,
        *,
        config: GeoPipelineConfig,
        discovery: LegacyDiscoveryResult,
        matches: list[MatchRecord],
        db: Session,
    ) -> PersistenceResult:
        updated = 0
        skipped = 0
        corrected = 0
        known_neighborhoods = sorted({str(item.get("bairro") or "").strip() for item in discovery.items if item.get("bairro")})

        for match in matches:
            imovel = db.query(Imovel).filter(Imovel.id == match.imovel_id).first()
            if not imovel:
                skipped += 1
                continue

            should_persist = match.match_status == "exato" or (
                config.persist_probable_matches and match.match_status == "provavel"
            )
            if not should_persist:
                imovel.localizacao_status = match.match_status
                imovel.localizacao_score = match.match_score
                skipped += 1
                continue

            if not match.legacy_codigo:
                skipped += 1
                continue

            row = discovery.by_codigo.get(match.legacy_codigo)
            if not row:
                skipped += 1
                continue

            payload = enrich_imovel_payload(
                {
                    "bairro": imovel.bairro,
                    "cidade": imovel.cidade,
                    "mapa_url": imovel.mapa_url,
                },
                source="legacy_audit",
                raw_row=row,
                known_neighborhoods=known_neighborhoods,
            )

            for key, value in payload.items():
                if not hasattr(imovel, key):
                    continue
                if getattr(imovel, key) != value and value is not None:
                    setattr(imovel, key, value)
                    corrected += 1

            # Always keep orchestrator match confidence trace.
            imovel.localizacao_status = match.match_status
            imovel.localizacao_score = match.match_score
            imovel.localizacao_origem = "legacy_audit"
            updated += 1

        db.commit()
        return PersistenceResult(updated=updated, skipped=skipped, corrected=corrected)


class ValidationSubagent:
    name = "validation_e2e_subagent"

    def run(self, db: Session, matches: list[MatchRecord], screenshot_map: dict[str, str]) -> list[ValidationRecord]:
        by_code = {match.codigo: match for match in matches}
        rows = db.query(Imovel).order_by(Imovel.id.asc()).all()
        report: list[ValidationRecord] = []

        for row in rows:
            match = by_code.get(row.codigo)
            match_status = match.match_status if match else "nao_encontrado"
            match_score = match.match_score if match else 0
            migration_status = "ok" if row.localizacao_status in {"exato", "provavel"} else "pendente"
            render_status = "ok" if (row.endereco_formatado or row.bairro or row.cidade) else "sem_localizacao"
            screenshot_path = screenshot_map.get(row.codigo)
            e2e_status = "ok" if screenshot_path else "pendente"
            observacoes = None
            if not row.mapa_url and row.endereco_formatado:
                observacoes = "Sem mapa_url, mas com endereco textual legado."
            elif row.localizacao_status in {"ambiguo", "nao_encontrado"}:
                observacoes = "Revisar match manualmente."

            report.append(
                ValidationRecord(
                    codigo=row.codigo,
                    match_status=match_status,
                    match_score=match_score,
                    migration_status=migration_status,
                    render_status=render_status,
                    e2e_status=e2e_status,
                    screenshot_path=screenshot_path,
                    observacoes=observacoes,
                )
            )
        return report


class GeolocationOrchestrator:
    def __init__(self, config: GeoPipelineConfig | None = None) -> None:
        self.config = config or GeoPipelineConfig()
        self.discovery_agent = LegacyDiscoverySubagent()
        self.matching_agent = MatchingSubagent()
        self.persistence_agent = PersistenceSubagent()
        self.validation_agent = ValidationSubagent()

    def run(self, screenshot_map: dict[str, str] | None = None) -> dict[str, Any]:
        screenshot_map = screenshot_map or {}
        started = time.perf_counter()

        emit_trace_event(
            str(self.config.trace_path),
            "geo_orchestrator_start",
            {"legacy_catalog_path": str(self.config.legacy_catalog_path)},
            enabled=True,
        )

        with SessionLocal() as db:
            discovery = self.discovery_agent.run(self.config)
            matches = self.matching_agent.run(discovery, db)
            persistence = self.persistence_agent.run(
                config=self.config,
                discovery=discovery,
                matches=matches,
                db=db,
            )
            validations = self.validation_agent.run(db, matches, screenshot_map)

        summary = {
            "total_properties": len(validations),
            "legacy_records": len(discovery.items),
            "map_urls_fetched_now": discovery.fetched_map_updates,
            "match_exact": sum(1 for item in matches if item.match_status == "exato"),
            "match_probable": sum(1 for item in matches if item.match_status == "provavel"),
            "match_ambiguous": sum(1 for item in matches if item.match_status == "ambiguo"),
            "match_not_found": sum(1 for item in matches if item.match_status == "nao_encontrado"),
            "persist_updated": persistence.updated,
            "persist_skipped": persistence.skipped,
            "persist_field_corrections": persistence.corrected,
            "e2e_ok": sum(1 for item in validations if item.e2e_status == "ok"),
            "e2e_pending": sum(1 for item in validations if item.e2e_status != "ok"),
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }

        report = {
            "summary": summary,
            "validations": [asdict(item) for item in validations],
        }

        self.config.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        log_structured(logger, "geo_orchestrator_summary", **summary)
        emit_trace_event(
            str(self.config.trace_path),
            "geo_orchestrator_finish",
            summary,
            enabled=True,
        )

        return report
