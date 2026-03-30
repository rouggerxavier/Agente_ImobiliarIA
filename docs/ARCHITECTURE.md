# Arquitetura Técnica — Agente ImobiliarIA V2

> Documento vivo. Atualizar sempre que uma decisão arquitetural for tomada ou revista.
> Referência direta para as seções 3 e 4 do `roadmap.md`.

---

## 1. Decisões de Produto (Seção 3.1 do Roadmap)

| Decisão | Escolha | Justificativa |
|---|---|---|
| **Modelo de produto** | **Triagem-first → Copiloto completo** | V1 foca em qualificação e roteamento; V2 adiciona recomendação e memória persistente |
| **Público principal** | Imobiliária multi-corretor (5–30 corretores) | Operação com volume médio, necessidade de triagem automatizada e roteamento inteligente |
| **Canais V1** | WhatsApp + Web Chat | Maior volume de leads imobiliários no Brasil |
| **Canais V2** | + Dashboard interno + E-mail | Expansão pós-estabilização do V1 |
| **Autonomia da IA** | Triagem, qualificação, recomendação e follow-up | Handoff obrigatório para negociação, contraproposta e assinatura |
| **Tom de voz** | Consultivo, acolhedor, direto | Sem promessas de preço ou disponibilidade sem confirmação do corretor |

### O que a IA pode fazer sem humano
- Qualificar lead (coletar perfil completo)
- Recomendar imóveis do catálogo
- Responder perguntas da base de conhecimento (FAQ)
- Calcular score e classificar temperatura
- Rotear para corretor adequado
- Enviar follow-ups automáticos (nurturing)

### O que exige handoff humano
- Negociar preço ou condições
- Confirmar disponibilidade em tempo real
- Assinar documentos ou contratos
- Lidar com reclamações graves
- Solicitar documentação legal

---

## 2. Arquitetura em Camadas (Seção 3.2 do Roadmap)

O projeto adota **Arquitetura Hexagonal** (Ports & Adapters) com 4 camadas:

```
┌─────────────────────────────────────────────────────────┐
│                    interfaces/                          │
│         (HTTP, webhooks, jobs, CLI)                     │
├─────────────────────────────────────────────────────────┤
│                   application/                          │
│         (casos de uso, orquestração)                    │
├─────────────────────────────────────────────────────────┤
│                     domain/                             │
│         (entidades, enums, regras, ports)               │
├─────────────────────────────────────────────────────────┤
│                 infrastructure/                         │
│         (banco, fila, LLM, WhatsApp API)                │
└─────────────────────────────────────────────────────────┘
```

### Regras de dependência
- `domain/` → **não importa nada** do projeto (só stdlib + pydantic)
- `application/` → importa apenas `domain/`
- `infrastructure/` → importa `domain/` e bibliotecas externas
- `interfaces/` → importa `application/` e `infrastructure/`

### Módulos existentes (legado)
Os módulos em `agent/` são tratados como **legado** enquanto a nova arquitetura é construída em paralelo.
A migração ocorre incrementalmente, sem quebrar funcionalidade existente.

| Módulo legado | Destino |
|---|---|
| `agent/state.py` | → `domain/entities.py` (SessionState → Lead + Conversation) |
| `agent/persistence.py` | → `infrastructure/persistence/` |
| `agent/scoring.py` | → `domain/` + `application/` |
| `agent/router.py` (corretor) | → `application/routing.py` |
| `agent/prompts.py` | → `infrastructure/llm/prompts/` |
| `core/config.py` | Mantém, expande para suportar novos serviços |
| `core/logging.py` | → Substituído por `core/trace.py` (logging estruturado + JSON) |

---

## 3. Fluxo Ponta a Ponta

```
Mensagem WhatsApp/Web
        │
        ▼
[interfaces/] Webhook recebe → valida assinatura → persiste evento bruto
        │
        ▼
[application/] Caso de uso ProcessMessage:
        ├── Busca/cria Lead no banco
        ├── Busca/cria Conversation ativa
        ├── Persiste Message (dedup por external_message_id)
        ├── Injeta trace_id, lead_id, conversation_id nos logs
        ├── Chama orquestrador conversacional
        │       ├── Classifica intenção (DetectedIntent)
        │       ├── Extrai campos estruturados
        │       ├── Atualiza perfil do lead (LeadPreferences)
        │       ├── Calcula score (LeadScore)
        │       ├── Consulta catálogo (se necessário)
        │       ├── Consulta knowledge base (se FAQ)
        │       ├── Decide próxima ação (NextAction)
        │       └── Gera resposta
        ├── Persiste DecisionLog
        ├── Atualiza Lead (score, status, perfil)
        └── Envia resposta pelo canal
```

---

## 4. Rastreabilidade (IDs de Correlação)

Todo evento no sistema carrega 4 IDs obrigatórios:

| ID | Descrição | Escopo |
|---|---|---|
| `trace_id` | UUID gerado por request HTTP | Uma interação completa (request → response) |
| `request_id` | UUID da request específica | Uma chamada HTTP |
| `lead_id` | ID do Lead no banco | Todo o ciclo de vida do lead |
| `conversation_id` | ID da Conversation ativa | Uma sessão de conversa |

Implementação via `core/trace.py` com Python `contextvars` — propaga automaticamente por `async/await` sem passar como parâmetro.

