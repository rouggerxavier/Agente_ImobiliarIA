"""
Entidades do domínio imobiliário — modelos Pydantic.

Todas as entidades possuem:
- id: UUID
- created_at / updated_at: timestamps
- Campos com semântica clara e validação explícita

Esta camada NÃO depende de ORM, banco de dados ou LLM.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .enums import (
    Channel,
    ConversationStatus,
    DetectedIntent,
    FollowUpStatus,
    FollowUpTrigger,
    HandoffReason,
    LeadIntent,
    LeadIntentStage,
    LeadStatus,
    LeadTemperature,
    MessageRole,
    MessageType,
    NextAction,
    PaymentType,
    PropertyPurpose,
    PropertyStatus,
    PropertyType,
    SLATier,
)


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ─────────────────────────────────────────────────────────────────────────────
# Lead
# ─────────────────────────────────────────────────────────────────────────────

class LeadPreferences(BaseModel):
    """Preferências imobiliárias estruturadas do lead."""
    intent: Optional[LeadIntent] = None
    property_type: Optional[PropertyType] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    micro_location: Optional[str] = None      # beira-mar, 1_quadra, etc.
    bedrooms_min: Optional[int] = None
    suites_min: Optional[int] = None
    bathrooms_min: Optional[int] = None
    parking_min: Optional[int] = None
    budget_min: Optional[int] = None          # R$
    budget_max: Optional[int] = None          # R$
    payment_type: Optional[PaymentType] = None
    furnished: Optional[bool] = None
    pet_friendly: Optional[bool] = None
    leisure_required: Optional[bool] = None
    leisure_level: Optional[str] = None       # simple|ok|full
    floor_pref: Optional[str] = None          # baixo|medio|alto
    sun_pref: Optional[str] = None            # nascente|poente
    timeline: Optional[str] = None           # 30d|3m|6m|12m|flexivel
    allows_short_term_rental: Optional[bool] = None
    condo_max: Optional[int] = None           # valor máximo de condomínio
    extra_requirements: Optional[str] = None  # texto livre


class PreferenceSignal(BaseModel):
    """Metadados auditaveis de um atributo consolidado do lead."""
    value: Any = None
    source: str = "unknown"
    updated_at: datetime = Field(default_factory=_now)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_text: Optional[str] = None


class LeadScore(BaseModel):
    """Score de qualificação do lead."""
    total: int = Field(default=0, ge=0, le=100)
    temperature: LeadTemperature = LeadTemperature.COLD
    profile_completeness: int = Field(default=0, ge=0, le=100)
    catalog_compatibility: int = Field(default=0, ge=0, le=100)
    urgency_score: int = Field(default=0, ge=0, le=100)
    engagement_score: int = Field(default=0, ge=0, le=100)
    financial_score: int = Field(default=0, ge=0, le=100)
    reasons: List[str] = Field(default_factory=list)
    formula_version: str = "1.0"
    computed_at: datetime = Field(default_factory=_now)


class Lead(BaseModel):
    """Entidade principal — representa um lead no CRM."""
    id: str = Field(default_factory=_new_id)
    # Dados de contato
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    # Origem
    channel: Channel = Channel.UNKNOWN
    external_id: Optional[str] = None   # ID no canal externo (WhatsApp, etc.)
    # Estado no CRM
    status: LeadStatus = LeadStatus.NEW
    intent_stage: LeadIntentStage = LeadIntentStage.UNKNOWN
    sla_tier: SLATier = SLATier.NURTURE
    assigned_broker_id: Optional[str] = None
    # Perfil
    preferences: LeadPreferences = Field(default_factory=LeadPreferences)
    preference_signals: Dict[str, PreferenceSignal] = Field(default_factory=dict)
    score: LeadScore = Field(default_factory=LeadScore)
    tags: List[str] = Field(default_factory=list)
    # Timestamps
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    last_activity_at: Optional[datetime] = None
    # Metadados
    source_url: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None

    def touch(self) -> None:
        self.updated_at = _now()
        self.last_activity_at = _now()


# ─────────────────────────────────────────────────────────────────────────────
# Conversa & Mensagem
# ─────────────────────────────────────────────────────────────────────────────

class Message(BaseModel):
    """Mensagem individual dentro de uma conversa."""
    id: str = Field(default_factory=_new_id)
    conversation_id: str
    lead_id: str
    role: MessageRole
    message_type: MessageType = MessageType.TEXT
    text: Optional[str] = None
    media_url: Optional[str] = None
    media_mime_type: Optional[str] = None
    transcription: Optional[str] = None   # para áudio
    external_message_id: Optional[str] = None  # ID no canal externo (dedup)
    detected_intent: Optional[DetectedIntent] = None
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    # Rastreabilidade
    trace_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


class ConversationSummary(BaseModel):
    """Resumo operacional da conversa — para handoff e continuação."""
    executive: str = ""        # Resumo para o corretor humano
    technical: str = ""        # Resumo para o agente retomar
    version: int = 0
    generated_at: datetime = Field(default_factory=_now)
    trigger: str = "initial"


class Conversation(BaseModel):
    """Conversa completa de um lead."""
    id: str = Field(default_factory=_new_id)
    lead_id: str
    channel: Channel = Channel.UNKNOWN
    status: ConversationStatus = ConversationStatus.ACTIVE
    messages: List[Message] = Field(default_factory=list)
    summary: ConversationSummary = Field(default_factory=ConversationSummary)
    summary_history: List[ConversationSummary] = Field(default_factory=list)
    # Roteamento
    assigned_broker_id: Optional[str] = None
    handoff_reason: Optional[HandoffReason] = None
    handoff_at: Optional[datetime] = None
    # Timestamps
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    last_message_at: Optional[datetime] = None

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        self.last_message_at = _now()
        self.updated_at = _now()


# ─────────────────────────────────────────────────────────────────────────────
# Imóvel / Catálogo
# ─────────────────────────────────────────────────────────────────────────────

class PropertyAmenities(BaseModel):
    """Comodidades e características do imóvel."""
    has_pool: bool = False
    has_gym: bool = False
    has_playground: bool = False
    has_party_room: bool = False
    has_gourmet_area: bool = False
    has_sauna: bool = False
    has_doorman: bool = False
    has_elevator: bool = False
    has_balcony: bool = False
    has_view: bool = False
    leisure_level: Optional[str] = None   # simple|ok|full
    other: List[str] = Field(default_factory=list)


class Property(BaseModel):
    """Imóvel do catálogo."""
    id: str = Field(default_factory=_new_id)
    external_ref: Optional[str] = None    # Código no sistema de origem
    # Localização
    city: str
    neighborhood: str
    address: Optional[str] = None
    micro_location: Optional[str] = None  # beira-mar, orla, etc.
    # Tipologia
    property_type: PropertyType
    purpose: PropertyPurpose
    # Dimensões
    area_m2: Optional[float] = None
    bedrooms: Optional[int] = None
    suites: Optional[int] = None
    bathrooms: Optional[int] = None
    parking: Optional[int] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    # Valores
    price: Optional[int] = None           # R$
    rent_price: Optional[int] = None      # R$ (para aluguel)
    condo_fee: Optional[int] = None       # R$
    iptu_annual: Optional[int] = None     # R$
    # Características
    furnished: Optional[bool] = None
    pet_friendly: Optional[bool] = None
    allows_short_term_rental: Optional[bool] = None
    sun_position: Optional[str] = None    # nascente|poente
    amenities: PropertyAmenities = Field(default_factory=PropertyAmenities)
    # Descrição
    description: Optional[str] = None     # Texto rico para busca semântica
    highlights: List[str] = Field(default_factory=list)
    # Status
    status: PropertyStatus = PropertyStatus.AVAILABLE
    unavailable_reason: Optional[str] = None  # Motivo quando não disponível
    unavailable_since: Optional[datetime] = None
    broker_id: Optional[str] = None
    # Campos internos (não expor ao lead/cliente)
    internal_notes: Optional[str] = None      # Notas privadas da operação
    cost_price: Optional[int] = None          # Preço de custo (campo privado)
    owner_name: Optional[str] = None          # Nome do proprietário (campo privado)
    owner_phone: Optional[str] = None         # Telefone do proprietário (campo privado)
    commission_pct: Optional[float] = None    # % de comissão (campo privado)
    # Timestamps
    listed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=_now)
    created_at: datetime = Field(default_factory=_now)

    def public_dict(self) -> dict:
        """Retorna apenas campos seguros para expor ao lead/cliente."""
        private = {"internal_notes", "cost_price", "owner_name", "owner_phone", "commission_pct"}
        return {k: v for k, v in self.model_dump().items() if k not in private}

    def is_showable(self) -> bool:
        """True se o imóvel pode ser sugerido ao lead (disponível ou reservado com aviso)."""
        return self.status in (PropertyStatus.AVAILABLE, PropertyStatus.RESERVED)


# ─────────────────────────────────────────────────────────────────────────────
# Corretor
# ─────────────────────────────────────────────────────────────────────────────

class Broker(BaseModel):
    """Corretor / agente humano."""
    id: str = Field(default_factory=_new_id)
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    # Especialidade
    specialty_cities: List[str] = Field(default_factory=list)
    specialty_neighborhoods: List[str] = Field(default_factory=list)
    specialty_types: List[PropertyType] = Field(default_factory=list)
    budget_min: Optional[int] = None      # Faixa que atende
    budget_max: Optional[int] = None
    # Disponibilidade
    is_active: bool = True
    max_daily_leads: int = 10
    current_lead_count: int = 0
    # Timestamps
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


# ─────────────────────────────────────────────────────────────────────────────
# Assignment — atribuição de lead a corretor
# ─────────────────────────────────────────────────────────────────────────────

class Assignment(BaseModel):
    """Atribuição de um lead a um corretor."""
    id: str = Field(default_factory=_new_id)
    lead_id: str
    broker_id: str
    conversation_id: Optional[str] = None
    reason: Optional[str] = None          # Motivo do roteamento
    score_at_assignment: int = 0
    summary_at_assignment: str = ""       # Resumo entregue ao corretor
    created_at: datetime = Field(default_factory=_now)


# ─────────────────────────────────────────────────────────────────────────────
# DecisionLog — auditoria de decisões da IA
# ─────────────────────────────────────────────────────────────────────────────

class DecisionLog(BaseModel):
    """Registro auditável de uma decisão tomada pela IA."""
    id: str = Field(default_factory=_new_id)
    lead_id: str
    conversation_id: str
    message_id: Optional[str] = None
    trace_id: Optional[str] = None
    # Decisão
    next_action: NextAction
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning: str = ""
    # Contexto usado
    lead_score: int = 0
    detected_intent: Optional[DetectedIntent] = None
    retrieval_context: List[str] = Field(default_factory=list)
    property_candidate_ids: List[str] = Field(default_factory=list)
    routing_decision: Optional[str] = None
    state_path: List[str] = Field(default_factory=list)
    checkpoint_id: Optional[str] = None
    guardrail_flags: List[str] = Field(default_factory=list)
    human_handoff_required: bool = False
    # LLM metadata
    model_used: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    # Timestamp
    created_at: datetime = Field(default_factory=_now)


# ─────────────────────────────────────────────────────────────────────────────
# FollowUpTask
# ─────────────────────────────────────────────────────────────────────────────

class FollowUpTask(BaseModel):
    """Tarefa de follow-up agendada."""
    id: str = Field(default_factory=_new_id)
    lead_id: str
    conversation_id: Optional[str] = None
    trigger: FollowUpTrigger
    status: FollowUpStatus = FollowUpStatus.PENDING
    message_template: str = ""
    channel: Channel = Channel.WHATSAPP
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


# ─────────────────────────────────────────────────────────────────────────────
# Recommendation — imóvel recomendado a um lead
# ─────────────────────────────────────────────────────────────────────────────

class Recommendation(BaseModel):
    """Recomendação de imóvel gerada pelo sistema."""
    id: str = Field(default_factory=_new_id)
    lead_id: str
    conversation_id: str
    property_id: str
    rank: int = 1                          # Posição no ranking
    match_score: float = Field(ge=0.0, le=1.0, default=0.0)
    match_reasons: List[str] = Field(default_factory=list)
    sales_pitch: str = ""                  # Justificativa orientada a venda
    shown_to_lead: bool = False
    lead_reaction: Optional[str] = None    # interested|not_interested|maybe
    created_at: datetime = Field(default_factory=_now)


# ─────────────────────────────────────────────────────────────────────────────
# EventEnvelope — envelope para eventos de domínio
# ─────────────────────────────────────────────────────────────────────────────

class EventEnvelope(BaseModel):
    """Envelope padronizado para eventos de domínio."""
    id: str = Field(default_factory=_new_id)
    event_type: str                         # Ex: "lead.qualified", "message.received"
    aggregate_id: str                       # ID da entidade principal
    aggregate_type: str                     # Ex: "Lead", "Conversation"
    payload: Dict[str, Any] = Field(default_factory=dict)
    # Rastreabilidade
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    lead_id: Optional[str] = None
    conversation_id: Optional[str] = None
    channel: Optional[Channel] = None
    # Timestamps
    occurred_at: datetime = Field(default_factory=_now)
    published_at: Optional[datetime] = None
    schema_version: str = "1.0"
