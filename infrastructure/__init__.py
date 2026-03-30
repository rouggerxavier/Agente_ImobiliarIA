"""
Infrastructure layer — adaptadores para banco, LLM, WhatsApp e storage.

Sub-pacotes:
  persistence/   — repositórios SQLAlchemy (Fase 1)
  llm/           — cliente LLM com fallback e retry
  whatsapp/      — integração WhatsApp Cloud API
  storage/       — bridge para o legado de arquivos JSON
"""
