from __future__ import annotations

import logging
import re
import time
from dataclasses import asdict
from typing import Callable, Dict, Any, Tuple

from .config import MultiAgentConfig
from .contracts import (
    HandoffRecord,
    OrchestratorDecision,
    OrchestratorRequest,
    OrchestratorResult,
    OrchestratorRoute,
    ToolCallRecord,
)
from .guardrails import evaluate_message_guardrail
from .observability import emit_trace_event, log_structured
from .openai_sdk_router import OpenAIAgentsSDKRouter
from .subagents import CatalogSubagent, KnowledgeSubagent, LegacyTriageSubagent

logger = logging.getLogger(__name__)


_CATALOG_HINTS = (
    "catalogo",
    "imoveis",
    "listar",
    "opcoes",
)

_KNOWLEDGE_HINTS = (
    "itbi",
    "cartorio",
    "financiamento",
    "documentacao",
    "condominio",
)


class MultiAgentOrchestrator:
    """Incremental orchestrator with controlled handoffs and safe fallbacks."""

    def __init__(
        self,
        *,
        config: MultiAgentConfig,
        legacy_handler: Callable[[str, str, str | None, str | None], Dict[str, Any]],
    ) -> None:
        self._config = config
        self._legacy = LegacyTriageSubagent(legacy_handler)
        self._catalog = CatalogSubagent()
        self._knowledge = KnowledgeSubagent()
        self._sdk_router = self._build_sdk_router()

    def _build_sdk_router(self) -> OpenAIAgentsSDKRouter | None:
        if not self._config.openai_sdk_router_enabled:
            return None
        if not OpenAIAgentsSDKRouter.is_available():
            logger.warning("MULTIAGENT_OPENAI_SDK_ROUTER_ENABLED=true but SDK is unavailable")
            return None
        try:
            return OpenAIAgentsSDKRouter(model=self._config.openai_sdk_model)
        except Exception as exc:
            logger.warning("openai_sdk_router_init_failed error=%s", exc)
            return None

    def _deterministic_route(self, message: str) -> Tuple[OrchestratorRoute, str]:
        normalized = (message or "").strip().lower()
        if not normalized:
            return OrchestratorRoute.SAFE_FALLBACK, "empty_message"

        has_catalog_hint = any(token in normalized for token in _CATALOG_HINTS)
        has_knowledge_hint = any(token in normalized for token in _KNOWLEDGE_HINTS)

        if has_catalog_hint:
            return OrchestratorRoute.CATALOG, "deterministic_catalog_hint"

        if has_knowledge_hint and "?" in normalized:
            return OrchestratorRoute.KNOWLEDGE, "deterministic_knowledge_hint"

        if normalized.startswith("/catalogo"):
            return OrchestratorRoute.CATALOG, "deterministic_catalog_command"

        if re.search(r"\b(quanto|como|quais|preciso|duvida)\b", normalized) and "?" in normalized:
            return OrchestratorRoute.KNOWLEDGE, "deterministic_question"

        return OrchestratorRoute.LEGACY_TRIAGE, "deterministic_default"

    def _safe_fallback_payload(self, reason: str) -> Dict[str, Any]:
        return {
            "reply": (
                "Nao consigo executar esse tipo de acao aqui com seguranca. "
                "Posso seguir com a triagem imobiliaria normal se voce quiser."
            ),
            "orchestrator_fallback": reason,
        }

    def _select_subagent(self, route: OrchestratorRoute):
        if route == OrchestratorRoute.CATALOG:
            return self._catalog
        if route == OrchestratorRoute.KNOWLEDGE:
            return self._knowledge
        return self._legacy

    def process(self, request: OrchestratorRequest) -> OrchestratorResult:
        trace_meta = {
            "session_id": request.session_id,
            "correlation_id": request.correlation_id,
            "message_preview": request.message[:120],
        }
        emit_trace_event(self._config.trace_path, "orchestrator_start", trace_meta, enabled=self._config.trace_enabled)

        verdict = evaluate_message_guardrail(
            request.message,
            allow_sensitive_actions=self._config.allow_sensitive_actions,
        )

        if not verdict.allowed:
            decision = OrchestratorDecision(
                route=OrchestratorRoute.SAFE_FALLBACK,
                reason=verdict.reason,
                delegated_to="none",
                used_openai_sdk_router=False,
            )
            payload = self._safe_fallback_payload(verdict.reason)
            emit_trace_event(
                self._config.trace_path,
                "orchestrator_guardrail_block",
                {**trace_meta, "reason": verdict.reason},
                enabled=self._config.trace_enabled,
            )
            return OrchestratorResult(payload=payload, decision=decision)

        route, reason = self._deterministic_route(request.message)
        used_sdk = False

        if self._sdk_router:
            try:
                sdk_decision = self._sdk_router.route(
                    request.message,
                    metadata={
                        "session_id": request.session_id,
                        "correlation_id": request.correlation_id,
                    },
                )
                route = sdk_decision.route
                reason = f"sdk_router:{sdk_decision.reason}"
                used_sdk = True
            except Exception:
                # Keep deterministic decision as conservative fallback.
                reason = f"{reason}|sdk_router_failed"

        decision = OrchestratorDecision(
            route=route,
            reason=reason,
            delegated_to=self._select_subagent(route).name,
            used_openai_sdk_router=used_sdk,
        )

        selected = self._select_subagent(route)
        started = time.perf_counter()
        sub_result = selected.run(request)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        tool_calls = [
            ToolCallRecord(
                name=f"subagent:{selected.name}",
                status="ok" if sub_result.handled else "error",
                duration_ms=elapsed_ms,
                input_payload={"route": route.value},
                output_payload={"reason": sub_result.reason},
                error=None if sub_result.handled else sub_result.reason,
            )
        ]

        handoffs: list[HandoffRecord] = []
        payload = sub_result.payload

        if route != OrchestratorRoute.LEGACY_TRIAGE and (sub_result.requires_handoff or not sub_result.handled):
            handoffs.append(
                HandoffRecord(
                    source=selected.name,
                    target=self._legacy.name,
                    reason=sub_result.reason or "subagent_unhandled",
                )
            )
            fallback_result = self._legacy.run(request)
            payload = fallback_result.payload
            tool_calls.append(
                ToolCallRecord(
                    name=f"subagent:{self._legacy.name}",
                    status="ok" if fallback_result.handled else "error",
                    duration_ms=0,
                    input_payload={"handoff_from": selected.name},
                    output_payload={"reason": fallback_result.reason},
                    error=None if fallback_result.handled else fallback_result.reason,
                )
            )

        emit_trace_event(
            self._config.trace_path,
            "orchestrator_finish",
            {
                **trace_meta,
                "route": decision.route.value,
                "delegated_to": decision.delegated_to,
                "used_sdk": used_sdk,
                "handoffs": [asdict(h) for h in handoffs],
            },
            enabled=self._config.trace_enabled,
        )

        log_structured(
            logger,
            "orchestrator_decision",
            route=decision.route.value,
            delegated_to=decision.delegated_to,
            used_sdk=decision.used_openai_sdk_router,
            correlation_id=request.correlation_id,
        )

        return OrchestratorResult(
            payload=payload,
            decision=decision,
            handoffs=handoffs,
            tool_calls=tool_calls,
        )

