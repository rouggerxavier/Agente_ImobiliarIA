"""
Persistencia em JSON para as entidades operacionais das Fases 3 e 4.

Mantem memoria conversacional e checkpoints fora da store em memoria do legado,
sem bloquear a futura migracao para SQLAlchemy/PostgreSQL.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Type

from pydantic import BaseModel

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
from infrastructure.persistence.in_memory import (
    InMemoryBrokerRepository,
    InMemoryPropertyRepository,
)
from infrastructure.storage.legacy_adapter import load_brokers, load_properties


STORE_DIR = Path(os.getenv("ORCHESTRATOR_STORE_DIR", "data/orchestrator"))
STORE_DIR.mkdir(parents=True, exist_ok=True)

_FILE_LOCKS: Dict[str, threading.RLock] = {}


def _file_lock(path: Path) -> threading.RLock:
    key = str(path.resolve())
    if key not in _FILE_LOCKS:
        _FILE_LOCKS[key] = threading.RLock()
    return _FILE_LOCKS[key]


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _atomic_write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
    temp.replace(path)


class _JsonModelRepository:
    def __init__(self, filename: str, model_type: Type[BaseModel]) -> None:
        self._path = STORE_DIR / filename
        self._model_type = model_type
        self._lock = _file_lock(self._path)

    def _read_models(self) -> Dict[str, BaseModel]:
        raw = _load_json(self._path)
        return {
            model_id: self._model_type.model_validate(payload)
            for model_id, payload in raw.items()
            if isinstance(payload, dict)
        }

    def _write_models(self, models: Dict[str, BaseModel]) -> None:
        payload = {model_id: model.model_dump(mode="json") for model_id, model in models.items()}
        _atomic_write(self._path, payload)

    def _save_model(self, model: BaseModel) -> BaseModel:
        with self._lock:
            models = self._read_models()
            models[getattr(model, "id")] = model
            self._write_models(models)
        return model

    def _get_model(self, model_id: str) -> Optional[BaseModel]:
        with self._lock:
            return self._read_models().get(model_id)

    def _list_models(self) -> List[BaseModel]:
        with self._lock:
            return list(self._read_models().values())


class JsonLeadRepository(_JsonModelRepository, LeadRepository):
    def __init__(self) -> None:
        super().__init__("leads.json", Lead)

    def save(self, lead: Lead) -> Lead:
        return self._save_model(lead)

    def get_by_id(self, lead_id: str) -> Optional[Lead]:
        return self._get_model(lead_id)

    def get_by_phone(self, phone: str) -> Optional[Lead]:
        for lead in self._list_models():
            if lead.phone == phone:
                return lead
        return None

    def get_by_session(self, session_id: str) -> Optional[Lead]:
        for lead in self._list_models():
            if lead.external_id == session_id:
                return lead
        return None

    def list_by_status(self, status: LeadStatus, limit: int = 50) -> List[Lead]:
        return [lead for lead in self._list_models() if lead.status == status][:limit]

    def update_score(self, lead_id: str, score_data: dict) -> None:
        lead = self.get_by_id(lead_id)
        if not lead:
            return
        for key, value in (score_data or {}).items():
            if hasattr(lead.score, key):
                setattr(lead.score, key, value)
        self.save(lead)


class JsonConversationRepository(_JsonModelRepository, ConversationRepository):
    def __init__(self) -> None:
        super().__init__("conversations.json", Conversation)

    def save(self, conversation: Conversation) -> Conversation:
        return self._save_model(conversation)

    def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        return self._get_model(conversation_id)

    def get_active_by_lead(self, lead_id: str) -> Optional[Conversation]:
        conversations = sorted(
            self._list_models(),
            key=lambda item: item.updated_at,
            reverse=True,
        )
        for conversation in conversations:
            if conversation.lead_id == lead_id and conversation.status == ConversationStatus.ACTIVE:
                return conversation
        return None

    def list_by_lead(self, lead_id: str) -> List[Conversation]:
        conversations = [conversation for conversation in self._list_models() if conversation.lead_id == lead_id]
        conversations.sort(key=lambda item: item.updated_at)
        return conversations

    def update_status(self, conversation_id: str, status: ConversationStatus) -> None:
        conversation = self.get_by_id(conversation_id)
        if not conversation:
            return
        conversation.status = status
        conversation.updated_at = datetime.utcnow()
        self.save(conversation)


class JsonMessageRepository(_JsonModelRepository, MessageRepository):
    def __init__(self) -> None:
        super().__init__("messages.json", Message)

    def save(self, message: Message) -> Message:
        return self._save_model(message)

    def get_by_id(self, message_id: str) -> Optional[Message]:
        return self._get_model(message_id)

    def get_by_external_id(self, external_message_id: str) -> Optional[Message]:
        for message in self._list_models():
            if message.external_message_id == external_message_id:
                return message
        return None

    def list_by_conversation(self, conversation_id: str, limit: int = 100) -> List[Message]:
        messages = [message for message in self._list_models() if message.conversation_id == conversation_id]
        messages.sort(key=lambda item: item.created_at)
        return messages[-limit:]


class JsonAssignmentRepository(_JsonModelRepository, AssignmentRepository):
    def __init__(self) -> None:
        super().__init__("assignments.json", Assignment)

    def save(self, assignment: Assignment) -> Assignment:
        return self._save_model(assignment)

    def get_by_lead(self, lead_id: str) -> Optional[Assignment]:
        assignments = [assignment for assignment in self._list_models() if assignment.lead_id == lead_id]
        assignments.sort(key=lambda item: item.created_at, reverse=True)
        return assignments[0] if assignments else None

    def list_by_broker(self, broker_id: str) -> List[Assignment]:
        return [assignment for assignment in self._list_models() if assignment.broker_id == broker_id]


class JsonDecisionLogRepository(_JsonModelRepository, DecisionLogRepository):
    def __init__(self) -> None:
        super().__init__("decision_logs.json", DecisionLog)

    def save(self, log: DecisionLog) -> DecisionLog:
        return self._save_model(log)

    def list_by_conversation(self, conversation_id: str) -> List[DecisionLog]:
        logs = [log for log in self._list_models() if log.conversation_id == conversation_id]
        logs.sort(key=lambda item: item.created_at)
        return logs

    def list_by_lead(self, lead_id: str) -> List[DecisionLog]:
        logs = [log for log in self._list_models() if log.lead_id == lead_id]
        logs.sort(key=lambda item: item.created_at)
        return logs


class JsonFollowUpRepository(_JsonModelRepository, FollowUpRepository):
    def __init__(self) -> None:
        super().__init__("followups.json", FollowUpTask)

    def save(self, task: FollowUpTask) -> FollowUpTask:
        return self._save_model(task)

    def get_by_id(self, task_id: str) -> Optional[FollowUpTask]:
        return self._get_model(task_id)

    def list_pending(self, before: Optional[datetime] = None) -> List[FollowUpTask]:
        tasks = [task for task in self._list_models() if task.status == FollowUpStatus.PENDING]
        if before is not None:
            tasks = [task for task in tasks if task.scheduled_at <= before]
        tasks.sort(key=lambda item: item.scheduled_at)
        return tasks

    def cancel_for_lead(self, lead_id: str, reason: str) -> None:
        tasks = self.list_pending()
        for task in tasks:
            if task.lead_id != lead_id:
                continue
            task.status = FollowUpStatus.CANCELLED
            task.cancel_reason = reason
            task.cancelled_at = datetime.utcnow()
            self.save(task)

    def update_status(self, task_id: str, status: FollowUpStatus) -> None:
        task = self.get_by_id(task_id)
        if not task:
            return
        task.status = status
        if status == FollowUpStatus.SENT:
            task.sent_at = datetime.utcnow()
        self.save(task)


class JsonRecommendationRepository(_JsonModelRepository, RecommendationRepository):
    def __init__(self) -> None:
        super().__init__("recommendations.json", Recommendation)

    def save(self, recommendation: Recommendation) -> Recommendation:
        return self._save_model(recommendation)

    def get_by_id(self, recommendation_id: str) -> Optional[Recommendation]:
        return self._get_model(recommendation_id)

    def list_by_lead(self, lead_id: str) -> List[Recommendation]:
        recs = [r for r in self._list_models() if r.lead_id == lead_id]
        recs.sort(key=lambda r: r.created_at)
        return recs

    def list_by_conversation(self, conversation_id: str) -> List[Recommendation]:
        recs = [r for r in self._list_models() if r.conversation_id == conversation_id]
        recs.sort(key=lambda r: r.created_at)
        return recs

    def update_reaction(self, recommendation_id: str, reaction: str) -> None:
        rec = self.get_by_id(recommendation_id)
        if not rec:
            return
        rec.lead_reaction = reaction
        self.save(rec)


class JsonEventRepository(_JsonModelRepository, EventRepository):
    def __init__(self) -> None:
        super().__init__("events.json", EventEnvelope)

    def publish(self, event: EventEnvelope) -> None:
        self._save_model(event)

    def list_unpublished(self, limit: int = 100) -> List[EventEnvelope]:
        events = [event for event in self._list_models() if event.published_at is None]
        events.sort(key=lambda item: item.occurred_at)
        return events[:limit]

    def mark_published(self, event_id: str) -> None:
        event = self._get_model(event_id)
        if not event:
            return
        event.published_at = datetime.utcnow()
        self._save_model(event)


class JsonCheckpointStore:
    def __init__(self) -> None:
        self._path = STORE_DIR / "checkpoints.json"
        self._lock = _file_lock(self._path)

    def save(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        checkpoint = dict(payload)
        checkpoint.setdefault("id", str(uuid.uuid4()))
        checkpoint.setdefault("created_at", datetime.utcnow().isoformat())
        with self._lock:
            data = _load_json(self._path)
            data[checkpoint["id"]] = checkpoint
            _atomic_write(self._path, data)
        return checkpoint

    def get(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return _load_json(self._path).get(checkpoint_id)

    def list_by_conversation(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            data = list(_load_json(self._path).values())
        items = [item for item in data if item.get("conversation_id") == conversation_id]
        items.sort(key=lambda item: item.get("created_at", ""))
        return items[-limit:]

    def get_latest(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        items = self.list_by_conversation(conversation_id, limit=1)
        return items[0] if items else None


def _map_property_type(raw_value: Any) -> PropertyType:
    normalized = str(raw_value or "").strip().lower()
    mapping = {
        "apartamento": PropertyType.APARTMENT,
        "ap": PropertyType.APARTMENT,
        "casa": PropertyType.HOUSE,
        "cobertura": PropertyType.PENTHOUSE,
        "studio": PropertyType.STUDIO,
        "comercial": PropertyType.COMMERCIAL,
        "terreno": PropertyType.LAND,
        "rural": PropertyType.RURAL,
    }
    return mapping.get(normalized, PropertyType.APARTMENT)


def _map_property_purpose(item: Dict[str, Any]) -> PropertyPurpose:
    sale_price = int(item.get("preco_venda") or 0)
    rent_price = int(item.get("preco_aluguel") or 0)
    if sale_price and rent_price:
        return PropertyPurpose.BOTH
    if sale_price:
        return PropertyPurpose.SALE
    return PropertyPurpose.RENT


def _load_property_repo() -> PropertyRepository:
    repo = InMemoryPropertyRepository()
    for item in load_properties():
        property_model = Property(
            external_ref=str(item.get("id") or item.get("codigo") or ""),
            city=str(item.get("cidade") or ""),
            neighborhood=str(item.get("bairro") or ""),
            property_type=_map_property_type(item.get("tipo")),
            purpose=_map_property_purpose(item),
            area_m2=item.get("area_m2"),
            bedrooms=item.get("quartos"),
            parking=item.get("vagas"),
            price=item.get("preco_venda") or None,
            rent_price=item.get("preco_aluguel") or None,
            condo_fee=item.get("condominio") or None,
            iptu_annual=item.get("iptu") or None,
            furnished=item.get("mobiliado"),
            pet_friendly=item.get("aceita_pet"),
            description=item.get("descricao_curta"),
            highlights=[item.get("titulo")] if item.get("titulo") else [],
            status=PropertyStatus.AVAILABLE,
        )
        repo.save(property_model)
    return repo


def _resolve_broker_source() -> Iterable[Dict[str, Any]]:
    candidates = [
        Path("data/agents.json"),
        Path("data/agents.example.json"),
    ]
    for path in candidates:
        if path.exists():
            data = load_brokers(str(path))
            if data:
                return data
    return []


def _load_broker_repo() -> BrokerRepository:
    repo = InMemoryBrokerRepository()
    for item in _resolve_broker_source():
        broker = Broker(
            id=str(item.get("id") or uuid.uuid4()),
            name=str(item.get("name") or item.get("nome") or "Corretor"),
            whatsapp=item.get("whatsapp"),
            phone=item.get("phone") or item.get("telefone"),
            email=item.get("email"),
            specialty_neighborhoods=list(item.get("coverage_neighborhoods") or item.get("specialty_neighborhoods") or []),
            specialty_cities=list(item.get("coverage_cities") or item.get("specialty_cities") or []),
            specialty_types=[],
            budget_min=item.get("price_min"),
            budget_max=item.get("price_max"),
            is_active=bool(item.get("active", True)),
            max_daily_leads=int(item.get("daily_capacity") or item.get("max_daily_leads") or 10),
        )
        repo.save(broker)
    return repo


def create_persistent_repos() -> Dict[str, Any]:
    return {
        "leads": JsonLeadRepository(),
        "conversations": JsonConversationRepository(),
        "messages": JsonMessageRepository(),
        "properties": _load_property_repo(),
        "brokers": _load_broker_repo(),
        "assignments": JsonAssignmentRepository(),
        "decision_logs": JsonDecisionLogRepository(),
        "followups": JsonFollowUpRepository(),
        "recommendations": JsonRecommendationRepository(),
        "events": JsonEventRepository(),
        "checkpoints": JsonCheckpointStore(),
    }
