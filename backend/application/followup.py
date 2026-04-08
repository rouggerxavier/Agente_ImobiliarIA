"""
[M5] Automações / Follow-up — agendamento e execução de follow-ups.

Casos de uso:
- ScheduleFollowUp: agenda follow-up baseado no estágio do lead
- CancelFollowUps: cancela pendentes quando lead responde
- ExecuteFollowUp: dispara mensagem no canal (para o scheduler)
- GetPending: lista tasks a executar agora
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from domain.entities import FollowUpTask, Lead
from domain.enums import (
    Channel,
    FollowUpStatus,
    FollowUpTrigger,
    LeadTemperature,
)
from domain.repositories import FollowUpRepository
from core.trace import get_logger

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Cadências de follow-up por estágio (dias para próximo contato)
FOLLOWUP_CADENCES: Dict[FollowUpTrigger, int] = {
    FollowUpTrigger.NO_RESPONSE: 2,          # Sem resposta → contato em 2 dias
    FollowUpTrigger.COLD_LEAD: 7,            # Lead frio → contato em 7 dias
    FollowUpTrigger.WARM_LEAD: 3,            # Lead morno → contato em 3 dias
    FollowUpTrigger.POST_VISIT: 1,           # Pós-visita → contato em 1 dia
    FollowUpTrigger.POST_PROPOSAL: 3,        # Pós-proposta → contato em 3 dias
    FollowUpTrigger.UNAVAILABLE_PROPERTY: 5, # Imóvel indisponível → 5 dias
}

# Templates de mensagem por trigger
FOLLOWUP_TEMPLATES: Dict[FollowUpTrigger, str] = {
    FollowUpTrigger.NO_RESPONSE: (
        "Olá, {name}! 😊 Passando para saber se você ainda está procurando um imóvel. "
        "Se precisar de ajuda, é só me chamar!"
    ),
    FollowUpTrigger.COLD_LEAD: (
        "Oi, {name}! Tudo bem? 🏠 Temos novidades no catálogo que podem te interessar. "
        "Quer dar uma olhada?"
    ),
    FollowUpTrigger.WARM_LEAD: (
        "Olá, {name}! Encontrei algumas opções que combinam com o que você procura. "
        "Posso te enviar os detalhes?"
    ),
    FollowUpTrigger.POST_VISIT: (
        "Oi, {name}! Espero que a visita tenha sido boa! 😊 "
        "O que você achou do imóvel? Tem alguma dúvida ou posso ajudar com algo?"
    ),
    FollowUpTrigger.POST_PROPOSAL: (
        "Olá, {name}! Passando para saber se você teve a oportunidade de analisar "
        "a proposta que enviamos. Ficou alguma dúvida?"
    ),
    FollowUpTrigger.UNAVAILABLE_PROPERTY: (
        "Oi, {name}! Um imóvel semelhante ao que você viu ficou disponível. "
        "Quer mais informações?"
    ),
}


@dataclass
class ScheduleResult:
    """Resultado do agendamento de follow-up."""
    task_id: str
    scheduled_at: datetime
    trigger: FollowUpTrigger
    cancelled_previous: int = 0    # Quantos follow-ups anteriores foram cancelados


class FollowUpService:
    """
    [M5] Serviço de automações de follow-up.

    Gerencia o ciclo completo: agendar → executar → cancelar.
    Não envia mensagem diretamente (delega ao canal via callback).
    """

    def __init__(self, followup_repo: FollowUpRepository) -> None:
        self._tasks = followup_repo

    # ─────────────────────────────────────────────────────────────────────────
    # Agendamento
    # ─────────────────────────────────────────────────────────────────────────

    def schedule(
        self,
        lead: Lead,
        trigger: FollowUpTrigger,
        conversation_id: Optional[str] = None,
        override_days: Optional[int] = None,
        override_message: Optional[str] = None,
    ) -> ScheduleResult:
        """
        Agenda um follow-up para o lead.

        Cancela automaticamente follow-ups do mesmo trigger que já existam pendentes.
        """
        days = override_days or FOLLOWUP_CADENCES.get(trigger, 3)
        scheduled_at = _utcnow() + timedelta(days=days)

        # Personaliza mensagem
        name = lead.name or "cliente"
        template = override_message or FOLLOWUP_TEMPLATES.get(trigger, "Olá, {name}! Como posso ajudar?")
        message = template.format(name=name.split()[0])

        # Cancela follow-ups pendentes do mesmo trigger para este lead
        # (evita duplicatas na fila)
        cancelled = self._cancel_duplicate_triggers(lead.id, trigger)

        task = FollowUpTask(
            lead_id=lead.id,
            conversation_id=conversation_id,
            trigger=trigger,
            status=FollowUpStatus.PENDING,
            message_template=message,
            channel=lead.channel,
            scheduled_at=scheduled_at,
        )
        saved = self._tasks.save(task)

        logger.info(
            "followup_scheduled",
            extra={
                "lead_id": lead.id,
                "task_id": saved.id,
                "trigger": trigger.value,
                "scheduled_at": scheduled_at.isoformat(),
                "days": days,
            },
        )
        return ScheduleResult(
            task_id=saved.id,
            scheduled_at=scheduled_at,
            trigger=trigger,
            cancelled_previous=cancelled,
        )

    def _cancel_duplicate_triggers(self, lead_id: str, trigger: FollowUpTrigger) -> int:
        """Cancela follow-ups pendentes do mesmo trigger para não duplicar."""
        pending = self._tasks.list_pending()
        count = 0
        for task in pending:
            if task.lead_id == lead_id and task.trigger == trigger:
                self._tasks.update_status(task.id, FollowUpStatus.CANCELLED)
                count += 1
        return count

    # ─────────────────────────────────────────────────────────────────────────
    # Cancelamento
    # ─────────────────────────────────────────────────────────────────────────

    def cancel_for_lead(self, lead_id: str, reason: str = "lead_responded") -> int:
        """
        Cancela todos os follow-ups pendentes de um lead.
        Chamado quando o lead responde uma mensagem.
        """
        self._tasks.cancel_for_lead(lead_id, reason)
        logger.info(
            "followup_cancelled_for_lead",
            extra={"lead_id": lead_id, "reason": reason},
        )
        return 0  # quantidade retornada pelo repo na implementação real

    # ─────────────────────────────────────────────────────────────────────────
    # Execução (scheduler)
    # ─────────────────────────────────────────────────────────────────────────

    def get_pending(self, before: Optional[datetime] = None) -> List[FollowUpTask]:
        """
        Lista follow-ups pendentes para execução.
        Chamado pelo scheduler (job periódico).
        """
        cutoff = before or _utcnow()
        tasks = self._tasks.list_pending(before=cutoff)
        logger.info("followup_pending_fetched", extra={"count": len(tasks)})
        return tasks

    def mark_sent(self, task_id: str) -> None:
        """Marca follow-up como enviado com sucesso."""
        self._tasks.update_status(task_id, FollowUpStatus.SENT)
        logger.info("followup_sent", extra={"task_id": task_id})

    def mark_failed(self, task_id: str) -> None:
        """Marca follow-up como falho."""
        self._tasks.update_status(task_id, FollowUpStatus.FAILED)
        logger.warning("followup_failed", extra={"task_id": task_id})

    # ─────────────────────────────────────────────────────────────────────────
    # Estratégia por temperatura
    # ─────────────────────────────────────────────────────────────────────────

    def decide_trigger(self, lead: Lead) -> Optional[FollowUpTrigger]:
        """
        Decide qual tipo de follow-up aplicar ao lead com base em seu estado.
        Retorna None se nenhum follow-up for apropriado.
        """
        temp = lead.score.temperature

        if temp == LeadTemperature.HOT:
            # Lead quente: follow-up rápido se não respondeu
            return FollowUpTrigger.WARM_LEAD
        elif temp == LeadTemperature.WARM:
            return FollowUpTrigger.NO_RESPONSE
        else:
            # Lead frio: nurturing de longo prazo
            return FollowUpTrigger.COLD_LEAD
