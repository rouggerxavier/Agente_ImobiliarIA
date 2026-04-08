"""
LLM sub-package — cliente unificado de modelos de linguagem.

Fornece abstração sobre OpenAI e Anthropic com:
  - Fallback automático entre provedores
  - Retry com backoff exponencial
  - Circuit breaker (modo degradado)
  - Logging de tokens, latência e custo
  - Timeout configurável por operação

Fase atual: bridge para agent/llm.py legado.
Fase 3+: implementação própria com contratos domain-driven.
"""
