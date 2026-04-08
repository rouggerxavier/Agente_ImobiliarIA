from unittest.mock import Mock

import pytest

import application.bootstrap as bootstrap_module
from infrastructure.persistence.session_state import (
    JsonSessionStateRepository,
    create_session_state_repository,
)


def _raising_sql_builder():
    raise RuntimeError("sql unavailable")


def test_production_sql_failure_does_not_fallback_to_json(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/agente")
    monkeypatch.setenv("ORCHESTRATOR_STATE_BACKEND", "auto")
    monkeypatch.setattr(
        "infrastructure.persistence.session_state._build_sql_session_state_repository",
        _raising_sql_builder,
    )

    with pytest.raises(RuntimeError, match="nao ha fallback para arquivo local"):
        create_session_state_repository()


def test_development_sql_failure_can_fallback_to_json(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ORCHESTRATOR_STATE_BACKEND", "auto")
    monkeypatch.setattr(
        "infrastructure.persistence.session_state._build_sql_session_state_repository",
        _raising_sql_builder,
    )

    repo = create_session_state_repository()
    assert isinstance(repo, JsonSessionStateRepository)


def test_production_forced_json_backend_fails_explicitly(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/agente")
    monkeypatch.setenv("ORCHESTRATOR_STATE_BACKEND", "json")

    with pytest.raises(RuntimeError, match="nao e permitido em producao"):
        create_session_state_repository()


def test_bootstrap_wires_session_state_repository(monkeypatch):
    sentinel_repo = Mock()
    bootstrap_module._runtime = None

    monkeypatch.setattr(bootstrap_module, "create_session_state_repository", lambda: sentinel_repo)
    monkeypatch.setattr(
        bootstrap_module,
        "create_persistent_repos",
        lambda: {
            "leads": Mock(),
            "conversations": Mock(),
            "messages": Mock(),
            "properties": Mock(),
            "brokers": Mock(),
            "assignments": Mock(),
            "decision_logs": Mock(),
            "followups": Mock(),
            "recommendations": Mock(),
            "events": Mock(),
            "checkpoints": Mock(),
        },
    )

    runtime = bootstrap_module.get_phase34_runtime()
    assert runtime["session_state_repo"] is sentinel_repo
    assert runtime["orchestrator"]._session_states is sentinel_repo

    bootstrap_module._runtime = None
