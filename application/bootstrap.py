"""
Bootstrap do fluxo das fases 3 e 4.
"""
from __future__ import annotations

import agent.knowledge_base as legacy_kb

from application.catalog import CatalogService
from application.conversation_orchestrator import ConversationOrchestrator, MessageInput
from application.crm import CRMService
from application.knowledge import KnowledgeService
from infrastructure.persistence.json_file import create_persistent_repos

_runtime: dict | None = None


def get_phase34_runtime() -> dict:
    global _runtime
    if _runtime is not None:
        return _runtime

    repos = create_persistent_repos()
    catalog = CatalogService(repos["properties"], repos["recommendations"])
    knowledge = KnowledgeService(legacy_kb=legacy_kb)
    crm = CRMService(repos["leads"], repos["brokers"], repos["assignments"])
    orchestrator = ConversationOrchestrator(
        lead_repo=repos["leads"],
        conversation_repo=repos["conversations"],
        message_repo=repos["messages"],
        decision_log_repo=repos["decision_logs"],
        event_repo=repos["events"],
        crm_service=crm,
        catalog_service=catalog,
        knowledge_service=knowledge,
        followup_service=None,
        analytics_service=None,
        checkpoint_store=repos["checkpoints"],
    )
    _runtime = {
        "repos": repos,
        "catalog": catalog,
        "knowledge": knowledge,
        "crm": crm,
        "orchestrator": orchestrator,
    }
    return _runtime


def process_phase34_message(msg_input: MessageInput) -> dict:
    runtime = get_phase34_runtime()
    orchestrator: ConversationOrchestrator = runtime["orchestrator"]
    return orchestrator.process_legacy_payload(msg_input)
