"""Namespace bridge to expose root ``agent`` as ``app.agent``."""

from pathlib import Path

__path__ = [str(Path(__file__).resolve().parents[2] / "agent")]
