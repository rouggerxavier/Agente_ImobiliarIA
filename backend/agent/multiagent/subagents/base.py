from __future__ import annotations

from typing import Protocol

from ..contracts import OrchestratorRequest, SubagentResult


class Subagent(Protocol):
    name: str

    def run(self, request: OrchestratorRequest) -> SubagentResult:
        ...

