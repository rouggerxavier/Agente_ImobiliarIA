from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class MultiAgentConfig:
    enabled: bool
    openai_sdk_router_enabled: bool
    openai_sdk_model: str
    trace_path: str
    trace_enabled: bool
    allow_sensitive_actions: bool


DEFAULT_TRACE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "multiagent_trace.jsonl",
)


def load_multiagent_config() -> MultiAgentConfig:
    return MultiAgentConfig(
        enabled=_env_bool("MULTIAGENT_ENABLED", False),
        openai_sdk_router_enabled=_env_bool("MULTIAGENT_OPENAI_SDK_ROUTER_ENABLED", False),
        openai_sdk_model=os.getenv("MULTIAGENT_OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
        trace_path=os.getenv("MULTIAGENT_TRACE_PATH", DEFAULT_TRACE_PATH),
        trace_enabled=_env_bool("MULTIAGENT_TRACE_ENABLED", True),
        allow_sensitive_actions=_env_bool("MULTIAGENT_ALLOW_SENSITIVE_ACTIONS", False),
    )

