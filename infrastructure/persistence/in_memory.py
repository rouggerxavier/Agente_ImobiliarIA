"""
Implementações in-memory dos repositórios do domínio.

Usadas em:
  - Testes unitários (sem banco real)
  - Desenvolvimento local sem PostgreSQL
  - Futura substituição por SQLAlchemy quando Fase 1 estiver pronta

Todas as operações são thread-safe com lock interno simples.
"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Dict, List, Optional

from domain.entities import (
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
from domain.enums import (
    ConversationStatus,
    FollowUpStatus,
    LeadStatus,
    PropertyPurpose,
    PropertyStatus,
    PropertyType,
)
from domain.repositories import (
    AssignmentRepository,
    BrokerRepository,
    ConversationRepository,
    DecisionLogRepository,
    EventRepository,
    FollowUpRepository,
    LeadRepository,
    MessageRepository,
    PropertyRepository,
    RecommendationRepository,
)


class InMemoryLeadRepository(LeadRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Lead] = {}
        self._by_session: Dict[str, str] = {}  # session_id → lead_id
        self._lock = threading.Lock()

    def save(self, lead: Lead) -> Lead:
        with self._lock:
            self._store[lead.id] = lead
            if lead.external_id:
                self._by_session[lead.external_id] = lead.id
        return lead

    def get_by_id(self, lead_id: str) -> Optional[Lead]:
        return self._store.get(lead_id)

    def get_by_phone(self, phone: str) -> Optional[Lead]:
        for lead in self._store.values():
            if lead.phone == phone:
                return lead
        return None

    def get_by_session(self, session_id: str) -> Optional[Lead]:
        lead_id = self._by_session.get(session_id)
        return self._store.get(lead_id) if lead_id else None

    def list_by_status(self, status: LeadStatus, limit: int = 50) -> List[Lead]:
        return [l for l in self._store.values() if l.status == status][:limit]

    def update_score(self, lead_id: str, score_data: dict) -> None:
        lead = self._store.get(lead_id)
        if lead:
            lead.score.total = score_data.get("total", lead.score.total)


class InMemoryConversationRepository(ConversationRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Conversation] = {}
        self._lock = threading.Lock()

    def save(self, conversation: Conversation) -> Conversation:
        with self._lock:
            self._store[conversation.id] = conversation
        return conversation

    def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        return self._store.get(conversation_id)

    def get_active_by_lead(self, lead_id: str) -> Optional[Conversation]:
        for conv in self._store.values():
            if conv.lead_id == lead_id and conv.status == ConversationStatus.ACTIVE:
                return conv
        return None

    def list_by_lead(self, lead_id: str) -> List[Conversation]:
        return [c for c in self._store.values() if c.lead_id == lead_id]

    def update_status(self, conversation_id: str, status: ConversationStatus) -> None:
        conv = self._store.get(conversation_id)
        if conv:
            conv.status = status


class InMemoryMessageRepository(MessageRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Message] = {}
        self._by_external: Dict[str, str] = {}  # external_id → message_id
        self._lock = threading.Lock()

    def save(self, message: Message) -> Message:
        with self._lock:
            self._store[message.id] = message
            if message.external_message_id:
                self._by_external[message.external_message_id] = message.id
        return message

    def get_by_id(self, message_id: str) -> Optional[Message]:
        return self._store.get(message_id)

    def get_by_external_id(self, external_message_id: str) -> Optional[Message]:
        msg_id = self._by_external.get(external_message_id)
        return self._store.get(msg_id) if msg_id else None

    def list_by_conversation(self, conversation_id: str, limit: int = 100) -> List[Message]:
        msgs = [m for m in self._store.values() if m.conversation_id == conversation_id]
        msgs.sort(key=lambda m: m.created_at)
        return msgs[-limit:]


class InMemoryPropertyRepository(PropertyRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Property] = {}
        self._lock = threading.Lock()

    def save(self, property: Property) -> Property:
        with self._lock:
            self._store[property.id] = property
        return property

    def get_by_id(self, property_id: str) -> Optional[Property]:
        return self._store.get(property_id)

    def search(
        self,
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
        purpose: Optional[PropertyPurpose] = None,
        property_type: Optional[PropertyType] = None,
        bedrooms_min: Optional[int] = None,
        budget_max: Optional[int] = None,
        budget_min: Optional[int] = None,
        status: PropertyStatus = PropertyStatus.AVAILABLE,
        limit: int = 10,
        order_by: str = "relevance",
    ) -> List[Property]:
        results = []
        for p in self._store.values():
            if p.status != status:
                continue
            if city and city.lower() not in p.city.lower():
                continue
            if neighborhood and neighborhood.lower() not in p.neighborhood.lower():
                continue
            if purpose and p.purpose != purpose:
                continue
            if property_type and p.property_type != property_type:
                continue
            if bedrooms_min and p.bedrooms and p.bedrooms < bedrooms_min:
                continue
            price = p.price or p.rent_price or 0
            if budget_max and price > budget_max:
                continue
            if budget_min and price < budget_min:
                continue
            results.append(p)

        results = self._sort_results(
            results,
            order_by=order_by,
            budget_max=budget_max,
            bedrooms_min=bedrooms_min,
            neighborhood=neighborhood,
        )
        return results[:limit]

    def _sort_results(
        self,
        results: List[Property],
        order_by: str,
        budget_max: Optional[int] = None,
        bedrooms_min: Optional[int] = None,
        neighborhood: Optional[str] = None,
    ) -> List[Property]:
        if order_by == "price_asc":
            return sorted(results, key=lambda p: (p.price or p.rent_price or 0))
        if order_by == "price_desc":
            return sorted(results, key=lambda p: (p.price or p.rent_price or 0), reverse=True)
        if order_by == "newest":
            return sorted(results, key=lambda p: p.created_at, reverse=True)
        # relevance — pontuação composta
        def relevance_score(p: Property) -> float:
            score = 0.0
            # Bairro exato tem alta relevância
            if neighborhood and p.neighborhood and neighborhood.lower() == p.neighborhood.lower():
                score += 3.0
            elif neighborhood and p.neighborhood and neighborhood.lower() in p.neighborhood.lower():
                score += 1.5
            # Preço próximo ao limite máximo (uso do orçamento ideal)
            price = p.price or p.rent_price or 0
            if budget_max and price:
                ratio = price / budget_max
                if 0.6 <= ratio <= 1.0:
                    score += 2.0 * (1.0 - abs(ratio - 0.85))
            # Quartos exatos ao mínimo
            if bedrooms_min and p.bedrooms:
                if p.bedrooms == bedrooms_min:
                    score += 1.0
                elif p.bedrooms > bedrooms_min:
                    score += 0.5
            # Imóvel com descrição completa
            if p.description:
                score += 0.3
            if p.highlights:
                score += 0.2
            return score
        return sorted(results, key=relevance_score, reverse=True)

    def list_by_broker(self, broker_id: str) -> List[Property]:
        return [p for p in self._store.values() if p.broker_id == broker_id]


class InMemoryBrokerRepository(BrokerRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Broker] = {}
        self._lock = threading.Lock()

    def save(self, broker: Broker) -> Broker:
        with self._lock:
            self._store[broker.id] = broker
        return broker

    def get_by_id(self, broker_id: str) -> Optional[Broker]:
        return self._store.get(broker_id)

    def list_active(self) -> List[Broker]:
        return [b for b in self._store.values() if b.is_active]

    def find_best_match(self, lead: Lead) -> Optional[Broker]:
        """Round-robin simples entre brokers ativos com capacidade disponível."""
        active = [
            b for b in self._store.values()
            if b.is_active and b.current_lead_count < b.max_daily_leads
        ]
        if not active:
            return None
        # Ordena por menor carga
        active.sort(key=lambda b: b.current_lead_count)
        return active[0]


class InMemoryAssignmentRepository(AssignmentRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Assignment] = {}
        self._lock = threading.Lock()

    def save(self, assignment: Assignment) -> Assignment:
        with self._lock:
            self._store[assignment.id] = assignment
        return assignment

    def get_by_lead(self, lead_id: str) -> Optional[Assignment]:
        for a in sorted(self._store.values(), key=lambda x: x.created_at, reverse=True):
            if a.lead_id == lead_id:
                return a
        return None

    def list_by_broker(self, broker_id: str) -> List[Assignment]:
        return [a for a in self._store.values() if a.broker_id == broker_id]


class InMemoryDecisionLogRepository(DecisionLogRepository):
    def __init__(self) -> None:
        self._store: Dict[str, DecisionLog] = {}
        self._lock = threading.Lock()

    def save(self, log: DecisionLog) -> DecisionLog:
        with self._lock:
            self._store[log.id] = log
        return log

    def list_by_conversation(self, conversation_id: str) -> List[DecisionLog]:
        return [l for l in self._store.values() if l.conversation_id == conversation_id]

    def list_by_lead(self, lead_id: str) -> List[DecisionLog]:
        return [l for l in self._store.values() if l.lead_id == lead_id]


class InMemoryFollowUpRepository(FollowUpRepository):
    def __init__(self) -> None:
        self._store: Dict[str, FollowUpTask] = {}
        self._lock = threading.Lock()

    def save(self, task: FollowUpTask) -> FollowUpTask:
        with self._lock:
            self._store[task.id] = task
        return task

    def get_by_id(self, task_id: str) -> Optional[FollowUpTask]:
        return self._store.get(task_id)

    def list_pending(self, before: Optional[datetime] = None) -> List[FollowUpTask]:
        tasks = [t for t in self._store.values() if t.status == FollowUpStatus.PENDING]
        if before:
            tasks = [t for t in tasks if t.scheduled_at <= before]
        return tasks

    def cancel_for_lead(self, lead_id: str, reason: str) -> None:
        with self._lock:
            for task in self._store.values():
                if task.lead_id == lead_id and task.status == FollowUpStatus.PENDING:
                    task.status = FollowUpStatus.CANCELLED
                    task.cancel_reason = reason

    def update_status(self, task_id: str, status: FollowUpStatus) -> None:
        task = self._store.get(task_id)
        if task:
            task.status = status


class InMemoryRecommendationRepository(RecommendationRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Recommendation] = {}
        self._lock = threading.Lock()

    def save(self, recommendation: Recommendation) -> Recommendation:
        with self._lock:
            self._store[recommendation.id] = recommendation
        return recommendation

    def get_by_id(self, recommendation_id: str) -> Optional[Recommendation]:
        return self._store.get(recommendation_id)

    def list_by_lead(self, lead_id: str) -> List[Recommendation]:
        return sorted(
            [r for r in self._store.values() if r.lead_id == lead_id],
            key=lambda r: r.created_at,
        )

    def list_by_conversation(self, conversation_id: str) -> List[Recommendation]:
        return sorted(
            [r for r in self._store.values() if r.conversation_id == conversation_id],
            key=lambda r: r.created_at,
        )

    def update_reaction(self, recommendation_id: str, reaction: str) -> None:
        rec = self._store.get(recommendation_id)
        if rec:
            rec.lead_reaction = reaction


class InMemoryEventRepository(EventRepository):
    def __init__(self) -> None:
        self._store: Dict[str, EventEnvelope] = {}
        self._lock = threading.Lock()

    def publish(self, event: EventEnvelope) -> None:
        with self._lock:
            self._store[event.id] = event

    def list_unpublished(self, limit: int = 100) -> List[EventEnvelope]:
        return [e for e in self._store.values() if e.published_at is None][:limit]

    def mark_published(self, event_id: str) -> None:
        event = self._store.get(event_id)
        if event:
            from datetime import datetime
            event.published_at = datetime.utcnow()


# ─────────────────────────────────────────────────────────────────────────────
# Factory — cria um conjunto completo de repos in-memory
# ─────────────────────────────────────────────────────────────────────────────

def create_in_memory_repos() -> dict:
    """
    Retorna dicionário com todos os repositórios in-memory instanciados.
    Útil para testes e desenvolvimento sem banco real.

    Uso:
        repos = create_in_memory_repos()
        orchestrator = ConversationOrchestrator(
            lead_repo=repos["leads"],
            conversation_repo=repos["conversations"],
            ...
        )
    """
    return {
        "leads": InMemoryLeadRepository(),
        "conversations": InMemoryConversationRepository(),
        "messages": InMemoryMessageRepository(),
        "properties": InMemoryPropertyRepository(),
        "brokers": InMemoryBrokerRepository(),
        "assignments": InMemoryAssignmentRepository(),
        "decision_logs": InMemoryDecisionLogRepository(),
        "followups": InMemoryFollowUpRepository(),
        "events": InMemoryEventRepository(),
    }
