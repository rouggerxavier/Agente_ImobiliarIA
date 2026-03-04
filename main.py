import os
import secrets
import logging
from datetime import datetime
from fastapi import FastAPI, Request, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from agent.controller import handle_message
from agent.llm import LLM_PREWARM, prewarm_llm
from core.logging import setup_logging
from core.config import settings
from routes.whatsapp import router as whatsapp_router

load_dotenv(override=True)

# Setup logging first
setup_logging()

logger = logging.getLogger(__name__)

# Rate limiter: chave por IP
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Agente Imobiliário WhatsApp", version="0.1.0")
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

# Include routers
app.include_router(whatsapp_router)


class WebhookRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=5000)
    name: str | None = Field(default=None, max_length=128)


async def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """Valida a chave de API no header X-API-Key.

    Se WEBHOOK_API_KEY não estiver configurado, loga um aviso mas permite
    acesso (compatibilidade com ambientes de desenvolvimento sem chave).
    """
    if not settings.WEBHOOK_API_KEY:
        logger.warning("WEBHOOK_API_KEY não configurado - endpoint /webhook sem autenticação")
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.WEBHOOK_API_KEY):
        logger.warning("Tentativa de acesso ao /webhook com chave inválida")
        raise HTTPException(status_code=401, detail="Chave de API inválida ou ausente")



@app.get("/health")
async def health():
    """Health check endpoint - returns 200 OK with status."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.on_event("startup")
async def _startup():
    """Application startup - validate settings and log configuration."""
    # Validate WhatsApp configuration
    validation = settings.validate_whatsapp_config()
    if validation["errors"]:
        for error in validation["errors"]:
            logger.error("Configuration error: %s", error)
    if validation["warnings"]:
        for warning in validation["warnings"]:
            logger.warning("Configuration warning: %s", warning)

    logger.info(
        "Application started - env=%s, log_level=%s, whatsapp_send=%s",
        settings.APP_ENV,
        settings.LOG_LEVEL,
        "disabled" if settings.DISABLE_WHATSAPP_SEND else "enabled",
    )

    # Prewarm desativado para evitar chamadas iniciais ao LLM.
    return


@app.post("/webhook", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def webhook(body: WebhookRequest, request: Request):
    correlation_id = os.urandom(8).hex()
    request.state.correlation_id = correlation_id
    logger.info(
        "webhook request - session=%s, msg_len=%d, correlation=%s",
        body.session_id,
        len(body.message),
        correlation_id,
    )
    # Only expose the textual reply to the client; hide internal state/session details.
    result = handle_message(body.session_id, body.message, name=body.name, correlation_id=correlation_id)
    if isinstance(result, dict) and "reply" in result:
        return {"reply": result["reply"]}
    return result


# Serve React frontend (built files) — must be last to not intercept API routes
_dist_path = os.path.join(os.path.dirname(__file__), "dist")
if os.path.isdir(_dist_path):
    app.mount("/", StaticFiles(directory=_dist_path, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