---

## 5. Critérios de Sucesso (Seção 4 do Roadmap)

### 5.1 Critérios de Negócio

| Métrica | Meta V1 | Como medir |
|---|---|---|
| Taxa de leads qualificados | > 60% dos leads que iniciam | `leads.status = QUALIFIED / leads.status IN (NEW, IN_QUALIFICATION, QUALIFIED)` |
| Tempo médio até 1ª resposta | < 30 segundos | `conversations.first_response_at - conversations.created_at` |
| Taxa de handoff bem-sucedido | > 80% dos roteamentos | `assignments com ACK do corretor / total assignments` |
| Taxa de visita agendada | > 15% dos leads HOT | `leads com visit_scheduled / leads com temperature=HOT` |
| Taxa de conversão por corretor | Baseline no 1º mês | `leads WON / leads assigned por broker_id` |
| Recuperação de leads frios | > 20% com follow-up | `leads que responderam follow-up / leads COLD com follow-up enviado` |
| Resposta útil sobre catálogo | > 85% de groundedness | Avaliação por amostragem + benchmark RAG |

### 5.2 Critérios Técnicos

| Critério | Meta | Como medir |
|---|---|---|
| Disponibilidade | 95%+ sem erro fatal | `1 - (erros 5xx / total requests)` |
| Persistência consistente | 99%+ de eventos salvos | Comparar webhook_received vs message.saved no log |
| Latência | < 5s em p95 | `request_end.latency_ms` (percentil 95) |
| Cobertura de testes | ≥ 80% por camada crítica | pytest-cov por módulo |
| Auditoria de IA | 100% das decisões logadas | `decision_logs` por conversation_id |
| Tracing | Trace completo por fluxo | Trace_id presente em 100% dos logs de um request |
| Staging separado | `APP_ENV=staging` com banco próprio | Deploy independente |
| Rollback | Deploy anterior em < 5min | Processo documentado no runbook |

---

## 6. Tecnologias Escolhidas

| Componente | Tecnologia | Status |
|---|---|---|
| API | FastAPI | ✅ Em uso |
| LLM | OpenAI + Anthropic (fallback) | ✅ Em uso |
| Storage atual | JSON files (`data/leads.jsonl`) | ⚠️ Legado — migrar para Fase 1 |
| Banco alvo | PostgreSQL | 🔲 Fase 1 |
| ORM | SQLAlchemy 2.x async | 🔲 Fase 1 |
| Migrations | Alembic | 🔲 Fase 1 |
| Fila | Redis (Bull/Celery) ou RabbitMQ | 🔲 Fase 4 |
| Embeddings | OpenAI text-embedding-3-small | 🔲 Fase 5/6 |
| Vector store | pgvector (PostgreSQL) | 🔲 Fase 5/6 |
| Observabilidade | OpenTelemetry → Jaeger/Grafana | 🔲 Fase 11 |
| CI/CD | GitHub Actions | 🔲 Fase 14 |

---

## 7. Dívidas Técnicas Priorizadas

| Prioridade | Dívida | Impacto | Fase |
|---|---|---|---|
| 🔴 CRÍTICO | `agent/controller.py` com 1.253 linhas — múltiplas responsabilidades | Manutenibilidade | Fase 0 |
| 🔴 CRÍTICO | Persistência em `data/leads.jsonl` sem transação | Confiabilidade | Fase 1 |
| 🔴 CRÍTICO | `InMemoryStore` — estado lost em restart | Confiabilidade | Fase 1 |
| 🟡 ALTO | Prompts espalhados em `agent/prompts.py` e `agent/llm.py` | Governança | Backlog |
| 🟡 ALTO | Regras de negócio em `agent/rules.py` misturadas com lógica de UI | Arquitetura | Fase 0 |
| 🟡 ALTO | Sem deduplicação de mensagens externas | Idempotência | Fase 2 |
| 🟢 NORMAL | Logs não estruturados (texto livre em alguns módulos) | Observabilidade | Em progresso |
| 🟢 NORMAL | Corretores em JSON (`data/agents.json`) sem banco | Escalabilidade | Fase 1 |
| 🟢 NORMAL | Sem testes de integração para fluxo WhatsApp→persistência | Confiabilidade | Fase 12 |

---

## 8. Variáveis de Ambiente Obrigatórias

| Variável | Obrigatório | Descrição |
|---|---|---|
| `APP_ENV` | Não (default: development) | `development` / `staging` / `production` |
| `LOG_LEVEL` | Não (default: INFO) | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `WEBHOOK_API_KEY` | Produção | Chave de autenticação do endpoint `/webhook` |
| `WHATSAPP_VERIFY_TOKEN` | Produção WhatsApp | Token de verificação do webhook Meta |
| `WHATSAPP_APP_SECRET` | Recomendado | Validação de assinatura HMAC |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp ativo | Token de acesso à Cloud API |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp ativo | ID do número no Meta |
| `OPENAI_API_KEY` | Sim | Chave da API OpenAI |
| `ANTHROPIC_API_KEY` | Fallback | Chave Anthropic (fallback do LLM) |
| `DATABASE_URL` | Fase 1 | URL do PostgreSQL |
| `PORT` | Não (default: 8000) | Porta do servidor |

---

*Última atualização: 2026-03-30*
*Autor: Arquitetura Agente ImobiliarIA*
