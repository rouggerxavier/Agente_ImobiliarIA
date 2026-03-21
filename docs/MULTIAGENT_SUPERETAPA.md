# Superetapa Multiagente (Incremental)

## Objetivo
Esta etapa adiciona uma camada de orquestracao multiagente sem quebrar os endpoints existentes. O fluxo legado continua como padrao e a nova camada e ativada por feature flag.

## Como ativar
No `.env`:

```env
MULTIAGENT_ENABLED=true
MULTIAGENT_OPENAI_SDK_ROUTER_ENABLED=true
MULTIAGENT_OPENAI_MODEL=gpt-4.1-mini
MULTIAGENT_TRACE_ENABLED=true
MULTIAGENT_TRACE_PATH=data/multiagent_trace.jsonl
MULTIAGENT_ALLOW_SENSITIVE_ACTIONS=false
```

## Arquitetura implementada

### 1. Gateway de runtime
- Arquivo: `agent/runtime.py`
- Funcao: `handle_message(...)`
- Comportamento:
  - `MULTIAGENT_ENABLED=false`: usa `agent.controller.handle_message` (legado).
  - `MULTIAGENT_ENABLED=true`: usa `MultiAgentOrchestrator`.
  - Em qualquer falha: fallback automatico para legado.

### 2. Orquestrador
- Arquivo: `agent/multiagent/orchestrator.py`
- Responsabilidades:
  - avaliar guardrails de entrada;
  - decidir rota (deterministica e opcionalmente via OpenAI Agents SDK);
  - delegar para subagent especializado;
  - executar handoff controlado para legado quando necessario;
  - registrar trace estruturado.

### 3. Subagents especializados
- `legacy_triage_subagent`: delega para controlador existente.
- `catalog_subagent`: consulta catalogo usando skill de busca.
- `knowledge_subagent`: consulta base de conhecimento.

### 4. Skills reutilizaveis
- `property_catalog_search`: extracao de filtros + busca com validacao.
- `knowledge_lookup`: consulta segura na knowledge base.
- Todos com `SkillResult` padronizado e tratamento de erro.

### 5. Guardrails
- Arquivo: `agent/multiagent/guardrails.py`
- Bloqueia padroes sensiveis por padrao (`drop table`, `rm -rf`, etc).
- Validacao de payload de tools para evitar entradas invalidas.

### 6. Observabilidade minima
- Arquivo: `agent/multiagent/observability.py`
- Eventos JSONL:
  - `orchestrator_start`
  - `orchestrator_guardrail_block`
  - `orchestrator_finish`
- Caminho configuravel por `MULTIAGENT_TRACE_PATH`.

### 7. OpenAI Agents SDK (opcional)
- Arquivo: `agent/multiagent/openai_sdk_router.py`
- Implementa classificador de rota com SDK oficial (`agents.Agent`, `Runner.run_sync`).
- Nao e obrigatorio para funcionar: se indisponivel ou falhar, usa roteamento deterministico.

## Compatibilidade e seguranca
- Endpoints existentes preservados.
- Contrato de `/webhook` preservado (resposta com `reply`).
- Fluxo legado permanece operacional.
- Sem acao sensivel automatica sem validacao.

## Pontos de extensao (proxima etapa)
1. Adicionar subagent de follow-up e subagent de CRM.
2. Instrumentar spans customizados do Agents SDK com exportador adicional.
3. Evoluir roteamento para politicas por score/estado da sessao.
4. Acrescentar approval explicito para tools sensiveis.

