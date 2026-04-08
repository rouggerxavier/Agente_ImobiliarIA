import importlib
import sys

import pytest


def _reload_app_db_module():
    sys.modules.pop("app.db", None)
    sys.modules.pop("db", None)
    return importlib.import_module("app.db")


@pytest.fixture(autouse=True)
def _restore_db_module_after_test(monkeypatch):
    yield
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./data/imoveis.db")
    _reload_app_db_module()


def test_production_without_database_url_fails_explicitly(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        _reload_app_db_module()


def test_production_with_sqlite_fails_explicitly(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./data/imoveis.db")

    with pytest.raises(RuntimeError, match="SQLite"):
        _reload_app_db_module()


def test_development_can_fallback_to_sqlite(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    db_module = _reload_app_db_module()
    assert db_module.DATABASE_URL.startswith("sqlite:///")
    assert db_module.current_database_backend() == "sqlite"


def test_database_url_postgres_is_normalized(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/agente")

    db_module = _reload_app_db_module()
    assert db_module.DATABASE_URL.startswith("postgresql+psycopg://")
    assert db_module.current_database_backend() == "postgresql"


def test_production_accepts_postgresql_with_psycopg(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/agente")

    db_module = _reload_app_db_module()
    assert db_module.DATABASE_URL.startswith("postgresql+psycopg://")
    assert db_module.current_database_backend() == "postgresql"
