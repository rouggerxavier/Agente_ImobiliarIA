"""Exports lazily loaded da camada de aplicacao."""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.catalog import CatalogService, PropertyMatch, SearchFilters
    from application.catalog_ingestion import CatalogIngestionService, IngestionReport
    from application.conversation_orchestrator import ConversationOrchestrator, MessageInput, OrchestratorResult
    from application.crm import CRMService, HandoffContext
    from application.knowledge import DocumentInput, KnowledgeResult, KnowledgeService
    from application.knowledge_eval import RAGEvalCase, RAGEvaluator


_EXPORTS = {
    "ConversationOrchestrator": ("application.conversation_orchestrator", "ConversationOrchestrator"),
    "MessageInput": ("application.conversation_orchestrator", "MessageInput"),
    "OrchestratorResult": ("application.conversation_orchestrator", "OrchestratorResult"),
    "CRMService": ("application.crm", "CRMService"),
    "HandoffContext": ("application.crm", "HandoffContext"),
    "CatalogService": ("application.catalog", "CatalogService"),
    "SearchFilters": ("application.catalog", "SearchFilters"),
    "PropertyMatch": ("application.catalog", "PropertyMatch"),
    "CatalogIngestionService": ("application.catalog_ingestion", "CatalogIngestionService"),
    "IngestionReport": ("application.catalog_ingestion", "IngestionReport"),
    "KnowledgeService": ("application.knowledge", "KnowledgeService"),
    "KnowledgeResult": ("application.knowledge", "KnowledgeResult"),
    "DocumentInput": ("application.knowledge", "DocumentInput"),
    "RAGEvaluator": ("application.knowledge_eval", "RAGEvaluator"),
    "RAGEvalCase": ("application.knowledge_eval", "RAGEvalCase"),
}

__all__ = list(_EXPORTS.keys())


def __getattr__(name: str):
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attr_name = target
    module = import_module(module_name)
    return getattr(module, attr_name)
