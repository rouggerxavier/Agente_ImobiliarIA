"""
Application layer — exporta todos os serviços e contratos.

Uso:
    from application.conversation_orchestrator import ConversationOrchestrator, MessageInput, OrchestratorResult
    from application.crm import CRMService, HandoffContext
    from application.catalog import CatalogService, SearchFilters, PropertyMatch
    from application.catalog_ingestion import CatalogIngestionService, IngestionReport
    from application.knowledge import KnowledgeService, KnowledgeResult
"""

from application.conversation_orchestrator import (
    ConversationOrchestrator,
    MessageInput,
    OrchestratorResult,
)
from application.crm import CRMService, HandoffContext
from application.catalog import CatalogService, SearchFilters, PropertyMatch
from application.catalog_ingestion import CatalogIngestionService, IngestionReport
from application.knowledge import KnowledgeService, KnowledgeResult, DocumentInput

__all__ = [
    # M1 - Orquestrador
    "ConversationOrchestrator",
    "MessageInput",
    "OrchestratorResult",
    # M2 - CRM
    "CRMService",
    "HandoffContext",
    # M3 - Catálogo
    "CatalogService",
    "SearchFilters",
    "PropertyMatch",
    "CatalogIngestionService",
    "IngestionReport",
    # M4 - Conhecimento
    "KnowledgeService",
    "KnowledgeResult",
    "DocumentInput",
]
