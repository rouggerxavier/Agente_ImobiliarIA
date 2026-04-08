"""Namespace bridge to expose root ``routes`` as ``app.routes``."""

from pathlib import Path

__path__ = [str(Path(__file__).resolve().parents[2] / "routes")]
