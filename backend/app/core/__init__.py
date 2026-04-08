"""Namespace bridge to expose root ``core`` as ``app.core``."""

from pathlib import Path

__path__ = [str(Path(__file__).resolve().parents[2] / "core")]
