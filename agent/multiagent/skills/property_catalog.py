from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from agent import tools

from ..guardrails import validate_tool_input
from .base import SkillContext, SkillResult


_BUDGET_REGEX = re.compile(r"(?:r\$\s*)?([0-9][0-9\.,]{2,})", re.IGNORECASE)
_BEDROOMS_REGEX = re.compile(r"(\d+)\s*(?:quartos?|dormitorios?)", re.IGNORECASE)


class PropertyCatalogSearchSkill:
    name = "property_catalog_search"

    def _extract_budget(self, message: str) -> Optional[int]:
        match = _BUDGET_REGEX.search(message)
        if not match:
            return None
        raw = match.group(1).replace(".", "").replace(",", "")
        try:
            value = int(raw)
        except ValueError:
            return None
        if value < 1000:
            # Evita confundir numero pequeno com preco
            return None
        return value

    def _extract_bedrooms(self, message: str) -> Optional[int]:
        match = _BEDROOMS_REGEX.search(message)
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

    def _extract_intent(self, message: str) -> str:
        normalized = message.lower()
        if any(token in normalized for token in ("alugar", "locacao", "loca\u00e7\u00e3o", "aluguel")):
            return "alugar"
        return "comprar"

    def _extract_neighborhood(self, message: str, known: List[str]) -> Optional[str]:
        normalized_message = message.lower()
        for neighborhood in known:
            if neighborhood.lower() in normalized_message:
                return neighborhood
        return None

    def _extract_city(self, message: str) -> Optional[str]:
        normalized = message.lower()
        if "joao pessoa" in normalized or "jo\u00e3o pessoa" in normalized:
            return "Joao Pessoa"
        if "cabedelo" in normalized:
            return "Cabedelo"
        if "bayeux" in normalized:
            return "Bayeux"
        if "santa rita" in normalized:
            return "Santa Rita"
        return None

    def _build_filters(self, message: str) -> Dict[str, Any]:
        neighborhoods = tools.get_neighborhoods()
        return {
            "city": self._extract_city(message),
            "neighborhood": self._extract_neighborhood(message, neighborhoods),
            "property_type": "apartamento" if "apart" in message.lower() else None,
            "bedrooms": self._extract_bedrooms(message),
            "pet": None,
            "furnished": None,
            "budget": self._extract_budget(message),
        }

    def run(self, context: SkillContext) -> SkillResult:
        filters = self._build_filters(context.message)
        verdict = validate_tool_input(self.name, filters)
        if not verdict.allowed:
            return SkillResult(success=False, error=verdict.reason, data={"filters": filters})

        try:
            intent = self._extract_intent(context.message)
            results = tools.search_properties(filters, intent=intent)
            return SkillResult(
                success=True,
                data={
                    "intent": intent,
                    "filters": filters,
                    "properties": results,
                },
            )
        except Exception as exc:
            return SkillResult(success=False, error=f"search_failed:{exc}", data={"filters": filters})

