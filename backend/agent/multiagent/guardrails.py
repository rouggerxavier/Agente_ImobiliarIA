from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


SENSITIVE_PATTERNS = (
    "rm -rf",
    "drop table",
    "truncate table",
    "delete from",
    "apagar tudo",
    "deletar banco",
    "excluir banco",
    "resetar banco",
    "vazar token",
    "mostrar api key",
)


@dataclass(slots=True)
class GuardrailVerdict:
    allowed: bool
    reason: str


def evaluate_message_guardrail(message: str, *, allow_sensitive_actions: bool) -> GuardrailVerdict:
    normalized = (message or "").strip().lower()
    if not normalized:
        return GuardrailVerdict(False, "empty_message")

    if allow_sensitive_actions:
        return GuardrailVerdict(True, "allowed_by_flag")

    for pattern in SENSITIVE_PATTERNS:
        if pattern in normalized:
            return GuardrailVerdict(False, f"blocked_sensitive_pattern:{pattern}")

    return GuardrailVerdict(True, "ok")


def validate_tool_input(tool_name: str, payload: Dict[str, Any]) -> GuardrailVerdict:
    if tool_name == "property_catalog_search":
        budget = payload.get("budget")
        bedrooms = payload.get("bedrooms")

        if budget is not None:
            try:
                budget_int = int(budget)
            except (TypeError, ValueError):
                return GuardrailVerdict(False, "invalid_budget_type")
            if budget_int < 0:
                return GuardrailVerdict(False, "negative_budget")
            if budget_int > 100_000_000:
                return GuardrailVerdict(False, "budget_out_of_bounds")

        if bedrooms is not None:
            try:
                bedrooms_int = int(bedrooms)
            except (TypeError, ValueError):
                return GuardrailVerdict(False, "invalid_bedrooms_type")
            if bedrooms_int < 0 or bedrooms_int > 20:
                return GuardrailVerdict(False, "bedrooms_out_of_bounds")

    return GuardrailVerdict(True, "ok")

