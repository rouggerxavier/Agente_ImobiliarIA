"""
[M6] Observabilidade / Analytics — métricas de negócio e produto.

Casos de uso:
- RecordBusinessEvent: registra evento de produto padronizado
- GetFunnelMetrics: taxa por estágio do funil
- GetBrokerPerformance: métricas por corretor
- GetAIQualityMetrics: groundedness, latência, custo LLM

Fase atual: eventos são logados estruturadamente e poderão ser
agregados por qualquer ferramenta de analytics (Grafana, Metabase, etc.).
Fase 11 do roadmap: instrumentar com OpenTelemetry.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.trace import get_logger

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ─────────────────────────────────────────────────────────────────────────────
# Catálogo de eventos de produto (nomenclatura padronizada)
# ─────────────────────────────────────────────────────────────────────────────

class BusinessEvent:
    """Nomenclatura oficial de eventos de produto."""

    # Ciclo do lead
    LEAD_CREATED = "lead.created"
    LEAD_QUALIFIED = "lead.qualified"
    LEAD_ASSIGNED = "lead.assigned"
    LEAD_WON = "lead.won"
    LEAD_LOST = "lead.lost"
    LEAD_REENGAGED = "lead.reengaged"

    # Conversa
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_COMPLETED = "conversation.completed"
    FIRST_RESPONSE_SENT = "conversation.first_response_sent"

    # Handoff
    HANDOFF_INITIATED = "handoff.initiated"
    HANDOFF_ACCEPTED = "handoff.accepted"

    # Visita
    VISIT_SCHEDULED = "visit.scheduled"
    VISIT_COMPLETED = "visit.completed"
    VISIT_NO_SHOW = "visit.no_show"

    # IA
    AI_DECISION_MADE = "ai.decision_made"
    AI_HALLUCINATION_DETECTED = "ai.hallucination_detected"
    AI_FALLBACK_USED = "ai.fallback_used"
    AI_QUALITY_LOW = "ai.quality_low"

    # Follow-up
    FOLLOWUP_SENT = "followup.sent"
    FOLLOWUP_RESPONDED = "followup.responded"

    # Catálogo
    CATALOG_MATCH_FOUND = "catalog.match_found"
    CATALOG_NO_MATCH = "catalog.no_match"


@dataclass
class BusinessEventPayload:
    """Payload padronizado de um evento de negócio."""
    event_type: str
    lead_id: Optional[str] = None
    conversation_id: Optional[str] = None
    broker_id: Optional[str] = None
    property_id: Optional[str] = None
    channel: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=_utcnow)


@dataclass
class FunnelMetrics:
    """Métricas do funil de vendas."""
    period_days: int
    total_leads: int = 0
    leads_new: int = 0
    leads_qualified: int = 0
    leads_assigned: int = 0
    leads_visit_scheduled: int = 0
    leads_won: int = 0
    leads_lost: int = 0
    qualification_rate: float = 0.0   # qualified / total
    assignment_rate: float = 0.0      # assigned / qualified
    visit_rate: float = 0.0           # visit / assigned
    conversion_rate: float = 0.0      # won / total
    avg_first_response_ms: int = 0


@dataclass
class AIQualityMetrics:
    """Métricas de qualidade da IA."""
    period_days: int
    total_decisions: int = 0
    avg_latency_ms: int = 0
    p95_latency_ms: int = 0
    fallback_rate: float = 0.0        # decisões com fallback / total
    hallucination_rate: float = 0.0   # estimado por amostragem
    groundedness_rate: float = 0.0    # respostas com fontes / total
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    avg_cost_per_message_usd: float = 0.0


class AnalyticsService:
    """
    [M6] Serviço de observabilidade e analytics.

    Fase atual: emite eventos estruturados via logger (JSON).
    Fase 11: integrar com OpenTelemetry + Grafana/Metabase.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # Registro de eventos
    # ─────────────────────────────────────────────────────────────────────────

    def record(self, event: BusinessEventPayload) -> None:
        """
        Registra evento de produto de forma padronizada.

        O log estruturado permite agregar por evento_type em qualquer
        ferramenta de analytics (Grafana Loki, Datadog, CloudWatch, etc.).
        """
        logger.info(
            event.event_type,
            extra={
                "event_type": event.event_type,
                "lead_id": event.lead_id,
                "conversation_id": event.conversation_id,
                "broker_id": event.broker_id,
                "property_id": event.property_id,
                "channel": event.channel,
                "occurred_at": event.occurred_at.isoformat(),
                **event.metadata,
            },
        )

    def record_lead_qualified(
        self,
        lead_id: str,
        score: int,
        temperature: str,
        conversation_id: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> None:
        self.record(BusinessEventPayload(
            event_type=BusinessEvent.LEAD_QUALIFIED,
            lead_id=lead_id,
            conversation_id=conversation_id,
            channel=channel,
            metadata={"score": score, "temperature": temperature},
        ))

    def record_handoff(
        self,
        lead_id: str,
        broker_id: str,
        reason: str,
        score: int,
        conversation_id: Optional[str] = None,
    ) -> None:
        self.record(BusinessEventPayload(
            event_type=BusinessEvent.HANDOFF_INITIATED,
            lead_id=lead_id,
            broker_id=broker_id,
            conversation_id=conversation_id,
            metadata={"reason": reason, "score": score},
        ))

    def record_ai_decision(
        self,
        lead_id: str,
        conversation_id: str,
        next_action: str,
        latency_ms: int,
        tokens: int,
        model: str,
        fallback_used: bool = False,
        cost_usd: float = 0.0,
    ) -> None:
        self.record(BusinessEventPayload(
            event_type=BusinessEvent.AI_DECISION_MADE,
            lead_id=lead_id,
            conversation_id=conversation_id,
            metadata={
                "next_action": next_action,
                "latency_ms": latency_ms,
                "tokens": tokens,
                "model": model,
                "fallback_used": fallback_used,
                "cost_usd": cost_usd,
            },
        ))

    def record_catalog_result(
        self,
        lead_id: str,
        found: bool,
        count: int,
        top_match_score: float = 0.0,
    ) -> None:
        event_type = BusinessEvent.CATALOG_MATCH_FOUND if found else BusinessEvent.CATALOG_NO_MATCH
        self.record(BusinessEventPayload(
            event_type=event_type,
            lead_id=lead_id,
            metadata={"count": count, "top_match_score": top_match_score},
        ))

    def record_first_response(
        self,
        lead_id: str,
        conversation_id: str,
        latency_ms: int,
        channel: str,
    ) -> None:
        self.record(BusinessEventPayload(
            event_type=BusinessEvent.FIRST_RESPONSE_SENT,
            lead_id=lead_id,
            conversation_id=conversation_id,
            channel=channel,
            metadata={"latency_ms": latency_ms},
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # Métricas agregadas (stubs — implementação completa na Fase 11)
    # ─────────────────────────────────────────────────────────────────────────

    def get_funnel_metrics(self, period_days: int = 30) -> FunnelMetrics:
        """
        Retorna métricas do funil.

        Fase atual: retorna estrutura vazia (requer banco na Fase 1).
        Fase 11: query direto no banco + cache.
        """
        logger.info("funnel_metrics_requested", extra={"period_days": period_days})
        return FunnelMetrics(period_days=period_days)

    def get_ai_quality_metrics(self, period_days: int = 7) -> AIQualityMetrics:
        """
        Retorna métricas de qualidade da IA.

        Fase atual: retorna estrutura vazia (requer DecisionLog no banco).
        Fase 11: query em decision_logs + agregações.
        """
        logger.info("ai_quality_metrics_requested", extra={"period_days": period_days})
        return AIQualityMetrics(period_days=period_days)
