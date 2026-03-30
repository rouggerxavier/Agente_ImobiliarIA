"""
[M1] Orquestrador conversacional com memoria persistente e grafo de estados.

O comportamento comercial continua vindo do controller legado, mas o fluxo passa
por um state graph explicito, com checkpoints, persistencia operacional e
resumos auditaveis.
"""
from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
from domain.repositories import ConversationRepository, DecisionLogRepository, EventRepository, LeadRepository, MessageRepository

logger = get_logger(__name__)

CONTEXT_WINDOW = max(6, int(os.getenv("ORCHESTRATOR_CONTEXT_WINDOW", "12")))
STALE_CONVERSATION_HOURS = max(1, int(os.getenv("ORCHESTRATOR_STALE_CONVERSATION_HOURS", "8")))
NODE_TIMEOUT_MS = max(250, int(os.getenv("ORCHESTRATOR_NODE_TIMEOUT_MS", "8000")))
NODE_RETRIES = max(0, int(os.getenv("ORCHESTRATOR_NODE_RETRIES", "1")))
EXECUTION_COST_LIMIT_USD = max(0.0, float(os.getenv("ORCHESTRATOR_EXECUTION_COST_LIMIT_USD", "0.25")))


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
            self.timestamp = datetime.utcnow()


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
                conversation.handoff_at = datetime.utcnow()
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
        legacy_store.reset(session_id)
        state = legacy_store.get(session_id)
        state.lead_profile.update({"name": lead.name, "phone": lead.phone, "email": lead.email})
        state.intent = lead.preferences.intent.value if lead.preferences.intent else None
        state.intent_stage = lead.intent_stage.value if hasattr(lead.intent_stage, "value") else str(lead.intent_stage)
        state.completed = conversation.status in {ConversationStatus.COMPLETED, ConversationStatus.HANDED_OFF, ConversationStatus.CLOSED}
        state.history = self._messages_to_legacy_history(self._messages.list_by_conversation(conversation.id, limit=CONTEXT_WINDOW * 3))
        state.message_index = len(state.history)
        state.last_bot_utterance = next((item["text"] for item in reversed(state.history) if item["role"] == "assistant"), None)
        state.lead_score.temperature = lead.score.temperature.value
        state.lead_score.score = lead.score.total
        state.lead_score.reasons = list(lead.score.reasons)
        self._apply_preferences_to_legacy_state(state, lead)
        return state

    def _messages_to_legacy_history(self, messages: List[Message]) -> List[Dict[str, str]]:
        history: List[Dict[str, str]] = []
        for message in messages[-CONTEXT_WINDOW:]:
            history.append({"role": "user" if message.role == MessageRole.USER else "assistant", "text": message.text or ""})
        return history

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
            updated_at_dt = datetime.utcfromtimestamp(float(updated_at)) if updated_at not in (None, "") else datetime.utcnow()
        except Exception:
            updated_at_dt = datetime.utcnow()
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
            generated_at=datetime.utcnow(),
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
        reference = current_timestamp or datetime.utcnow()
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
