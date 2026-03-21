import logging
import os
import secrets
from datetime import datetime

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from agent.runtime import handle_message
from core.config import settings
from core.logging import setup_logging
from db import init_db
from routes.contato import router as contato_router
from routes.imoveis import router as imoveis_router
from routes.whatsapp import router as whatsapp_router

load_dotenv(override=True)

setup_logging()
logger = logging.getLogger(__name__)

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


class SPAStaticFiles(StaticFiles):
    """Static files with fallback to index.html for client-side routing."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


_img_path = os.path.join(os.path.dirname(__file__), "public", "imoveis")
if os.path.isdir(_img_path):
    app.mount("/imoveis-img", StaticFiles(directory=_img_path), name="imoveis-img")

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
    correlation_id = os.urandom(8).hex()
    request.state.correlation_id = correlation_id
    session_short = body.session_id[:8]

    logger.info("USER [%s] %s (correlation=%s)", session_short, body.message[:300], correlation_id)

    result = handle_message(body.session_id, body.message, name=body.name, correlation_id=correlation_id)
    if isinstance(result, dict) and "reply" in result:
        logger.info("AGENT [%s] %s (correlation=%s)", session_short, result["reply"][:300], correlation_id)
        return {"reply": result["reply"]}
    return result


_dist_path = os.path.join(os.path.dirname(__file__), "dist")
if os.path.isdir(_dist_path):
    app.mount("/", SPAStaticFiles(directory=_dist_path, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
