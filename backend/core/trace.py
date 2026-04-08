"""
Logging estruturado com IDs de correlação e contexto de rastreabilidade.

Princípios implementados (Seção 3.2 do roadmap):
- Logs em JSON estruturado
- Campos obrigatórios: trace_id, lead_id, conversation_id, request_id, channel
- Sanitização automática de dados sensíveis
- Context vars para propagar IDs sem passar como parâmetro
- Compatível com o setup_logging() existente em core/logging.py

Uso:
    from core.trace import set_trace_context, get_logger

    set_trace_context(trace_id="abc", lead_id="123", conversation_id="456")
    logger = get_logger(__name__)
    logger.info("Mensagem processada", extra={"message_id": "789"})
"""
from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Context variables — propagam automaticamente por async/await e threads
# ─────────────────────────────────────────────────────────────────────────────

_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_request_id: ContextVar[str] = ContextVar("request_id", default="")
_lead_id: ContextVar[str] = ContextVar("lead_id", default="")
_conversation_id: ContextVar[str] = ContextVar("conversation_id", default="")
_message_id: ContextVar[str] = ContextVar("message_id", default="")
_channel: ContextVar[str] = ContextVar("channel", default="")


def set_trace_context(
    *,
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    message_id: Optional[str] = None,
    channel: Optional[str] = None,
) -> str:
    """
    Define o contexto de rastreabilidade para a tarefa/request atual.

    Retorna o trace_id gerado (ou o passado).
    Os valores ficam disponíveis automaticamente em todos os logs
    emitidos a partir deste ponto na mesma task/thread.
    """
    tid = trace_id or str(uuid.uuid4())
    rid = request_id or str(uuid.uuid4())
    _trace_id.set(tid)
    _request_id.set(rid)
    if lead_id:
        _lead_id.set(lead_id)
    if conversation_id:
        _conversation_id.set(conversation_id)
    if message_id:
        _message_id.set(message_id)
    if channel:
        _channel.set(channel)
    return tid


def get_trace_context() -> Dict[str, str]:
    """Retorna o contexto de trace atual como dicionário."""
    ctx: Dict[str, str] = {}
    if _trace_id.get():
        ctx["trace_id"] = _trace_id.get()
    if _request_id.get():
        ctx["request_id"] = _request_id.get()
    if _lead_id.get():
        ctx["lead_id"] = _lead_id.get()
    if _conversation_id.get():
        ctx["conversation_id"] = _conversation_id.get()
    if _message_id.get():
        ctx["message_id"] = _message_id.get()
    if _channel.get():
        ctx["channel"] = _channel.get()
    return ctx


# ─────────────────────────────────────────────────────────────────────────────
# JSON Formatter com contexto automático
# ─────────────────────────────────────────────────────────────────────────────

_SENSITIVE_KEYS = {
    "token", "secret", "password", "api_key", "access_token",
    "verify_token", "app_secret", "authorization", "x-hub-signature",
    "private_key", "client_secret",
}


def _sanitize(value: Any, key: str = "") -> Any:
    """Remove dados sensíveis de valores de log."""
    key_lower = key.lower().replace("-", "_").replace(" ", "_")
    if any(s in key_lower for s in _SENSITIVE_KEYS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {k: _sanitize(v, k) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    return value


class StructuredJsonFormatter(logging.Formatter):
    """
    Formatter que emite cada log como uma linha JSON com campos padronizados.

    Campos sempre presentes:
        ts, level, logger, message
    Campos de correlação (quando presentes no contexto):
        trace_id, request_id, lead_id, conversation_id, message_id, channel
    Campos extras passados via extra={}:
        Qualquer chave do dicionário extra
    """

    def format(self, record: logging.LogRecord) -> str:
        ctx = get_trace_context()

        payload: Dict[str, Any] = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Adiciona contexto de trace (se presente)
        payload.update(ctx)

        # Adiciona campos extras passados via extra={}
        skip = {
            "args", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "message",
            "module", "msecs", "msg", "name", "pathname", "process",
            "processName", "relativeCreated", "stack_info", "taskName",
            "thread", "threadName",
        }
        for key, val in record.__dict__.items():
            if key not in skip and not key.startswith("_"):
                payload[key] = _sanitize(val, key)

        # Exception
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        try:
            return json.dumps(payload, ensure_ascii=False, default=str)
        except Exception:
            return json.dumps({"ts": payload["ts"], "level": "ERROR",
                               "message": "Log serialization failed"})


# ─────────────────────────────────────────────────────────────────────────────
# Logging contextual — injeta trace automaticamente no extra
# ─────────────────────────────────────────────────────────────────────────────

class TraceLogger(logging.LoggerAdapter):
    """
    Logger que injeta automaticamente o contexto de trace em cada mensagem.

    Uso:
        logger = get_logger(__name__)
        logger.info("Mensagem", extra={"key": "value"})
        # Saída inclui: trace_id, lead_id, conversation_id, etc.
    """

    def process(self, msg: str, kwargs: Dict[str, Any]):
        extra = kwargs.get("extra", {}) or {}
        extra.update(get_trace_context())
        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str) -> TraceLogger:
    """
    Retorna um logger com injeção automática de contexto de trace.

    Substitui `logging.getLogger(name)` em todos os novos módulos.
    """
    return TraceLogger(logging.getLogger(name), extra={})


# ─────────────────────────────────────────────────────────────────────────────
# Utilitário de performance logging
# ─────────────────────────────────────────────────────────────────────────────

class timer:
    """
    Context manager para medir latência de operações e logar automaticamente.

    Uso:
        logger = get_logger(__name__)
        with timer(logger, "llm_call", lead_id="123"):
            result = call_llm(...)
        # Log: {"message": "llm_call", "latency_ms": 420, "lead_id": "123"}
    """

    def __init__(self, logger: TraceLogger, operation: str, **extra_fields: Any) -> None:
        self._logger = logger
        self._operation = operation
        self._extra = extra_fields
        self._start: float = 0.0

    def __enter__(self) -> "timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        elapsed_ms = int((time.perf_counter() - self._start) * 1000)
        level = logging.ERROR if exc_type else logging.INFO
        self._logger.log(
            level,
            self._operation,
            extra={"latency_ms": elapsed_ms, "success": exc_type is None, **self._extra},
        )
        return False  # Não suprime exceção


# ─────────────────────────────────────────────────────────────────────────────
# Setup global — chamado no startup da aplicação
# ─────────────────────────────────────────────────────────────────────────────

def setup_structured_logging(log_level: str = "INFO", json_output: bool = True) -> None:
    """
    Configura o sistema de logging estruturado.

    Args:
        log_level: Nível de log (DEBUG, INFO, WARNING, ERROR)
        json_output: Se True, emite JSON; se False, emite texto legível (dev)
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if json_output:
        handler.setFormatter(StructuredJsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = []
    root.addHandler(handler)

    # Silencia loggers muito verbosos de bibliotecas
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
