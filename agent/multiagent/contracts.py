from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class OrchestratorRoute(str, Enum):
    LEGACY_TRIAGE = "legacy_triage"
    CATALOG = "catalog"
    KNOWLEDGE = "knowledge"
    SAFE_FALLBACK = "safe_fallback"


@dataclass(slots=True)
class OrchestratorRequest:
    session_id: str
    message: str
    name: Optional[str] = None
    correlation_id: Optional[str] = None


@dataclass(slots=True)
class ToolCallRecord:
    name: str
    status: str
    duration_ms: int
    input_payload: Dict[str, Any] = field(default_factory=dict)
    output_payload: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass(slots=True)
class HandoffRecord:
    source: str
    target: str
    reason: str


@dataclass(slots=True)
class OrchestratorDecision:
    route: OrchestratorRoute
    reason: str
    delegated_to: str
    used_openai_sdk_router: bool = False


@dataclass(slots=True)
class SubagentResult:
    payload: Dict[str, Any]
    handled: bool = True
    reason: str = ""
    requires_handoff: bool = False


@dataclass(slots=True)
class OrchestratorResult:
    payload: Dict[str, Any]
    decision: OrchestratorDecision
    handoffs: List[HandoffRecord] = field(default_factory=list)
    tool_calls: List[ToolCallRecord] = field(default_factory=list)

