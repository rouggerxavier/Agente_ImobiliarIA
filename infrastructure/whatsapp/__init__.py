"""
WhatsApp sub-package — integração com WhatsApp Cloud API.

Responsabilidades:
  - Deserializar payload do webhook Meta
  - Validar assinatura HMAC (X-Hub-Signature-256)
  - Enviar mensagens de texto, mídia e templates
  - Registrar status de entrega/leitura
  - Modo sandbox para testes sem envio real

Fase atual: bridge para services/whatsapp_sender.py legado.
Fase 2: implementação completa com idempotência e retry.
"""
