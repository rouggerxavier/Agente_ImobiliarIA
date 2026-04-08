"""
Persistencia do estado critico da sessao do orquestrador.

Regras:
- Preferir SQL (Postgres em producao, SQLite em dev quando configurado no app.db).
- Permitir fallback para arquivo JSON apenas em desenvolvimento.
- Nunca fazer fallback silencioso para arquivo em producao.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column, DateTime, MetaData, String, Table, select

from core.trace import get_logger
from domain.repositories import SessionStateRepository

logger = get_logger(__name__)


def _utcnow() -> datetime:
    # Mantem datetime UTC "naive" para compatibilidade com payloads atuais.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SqlSessionStateRepository(SessionStateRepository):
    def __init__(self, engine=None, table_name: str = "orchestrator_session_states") -> None:
        if engine is None:
            from app.db import engine as app_engine

            engine = app_engine
        self._engine = engine
        self._metadata = MetaData()
        self._table = Table(
            table_name,
            self._metadata,
            Column("session_id", String(191), primary_key=True),
            Column("lead_id", String(64), nullable=True),
            Column("conversation_id", String(64), nullable=True),
            Column("trace_id", String(64), nullable=True),
            Column("state_json", JSON, nullable=False),
            Column("created_at", DateTime, nullable=False),
            Column("updated_at", DateTime, nullable=False),
        )
        self._metadata.create_all(bind=self._engine, tables=[self._table], checkfirst=True)

    def upsert(
        self,
        session_id: str,
        state: Dict[str, Any],
        *,
        lead_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        if not session_id:
            raise ValueError("session_id e obrigatorio para persistir session state")
        payload = dict(state or {})
        now = _utcnow()

        with self._engine.begin() as conn:
            existing = conn.execute(
                select(self._table.c.session_id).where(self._table.c.session_id == session_id)
            ).first()
            values = {
                "lead_id": lead_id,
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "state_json": payload,
                "updated_at": now,
            }
            if existing is None:
                conn.execute(
                    self._table.insert().values(
                        session_id=session_id,
                        created_at=now,
                        **values,
                    )
                )
            else:
                conn.execute(
                    self._table.update()
                    .where(self._table.c.session_id == session_id)
                    .values(**values)
                )

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        with self._engine.connect() as conn:
            row = conn.execute(
                select(self._table.c.state_json).where(self._table.c.session_id == session_id)
            ).mappings().first()
        if not row:
            return None
        payload = row.get("state_json")
        if isinstance(payload, dict):
            return payload
        logger.error(
            "orchestrator_state_sql_invalid_payload_type",
            extra={"session_id": session_id, "payload_type": type(payload).__name__},
        )
        return None


class JsonSessionStateRepository(SessionStateRepository):
    def __init__(self, path: Optional[Path] = None) -> None:
        default_dir = Path(os.getenv("ORCHESTRATOR_STORE_DIR", "data/orchestrator"))
        self.path = path or Path(os.getenv("ORCHESTRATOR_STATE_FILE_PATH", str(default_dir / "session_states.json")))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _load_all(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return data
            logger.error(
                "orchestrator_state_json_invalid_root",
                extra={"path": str(self.path), "root_type": type(data).__name__},
            )
            return {}
        except Exception as exc:
            quarantine_path = None
            try:
                quarantine_path = self.path.with_suffix(self.path.suffix + f".corrupted-{int(_utcnow().timestamp())}")
                self.path.replace(quarantine_path)
            except Exception:
                quarantine_path = None
            logger.error(
                "orchestrator_state_json_load_error",
                extra={
                    "path": str(self.path),
                    "error": str(exc),
                    "quarantined_to": str(quarantine_path) if quarantine_path else None,
                },
            )
            return {}

    def _write_all(self, data: Dict[str, Any]) -> None:
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        with temp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2, default=str)
        temp.replace(self.path)

    def upsert(
        self,
        session_id: str,
        state: Dict[str, Any],
        *,
        lead_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        if not session_id:
            raise ValueError("session_id e obrigatorio para persistir session state")
        now_iso = _utcnow().isoformat()
        with self._lock:
            records = self._load_all()
            existing = records.get(session_id, {}) if isinstance(records.get(session_id), dict) else {}
            records[session_id] = {
                "session_id": session_id,
                "lead_id": lead_id,
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "created_at": existing.get("created_at") or now_iso,
                "updated_at": now_iso,
                "state": dict(state or {}),
            }
            self._write_all(records)

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        with self._lock:
            records = self._load_all()
            entry = records.get(session_id)
        if not isinstance(entry, dict):
            return None
        state = entry.get("state")
        if isinstance(state, dict):
            return state
        logger.error(
            "orchestrator_state_json_invalid_state_payload",
            extra={"session_id": session_id, "payload_type": type(state).__name__},
        )
        return None


def _is_production() -> bool:
    try:
        from app.db import is_production_environment

        return bool(is_production_environment())
    except Exception:
        env = (os.getenv("APP_ENV") or os.getenv("ENV") or "development").strip().lower()
        return env in {"production", "prod"}


def _build_sql_session_state_repository() -> SqlSessionStateRepository:
    return SqlSessionStateRepository()


def create_session_state_repository() -> SessionStateRepository:
    """
    Fabrica do repositório de estado critico do orquestrador.

    `ORCHESTRATOR_STATE_BACKEND`:
      - `auto` (default): tenta SQL e cai para JSON apenas fora de producao.
      - `sql`: exige SQL; sem fallback.
      - `json`: apenas dev; bloqueado em producao.
    """
    backend_pref = (os.getenv("ORCHESTRATOR_STATE_BACKEND") or "auto").strip().lower()
    production = _is_production()

    if backend_pref == "json":
        if production:
            raise RuntimeError(
                "Configuracao invalida: ORCHESTRATOR_STATE_BACKEND=json nao e permitido em producao."
            )
        repo = JsonSessionStateRepository()
        logger.warning(
            "orchestrator_state_backend_json_forced",
            extra={"path": str(repo.path)},
        )
        return repo

    try:
        repo = _build_sql_session_state_repository()
        logger.info(
            "orchestrator_state_backend_sql_ready",
            extra={"table": "orchestrator_session_states"},
        )
        return repo
    except Exception as exc:
        logger.error(
            "orchestrator_state_backend_sql_error",
            extra={
                "error": str(exc),
                "backend_pref": backend_pref,
                "production": production,
            },
        )
        if production or backend_pref == "sql":
            raise RuntimeError(
                "Falha ao inicializar persistencia critica do orquestrador em SQL. "
                "Em producao, nao ha fallback para arquivo local."
            ) from exc
        fallback = JsonSessionStateRepository()
        logger.warning(
            "orchestrator_state_backend_json_fallback",
            extra={"path": str(fallback.path)},
        )
        return fallback


__all__ = [
    "SqlSessionStateRepository",
    "JsonSessionStateRepository",
    "create_session_state_repository",
]
