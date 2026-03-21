from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    from agents import Agent, RunConfig, Runner, trace
except Exception:  # pragma: no cover - optional dependency
    Agent = None  # type: ignore[assignment]
    Runner = None  # type: ignore[assignment]
    RunConfig = None  # type: ignore[assignment]
    trace = None  # type: ignore[assignment]

from pydantic import BaseModel, Field

from .contracts import OrchestratorRoute

logger = logging.getLogger(__name__)


class RouterDecisionOutput(BaseModel):
    route: str = Field(description="legacy_triage|catalog|knowledge|safe_fallback")
    reason: str = Field(default="")


@dataclass(slots=True)
class SDKRoutingDecision:
    route: OrchestratorRoute
    reason: str


class OpenAIAgentsSDKRouter:
    """Optional route classifier built with OpenAI Agents SDK.

    This class is intentionally optional. If the SDK or API key is unavailable,
    callers should skip it and use deterministic routing.
    """

    def __init__(self, model: str) -> None:
        if not self.is_available():
            raise RuntimeError("openai_agents_sdk_not_available")

        instructions = (
            "You are a strict route classifier for a real-estate assistant. "
            "Choose exactly one route among: legacy_triage, catalog, knowledge, safe_fallback. "
            "Rules: use catalog when user asks to list/search properties with criteria. "
            "Use knowledge when user asks informational questions about process, costs or documentation. "
            "Use legacy_triage for onboarding, qualification and most mixed intents. "
            "Use safe_fallback only for clearly unsafe or out-of-scope requests. "
            "Return concise reason in pt-BR or english."
        )

        self._model = model
        self._agent = Agent(
            name="route_orchestrator",
            instructions=instructions,
            output_type=RouterDecisionOutput,
            model=model,
        )

    @staticmethod
    def is_available() -> bool:
        return Agent is not None and Runner is not None and RunConfig is not None and trace is not None

    @staticmethod
    def _map_route(raw: str) -> OrchestratorRoute:
        value = (raw or "").strip().lower()
        if value == OrchestratorRoute.CATALOG.value:
            return OrchestratorRoute.CATALOG
        if value == OrchestratorRoute.KNOWLEDGE.value:
            return OrchestratorRoute.KNOWLEDGE
        if value == OrchestratorRoute.SAFE_FALLBACK.value:
            return OrchestratorRoute.SAFE_FALLBACK
        return OrchestratorRoute.LEGACY_TRIAGE

    def route(self, message: str, *, metadata: Optional[Dict[str, Any]] = None) -> SDKRoutingDecision:
        trace_ctx = trace("multiagent-sdk-router") if trace else None

        if trace_ctx:
            trace_ctx.__enter__()

        try:
            result = Runner.run_sync(
                self._agent,
                message,
                context=metadata or {},
                run_config=RunConfig(
                    workflow_name="multiagent_route_classification",
                    trace_include_sensitive_data=False,
                ),
            )
            output = result.final_output
            if isinstance(output, RouterDecisionOutput):
                mapped = self._map_route(output.route)
                return SDKRoutingDecision(route=mapped, reason=output.reason or "sdk_router")

            if isinstance(output, dict):
                mapped = self._map_route(str(output.get("route", "")))
                return SDKRoutingDecision(route=mapped, reason=str(output.get("reason", "sdk_router")))

            mapped = self._map_route(str(output))
            return SDKRoutingDecision(route=mapped, reason="sdk_router_raw_output")
        except Exception as exc:
            logger.warning("openai_sdk_router_failed error=%s", exc)
            raise
        finally:
            if trace_ctx:
                trace_ctx.__exit__(None, None, None)

