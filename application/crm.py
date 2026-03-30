"""
[M2] CRM — gerenciamento do ciclo de vida do lead.

Casos de uso:
- QualifyLead: atualiza perfil e recalcula score
- AssignToBroker: roteia lead para o melhor corretor disponível
- UpdateLeadStatus: muda status no funil
- RecordHandoff: registra handoff humano com contexto completo
- GetLeadSummary: gera resumo executivo para o corretor
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from domain.entities import Assignment, Broker, Lead, LeadScore, LeadPreferences
from domain.enums import (
    HandoffReason,
    LeadStatus,
    LeadTemperature,
    NextAction,
    SLATier,
)
from domain.repositories import (
    AssignmentRepository,
    BrokerRepository,
    LeadRepository,
)
from core.trace import get_logger

logger = get_logger(__name__)


@dataclass
class HandoffContext:
    """Contexto completo entregue ao corretor no momento do handoff."""
    lead_id: str
    lead_name: Optional[str]
    lead_phone: Optional[str]
    lead_score: int
    lead_temperature: str
    conversation_summary: str
    preferences_summary: str
    suggested_properties: List[str]
    objections_raised: List[str]
    next_action_recommendation: str
    handoff_reason: HandoffReason
    handoff_at: datetime


class CRMService:
    """
    [M2] Serviço de CRM — gerencia o ciclo de vida do lead.

    Não contém regra de negócio de score (isso é do domínio).
    Orquestra operações: update, assign, handoff, summary.
    """

    def __init__(
        self,
        lead_repo: LeadRepository,
        broker_repo: BrokerRepository,
        assignment_repo: AssignmentRepository,
    ) -> None:
        self._leads = lead_repo
        self._brokers = broker_repo
        self._assignments = assignment_repo

    # ─────────────────────────────────────────────────────────────────────────
    # Qualificação
    # ─────────────────────────────────────────────────────────────────────────

    def qualify_lead(
        self,
        lead_id: str,
        preferences: LeadPreferences,
        new_score: LeadScore,
    ) -> Lead:
        """
        Atualiza o perfil do lead após extração de critérios e recalcula score.
        Muda status para QUALIFIED se score atingir limiar.
        """
        lead = self._leads.get_by_id(lead_id)
        if lead is None:
            raise ValueError(f"Lead {lead_id} não encontrado")

        lead.preferences = preferences
        lead.score = new_score
        lead.touch()

        # Determina temperatura e SLA
        if new_score.temperature == LeadTemperature.HOT:
            lead.sla_tier = SLATier.IMMEDIATE
        elif new_score.temperature == LeadTemperature.WARM:
            lead.sla_tier = SLATier.NORMAL
        else:
            lead.sla_tier = SLATier.NURTURE

        # Avança status se qualificado
        if lead.status == LeadStatus.NEW and new_score.total >= 40:
            lead.status = LeadStatus.IN_QUALIFICATION
        if new_score.total >= 70:
            lead.status = LeadStatus.QUALIFIED

        saved = self._leads.save(lead)
        logger.info(
            "lead_qualified",
            extra={
                "lead_id": lead_id,
                "score": new_score.total,
                "temperature": new_score.temperature.value,
                "status": saved.status.value,
            },
        )
        return saved

    # ─────────────────────────────────────────────────────────────────────────
    # Roteamento
    # ─────────────────────────────────────────────────────────────────────────

    def assign_to_broker(
        self,
        lead_id: str,
        conversation_id: Optional[str] = None,
        override_broker_id: Optional[str] = None,
    ) -> Assignment:
        """
        Atribui lead ao corretor mais adequado.

        Se override_broker_id for passado, usa aquele corretor diretamente.
        Caso contrário, usa BrokerRepository.find_best_match().
        """
        lead = self._leads.get_by_id(lead_id)
        if lead is None:
            raise ValueError(f"Lead {lead_id} não encontrado")

        if override_broker_id:
            broker = self._brokers.get_by_id(override_broker_id)
        else:
            broker = self._brokers.find_best_match(lead)

        if broker is None:
            raise RuntimeError("Nenhum corretor disponível para o perfil deste lead")

        assignment = Assignment(
            lead_id=lead_id,
            broker_id=broker.id,
            conversation_id=conversation_id,
            reason=f"Roteamento automático — score={lead.score.total}",
            score_at_assignment=lead.score.total,
            summary_at_assignment=self.get_lead_summary(lead_id),
        )
        saved_assignment = self._assignments.save(assignment)

        # Atualiza lead
        lead.assigned_broker_id = broker.id
        lead.status = LeadStatus.ASSIGNED
        lead.touch()
        self._leads.save(lead)

        logger.info(
            "lead_assigned",
            extra={
                "lead_id": lead_id,
                "broker_id": broker.id,
                "broker_name": broker.name,
            },
        )
        return saved_assignment

    # ─────────────────────────────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────────────────────────────

    def update_status(self, lead_id: str, new_status: LeadStatus, reason: str = "") -> Lead:
        """Atualiza o status do lead no funil."""
        lead = self._leads.get_by_id(lead_id)
        if lead is None:
            raise ValueError(f"Lead {lead_id} não encontrado")

        old_status = lead.status
        lead.status = new_status
        lead.touch()
        saved = self._leads.save(lead)

        logger.info(
            "lead_status_changed",
            extra={
                "lead_id": lead_id,
                "from_status": old_status.value,
                "to_status": new_status.value,
                "reason": reason,
            },
        )
        return saved

    # ─────────────────────────────────────────────────────────────────────────
    # Handoff
    # ─────────────────────────────────────────────────────────────────────────

    def record_handoff(
        self,
        lead_id: str,
        conversation_id: str,
        reason: HandoffReason,
        conversation_summary: str,
        suggested_properties: Optional[List[str]] = None,
        objections: Optional[List[str]] = None,
    ) -> HandoffContext:
        """
        Registra handoff para humano e monta contexto completo para o corretor.
        Dispara atribuição automática se ainda não atribuído.
        """
        lead = self._leads.get_by_id(lead_id)
        if lead is None:
            raise ValueError(f"Lead {lead_id} não encontrado")

        # Atribui corretor se necessário
        if not lead.assigned_broker_id:
            try:
                self.assign_to_broker(lead_id, conversation_id)
                lead = self._leads.get_by_id(lead_id)  # reload
            except RuntimeError:
                logger.warning("Nenhum corretor disponível para handoff automático", extra={"lead_id": lead_id})

        context = HandoffContext(
            lead_id=lead_id,
            lead_name=lead.name,
            lead_phone=lead.phone,
            lead_score=lead.score.total,
            lead_temperature=lead.score.temperature.value,
            conversation_summary=conversation_summary,
            preferences_summary=self._format_preferences(lead),
            suggested_properties=suggested_properties or [],
            objections_raised=objections or [],
            next_action_recommendation=self._recommend_next_action(lead),
            handoff_reason=reason,
            handoff_at=datetime.utcnow(),
        )

        # Atualiza status
        self.update_status(lead_id, LeadStatus.ASSIGNED, reason=reason.value)

        logger.info(
            "handoff_recorded",
            extra={
                "lead_id": lead_id,
                "reason": reason.value,
                "broker_id": lead.assigned_broker_id,
            },
        )
        return context

    # ─────────────────────────────────────────────────────────────────────────
    # Sumário
    # ─────────────────────────────────────────────────────────────────────────

    def get_lead_summary(self, lead_id: str) -> str:
        """
        Gera resumo textual do lead para handoff para corretor.
        Formato estruturado, fácil de ler em WhatsApp.
        """
        lead = self._leads.get_by_id(lead_id)
        if lead is None:
            return "Lead não encontrado."

        p = lead.preferences
        lines = [
            f"👤 *{lead.name or 'Lead sem nome'}*",
            f"📞 {lead.phone or 'sem telefone'}",
            f"🌡️ Score: {lead.score.total}/100 ({lead.score.temperature.value.upper()})",
            "",
            "*🏠 O que procura:*",
        ]
        if p.intent:
            lines.append(f"• Intenção: {p.intent.value}")
        if p.city:
            lines.append(f"• Cidade: {p.city}")
        if p.neighborhood:
            lines.append(f"• Bairro: {p.neighborhood}")
        if p.property_type:
            lines.append(f"• Tipo: {p.property_type.value}")
        if p.bedrooms_min:
            lines.append(f"• Quartos (mín): {p.bedrooms_min}")
        if p.budget_max:
            lines.append(f"• Orçamento máx: R$ {p.budget_max:,.0f}".replace(",", "."))
        if p.payment_type:
            lines.append(f"• Pagamento: {p.payment_type.value}")
        if p.timeline:
            lines.append(f"• Prazo: {p.timeline}")
        if p.extra_requirements:
            lines.append(f"• Extras: {p.extra_requirements}")

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _format_preferences(self, lead: Lead) -> str:
        return self.get_lead_summary(lead.id)

    def _recommend_next_action(self, lead: Lead) -> str:
        score = lead.score.total
        if score >= 80:
            return "Ligar imediatamente e propor visita"
        elif score >= 60:
            return "Entrar em contato hoje e qualificar orçamento"
        elif score >= 40:
            return "Enviar opções por WhatsApp e aguardar retorno"
        else:
            return "Incluir em cadência de nurturing automatizado"
