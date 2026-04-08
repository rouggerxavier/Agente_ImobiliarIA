"""
Enumerações oficiais do domínio imobiliário.

Centraliza todos os status, tipos e estágios usados no sistema.
Fonte única da verdade para valores enumerados.
"""

from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# Lead
# ─────────────────────────────────────────────────────────────────────────────

class LeadStatus(str, Enum):
    """Status do ciclo de vida de um lead."""
    NEW = "new"                       # Acabou de entrar
    IN_QUALIFICATION = "in_qualification"  # Em processo de qualificação pelo bot
    QUALIFIED = "qualified"           # Perfil completo o suficiente
    ASSIGNED = "assigned"             # Atribuído a um corretor
    IN_NEGOTIATION = "in_negotiation" # Negociação ativa
    VISIT_SCHEDULED = "visit_scheduled"   # Visita agendada
    VISIT_DONE = "visit_done"         # Visita realizada
    WON = "won"                       # Fechamento
    LOST = "lost"                     # Lead perdido
    COLD = "cold"                     # Lead esfriou (sem resposta)
    DISQUALIFIED = "disqualified"     # Fora do perfil da operação


class LeadTemperature(str, Enum):
    """Temperatura do lead — urgência e engajamento."""
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


class LeadIntent(str, Enum):
    """Intenção principal do lead."""
    BUY = "comprar"
    RENT = "alugar"
    INVEST = "investir"


class LeadIntentStage(str, Enum):
    """Estágio de intenção dentro do funil."""
    RESEARCHING = "researching"         # Pesquisando, sem urgência
    READY_TO_VISIT = "ready_to_visit"   # Pronto para visitar
    NEGOTIATING = "negotiating"         # Em negociação
    UNKNOWN = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Conversa / Mensagem
# ─────────────────────────────────────────────────────────────────────────────

class ConversationStatus(str, Enum):
    """Status de uma conversa."""
    ACTIVE = "active"
    PAUSED = "paused"           # Lead parou de responder
    COMPLETED = "completed"     # Triagem completa
    HANDED_OFF = "handed_off"   # Passada para humano
    CLOSED = "closed"           # Encerrada


class MessageRole(str, Enum):
    """Papel do autor da mensagem."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, Enum):
    """Tipo / modalidade da mensagem."""
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    DOCUMENT = "document"
    LOCATION = "location"
    STICKER = "sticker"


class Channel(str, Enum):
    """Canal de origem da conversa."""
    WHATSAPP = "whatsapp"
    WEB = "web"
    DASHBOARD = "dashboard"
    EMAIL = "email"
    SMS = "sms"
    UNKNOWN = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Intenção detectada pelo LLM
# ─────────────────────────────────────────────────────────────────────────────

class DetectedIntent(str, Enum):
    """Intenção detectada na mensagem individual."""
    BUY = "buy"
    RENT = "rent"
    FAQ = "faq"
    SCHEDULE_VISIT = "schedule_visit"
    NEGOTIATE_PRICE = "negotiate_price"
    COMPLAINT = "complaint"
    GREETING = "greeting"
    FAREWELL = "farewell"
    OUT_OF_SCOPE = "out_of_scope"
    UNKNOWN = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Imóvel
# ─────────────────────────────────────────────────────────────────────────────

class PropertyType(str, Enum):
    """Tipo de imóvel."""
    APARTMENT = "apartamento"
    HOUSE = "casa"
    PENTHOUSE = "cobertura"
    STUDIO = "studio"
    COMMERCIAL = "comercial"
    LAND = "terreno"
    RURAL = "rural"


class PropertyStatus(str, Enum):
    """Status comercial do imóvel no catálogo."""
    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"
    RENTED = "rented"
    OFF_MARKET = "off_market"


class PropertyPurpose(str, Enum):
    """Finalidade do imóvel."""
    SALE = "venda"
    RENT = "aluguel"
    BOTH = "venda_e_aluguel"


# ─────────────────────────────────────────────────────────────────────────────
# Handoff / Roteamento
# ─────────────────────────────────────────────────────────────────────────────

class HandoffReason(str, Enum):
    """Motivo do handoff para humano."""
    HIGH_SCORE = "high_score"
    USER_REQUEST = "user_request"
    NEGOTIATION = "negociacao"
    CONFUSION = "confusion"
    COMPLAINT = "complaint"
    POLICY_VIOLATION = "policy_violation"
    LLM_FAILURE = "llm_failure"
    TIMEOUT = "timeout"
    OTHER = "outro"


class RoutingStrategy(str, Enum):
    """Estratégia de roteamento de lead para corretor."""
    ROUND_ROBIN = "round_robin"
    SPECIALTY = "specialty"          # Por especialidade/região
    LOAD_BALANCE = "load_balance"    # Por carga atual
    PRIORITY = "priority"            # Leads quentes primeiro


# ─────────────────────────────────────────────────────────────────────────────
# Follow-up
# ─────────────────────────────────────────────────────────────────────────────

class FollowUpStatus(str, Enum):
    """Status de uma tarefa de follow-up."""
    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class FollowUpTrigger(str, Enum):
    """Gatilho que originou o follow-up."""
    COLD_LEAD = "cold_lead"
    NO_RESPONSE = "no_response"
    POST_VISIT = "post_visit"
    POST_PROPOSAL = "post_proposal"
    UNAVAILABLE_PROPERTY = "unavailable_property"
    WARM_LEAD = "warm_lead"


# ─────────────────────────────────────────────────────────────────────────────
# Decisão da IA (Next Best Action)
# ─────────────────────────────────────────────────────────────────────────────

class NextAction(str, Enum):
    """Próxima ação recomendada pelo motor de decisão."""
    ASK_MISSING_FIELD = "ask_missing_field"
    SUGGEST_PROPERTIES = "suggest_properties"
    ANSWER_OBJECTION = "answer_objection"
    INVITE_VISIT = "invite_visit"
    REQUEST_DOCUMENT = "request_document"
    ROUTE_TO_BROKER = "route_to_broker"
    SCHEDULE_FOLLOWUP = "schedule_followup"
    CLOSE_WITH_FUTURE_RETURN = "close_with_future_return"
    HUMAN_HANDOFF = "human_handoff"
    RESPOND_FAQ = "respond_faq"


# ─────────────────────────────────────────────────────────────────────────────
# SLA
# ─────────────────────────────────────────────────────────────────────────────

class SLATier(str, Enum):
    """Nível de SLA de atendimento."""
    IMMEDIATE = "immediate"   # HOT — contato em minutos
    NORMAL = "normal"         # WARM — dentro de horas
    NURTURE = "nurture"       # COLD — nurturing automatizado


# ─────────────────────────────────────────────────────────────────────────────
# Forma de pagamento
# ─────────────────────────────────────────────────────────────────────────────

class PaymentType(str, Enum):
    """Forma de pagamento preferida pelo lead."""
    FINANCING = "financiamento"
    FGTS = "fgts"
    CASH = "a_vista"
    CONSORTIUM = "consorcio"
    MIXED = "misto"
    UNKNOWN = "unknown"
