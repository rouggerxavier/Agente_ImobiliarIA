"""Database session and engine configuration.

Default database is SQLite for local tests. To migrate to PostgreSQL,
set DATABASE_URL (for example):
postgresql+psycopg://user:password@host:5432/database
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/imoveis.db")
logger = logging.getLogger(__name__)


def _ensure_sqlite_directory(db_url: str) -> None:
    """Ensure local directory exists when using SQLite file database."""
    if not db_url.startswith("sqlite:///"):
        return

    sqlite_path = db_url.replace("sqlite:///", "", 1)
    db_dir = Path(sqlite_path).parent
    if str(db_dir) and str(db_dir) != ".":
        db_dir.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_directory(DATABASE_URL)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def _prepare_metadata_for_model_reload() -> None:
    """
    Clear stale SQLAlchemy table metadata before a forced model re-import in tests.

    Some tests remove `models.imovel` from `sys.modules` and then call `init_db()`
    again while reusing the already-imported `app.db` module. In this case the old
    `Base.metadata` still contains the previous `imoveis` table definition, which
    causes duplicate table registration during the new import.
    """
    if "models.imovel" in sys.modules:
        return
    if Base.metadata.tables:
        Base.metadata.clear()


def _sqlite_schema_needs_reset() -> bool:
    """Detect very old SQLite schema and trigger a one-time rebuild."""
    if not DATABASE_URL.startswith("sqlite"):
        return False

    inspector = inspect(engine)
    if "imoveis" not in inspector.get_table_names():
        return False

    columns = {column["name"] for column in inspector.get_columns("imoveis")}
    required_core = {
        "codigo",
        "tipo_negocio",
        "titulo",
        "descricao",
        "foto_url",
        "area_m2",
        "bairro",
        "cidade",
    }
    return not required_core.issubset(columns)


def _ensure_missing_columns() -> list[str]:
    """Add optional columns to legacy ``imoveis`` tables without data loss."""
    from models.imovel import Imovel

    inspector = inspect(engine)
    if "imoveis" not in inspector.get_table_names():
        return []

    existing_columns = {column["name"] for column in inspector.get_columns("imoveis")}
    missing_columns: list[str] = []
    table = Imovel.__table__

    with engine.begin() as connection:
        for column in table.columns:
            if column.name in existing_columns:
                continue
            statement = text(
                f"ALTER TABLE {engine.dialect.identifier_preparer.quote(table.name)} "
                f"ADD COLUMN {engine.dialect.identifier_preparer.quote(column.name)} "
                f"{column.type.compile(dialect=engine.dialect)}"
            )
            connection.execute(statement)
            missing_columns.append(column.name)
            logger.info("Added missing column to imoveis table: %s", column.name)

    return missing_columns


def init_db() -> None:
    """Create tables if they do not exist."""
    _prepare_metadata_for_model_reload()
    # Import model modules here to ensure metadata is populated.
    from models import imovel as _imovel  # noqa: F401
    from seeds.imoveis_seed import seed_imoveis

    reset_triggered = _sqlite_schema_needs_reset()
    if reset_triggered:
        logger.warning("SQLite legacy schema detected. Rebuilding `imoveis` table with current model.")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    missing_columns = _ensure_missing_columns()

    with SessionLocal() as db:
        seed_imoveis(db)
    logger.info(
        "Database initialized db_url=%s reset_triggered=%s missing_columns=%s",
        DATABASE_URL,
        reset_triggered,
        missing_columns,
    )


def get_db() -> Generator[Session, None, None]:
    """Yield a DB session for request scope."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
