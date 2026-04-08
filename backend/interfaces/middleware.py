"""
Middleware de rastreabilidade — injeta trace_id e correlation IDs em cada request HTTP.

Integra com core/trace.py para propagar automaticamente os IDs de correlação
para todos os logs gerados durante o processamento da request.

Headers suportados:
    X-Trace-Id     — trace externo (ex: do gateway)
    X-Request-Id   — ID da request específica
    X-Correlation-Id — ID de correlação legado

Headers de saída (response):
    X-Trace-Id, X-Request-Id
"""
from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.trace import get_logger, set_trace_context

logger = get_logger(__name__)


class TraceMiddleware(BaseHTTPMiddleware):
    """
    Middleware que:
    1. Lê/gera trace_id e request_id da request de entrada
    2. Seta o contexto de trace (disponível para todos os logs da request)
    3. Mede latência total da request
    4. Adiciona headers de trace na response
    5. Loga início e fim de cada request
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Lê IDs externos ou gera novos
        trace_id = (
            request.headers.get("X-Trace-Id")
            or request.headers.get("X-Correlation-Id")
            or str(uuid.uuid4())
        )
        request_id = (
            request.headers.get("X-Request-Id")
            or str(uuid.uuid4())
        )

        # Seta o contexto — propaga para todos os logs desta request
        set_trace_context(
            trace_id=trace_id,
            request_id=request_id,
        )

        # Injeta no estado da request para uso nos endpoints
        request.state.trace_id = trace_id
        request.state.request_id = request_id

        # Mede latência
        start = time.perf_counter()

        logger.info(
            "request_start",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
            },
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.error(
                "request_error",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "latency_ms": elapsed_ms,
                    "error": str(exc),
                },
                exc_info=True,
            )
            raise

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        logger.info(
            "request_end",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": elapsed_ms,
            },
        )

        # Propaga trace IDs na response
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Request-Id"] = request_id

        return response
