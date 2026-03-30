"""
Storage sub-package — bridge para armazenamento legado em arquivos JSON.

Propósito:
  Encapsular toda dependência de arquivo legado (leads.jsonl, agents.json,
  properties.json) num único adaptador, facilitando a migração para PostgreSQL
  na Fase 1 sem quebrar o comportamento atual.

Usado APENAS durante a migração. Após Fase 1, este pacote será descontinuado.
"""
