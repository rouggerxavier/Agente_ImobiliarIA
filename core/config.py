"""
Configuration module for production environment.
All settings loaded via environment variables with secure defaults.

Behavior por APP_ENV:
  development: ausência de tokens WhatsApp é WARNING (não bloqueia startup)
  production:  ausência de WHATSAPP_VERIFY_TOKEN é ERROR; sem WEBHOOK_API_KEY é WARNING
"""
import logging
import os
from typing import Literal

logger = logging.getLogger(__name__)


class Settings:
    """Application settings loaded from environment variables."""
    # Environment — padrão "development" para evitar falso-positivo em dev local
    APP_ENV: Literal["production", "development"] = os.getenv("APP_ENV", "development")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # WhatsApp Cloud API
    WHATSAPP_VERIFY_TOKEN: str | None = os.getenv("WHATSAPP_VERIFY_TOKEN")
    WHATSAPP_APP_SECRET: str | None = os.getenv("WHATSAPP_APP_SECRET")
    WHATSAPP_ACCESS_TOKEN: str | None = os.getenv("WHATSAPP_ACCESS_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID: str | None = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    # Feature flags
    DISABLE_WHATSAPP_SEND: bool = os.getenv("DISABLE_WHATSAPP_SEND", "true").lower() == "true"

    # Server
    PORT: int = int(os.getenv("PORT", "8000"))

    # Security: API key for the generic /webhook endpoint
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    WEBHOOK_API_KEY: str | None = os.getenv("WEBHOOK_API_KEY")

    @classmethod
    def is_development(cls) -> bool:
        return cls.APP_ENV in {"development", "dev", "test"}

    @classmethod
    def validate_whatsapp_config(cls) -> dict[str, list]:
        """
        Valida configuração WhatsApp e retorna issues classificados.

        Em development: ausência de tokens é WARNING (não impede startup).
        Em production:  WHATSAPP_VERIFY_TOKEN ausente é ERROR.
        """
        issues: dict[str, list] = {"errors": [], "warnings": []}
        dev_mode = cls.is_development()

        if not cls.WHATSAPP_VERIFY_TOKEN:
            msg = "WHATSAPP_VERIFY_TOKEN não configurado — webhook de verificação do WhatsApp desativado"
            if dev_mode:
                issues["warnings"].append(msg + " (modo dev: OK)")
            else:
                issues["errors"].append(msg + " (obrigatório em produção)")

        if not cls.WHATSAPP_APP_SECRET:
            issues["warnings"].append(
                "WHATSAPP_APP_SECRET não configurado — validação de assinatura do webhook desativada"
                + (" (não recomendado em produção)" if not dev_mode else "")
            )

        if cls.DISABLE_WHATSAPP_SEND:
            issues["warnings"].append("DISABLE_WHATSAPP_SEND=true — envio de mensagens desativado (modo teste)")

        if not cls.WHATSAPP_ACCESS_TOKEN and not cls.DISABLE_WHATSAPP_SEND:
            issues["warnings"].append("WHATSAPP_ACCESS_TOKEN não configurado — não é possível enviar mensagens")

        if not cls.WEBHOOK_API_KEY:
            issues["warnings"].append(
                "WEBHOOK_API_KEY não configurado — endpoint /webhook sem proteção. "
                "Gere com: python -c \"import secrets; print(secrets.token_hex(32))\""
            )

        return issues

    @classmethod
    def log_startup_issues(cls) -> None:
        """Loga issues de configuração no startup com nível adequado ao ambiente."""
        issues = cls.validate_whatsapp_config()
        for err in issues.get("errors", []):
            logger.error("[CONFIG] %s", err)
        for warn in issues.get("warnings", []):
            logger.warning("[CONFIG] %s", warn)


settings = Settings()
