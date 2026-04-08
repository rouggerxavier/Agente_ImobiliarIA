"""
[M1] Orquestrador conversacional com memoria persistente e grafo de estados.

O comportamento comercial continua vindo do controller legado, mas o fluxo passa
por um state graph explicito, com checkpoints, persistencia operacional e
resumos auditaveis.
"""
from __future__ import annotations

import os
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from agent.controller import handle_message as legacy_handle_message
from agent.state import SessionState, store as legacy_store
from app.faq import detect_faq_intent
from core.trace import get_logger, set_trace_context, timer
from domain.entities import Conversation, ConversationSummary, DecisionLog, EventEnvelope, Lead, Message, PreferenceSignal
from domain.enums import (
    Channel,
    ConversationStatus,
    DetectedIntent,
    HandoffReason,
    LeadIntent,
    LeadIntentStage,
    LeadStatus,
    LeadTemperature,
    MessageRole,
    MessageType,
    NextAction,
    PaymentType,
    PropertyType,
)
from domain.repositories import (
    ConversationRepository,
    DecisionLogRepository,
    EventRepository,
    LeadRepository,
    MessageRepository,
    SessionStateRepository,
)

logger = get_logger(__name__)

CONTEXT_WINDOW = max(6, int(os.getenv("ORCHESTRATOR_CONTEXT_WINDOW", "12")))
STALE_CONVERSATION_HOURS = max(1, int(os.getenv("ORCHESTRATOR_STALE_CONVERSATION_HOURS", "8")))
NODE_TIMEOUT_MS = max(250, int(os.getenv("ORCHESTRATOR_NODE_TIMEOUT_MS", "8000")))
NODE_RETRIES = max(0, int(os.getenv("ORCHESTRATOR_NODE_RETRIES", "1")))
EXECUTION_COST_LIMIT_USD = max(0.0, float(os.getenv("ORCHESTRATOR_EXECUTION_COST_LIMIT_USD", "0.25")))


def _utcnow() -> datetime:
    # Mantem datetime UTC "naive" para compatibilidade com entidades/repositórios atuais.
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class MessageInput:
    session_id: str
    message_text: str
    channel: Channel = Channel.UNKNOWN
    external_message_id: Optional[str] = None
    sender_name: Optional[str] = None
    trace_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    media_url: Optional[str] = None
    message_type: MessageType = MessageType.TEXT

    def __post_init__(self) -> None:
        if not self.external_message_id:
            self.external_message_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = _utcnow()


@dataclass
class OrchestratorResult:
    reply: str
    next_action: NextAction
    lead_id: str
    conversation_id: str
    trace_id: str
    human_handoff: bool = False
    handoff_reason: Optional[HandoffReason] = None
    lead_score: int = 0
    lead_temperature: str = "cold"
    latency_ms: int = 0
    decision_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    debug: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorGraphState:
    trace_id: str
    lead_id: str
    conversation_id: str
    channel: Channel
    message_input: MessageInput
    lead_profile: Dict[str, Any] = field(default_factory=dict)
    conversation_summary: str = ""
    detected_intent: DetectedIntent = DetectedIntent.UNKNOWN
    retrieval_context: List[str] = field(default_factory=list)
    property_candidates: List[str] = field(default_factory=list)
    property_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    lead_score: int = 0
    routing_decision: Optional[str] = None
    next_action: NextAction = NextAction.ASK_MISSING_FIELD
    confidence: float = 0.0
    guardrail_flags: List[str] = field(default_factory=list)
    human_handoff_required: bool = False
    state_path: List[str] = field(default_factory=list)
    checkpoint_ids: List[str] = field(default_factory=list)
    reply: str = ""
    legacy_payload: Dict[str, Any] = field(default_factory=dict)
    latest_user_message: Optional[Message] = None
    latest_assistant_message: Optional[Message] = None
    knowledge_sources: List[str] = field(default_factory=list)
    knowledge_reply: str = ""
    catalog_reply: str = ""
    node_metrics: Dict[str, int] = field(default_factory=dict)
    execution_cost_usd: float = 0.0


