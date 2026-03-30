"""
Bridge para o storage legado baseado em arquivos JSON.

Adapta o comportamento atual de agent/persistence.py para os
contratos do domínio, permitindo migração gradual para PostgreSQL.

Este módulo será DESCONTINUADO após a Fase 1 do roadmap.
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, Optional

from core.trace import get_logger

logger = get_logger(__name__)

_lock = threading.Lock()

LEADS_PATH = os.getenv("LEADS_LOG_PATH") or (
    "/mnt/data/leads.jsonl" if os.path.exists("/mnt/data") else "data/leads.jsonl"
)
EVENTS_PATH = os.getenv("EVENTS_PATH") or (
    "/mnt/data/events.jsonl" if os.path.exists("/mnt/data") else "data/events.jsonl"
)


def _ensure_dir(path: str) -> None:
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def append_lead_jsonl(payload: Dict[str, Any]) -> None:
    """
    Persiste lead no arquivo JSONL legado.
    Mantém compatibilidade com o sistema atual enquanto o banco não está pronto.
    """
    _ensure_dir(LEADS_PATH)
    line = json.dumps(payload, ensure_ascii=False, default=str)
    with _lock:
        with open(LEADS_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    logger.info(
        "legacy_lead_persisted",
        extra={"path": LEADS_PATH, "session_id": payload.get("session_id")},
    )


def append_event_jsonl(event: Dict[str, Any]) -> None:
    """Persiste evento no arquivo JSONL legado."""
    _ensure_dir(EVENTS_PATH)
    with _lock:
        with open(EVENTS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


def load_brokers(path: str = "data/agents.json") -> list:
    """
    Carrega corretores do arquivo JSON legado.
    Será substituído por BrokerRepository na Fase 1.
    """
    if not os.path.exists(path):
        logger.warning("legacy_brokers_file_not_found", extra={"path": path})
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else data.get("agents", [])
    except Exception as e:
        logger.error("legacy_brokers_load_error", extra={"error": str(e)})
        return []


def load_properties(path: str = "data/properties.json") -> list:
    """
    Carrega imóveis do arquivo JSON legado.
    Será substituído por PropertyRepository na Fase 1.
    """
    if not os.path.exists(path):
        logger.warning("legacy_properties_file_not_found", extra={"path": path})
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.error("legacy_properties_load_error", extra={"error": str(e)})
        return []
