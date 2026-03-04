"""Namespace bridge to expose root ``services`` as ``app.services``."""

from pathlib import Path

__path__ = [str(Path(__file__).resolve().parents[2] / "services")]
