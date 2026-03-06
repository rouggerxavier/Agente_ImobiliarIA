from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional
from .geo_normalizer import has_non_ascii, location_key, preferred_label
from .knowledge_base import list_geo_neighborhoods

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "properties.json")
AGENTS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "agents.json")
EXPOSE_AGENT_CONTACT = os.getenv("EXPOSE_AGENT_CONTACT", "false").lower() in ("true", "1", "yes")


def load_properties() -> List[Dict[str, Any]]:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


PROPERTIES_CACHE = load_properties()


def _normalize_location(text: str) -> str:
    return location_key(text)


def _load_agent_neighborhoods() -> List[str]:
    if not os.path.exists(AGENTS_PATH):
        return []
    try:
        with open(AGENTS_PATH, "r", encoding="utf-8") as f:
            agents = json.load(f)
    except Exception:
        return []

    out: List[str] = []
    for agent in agents:
        for bairro in agent.get("coverage_neighborhoods", []) or []:
            if bairro and bairro != "*":
                out.append(str(bairro))
    return out


def _build_neighborhood_registry() -> List[str]:
    by_key: Dict[str, str] = {}

    def add_name(name: str) -> None:
        raw = (name or "").strip()
        if not raw:
            return
        key = _normalize_location(raw)
        if not key:
            return
        prev = by_key.get(key)
        if not prev:
            by_key[key] = raw
            return
        by_key[key] = preferred_label(prev, raw)

    for p in PROPERTIES_CACHE:
        add_name(str(p.get("bairro") or ""))

    for bairro in _load_agent_neighborhoods():
        add_name(bairro)

    for bairro in list_geo_neighborhoods():
        add_name(bairro)

    return [by_key[k] for k in sorted(by_key.keys())]


NEIGHBORHOOD_REGISTRY = _build_neighborhood_registry()


def get_neighborhoods() -> List[str]:
    return list(NEIGHBORHOOD_REGISTRY)


def get_property(prop_id: str) -> Optional[Dict[str, Any]]:
    for p in PROPERTIES_CACHE:
        if p.get("id") == prop_id:
            return p
    return None


def _price_for_intent(prop: Dict[str, Any], intent: str) -> Optional[int]:
    if intent == "alugar":
        price = prop.get("preco_aluguel") or 0
    else:
        price = prop.get("preco_venda") or 0
    return price if price > 0 else None


def _match_location(prop: Dict[str, Any], city: Optional[str], neighborhood: Optional[str]) -> bool:
    if neighborhood:
        return _normalize_location(prop.get("bairro", "")) == _normalize_location(neighborhood)
    if city:
        return _normalize_location(prop.get("cidade", "")) == _normalize_location(city)
    return False


def search_properties(filters: Dict[str, Any], intent: str) -> List[Dict[str, Any]]:
    city = filters.get("city")
    neighborhood = filters.get("neighborhood")
    prop_type = filters.get("property_type")
    bedrooms = filters.get("bedrooms")
    pet = filters.get("pet")
    furnished = filters.get("furnished")
    budget = filters.get("budget")

    results: List[Dict[str, Any]] = []
    for prop in PROPERTIES_CACHE:
        if not _match_location(prop, city, neighborhood):
            continue
        if prop_type and prop_type != "qualquer" and prop.get("tipo") != prop_type:
            continue
        price = _price_for_intent(prop, intent)
        if price is None or (budget and price > budget * 1.1):  # small tolerance
            continue
        if bedrooms and prop.get("quartos") and prop.get("quartos") < bedrooms:
            continue
        if pet is not None and prop.get("aceita_pet") is not None and prop.get("aceita_pet") != pet:
            continue
        if furnished is not None and prop.get("mobiliado") is not None and prop.get("mobiliado") != furnished:
            continue

        score = 0
        if neighborhood and _normalize_location(prop.get("bairro", "")) == _normalize_location(neighborhood):
            score += 5
        elif city and _normalize_location(prop.get("cidade", "")) == _normalize_location(city):
            score += 3
        if prop_type and prop_type != "qualquer" and prop.get("tipo") == prop_type:
            score += 3
        if bedrooms and prop.get("quartos") == bedrooms:
            score += 2
        if pet is not None and prop.get("aceita_pet") == pet:
            score += 1
        if furnished is not None and prop.get("mobiliado") == furnished:
            score += 1
        if budget and price:
            diff = abs(price - budget)
            budget_score = max(0, 3 - (diff / max(budget, 1)) * 3)
            score += budget_score
        prop["_score"] = score
        results.append(prop)

    results.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return results[:6]


# stubs for scheduling/handoff

def schedule_visit(property_id: str, preferred_times: List[str], mode: str) -> Dict[str, Any]:
    return {
        "property_id": property_id,
        "preferred_times": preferred_times,
        "mode": mode,
        "status": "registrado",
    }


def handoff_human(summary: str) -> Dict[str, Any]:
    return {
        "status": "handoff",
        "summary": summary,
    }
