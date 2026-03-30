from __future__ import annotations

import logging
import os
from typing import Any, Dict

from application.bootstrap import process_phase34_message
from application.conversation_orchestrator import MessageInput
from domain.enums import Channel

from .controller import handle_message as legacy_handle_message
from .multiagent import MultiAgentOrchestrator, OrchestratorRequest, load_multiagent_config

logger = logging.getLogger(__name__)
STATE_GRAPH_ENABLED = os.getenv("STATE_GRAPH_ENABLED", "true").lower() == "true"


def _handle_phase34(session_id: str, message: str, name: str | None = None, correlation_id: str | None = None) -> Dict[str, Any]:
    return process_phase34_message(
        MessageInput(
            session_id=session_id,
            message_text=message,
            sender_name=name,
            trace_id=correlation_id,
            channel=Channel.UNKNOWN,
        )
    )


def handle_message(session_id: str, message: str, name: str | None = None, correlation_id: str | None = None) -> Dict[str, Any]:
    """Gateway for safe incremental migration to multi-agent orchestration.

    Behavior:
    - MULTIAGENT_ENABLED=false: uses legacy controller unchanged.
    - MULTIAGENT_ENABLED=true: routes through orchestrator with automatic fallback.
    """
    config = load_multiagent_config()
    if not config.enabled:
        if not STATE_GRAPH_ENABLED:
            return legacy_handle_message(session_id, message, name=name, correlation_id=correlation_id)
        try:
            return _handle_phase34(session_id, message, name=name, correlation_id=correlation_id)
        except Exception as exc:
            logger.exception("phase34_orchestrator_failed fallback=legacy error=%s", exc)
            return legacy_handle_message(session_id, message, name=name, correlation_id=correlation_id)

    orchestrator = MultiAgentOrchestrator(config=config, legacy_handler=legacy_handle_message)
    request = OrchestratorRequest(
        session_id=session_id,
        message=message,
        name=name,
        correlation_id=correlation_id,
    )

    try:
        result = orchestrator.process(request)
    except Exception as exc:
        logger.exception("multiagent_orchestrator_failed fallback=legacy error=%s", exc)
        return legacy_handle_message(session_id, message, name=name, correlation_id=correlation_id)

    payload = dict(result.payload)
    payload.setdefault(
        "orchestration",
        {
            "route": result.decision.route.value,
            "delegated_to": result.decision.delegated_to,
            "used_openai_sdk_router": result.decision.used_openai_sdk_router,
            "handoffs": [
                {"source": h.source, "target": h.target, "reason": h.reason}
                for h in result.handoffs
            ],
            "tool_calls": [
                {
                    "name": t.name,
                    "status": t.status,
                    "duration_ms": t.duration_ms,
                    "error": t.error,
                }
                for t in result.tool_calls
            ],
        },
    )
    return payload

