"""
Interfaces (ports) dos repositórios — contratos que infrastructure/ deve implementar.

Seguindo o padrão Ports & Adapters (Hexagonal Architecture).
O domínio define O QUE precisa; infrastructure/ define COMO fazer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from .entities import (
    Assignment,
    Broker,
    Conversation,
    DecisionLog,
    EventEnvelope,
    FollowUpTask,
    Lead,
    Message,
    Property,
    Recommendation,
)

from .enums import (
    ConversationStatus,
    FollowUpStatus,
    LeadStatus,
    PropertyPurpose,
    PropertyStatus,
    PropertyType,
)


class LeadRepository(ABC):
    """Port para persistência de leads."""

    @abstractmethod
    def save(self, lead: Lead) -> Lead:
        ...

    @abstractmethod
    def get_by_id(self, lead_id: str) -> Optional[Lead]:
        ...

    @abstractmethod
    def get_by_phone(self, phone: str) -> Optional[Lead]:
        ...

    @abstractmethod
    def get_by_session(self, session_id: str) -> Optional[Lead]:
        ...

    @abstractmethod
    def list_by_status(self, status: LeadStatus, limit: int = 50) -> List[Lead]:
        ...

    @abstractmethod
    def update_score(self, lead_id: str, score_data: dict) -> None:
        ...


class ConversationRepository(ABC):
    """Port para persistência de conversas."""

    @abstractmethod
    def save(self, conversation: Conversation) -> Conversation:
        ...

    @abstractmethod
    def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        ...

    @abstractmethod
    def get_active_by_lead(self, lead_id: str) -> Optional[Conversation]:
        ...

    @abstractmethod
    def list_by_lead(self, lead_id: str) -> List[Conversation]:
        ...

    @abstractmethod
    def update_status(self, conversation_id: str, status: ConversationStatus) -> None:
        ...


class MessageRepository(ABC):
    """Port para persistência de mensagens."""

    @abstractmethod
    def save(self, message: Message) -> Message:
        ...

    @abstractmethod
    def get_by_id(self, message_id: str) -> Optional[Message]:
        ...

    @abstractmethod
    def get_by_external_id(self, external_message_id: str) -> Optional[Message]:
        """Usado para deduplicação de mensagens do canal externo."""
        ...

    @abstractmethod
    def list_by_conversation(self, conversation_id: str, limit: int = 100) -> List[Message]:
        ...


class PropertyRepository(ABC):
    """Port para o catálogo de imóveis."""

    @abstractmethod
    def save(self, property: Property) -> Property:
        ...

    @abstractmethod
    def get_by_id(self, property_id: str) -> Optional[Property]:
        ...

    @abstractmethod
    def search(
        self,
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
        purpose: Optional[PropertyPurpose] = None,
        property_type: Optional[PropertyType] = None,
        bedrooms_min: Optional[int] = None,
        budget_max: Optional[int] = None,
        budget_min: Optional[int] = None,
        status: Optional[PropertyStatus] = PropertyStatus.AVAILABLE,
        limit: int = 10,
        order_by: str = "relevance",  # "relevance" | "price_asc" | "price_desc" | "newest"
    ) -> List[Property]:
        ...

    @abstractmethod
    def list_by_broker(self, broker_id: str) -> List[Property]:
        ...


class BrokerRepository(ABC):
    """Port para corretores."""

    @abstractmethod
    def save(self, broker: Broker) -> Broker:
        ...

    @abstractmethod
    def get_by_id(self, broker_id: str) -> Optional[Broker]:
        ...

    @abstractmethod
    def list_active(self) -> List[Broker]:
        ...

    @abstractmethod
    def find_best_match(self, lead: Lead) -> Optional[Broker]:
        """Encontra o corretor mais adequado para o lead."""
        ...


class AssignmentRepository(ABC):
    """Port para atribuições lead-corretor."""

    @abstractmethod
    def save(self, assignment: Assignment) -> Assignment:
        ...

    @abstractmethod
    def get_by_lead(self, lead_id: str) -> Optional[Assignment]:
        ...

    @abstractmethod
    def list_by_broker(self, broker_id: str) -> List[Assignment]:
        ...


class DecisionLogRepository(ABC):
    """Port para log de decisões da IA."""

    @abstractmethod
    def save(self, log: DecisionLog) -> DecisionLog:
        ...

    @abstractmethod
    def list_by_conversation(self, conversation_id: str) -> List[DecisionLog]:
        ...

    @abstractmethod
    def list_by_lead(self, lead_id: str) -> List[DecisionLog]:
        ...


class FollowUpRepository(ABC):
    """Port para tarefas de follow-up."""

    @abstractmethod
    def save(self, task: FollowUpTask) -> FollowUpTask:
        ...

    @abstractmethod
    def get_by_id(self, task_id: str) -> Optional[FollowUpTask]:
        ...

    @abstractmethod
    def list_pending(self, before: Optional[datetime] = None) -> List[FollowUpTask]:
        """Lista follow-ups pendentes agendados até `before` (datetime)."""
        ...

    @abstractmethod
    def cancel_for_lead(self, lead_id: str, reason: str) -> None:
        """Cancela todos os follow-ups pendentes de um lead."""
        ...

    @abstractmethod
    def update_status(self, task_id: str, status: FollowUpStatus) -> None:
        ...


class RecommendationRepository(ABC):
    """Port para persistência de recomendações de imóveis."""

    @abstractmethod
    def save(self, recommendation: Recommendation) -> Recommendation:
        ...

    @abstractmethod
    def get_by_id(self, recommendation_id: str) -> Optional[Recommendation]:
        ...

    @abstractmethod
    def list_by_lead(self, lead_id: str) -> List[Recommendation]:
        ...

    @abstractmethod
    def list_by_conversation(self, conversation_id: str) -> List[Recommendation]:
        ...

    @abstractmethod
    def update_reaction(self, recommendation_id: str, reaction: str) -> None:
        """Registra reação do lead: interested|not_interested|maybe."""
        ...


class EventRepository(ABC):
    """Port para eventos de domínio (outbox / event log)."""

    @abstractmethod
    def publish(self, event: EventEnvelope) -> None:
        ...

    @abstractmethod
    def list_unpublished(self, limit: int = 100) -> List[EventEnvelope]:
        ...

    @abstractmethod
    def mark_published(self, event_id: str) -> None:
        ...
