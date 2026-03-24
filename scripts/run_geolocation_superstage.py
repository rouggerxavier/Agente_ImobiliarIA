from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.multiagent.geolocation_pipeline import GeoPipelineConfig, GeolocationOrchestrator


def _load_screenshot_map(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return {str(key): str(value) for key, value in payload.items()}
    if isinstance(payload, list):
        mapping: dict[str, str] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            codigo = str(item.get("codigo") or "").strip()
            screenshot_path = str(item.get("screenshot_path") or "").strip()
            if codigo and screenshot_path:
                mapping[codigo] = screenshot_path
        return mapping
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa a superetapa de geolocalizacao com orquestracao multiagente.")
    parser.add_argument(
        "--legacy-catalog",
        default="data/grankasa_catalog_enriched.json",
        help="Arquivo JSON do catalogo legado enriquecido.",
    )
    parser.add_argument(
        "--trace-path",
        default="data/geo_localizacao_trace.jsonl",
        help="Arquivo JSONL de tracing da orquestracao.",
    )
    parser.add_argument(
        "--report-path",
        default="artifacts/geolocalizacao/geolocalizacao_auditoria.json",
        help="Arquivo JSON de auditoria final por imovel.",
    )
    parser.add_argument(
        "--screenshots-json",
        default="artifacts/geolocalizacao/geolocalizacao_screenshots.json",
        help="JSON com mapeamento codigo->screenshot_path (gerado na validacao E2E).",
    )
    parser.add_argument(
        "--persist-probable",
        action="store_true",
        help="Permite persistir matches provaveis (por padrao, apenas matches exatos).",
    )
    parser.add_argument(
        "--skip-map-fetch",
        action="store_true",
        help="Nao tenta buscar mapa_url faltante no site legado.",
    )
    args = parser.parse_args()

    screenshot_map = _load_screenshot_map(Path(args.screenshots_json))
    orchestrator = GeolocationOrchestrator(
        GeoPipelineConfig(
            legacy_catalog_path=Path(args.legacy_catalog),
            trace_path=Path(args.trace_path),
            report_path=Path(args.report_path),
            screenshot_report_path=Path(args.screenshots_json),
            fetch_missing_map_url=not args.skip_map_fetch,
            persist_probable_matches=args.persist_probable,
        )
    )
    report = orchestrator.run(screenshot_map=screenshot_map)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
