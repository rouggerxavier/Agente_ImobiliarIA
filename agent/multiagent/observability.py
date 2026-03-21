from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_trace_event(path: str, event_type: str, payload: Dict[str, Any], *, enabled: bool = True) -> None:
    if not enabled:
        return

    record = {
        "ts": _utc_now_iso(),
        "event_type": event_type,
        "payload": payload,
    }

    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.warning("multiagent_trace_write_failed path=%s error=%s", path, exc)


def log_structured(logger_obj: logging.Logger, event_type: str, **fields: Any) -> None:
    safe_fields = {"event_type": event_type, **fields}
    logger_obj.info("multiagent_event=%s", json.dumps(safe_fields, ensure_ascii=False, default=str))