class ConversationOrchestrator:
    def __init__(
        self,
        lead_repo: LeadRepository,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        decision_log_repo: DecisionLogRepository,
        event_repo: EventRepository,
        crm_service=None,
        catalog_service=None,
        knowledge_service=None,
        followup_service=None,
        analytics_service=None,
        llm_service=None,
        checkpoint_store=None,
        session_state_repo: Optional[SessionStateRepository] = None,
    ) -> None:
        self._leads = lead_repo
        self._conversations = conversation_repo
        self._messages = message_repo
        self._decisions = decision_log_repo
        self._events = event_repo
        self._crm = crm_service
        self._catalog = catalog_service
        self._knowledge = knowledge_service
        self._followup = followup_service
        self._analytics = analytics_service
        self._llm = llm_service
        self._checkpoints = checkpoint_store
        self._session_states = session_state_repo

    def process_legacy_payload(self, msg_input: MessageInput) -> Dict[str, Any]:
        return self.process(msg_input).payload

    def process(self, msg_input: MessageInput) -> OrchestratorResult:
        start = time.perf_counter()
        trace_id = msg_input.trace_id or str(uuid.uuid4())

        lead = self._resolve_lead(msg_input)
        conversation = self._resolve_conversation(lead, msg_input.channel, msg_input.timestamp)
        set_trace_context(
            trace_id=trace_id,
            lead_id=lead.id,
            conversation_id=conversation.id,
            channel=msg_input.channel.value,
        )

        if msg_input.external_message_id:
            duplicate = self._messages.get_by_external_id(msg_input.external_message_id)
            if duplicate:
                logger.warning("duplicate_message_ignored", extra={"external_message_id": msg_input.external_message_id})
                return self._build_duplicate_result(lead, conversation, trace_id, start)

        graph_state = OrchestratorGraphState(
            trace_id=trace_id,
            lead_id=lead.id,
            conversation_id=conversation.id,
            channel=msg_input.channel,
            message_input=msg_input,
            lead_profile=self._snapshot_lead_profile(lead),
            conversation_summary=conversation.summary.technical,
            lead_score=lead.score.total,
            confidence=0.2,
        )
        self._publish_event(
            "message.received",
            aggregate=conversation,
            payload={"session_id": msg_input.session_id, "external_message_id": msg_input.external_message_id},
            trace_id=trace_id,
        )

        nodes: List[tuple[str, Callable[[Lead, Conversation, OrchestratorGraphState], None]]] = [
            ("ingest_normalize", self._node_ingest_normalize),
            ("recover_context", self._node_recover_context),
            ("classify_intent", self._node_classify_intent),
            ("retrieve_knowledge", self._node_retrieve_knowledge),
            ("retrieve_properties", self._node_retrieve_properties),
            ("decide_and_respond", self._node_decide_and_respond),
            ("persist_memory", self._node_persist_memory),
            ("persist_decision", self._node_persist_decision),
            ("post_actions", self._node_post_actions),
        ]
        for node_name, node_handler in nodes:
            self._run_node(node_name, node_handler, lead, conversation, graph_state)

        latency_ms = int((time.perf_counter() - start) * 1000)
        payload = dict(graph_state.legacy_payload)
        payload.setdefault("reply", graph_state.reply)
        payload.setdefault("state", self._legacy_state_to_public_dict(msg_input.session_id))
        payload["summary"] = {
            "executive": conversation.summary.executive,
            "technical": conversation.summary.technical,
            "version": conversation.summary.version,
            "trigger": conversation.summary.trigger,
        }
        payload["orchestration"] = {
            "path": graph_state.state_path,
            "checkpoints": graph_state.checkpoint_ids,
            "detected_intent": graph_state.detected_intent.value,
            "next_action": graph_state.next_action.value,
            "routing_decision": graph_state.routing_decision,
            "human_handoff_required": graph_state.human_handoff_required,
            "guardrail_flags": graph_state.guardrail_flags,
            "knowledge_sources": graph_state.knowledge_sources,
            "property_candidates": graph_state.property_candidates,
            "node_metrics_ms": graph_state.node_metrics,
        }

        return OrchestratorResult(
            reply=graph_state.reply,
            next_action=graph_state.next_action,
            lead_id=lead.id,
            conversation_id=conversation.id,
            trace_id=trace_id,
            human_handoff=graph_state.human_handoff_required,
            handoff_reason=self._infer_handoff_reason(graph_state, payload),
            lead_score=lead.score.total,
            lead_temperature=lead.score.temperature.value,
            latency_ms=latency_ms,
            payload=payload,
            debug={"state_path": graph_state.state_path, "checkpoint_ids": graph_state.checkpoint_ids},
        )

    def reprocess_from_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        if self._checkpoints is None:
            raise RuntimeError("Checkpoint store nao configurado")
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} nao encontrado")
        snapshot = checkpoint.get("state_snapshot") or {}
        msg = snapshot.get("message_input") or {}
        restored_input = MessageInput(
            session_id=msg["session_id"],
            message_text=msg["message_text"],
            channel=Channel(msg.get("channel", Channel.UNKNOWN.value)),
            external_message_id=None,
            sender_name=msg.get("sender_name"),
            trace_id=msg.get("trace_id"),
            timestamp=datetime.fromisoformat(msg["timestamp"]) if msg.get("timestamp") else None,
            media_url=msg.get("media_url"),
            message_type=MessageType(msg.get("message_type", MessageType.TEXT.value)),
        )
        return self.process_legacy_payload(restored_input)

    def _run_node(
        self,
        node_name: str,
        node_handler: Callable[[Lead, Conversation, OrchestratorGraphState], None],
        lead: Lead,
        conversation: Conversation,
        graph_state: OrchestratorGraphState,
    ) -> None:
        last_error: Optional[Exception] = None
        for attempt in range(NODE_RETRIES + 1):
            checkpoint = self._save_checkpoint(node_name, "before", lead, conversation, graph_state)
            if checkpoint:
                graph_state.checkpoint_ids.append(checkpoint["id"])
            start = time.perf_counter()
            try:
                with timer(logger, f"graph_node.{node_name}", node=node_name, attempt=attempt + 1):
                    node_handler(lead, conversation, graph_state)
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                if elapsed_ms > NODE_TIMEOUT_MS:
                    raise TimeoutError(f"Node {node_name} excedeu timeout de {NODE_TIMEOUT_MS}ms")
                graph_state.node_metrics[node_name] = elapsed_ms
                graph_state.state_path.append(node_name)
                checkpoint = self._save_checkpoint(node_name, "after", lead, conversation, graph_state)
                if checkpoint:
                    graph_state.checkpoint_ids.append(checkpoint["id"])
                logger.info("graph_node_transition", extra={"node": node_name, "latency_ms": elapsed_ms})
                return
            except Exception as exc:
                last_error = exc
                logger.warning("graph_node_error", extra={"node": node_name, "attempt": attempt + 1, "error": str(exc)})
        if last_error:
            raise last_error

    def _node_ingest_normalize(self, lead: Lead, conversation: Conversation, graph_state: OrchestratorGraphState) -> None:
        msg_input = graph_state.message_input
        user_message = Message(
            conversation_id=conversation.id,
            lead_id=lead.id,
            role=MessageRole.USER,
            message_type=msg_input.message_type,
            text=msg_input.message_text,
            media_url=msg_input.media_url,
            external_message_id=msg_input.external_message_id,
            trace_id=graph_state.trace_id,
        )
        saved = self._messages.save(user_message)
        conversation.add_message(saved)
        self._conversations.save(conversation)
        graph_state.latest_user_message = saved

    def _node_recover_context(self, lead: Lead, conversation: Conversation, graph_state: OrchestratorGraphState) -> None:
        recent_messages = self._messages.list_by_conversation(conversation.id, limit=CONTEXT_WINDOW * 3)
        graph_state.retrieval_context = self._build_context_window(recent_messages, conversation.summary)
        graph_state.conversation_summary = conversation.summary.technical
        if conversation.summary.trigger == "resume":
            graph_state.guardrail_flags.append("resumed_after_inactivity")
        elif conversation.last_message_at and self._is_stale(conversation.last_message_at, graph_state.message_input.timestamp):
            graph_state.guardrail_flags.append("resumed_after_inactivity")

    def _node_classify_intent(self, lead: Lead, conversation: Conversation, graph_state: OrchestratorGraphState) -> None:
        message = graph_state.message_input.message_text.lower()
        if detect_faq_intent(graph_state.message_input.message_text):
            graph_state.detected_intent = DetectedIntent.FAQ
        elif any(token in message for token in ["visita", "visitar", "agendar"]):
            graph_state.detected_intent = DetectedIntent.SCHEDULE_VISIT
        elif any(token in message for token in ["desconto", "negoci", "baixar o preco", "baixar o preço"]):
            graph_state.detected_intent = DetectedIntent.NEGOTIATE_PRICE
        elif any(token in message for token in ["alugar", "aluguel"]):
            graph_state.detected_intent = DetectedIntent.RENT
        elif any(token in message for token in ["comprar", "compra", "investir", "investimento"]):
            graph_state.detected_intent = DetectedIntent.BUY
        elif any(token in message for token in ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"]):
            graph_state.detected_intent = DetectedIntent.GREETING
        else:
            graph_state.detected_intent = DetectedIntent.UNKNOWN

    def _node_retrieve_knowledge(self, lead: Lead, conversation: Conversation, graph_state: OrchestratorGraphState) -> None:
        if graph_state.detected_intent != DetectedIntent.FAQ or self._knowledge is None:
            return
        result = self._knowledge.answer(
            graph_state.message_input.message_text,
            city=lead.preferences.city,
            neighborhood=lead.preferences.neighborhood,
            domain="faq",
        )
        if not result:
            return
        graph_state.knowledge_sources = list(result.sources)
        graph_state.retrieval_context.extend(result.retrieved_chunks or [])
        graph_state.knowledge_reply = result.reply_text
        graph_state.confidence = max(graph_state.confidence, float(result.confidence or 0.5))

    def _node_retrieve_properties(self, lead: Lead, conversation: Conversation, graph_state: OrchestratorGraphState) -> None:
        if self._catalog is None:
            return
        if graph_state.detected_intent not in {DetectedIntent.BUY, DetectedIntent.RENT}:
            return
        if not self._catalog.can_recommend(lead):
            return
        matches = self._catalog.recommend(lead, conversation_id=conversation.id, limit=3)
        graph_state.property_candidates = [match.property.external_ref or match.property.id for match in matches]
        graph_state.property_recommendations = self._catalog.serialize_matches(
            matches,
            lead.preferences.intent.value if lead.preferences.intent else None,
        )
        if matches:
            graph_state.catalog_reply = self._catalog.build_recommendation_reply(matches, lead)
        else:
            graph_state.catalog_reply = self._catalog.fallback_message(self._catalog.build_filters_for_lead(lead, limit=3))

    def _node_decide_and_respond(self, lead: Lead, conversation: Conversation, graph_state: OrchestratorGraphState) -> None:
        if graph_state.execution_cost_usd > EXECUTION_COST_LIMIT_USD:
            raise RuntimeError("Execution cost limit exceeded before response generation")

        self._rehydrate_legacy_state(lead, conversation, graph_state)
        payload = legacy_handle_message(
            graph_state.message_input.session_id,
            graph_state.message_input.message_text,
            name=graph_state.message_input.sender_name,
            correlation_id=graph_state.trace_id,
        )
        if graph_state.detected_intent == DetectedIntent.FAQ and graph_state.knowledge_reply:
            payload["reply"] = self._merge_knowledge_reply(payload.get("reply", ""), graph_state.knowledge_reply)
            payload["sources"] = list(graph_state.knowledge_sources)
        if graph_state.property_recommendations and not payload.get("properties"):
            payload["properties"] = graph_state.property_recommendations
            payload["reply"] = self._merge_catalog_reply(payload.get("reply", ""), graph_state.catalog_reply)
        elif graph_state.catalog_reply and not payload.get("properties"):
            payload["reply"] = self._merge_catalog_reply(payload.get("reply", ""), graph_state.catalog_reply)
        graph_state.legacy_payload = payload
        graph_state.reply = payload.get("reply", "")

        legacy_state = legacy_store.get(graph_state.message_input.session_id)
        graph_state.lead_profile = dict(legacy_state.lead_profile)
        graph_state.lead_score = int(getattr(legacy_state.lead_score, "score", 0))
        graph_state.human_handoff_required = bool(getattr(legacy_state, "human_handoff", False) or payload.get("handoff"))
        graph_state.routing_decision = (((payload.get("summary") or {}).get("assigned_agent", {}) or {}).get("id"))
        graph_state.next_action = self._infer_next_action(graph_state, legacy_state, payload)
        graph_state.confidence = max(graph_state.confidence, 0.9 if graph_state.human_handoff_required else 0.75)
        graph_state.execution_cost_usd += 0.01

    def _node_persist_memory(self, lead: Lead, conversation: Conversation, graph_state: OrchestratorGraphState) -> None:
        legacy_state = legacy_store.get(graph_state.message_input.session_id)
        self._sync_lead_from_legacy_state(lead, legacy_state, graph_state)
        self._persist_critical_state_snapshot(
            session_id=graph_state.message_input.session_id,
            legacy_state=legacy_state,
            lead_id=lead.id,
            conversation_id=conversation.id,
            trace_id=graph_state.trace_id,
        )
        graph_state.latest_assistant_message = self._persist_assistant_message(lead, conversation, graph_state.reply, graph_state.trace_id)
        self._apply_summary(conversation, self._build_summary(lead, conversation, legacy_state, graph_state))
        self._conversations.save(conversation)
        self._leads.save(lead)

    def _node_persist_decision(self, lead: Lead, conversation: Conversation, graph_state: OrchestratorGraphState) -> None:
        decision = self._persist_decision(
            lead=lead,
            conversation=conversation,
            message=graph_state.latest_user_message or Message(conversation_id=conversation.id, lead_id=lead.id, role=MessageRole.USER, text=graph_state.message_input.message_text),
            next_action=graph_state.next_action,
            reasoning=self._build_reasoning(graph_state),
            confidence=graph_state.confidence,
            trace_id=graph_state.trace_id,
            detected_intent=graph_state.detected_intent,
            guardrail_flags=graph_state.guardrail_flags,
            human_handoff=graph_state.human_handoff_required,
            retrieval_context=graph_state.retrieval_context,
            property_candidate_ids=graph_state.property_candidates,
            routing_decision=graph_state.routing_decision,
            state_path=graph_state.state_path,
            checkpoint_id=graph_state.checkpoint_ids[-1] if graph_state.checkpoint_ids else None,
        )
        graph_state.legacy_payload.setdefault("decision_log_id", decision.id)

    def _node_post_actions(self, lead: Lead, conversation: Conversation, graph_state: OrchestratorGraphState) -> None:
        if self._analytics is not None:
            self._analytics.record_ai_decision(
                lead_id=lead.id,
                conversation_id=conversation.id,
                next_action=graph_state.next_action.value,
                latency_ms=sum(graph_state.node_metrics.values()),
                tokens=0,
                model="legacy_controller_bridge",
                fallback_used=False,
                cost_usd=graph_state.execution_cost_usd,
            )
        if graph_state.human_handoff_required and self._crm is not None:
            handoff_reason = self._infer_handoff_reason(graph_state, graph_state.legacy_payload) or HandoffReason.OTHER
            try:
                self._crm.record_handoff(
                    lead.id,
                    conversation.id,
                    handoff_reason,
                    conversation.summary.executive,
                    suggested_properties=graph_state.property_candidates,
                )
                conversation.status = ConversationStatus.HANDED_OFF
                conversation.handoff_reason = handoff_reason
                conversation.handoff_at = _utcnow()
                self._conversations.save(conversation)
            except Exception as exc:
                graph_state.guardrail_flags.append("handoff_record_failed")
                logger.warning("handoff_record_failed", extra={"error": str(exc)})
        elif self._followup is not None and lead.score.temperature == LeadTemperature.COLD:
            trigger = self._followup.decide_trigger(lead)
            if trigger is not None:
                self._followup.schedule(lead, trigger, conversation_id=conversation.id)

    def _resolve_lead(self, msg_input: MessageInput) -> Lead:
        lead = self._leads.get_by_session(msg_input.session_id)
        if lead is None:
            lead = Lead(channel=msg_input.channel, external_id=msg_input.session_id, name=msg_input.sender_name, status=LeadStatus.NEW)
        else:
            lead.touch()
            if msg_input.sender_name and not lead.name:
                lead.name = msg_input.sender_name
        return self._leads.save(lead)

    def _resolve_conversation(self, lead: Lead, channel: Channel, timestamp: Optional[datetime]) -> Conversation:
        conversation = self._conversations.get_active_by_lead(lead.id)
        if conversation is None:
            return self._conversations.save(Conversation(lead_id=lead.id, channel=channel, status=ConversationStatus.ACTIVE))
        if conversation.last_message_at and self._is_stale(conversation.last_message_at, timestamp):
            conversation.summary_history.append(conversation.summary)
            conversation.summary = ConversationSummary(
                executive=conversation.summary.executive,
                technical=conversation.summary.technical,
                version=conversation.summary.version + 1,
                trigger="resume",
            )
        return conversation

    def _persist_assistant_message(self, lead: Lead, conversation: Conversation, reply: str, trace_id: str) -> Optional[Message]:
        if not reply or not reply.strip():
            return None
        existing = self._messages.list_by_conversation(conversation.id, limit=1)
        if existing and existing[-1].role == MessageRole.ASSISTANT and existing[-1].text == reply:
            return existing[-1]
        message = Message(
            conversation_id=conversation.id,
            lead_id=lead.id,
            role=MessageRole.ASSISTANT,
            message_type=MessageType.TEXT,
            text=reply,
            trace_id=trace_id,
        )
        saved = self._messages.save(message)
        conversation.add_message(saved)
        return saved

    def _persist_decision(
        self,
        lead: Lead,
        conversation: Conversation,
        message: Message,
        next_action: NextAction,
        reasoning: str,
        confidence: float,
        trace_id: str,
        model_used: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: int = 0,
        detected_intent: Optional[DetectedIntent] = None,
        guardrail_flags: Optional[List[str]] = None,
        human_handoff: bool = False,
        retrieval_context: Optional[List[str]] = None,
        property_candidate_ids: Optional[List[str]] = None,
        routing_decision: Optional[str] = None,
        state_path: Optional[List[str]] = None,
        checkpoint_id: Optional[str] = None,
    ) -> DecisionLog:
        log = DecisionLog(
            lead_id=lead.id,
            conversation_id=conversation.id,
            message_id=message.id,
            trace_id=trace_id,
            next_action=next_action,
            confidence=confidence,
            reasoning=reasoning,
            lead_score=lead.score.total,
            detected_intent=detected_intent,
            retrieval_context=retrieval_context or [],
            property_candidate_ids=property_candidate_ids or [],
            routing_decision=routing_decision,
            state_path=state_path or [],
            checkpoint_id=checkpoint_id,
            guardrail_flags=guardrail_flags or [],
            human_handoff_required=human_handoff,
            model_used=model_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )
        return self._decisions.save(log)

    def _publish_event(self, event_type: str, aggregate: Lead | Conversation, payload: Dict[str, Any], trace_id: str) -> None:
        agg_type = type(aggregate).__name__
        event = EventEnvelope(
            event_type=event_type,
            aggregate_id=aggregate.id,
            aggregate_type=agg_type,
            payload=payload,
            trace_id=trace_id,
            lead_id=aggregate.id if agg_type == "Lead" else getattr(aggregate, "lead_id", None),
            conversation_id=aggregate.id if agg_type == "Conversation" else None,
            channel=getattr(aggregate, "channel", None),
        )
        self._events.publish(event)

    def _save_checkpoint(
        self,
        node_name: str,
        stage: str,
        lead: Lead,
        conversation: Conversation,
        graph_state: OrchestratorGraphState,
    ) -> Optional[Dict[str, Any]]:
        if self._checkpoints is None:
            return None
        return self._checkpoints.save(
            {
                "conversation_id": conversation.id,
                "lead_id": lead.id,
                "trace_id": graph_state.trace_id,
                "node": node_name,
                "stage": stage,
                "state_snapshot": self._graph_state_snapshot(graph_state),
            }
        )

    def _graph_state_snapshot(self, graph_state: OrchestratorGraphState) -> Dict[str, Any]:
        return {
            "trace_id": graph_state.trace_id,
            "lead_id": graph_state.lead_id,
            "conversation_id": graph_state.conversation_id,
            "channel": graph_state.channel.value,
            "lead_profile": graph_state.lead_profile,
            "conversation_summary": graph_state.conversation_summary,
            "detected_intent": graph_state.detected_intent.value,
            "retrieval_context": graph_state.retrieval_context,
            "knowledge_sources": graph_state.knowledge_sources,
            "property_candidates": graph_state.property_candidates,
            "lead_score": graph_state.lead_score,
            "routing_decision": graph_state.routing_decision,
            "next_action": graph_state.next_action.value,
            "confidence": graph_state.confidence,
            "guardrail_flags": graph_state.guardrail_flags,
            "human_handoff_required": graph_state.human_handoff_required,
            "state_path": graph_state.state_path,
            "message_input": {
                "session_id": graph_state.message_input.session_id,
                "message_text": graph_state.message_input.message_text,
                "channel": graph_state.message_input.channel.value,
                "external_message_id": graph_state.message_input.external_message_id,
                "sender_name": graph_state.message_input.sender_name,
                "trace_id": graph_state.message_input.trace_id,
                "timestamp": graph_state.message_input.timestamp.isoformat() if graph_state.message_input.timestamp else None,
                "media_url": graph_state.message_input.media_url,
                "message_type": graph_state.message_input.message_type.value,
            },
        }

    def _build_duplicate_result(self, lead: Lead, conversation: Conversation, trace_id: str, start: float) -> OrchestratorResult:
        return OrchestratorResult(
            reply="",
            next_action=NextAction.ASK_MISSING_FIELD,
            lead_id=lead.id,
            conversation_id=conversation.id,
            trace_id=trace_id,
            latency_ms=int((time.perf_counter() - start) * 1000),
            payload={"reply": "", "duplicate": True},
            debug={"duplicate": True},
        )

    def _merge_catalog_reply(self, base_reply: str, catalog_reply: str) -> str:
        base = (base_reply or "").strip()
        catalog = (catalog_reply or "").strip()
        if not catalog:
            return base
        if not base:
            return catalog
        if catalog in base:
            return base
        return f"{base}\n\n{catalog}"

    def _merge_knowledge_reply(self, base_reply: str, knowledge_reply: str) -> str:
        knowledge = (knowledge_reply or "").strip()
        base = (base_reply or "").strip()
        if not knowledge:
            return base
        if not base:
            return knowledge
        lowered = base.lower()
        if "fontes internas:" in lowered:
            return base
        if knowledge in base:
            return base
        return f"{knowledge}\n\n{base}"

    def _build_context_window(self, messages: List[Message], summary: ConversationSummary) -> List[str]:
        window: List[str] = []
        previous_signature: Optional[str] = None
        for message in messages:
            if not message.text or not message.text.strip():
                continue
            signature = f"{message.role.value}:{message.text.strip().lower()}"
            if signature == previous_signature:
                continue
            previous_signature = signature
            prefix = "lead" if message.role == MessageRole.USER else "assistente"
            window.append(f"{prefix}: {message.text.strip()}")
        window = window[-CONTEXT_WINDOW:]
        if summary.technical:
            return [f"resumo_tecnico: {summary.technical}"] + window
        return window

    def _rehydrate_legacy_state(self, lead: Lead, conversation: Conversation, graph_state: OrchestratorGraphState) -> SessionState:
        session_id = graph_state.message_input.session_id
        state = legacy_store.get(session_id)
        persisted_snapshot = self._load_persisted_state_snapshot(session_id)

        # Merge non-destructively:
        # 1) existing legacy state (latest in-memory turn) wins when already valid
        # 2) persisted critical session state fills missing values
        # 3) orchestrator persistent state (Lead/Conversation) fills missing values
        # 4) inferred pending context (from last bot utterance) only as fallback
        self._merge_persisted_critical_state(state, persisted_snapshot)
        self._merge_lead_profile_from_orchestrator(state, lead)
        self._merge_intent_snapshot_from_orchestrator(state, lead)
        self._merge_completion_snapshot(state, lead, conversation)
        self._merge_history_snapshot(state, conversation)
        self._merge_lead_score_snapshot(state, lead)
        self._apply_preferences_to_legacy_state(state, lead)
        self._restore_pending_question_context(state)
        return state

    def _messages_to_legacy_history(self, messages: List[Message]) -> List[Dict[str, str]]:
        history: List[Dict[str, str]] = []
        for message in messages[-CONTEXT_WINDOW:]:
            history.append({"role": "user" if message.role == MessageRole.USER else "assistant", "text": message.text or ""})
        return history

    def _load_persisted_state_snapshot(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self._session_states is None:
            return None
        try:
            snapshot = self._session_states.get(session_id)
        except Exception as exc:
            logger.error(
                "orchestrator_state_snapshot_load_failed",
                extra={"session_id": session_id, "error": str(exc)},
            )
            raise
        if snapshot is None:
            return None
        if not isinstance(snapshot, dict):
            logger.error(
                "orchestrator_state_snapshot_invalid_type",
                extra={"session_id": session_id, "snapshot_type": type(snapshot).__name__},
            )
            return None
        return snapshot

    def _merge_persisted_critical_state(self, state: SessionState, snapshot: Optional[Dict[str, Any]]) -> None:
        if not snapshot:
            return

        self._merge_scalar_if_missing(state, "intent", snapshot.get("intent"))
        persisted_stage = snapshot.get("intent_stage")
        if (not self._has_meaningful_value(state.intent_stage) or str(state.intent_stage).lower() == "unknown") and self._has_meaningful_value(persisted_stage):
            state.intent_stage = str(persisted_stage)
        persisted_session_stage = snapshot.get("stage")
        if str(getattr(state, "stage", "") or "").strip().lower() in {"", "inicio"} and self._has_meaningful_value(persisted_session_stage):
            state.stage = str(persisted_session_stage)

        state.completed = bool(state.completed or snapshot.get("completed"))
        state.human_handoff = bool(state.human_handoff or snapshot.get("human_handoff"))
        state.awaiting_clarification = bool(state.awaiting_clarification or snapshot.get("awaiting_clarification"))
        state.quality_gate_turns = max(int(getattr(state, "quality_gate_turns", 0) or 0), self._as_non_negative_int(snapshot.get("quality_gate_turns")))
        state.message_index = max(int(getattr(state, "message_index", 0) or 0), self._as_non_negative_int(snapshot.get("message_index")))
        state.last_activity_at = max(float(getattr(state, "last_activity_at", 0.0) or 0.0), self._as_float(snapshot.get("last_activity_at")))

        persisted_lead_profile = snapshot.get("lead_profile")
        if isinstance(persisted_lead_profile, dict):
            for key in ("name", "phone", "email"):
                if not self._has_meaningful_value(state.lead_profile.get(key)) and self._has_meaningful_value(persisted_lead_profile.get(key)):
                    state.lead_profile[key] = persisted_lead_profile.get(key)

        persisted_criteria = snapshot.get("criteria")
        if isinstance(persisted_criteria, dict):
            for key, value in persisted_criteria.items():
                if value is None:
                    continue
                if self._legacy_field_has_value(state, key):
                    continue
                state.set_criterion(key, value, status="confirmed", source="persisted_state")

        persisted_criteria_status = snapshot.get("criteria_status")
        if isinstance(persisted_criteria_status, dict):
            for key, status in persisted_criteria_status.items():
                if key not in state.criteria_status and isinstance(status, str):
                    state.criteria_status[key] = status

        persisted_triage_fields = snapshot.get("triage_fields")
        if isinstance(persisted_triage_fields, dict):
            for key, metadata in persisted_triage_fields.items():
                if not isinstance(metadata, dict):
                    continue
                value = metadata.get("value")
                if value is None or self._legacy_field_has_value(state, key):
                    continue
                status = str(metadata.get("status") or "confirmed")
                source = str(metadata.get("source") or "persisted_state")
                state.set_criterion(key, value, status=status, source=source)
                if key in state.triage_fields:
                    if metadata.get("updated_at") is not None:
                        state.triage_fields[key]["updated_at"] = metadata.get("updated_at")
                    if metadata.get("raw_text"):
                        state.triage_fields[key]["raw_text"] = metadata.get("raw_text")
                    if metadata.get("turn_id") is not None:
                        state.triage_fields[key]["turn_id"] = metadata.get("turn_id")

        persisted_score = snapshot.get("lead_score")
        if isinstance(persisted_score, dict):
            persisted_temperature = persisted_score.get("temperature")
            if self._has_meaningful_value(persisted_temperature):
                state.lead_score.temperature = str(persisted_temperature)
            state.lead_score.score = max(
                int(getattr(state.lead_score, "score", 0) or 0),
                self._as_non_negative_int(persisted_score.get("score")),
            )
            persisted_reasons = persisted_score.get("reasons")
            if isinstance(persisted_reasons, list) and persisted_reasons:
                current_reasons = list(getattr(state.lead_score, "reasons", []) or [])
                for reason in persisted_reasons:
                    if reason not in current_reasons:
                        current_reasons.append(reason)
                state.lead_score.reasons = current_reasons

        persisted_asked_questions = snapshot.get("asked_questions")
        if isinstance(persisted_asked_questions, list):
            for question_key in persisted_asked_questions:
                if isinstance(question_key, str) and question_key and question_key not in state.asked_questions:
                    state.asked_questions.append(question_key)

        persisted_field_ask_count = snapshot.get("field_ask_count")
        if isinstance(persisted_field_ask_count, dict):
            for key, count in persisted_field_ask_count.items():
                if not isinstance(key, str):
                    continue
                state.field_ask_count[key] = max(state.field_ask_count.get(key, 0), self._as_non_negative_int(count))

        persisted_field_refusals = snapshot.get("field_refusals")
        if isinstance(persisted_field_refusals, dict):
            for key, count in persisted_field_refusals.items():
                if not isinstance(key, str):
                    continue
                state.field_refusals[key] = max(state.field_refusals.get(key, 0), self._as_non_negative_int(count))

        if not self._has_meaningful_value(state.last_question_key) and self._has_meaningful_value(snapshot.get("last_question_key")):
            state.last_question_key = str(snapshot.get("last_question_key"))

        persisted_pending = snapshot.get("pending_field")
        if (
            not self._has_meaningful_value(state.pending_field)
            and self._has_meaningful_value(persisted_pending)
            and not self._legacy_field_has_value(state, str(persisted_pending))
        ):
            state.pending_field = str(persisted_pending)

        persisted_qg_pending = snapshot.get("_quality_gate_pending_field")
        if (
            not self._has_meaningful_value(getattr(state, "_quality_gate_pending_field", None))
            and self._has_meaningful_value(persisted_qg_pending)
            and not self._legacy_field_has_value(state, str(persisted_qg_pending))
        ):
            state._quality_gate_pending_field = str(persisted_qg_pending)

        if not self._has_meaningful_value(state.last_bot_utterance) and self._has_meaningful_value(snapshot.get("last_bot_utterance")):
            state.last_bot_utterance = str(snapshot.get("last_bot_utterance"))

        persisted_history = snapshot.get("history")
        if isinstance(persisted_history, list) and not state.history:
            restored_history: List[Dict[str, str]] = []
            for item in persisted_history:
                if not isinstance(item, dict):
                    continue
                role = str(item.get("role") or "").strip().lower()
                text = str(item.get("text") or "")
                if role not in {"user", "assistant"}:
                    continue
                restored_history.append({"role": role, "text": text})
            if restored_history:
                state.history = restored_history[-(CONTEXT_WINDOW * 3) :]

    def _persist_critical_state_snapshot(
        self,
        *,
        session_id: str,
        legacy_state: SessionState,
        lead_id: Optional[str],
        conversation_id: Optional[str],
        trace_id: Optional[str],
    ) -> None:
        if self._session_states is None:
            return
        payload = self._build_critical_state_snapshot(legacy_state)
        try:
            self._session_states.upsert(
                session_id=session_id,
                state=payload,
                lead_id=lead_id,
                conversation_id=conversation_id,
                trace_id=trace_id,
            )
        except Exception as exc:
            logger.error(
                "orchestrator_state_snapshot_persist_failed",
                extra={
                    "session_id": session_id,
                    "lead_id": lead_id,
                    "conversation_id": conversation_id,
                    "error": str(exc),
                },
            )
            raise

    def _build_critical_state_snapshot(self, state: SessionState) -> Dict[str, Any]:
        triage_fields: Dict[str, Dict[str, Any]] = {}
        for key, metadata in dict(getattr(state, "triage_fields", {}) or {}).items():
            if not isinstance(metadata, dict):
                continue
            triage_fields[str(key)] = dict(metadata)

        history = []
        for item in list(getattr(state, "history", []) or [])[-(CONTEXT_WINDOW * 3) :]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip().lower()
            text = str(item.get("text") or "")
            if role not in {"user", "assistant"}:
                continue
            history.append({"role": role, "text": text})

        return {
            "snapshot_version": 1,
            "session_id": state.session_id,
            "intent": state.intent,
            "intent_stage": state.intent_stage,
            "stage": state.stage,
            "criteria": dict(getattr(state.criteria, "__dict__", {}) or {}),
            "criteria_status": dict(getattr(state, "criteria_status", {}) or {}),
            "triage_fields": triage_fields,
            "lead_profile": dict(getattr(state, "lead_profile", {}) or {}),
            "lead_score": {
                "temperature": getattr(state.lead_score, "temperature", "cold"),
                "score": int(getattr(state.lead_score, "score", 0) or 0),
                "reasons": list(getattr(state.lead_score, "reasons", []) or []),
            },
            "asked_questions": list(getattr(state, "asked_questions", []) or []),
            "last_question_key": getattr(state, "last_question_key", None),
            "pending_field": getattr(state, "pending_field", None),
            "field_ask_count": dict(getattr(state, "field_ask_count", {}) or {}),
            "_quality_gate_pending_field": getattr(state, "_quality_gate_pending_field", None),
            "quality_gate_turns": int(getattr(state, "quality_gate_turns", 0) or 0),
            "field_refusals": dict(getattr(state, "field_refusals", {}) or {}),
            "last_bot_utterance": getattr(state, "last_bot_utterance", None),
            "awaiting_clarification": bool(getattr(state, "awaiting_clarification", False)),
            "completed": bool(getattr(state, "completed", False)),
            "human_handoff": bool(getattr(state, "human_handoff", False)),
            "message_index": int(getattr(state, "message_index", 0) or 0),
            "last_activity_at": float(getattr(state, "last_activity_at", 0.0) or 0.0),
            "history": history,
        }

    def _merge_scalar_if_missing(self, state: SessionState, attr_name: str, value: Any) -> None:
        if not self._has_meaningful_value(value):
            return
        current = getattr(state, attr_name, None)
        if self._has_meaningful_value(current):
            return
        setattr(state, attr_name, value)

    def _as_non_negative_int(self, value: Any) -> int:
        try:
            parsed = int(value)
        except Exception:
            return 0
        return parsed if parsed >= 0 else 0

    def _as_float(self, value: Any) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

    def _merge_lead_profile_from_orchestrator(self, state: SessionState, lead: Lead) -> None:
        profile = dict(getattr(state, "lead_profile", {}) or {})
        profile.setdefault("name", None)
        profile.setdefault("phone", None)
        profile.setdefault("email", None)
        state.lead_profile = profile

        if not self._has_meaningful_value(profile.get("name")) and self._has_meaningful_value(lead.name):
            state.lead_profile["name"] = lead.name
        if not self._has_meaningful_value(profile.get("phone")) and self._has_meaningful_value(lead.phone):
            state.lead_profile["phone"] = lead.phone
        if not self._has_meaningful_value(profile.get("email")) and self._has_meaningful_value(lead.email):
            state.lead_profile["email"] = lead.email

    def _merge_intent_snapshot_from_orchestrator(self, state: SessionState, lead: Lead) -> None:
        lead_intent = lead.preferences.intent.value if lead.preferences.intent else None
        if not self._has_meaningful_value(state.intent) and self._has_meaningful_value(lead_intent):
            state.intent = lead_intent

        lead_stage = lead.intent_stage.value if hasattr(lead.intent_stage, "value") else str(lead.intent_stage)
        if (not self._has_meaningful_value(state.intent_stage) or str(state.intent_stage).lower() == "unknown") and self._has_meaningful_value(lead_stage):
            state.intent_stage = lead_stage

    def _merge_completion_snapshot(self, state: SessionState, lead: Lead, conversation: Conversation) -> None:
        completed_by_conversation = conversation.status in {ConversationStatus.COMPLETED, ConversationStatus.HANDED_OFF, ConversationStatus.CLOSED}
        completed_by_lead = lead.status in {
            LeadStatus.QUALIFIED,
            LeadStatus.ASSIGNED,
            LeadStatus.IN_NEGOTIATION,
            LeadStatus.VISIT_SCHEDULED,
            LeadStatus.VISIT_DONE,
            LeadStatus.WON,
            LeadStatus.LOST,
            LeadStatus.DISQUALIFIED,
        }
        state.completed = bool(state.completed or completed_by_conversation or completed_by_lead)

    def _merge_history_snapshot(self, state: SessionState, conversation: Conversation) -> None:
        persisted_history = self._messages_to_legacy_history(
            self._messages.list_by_conversation(conversation.id, limit=CONTEXT_WINDOW * 3)
        )
        if persisted_history:
            state.history = persisted_history
        state.message_index = max(
            int(getattr(state, "message_index", 0) or 0),
            len(state.history),
            len(persisted_history),
        )
        source_history = persisted_history if persisted_history else state.history
        latest_assistant = next((item["text"] for item in reversed(source_history) if item["role"] == "assistant"), None)
        if self._has_meaningful_value(latest_assistant):
            state.last_bot_utterance = latest_assistant

    def _merge_lead_score_snapshot(self, state: SessionState, lead: Lead) -> None:
        if self._has_meaningful_value(getattr(lead.score, "temperature", None)):
            state.lead_score.temperature = lead.score.temperature.value
        if int(getattr(lead.score, "total", 0) or 0) > 0 or not self._has_meaningful_value(getattr(state.lead_score, "score", 0)):
            state.lead_score.score = int(getattr(lead.score, "total", 0) or 0)
        if getattr(lead.score, "reasons", None):
            state.lead_score.reasons = list(lead.score.reasons)

    def _restore_pending_question_context(self, state: SessionState) -> None:
        if state.pending_field and self._legacy_field_has_value(state, state.pending_field):
            state.pending_field = None

        if state.pending_field and not state.last_question_key:
            state.last_question_key = state.pending_field
        if state.last_question_key and not state.pending_field and not self._legacy_field_has_value(state, state.last_question_key):
            state.pending_field = state.last_question_key

        if state.last_question_key:
            if state.last_question_key not in state.asked_questions:
                state.asked_questions.append(state.last_question_key)
            return

        inferred_key = self._infer_question_key_from_utterance(state.last_bot_utterance)
        if not inferred_key:
            return
        if self._legacy_field_has_value(state, inferred_key):
            return
        state.last_question_key = inferred_key
        state.pending_field = inferred_key
        if inferred_key not in state.asked_questions:
            state.asked_questions.append(inferred_key)

    def _infer_question_key_from_utterance(self, utterance: Optional[str]) -> Optional[str]:
        normalized = self._normalize_text(utterance)
        if not normalized:
            return None

        name_markers = ("como posso te chamar", "qual e o seu nome", "qual e seu nome", "seu nome")
        if any(marker in normalized for marker in name_markers):
            return "lead_name"

        phone_markers = ("numero de whatsapp", "numero do whatsapp", "seu whatsapp", "seu celular", "numero de telefone")
        if any(marker in normalized for marker in phone_markers):
            return "lead_phone"

        return None

    def _normalize_text(self, value: Optional[str]) -> str:
        if not value:
            return ""
        normalized = unicodedata.normalize("NFKD", str(value))
        normalized = normalized.encode("ascii", "ignore").decode("ascii")
        return " ".join(normalized.lower().split())

    def _legacy_field_has_value(self, state: SessionState, key: Optional[str]) -> bool:
        if not key:
            return False
        if key in {"intent", "operation"}:
            return self._has_meaningful_value(state.intent)
        if key in {"lead_name", "name"}:
            return self._has_meaningful_value(state.lead_profile.get("name"))
        if key in {"lead_phone", "phone"}:
            return self._has_meaningful_value(state.lead_profile.get("phone"))
        if hasattr(state.criteria, key):
            return self._has_meaningful_value(getattr(state.criteria, key))
        return self._has_meaningful_value((state.triage_fields.get(key) or {}).get("value"))

    def _has_meaningful_value(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, (list, dict, tuple, set)):
            return len(value) > 0
        return str(value).strip() != ""

    def _apply_preferences_to_legacy_state(self, state: SessionState, lead: Lead) -> None:
        mapping = {
            "city": lead.preferences.city,
            "neighborhood": lead.preferences.neighborhood,
            "micro_location": lead.preferences.micro_location,
            "bedrooms": lead.preferences.bedrooms_min,
            "suites": lead.preferences.suites_min,
            "bathrooms_min": lead.preferences.bathrooms_min,
            "parking": lead.preferences.parking_min,
            "budget": lead.preferences.budget_max,
            "budget_min": lead.preferences.budget_min,
            "timeline": lead.preferences.timeline,
            "condo_max": lead.preferences.condo_max,
            "extra_requirements": lead.preferences.extra_requirements,
        }
        if lead.preferences.property_type is not None:
            mapping["property_type"] = lead.preferences.property_type.value
        if lead.preferences.payment_type is not None:
            mapping["payment_type"] = lead.preferences.payment_type.value
        for key, value in mapping.items():
            if value is None:
                continue
            if self._legacy_field_has_value(state, key):
                continue
            signal = lead.preference_signals.get(key)
            source = signal.source if signal else "memory"
            state.set_criterion(key, value, status="confirmed", source=source)
            if key in state.triage_fields and signal is not None:
                state.triage_fields[key]["updated_at"] = signal.updated_at.timestamp()
                if signal.raw_text:
                    state.triage_fields[key]["raw_text"] = signal.raw_text

    def _sync_lead_from_legacy_state(self, lead: Lead, legacy_state: SessionState, graph_state: OrchestratorGraphState) -> None:
        lead.touch()
        lead.name = legacy_state.lead_profile.get("name") or lead.name
        lead.phone = legacy_state.lead_profile.get("phone") or lead.phone
        lead.email = legacy_state.lead_profile.get("email") or lead.email
        lead.intent_stage = self._map_intent_stage(legacy_state.intent_stage)
        lead.preferences.intent = self._map_intent(legacy_state.intent)
        lead.preferences.city = getattr(legacy_state.criteria, "city", None)
        lead.preferences.neighborhood = getattr(legacy_state.criteria, "neighborhood", None)
        lead.preferences.micro_location = getattr(legacy_state.criteria, "micro_location", None)
        lead.preferences.bedrooms_min = getattr(legacy_state.criteria, "bedrooms", None)
        lead.preferences.suites_min = getattr(legacy_state.criteria, "suites", None)
        lead.preferences.bathrooms_min = getattr(legacy_state.criteria, "bathrooms_min", None)
        lead.preferences.parking_min = getattr(legacy_state.criteria, "parking", None)
        lead.preferences.budget_max = getattr(legacy_state.criteria, "budget", None)
        lead.preferences.budget_min = getattr(legacy_state.criteria, "budget_min", None)
        lead.preferences.timeline = getattr(legacy_state.criteria, "timeline", None)
        lead.preferences.floor_pref = getattr(legacy_state.criteria, "floor_pref", None)
        lead.preferences.sun_pref = getattr(legacy_state.criteria, "sun_pref", None)
        lead.preferences.condo_max = getattr(legacy_state.criteria, "condo_max", None)
        lead.preferences.extra_requirements = getattr(legacy_state.criteria, "extra_requirements", None)
        lead.preferences.payment_type = self._map_payment_type(legacy_state.triage_fields.get("payment_type", {}).get("value"))
        lead.preferences.property_type = self._map_property_type(getattr(legacy_state.criteria, "property_type", None))
        lead.preferences.furnished = self._coerce_bool(getattr(legacy_state.criteria, "furnished", None))
        lead.preferences.pet_friendly = self._coerce_bool(getattr(legacy_state.criteria, "pet", None))
        lead.preferences.leisure_required = self._coerce_bool(getattr(legacy_state.criteria, "leisure_required", None))
        lead.preferences.leisure_level = getattr(legacy_state.criteria, "leisure_level", None)
        lead.preferences.allows_short_term_rental = self._coerce_bool(getattr(legacy_state.criteria, "allows_short_term_rental", None))

        lead.score.total = int(getattr(legacy_state.lead_score, "score", 0))
        lead.score.temperature = self._map_temperature(getattr(legacy_state.lead_score, "temperature", "cold"))
        lead.score.reasons = list(getattr(legacy_state.lead_score, "reasons", []))
        lead.score.profile_completeness = min(100, len([v for v in legacy_state.criteria.__dict__.values() if v not in (None, "", [])]) * 10)
        lead.score.engagement_score = min(100, len(legacy_state.history) * 5)
        lead.score.urgency_score = 100 if getattr(legacy_state.criteria, "timeline", None) == "30d" else 40
        lead.score.financial_score = 100 if getattr(legacy_state.criteria, "budget", None) else 20

        if graph_state.human_handoff_required:
            lead.status = LeadStatus.ASSIGNED
        elif legacy_state.completed:
            lead.status = LeadStatus.QUALIFIED
        elif lead.score.total >= 40:
            lead.status = LeadStatus.IN_QUALIFICATION
        else:
            lead.status = LeadStatus.NEW

        for field_name, metadata in legacy_state.triage_fields.items():
            self._sync_preference_signal(lead, field_name, metadata)

    def _sync_preference_signal(self, lead: Lead, field_name: str, metadata: Dict[str, Any]) -> None:
        value = metadata.get("value")
        updated_at = metadata.get("updated_at")
        try:
            updated_at_dt = (
                datetime.fromtimestamp(float(updated_at), tz=timezone.utc).replace(tzinfo=None)
                if updated_at not in (None, "")
                else _utcnow()
            )
        except Exception:
            updated_at_dt = _utcnow()
        lead.preference_signals[field_name] = PreferenceSignal(
            value=value,
            source=str(metadata.get("source") or "legacy_bridge"),
            updated_at=updated_at_dt,
            confidence=1.0 if metadata.get("status") == "confirmed" else 0.6,
            raw_text=metadata.get("raw_text"),
        )

    def _build_summary(self, lead: Lead, conversation: Conversation, legacy_state: SessionState, graph_state: OrchestratorGraphState) -> ConversationSummary:
        executive_lines = [
            f"{lead.name or 'Lead sem nome'} | score {lead.score.total}/100 ({lead.score.temperature.value})",
            f"Intencao: {lead.preferences.intent.value if lead.preferences.intent else 'nao definida'}",
            f"Busca: {lead.preferences.property_type.value if lead.preferences.property_type else 'tipo aberto'} em {lead.preferences.neighborhood or lead.preferences.city or 'local ainda aberto'}",
            f"Orcamento max: {lead.preferences.budget_max or 'nao informado'}",
            f"Proxima acao: {graph_state.next_action.value}",
        ]
        if graph_state.human_handoff_required:
            executive_lines.append("Handoff humano necessario nesta etapa.")

        recent_history = self._messages.list_by_conversation(conversation.id, limit=6)
        technical_lines = [
            f"path={' > '.join(graph_state.state_path)}",
            f"intent={graph_state.detected_intent.value}",
            f"guardrails={','.join(graph_state.guardrail_flags) or 'none'}",
            f"routing={graph_state.routing_decision or 'n/a'}",
            "historico_recente=" + " | ".join(f"{msg.role.value}:{(msg.text or '').strip()[:80]}" for msg in recent_history if msg.text),
        ]

        previous = conversation.summary
        changed = "\n".join(executive_lines) != previous.executive or "\n".join(technical_lines) != previous.technical
        return ConversationSummary(
            executive="\n".join(executive_lines),
            technical="\n".join(technical_lines),
            version=previous.version + 1 if changed else previous.version,
            generated_at=_utcnow(),
            trigger="relevant_change" if changed else previous.trigger,
        )

    def _apply_summary(self, conversation: Conversation, new_summary: ConversationSummary) -> None:
        current = conversation.summary
        changed = current.executive != new_summary.executive or current.technical != new_summary.technical
        if changed and (current.executive or current.technical):
            conversation.summary_history.append(current)
        conversation.summary = new_summary

    def _build_reasoning(self, graph_state: OrchestratorGraphState) -> str:
        return "; ".join(
            [
                f"intent={graph_state.detected_intent.value}",
                f"context_messages={len(graph_state.retrieval_context)}",
                f"property_candidates={len(graph_state.property_candidates)}",
                f"human_handoff_required={graph_state.human_handoff_required}",
                f"path={' > '.join(graph_state.state_path)}",
            ]
        )

    def _infer_next_action(self, graph_state: OrchestratorGraphState, legacy_state: SessionState, payload: Dict[str, Any]) -> NextAction:
        if graph_state.human_handoff_required:
            return NextAction.HUMAN_HANDOFF
        if payload.get("properties") or graph_state.property_candidates:
            return NextAction.SUGGEST_PROPERTIES
        if graph_state.detected_intent == DetectedIntent.FAQ:
            return NextAction.RESPOND_FAQ
        if graph_state.detected_intent == DetectedIntent.SCHEDULE_VISIT:
            return NextAction.INVITE_VISIT
        if legacy_state.completed:
            return NextAction.ROUTE_TO_BROKER
        return NextAction.ASK_MISSING_FIELD

    def _infer_handoff_reason(self, graph_state: OrchestratorGraphState, payload: Dict[str, Any]) -> Optional[HandoffReason]:
        if not graph_state.human_handoff_required:
            return None
        text = graph_state.message_input.message_text.lower()
        if "negoci" in text or graph_state.detected_intent == DetectedIntent.NEGOTIATE_PRICE:
            return HandoffReason.NEGOTIATION
        if "reclama" in text:
            return HandoffReason.COMPLAINT
        if graph_state.lead_score >= 80:
            return HandoffReason.HIGH_SCORE
        return HandoffReason.OTHER

    def _snapshot_lead_profile(self, lead: Lead) -> Dict[str, Any]:
        return {
            "name": lead.name,
            "phone": lead.phone,
            "email": lead.email,
            "intent": lead.preferences.intent.value if lead.preferences.intent else None,
            "city": lead.preferences.city,
            "neighborhood": lead.preferences.neighborhood,
            "property_type": lead.preferences.property_type.value if lead.preferences.property_type else None,
            "budget_max": lead.preferences.budget_max,
        }

    def _legacy_state_to_public_dict(self, session_id: str) -> Dict[str, Any]:
        return legacy_store.get(session_id).to_public_dict()

    def _is_stale(self, last_message_at: datetime, current_timestamp: Optional[datetime]) -> bool:
        reference = current_timestamp or _utcnow()
        return reference - last_message_at > timedelta(hours=STALE_CONVERSATION_HOURS)

    def _map_intent(self, value: Optional[str]) -> Optional[LeadIntent]:
        mapping = {"comprar": LeadIntent.BUY, "buy": LeadIntent.BUY, "alugar": LeadIntent.RENT, "rent": LeadIntent.RENT, "investir": LeadIntent.INVEST, "invest": LeadIntent.INVEST}
        return mapping.get(str(value).lower()) if value else None

    def _map_intent_stage(self, value: Optional[str]) -> LeadIntentStage:
        mapping = {"researching": LeadIntentStage.RESEARCHING, "ready_to_visit": LeadIntentStage.READY_TO_VISIT, "negotiating": LeadIntentStage.NEGOTIATING}
        return mapping.get(str(value or "").lower(), LeadIntentStage.UNKNOWN)

    def _map_payment_type(self, value: Optional[str]) -> Optional[PaymentType]:
        mapping = {"financiamento": PaymentType.FINANCING, "fgts": PaymentType.FGTS, "a_vista": PaymentType.CASH, "consorcio": PaymentType.CONSORTIUM, "misto": PaymentType.MIXED, "unknown": PaymentType.UNKNOWN}
        return mapping.get(str(value).lower()) if value else None

    def _map_property_type(self, value: Optional[str]) -> Optional[PropertyType]:
        mapping = {"apartamento": PropertyType.APARTMENT, "casa": PropertyType.HOUSE, "cobertura": PropertyType.PENTHOUSE, "studio": PropertyType.STUDIO, "comercial": PropertyType.COMMERCIAL, "terreno": PropertyType.LAND, "rural": PropertyType.RURAL}
        return mapping.get(str(value).lower()) if value else None

    def _map_temperature(self, value: str) -> LeadTemperature:
        mapping = {"hot": LeadTemperature.HOT, "warm": LeadTemperature.WARM, "cold": LeadTemperature.COLD}
        return mapping.get(str(value).lower(), LeadTemperature.COLD)

    def _coerce_bool(self, value: Any) -> Optional[bool]:
        if isinstance(value, bool):
            return value
        normalized = str(value or "").strip().lower()
        if normalized in {"sim", "true", "yes", "y"}:
            return True
        if normalized in {"nao", "não", "false", "no", "n"}:
            return False
        return None
