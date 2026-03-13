"""Database session and engine configuration.

Default database is SQLite for local tests. To migrate to PostgreSQL,
set DATABASE_URL (for example):
postgresql+psycopg://user:password@host:5432/database
"""

from __future__ import annotations

import os
from pathlib import Path
from collections.abc import Generator

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import declarative_base, sessionmaker, Session


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/imoveis.db")


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


def _sqlite_schema_needs_reset() -> bool:
    """Detect legacy SQLite schema for `imoveis` and trigger rebuild."""
    if not DATABASE_URL.startswith("sqlite"):
        return False

    inspector = inspect(engine)
    if "imoveis" not in inspector.get_table_names():
        return False

    columns = {column["name"] for column in inspector.get_columns("imoveis")}
    required_columns = {"codigo", "tipo_negocio", "titulo", "condominio", "tem_elevadores", "foto_url"}
    return not required_columns.issubset(columns)


def init_db() -> None:
    """Create tables if they do not exist."""
    # Import model modules here to ensure metadata is populated.
    from models import imovel as _imovel  # noqa: F401
    from seeds.imoveis_seed import seed_imoveis

    if _sqlite_schema_needs_reset():
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        seed_imoveis(db)


def get_db() -> Generator[Session, None, None]:
    """Yield a DB session for request scope."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
