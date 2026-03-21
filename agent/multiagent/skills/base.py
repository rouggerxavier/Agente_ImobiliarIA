from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Protocol


@dataclass(slots=True)
class SkillContext:
    session_id: str
    message: str
    correlation_id: str | None = None


@dataclass(slots=True)
class SkillResult:
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class Skill(Protocol):
    name: str

    def run(self, context: SkillContext) -> SkillResult:
        ...

