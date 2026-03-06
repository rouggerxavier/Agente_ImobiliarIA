from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.geo_normalizer import canonical_city, canonical_neighborhood

PROPERTIES_PATH = ROOT_DIR / "data" / "properties.json"
AGENTS_PATH = ROOT_DIR / "data" / "agents.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_properties(properties: List[Dict[str, Any]]) -> int:
    changes = 0
    for row in properties:
        original_city = row.get("cidade")
        original_neighborhood = row.get("bairro")
        new_city = canonical_city(original_city) if original_city else original_city
        new_neighborhood = canonical_neighborhood(original_neighborhood) if original_neighborhood else original_neighborhood
        if new_city != original_city:
            row["cidade"] = new_city
            changes += 1
        if new_neighborhood != original_neighborhood:
            row["bairro"] = new_neighborhood
            changes += 1
    return changes


def normalize_agents(agents: List[Dict[str, Any]]) -> int:
    changes = 0
    for row in agents:
        coverage = row.get("coverage_neighborhoods") or []
        normalized = []
        changed = False
        for neighborhood in coverage:
            if neighborhood == "*":
                normalized.append(neighborhood)
                continue
            canon = canonical_neighborhood(str(neighborhood))
            normalized.append(canon)
            if canon != neighborhood:
                changed = True
        if changed:
            row["coverage_neighborhoods"] = normalized
            changes += 1
    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview/backfill de normalizacao canônica geo")
    parser.add_argument("--write", action="store_true", help="Persiste mudancas em data/properties.json e data/agents.json")
    args = parser.parse_args()

    properties = _load_json(PROPERTIES_PATH)
    agents = _load_json(AGENTS_PATH)

    prop_changes = normalize_properties(properties)
    agent_changes = normalize_agents(agents)

    print(f"properties changes: {prop_changes}")
    print(f"agents changes: {agent_changes}")

    if args.write:
        _save_json(PROPERTIES_PATH, properties)
        _save_json(AGENTS_PATH, agents)
        print("changes written to disk")
    else:
        print("dry-run only (use --write to persist)")


if __name__ == "__main__":
    main()
