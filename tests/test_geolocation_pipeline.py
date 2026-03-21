import importlib
import os
import sys
from pathlib import Path


def test_geolocation_orchestrator_generates_audit_report(tmp_path):
    db_path = tmp_path / "geo_pipeline.db"
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"

    try:
        for module_name in [
            "main",
            "db",
            "models.imovel",
            "routes.imoveis",
            "seeds.imoveis_seed",
            "agent.multiagent.geolocation_pipeline",
        ]:
            sys.modules.pop(module_name, None)

        db = importlib.import_module("db")
        db.init_db()

        pipeline_module = importlib.import_module("agent.multiagent.geolocation_pipeline")
        GeoPipelineConfig = pipeline_module.GeoPipelineConfig
        GeolocationOrchestrator = pipeline_module.GeolocationOrchestrator

        report_path = tmp_path / "geo_audit.json"
        trace_path = tmp_path / "geo_trace.jsonl"
        orchestrator = GeolocationOrchestrator(
            GeoPipelineConfig(
                legacy_catalog_path=Path("data/grankasa_catalog_enriched.json"),
                report_path=report_path,
                trace_path=trace_path,
                fetch_missing_map_url=False,
                persist_probable_matches=False,
            )
        )
        report = orchestrator.run(screenshot_map={})

        assert report_path.exists()
        assert trace_path.exists()
        assert report["summary"]["total_properties"] > 0
        assert report["summary"]["legacy_records"] > 0
        assert report["summary"]["match_exact"] >= 1
        assert len(report["validations"]) == report["summary"]["total_properties"]
        assert any(item["match_status"] in {"exato", "provavel"} for item in report["validations"])
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
