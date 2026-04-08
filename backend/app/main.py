import os
import secrets
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

load_dotenv(override=True)

from agent.runtime import handle_message
from application.bootstrap import process_phase34_message
from application.conversation_orchestrator import MessageInput
from domain.enums import Channel
from app.db import init_db
from core.config import settings
from core.logging import setup_logging
from core.trace import get_logger, set_trace_context
from interfaces.middleware import TraceMiddleware
from routes.contato import router as contato_router
from routes.imoveis import router as imoveis_router
from routes.whatsapp import router as whatsapp_router

setup_logging()
logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Agente Imobiliario WhatsApp", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

frontend_origins_env = os.getenv("FRONTEND_ORIGINS")
if frontend_origins_env:
    allowed_origins = [origin.strip() for origin in frontend_origins_env.split(",") if origin.strip()]
else:
    allowed_origins = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de rastreabilidade — injeta trace_id/request_id em todos os requests
app.add_middleware(TraceMiddleware)


class SPAStaticFiles(StaticFiles):
    """Static files with fallback to index.html for client-side routing."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


_BASE_DIR = Path(__file__).resolve().parents[1]
_img_path = _BASE_DIR / "public" / "imoveis"
if _img_path.is_dir():
    app.mount("/imoveis-img", StaticFiles(directory=str(_img_path)), name="imoveis-img")

app.include_router(whatsapp_router)
app.include_router(imoveis_router)
app.include_router(contato_router)


class WebhookRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=5000)
    name: str | None = Field(default=None, max_length=128)


async def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """Validate API key in X-API-Key header."""
    if not settings.WEBHOOK_API_KEY:
        logger.warning("WEBHOOK_API_KEY nao configurado - endpoint /webhook sem autenticacao")
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.WEBHOOK_API_KEY):
        logger.warning("Tentativa de acesso ao /webhook com chave invalida")
        raise HTTPException(status_code=401, detail="Chave de API invalida ou ausente")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "agente_imobiliario_api",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/")
async def home():
    """Home page with API status and useful links."""
    timestamp = datetime.now().isoformat()
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agente Imobiliario API</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #333; margin-top: 0; }}
            .status {{ color: #28a745; font-weight: bold; }}
            .links {{ margin-top: 20px; }}
            .links a {{
                display: inline-block;
                margin-right: 15px;
                color: #007bff;
                text-decoration: none;
                padding: 8px 15px;
                border: 1px solid #007bff;
                border-radius: 4px;
                transition: all 0.2s;
            }}
            .links a:hover {{
                background: #007bff;
                color: white;
            }}
            .info {{ margin-top: 20px; color: #666; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Agente Imobiliario API</h1>
            <p class="status">Status: Online</p>
            <div class="links">
                <a href="/docs">API Documentation</a>
                <a href="/health">Health Check</a>
            </div>
            <div class="info">
                <p><strong>Endpoints disponiveis:</strong></p>
                <ul>
                    <li><code>GET /</code> - Esta pagina</li>
                    <li><code>GET /health</code> - Health check</li>
                    <li><code>POST /webhook</code> - Webhook do agente (requer X-API-Key)</li>
                    <li><code>GET /webhook/whatsapp</code> - Verificacao WhatsApp</li>
                    <li><code>POST /webhook/whatsapp</code> - Eventos WhatsApp</li>
                    <li><code>GET /docs</code> - Documentacao interativa</li>
                </ul>
                <p style="margin-top: 20px;">
                    <small>Timestamp: {timestamp}</small>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.on_event("startup")
async def _startup():
    init_db()
    settings.log_startup_issues()

    logger.info(
        "Application started - env=%s, log_level=%s, whatsapp_send=%s",
        settings.APP_ENV,
        settings.LOG_LEVEL,
        "disabled" if settings.DISABLE_WHATSAPP_SEND else "enabled",
    )


@app.post("/webhook", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def webhook(body: WebhookRequest, request: Request):
    # Enriquece contexto de trace com IDs de sessão (já iniciado pelo TraceMiddleware)
    trace_id = getattr(request.state, "trace_id", None)
    set_trace_context(
        trace_id=trace_id,
        lead_id=body.session_id,
        channel="web",
    )
    session_short = body.session_id[:8]

    logger.info(
        "webhook_user_message",
        extra={"session_short": session_short, "message_preview": body.message[:300]},
    )

    try:
        result = process_phase34_message(
            MessageInput(
                session_id=body.session_id,
                message_text=body.message,
                sender_name=body.name,
                trace_id=trace_id,
                channel=Channel.WEB,
            )
        )
    except Exception:
        logger.exception("webhook_phase34_failed fallback=runtime")
        result = handle_message(
            body.session_id,
            body.message,
            name=body.name,
            correlation_id=trace_id,
        )
    if isinstance(result, dict) and "reply" in result:
        logger.info(
            "webhook_agent_reply",
            extra={"session_short": session_short, "reply_preview": result["reply"][:300]},
        )
        return {"reply": result["reply"]}
    return result


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
