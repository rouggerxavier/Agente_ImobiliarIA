# Macroarquitetura Alvo — Agente ImobiliarIA V2

> Documento técnico oficial. Respostas diretas às questões da Seção 5 do `roadmap.md`.
> Em caso de conflito com outros documentos, este prevalece.

---

## 1. Decisão: Monólito Modular (V1) → Serviços Independentes (V2+)

### Decisão formal

**V1: Monólito modular**

O projeto continuará como um único processo Python/FastAPI com módulos bem separados por domínio funcional.
Cada módulo segue os contratos de `domain/repositories.py` (ports & adapters), o que torna a extração futura em serviço independente uma troca de adaptador, não uma reescrita.

**Critério de saída para microsserviços:**
- Volume > 500 conversas simultâneas sustentadas
- Times diferentes precisam fazer deploy independente de módulos
- SLA de um módulo impacta negativamente outro (ex: RAG lento derrubando triagem)

### Justificativa

| Fator | Monólito ✅ | Microsserviços ❌ |
|---|---|---|
| Complexidade operacional | Baixa | Alta (k8s, service mesh, etc.) |
| Latência inter-módulo | In-process (µs) | Rede (ms) |
| Debug e observabilidade | Simples | Requer tracing distribuído robusto |
| Time size | 1-3 devs | 5+ devs |
| Estágio atual | Early product | Escala validada |

---

## 2. Mapa de Módulos (Serviços Lógicos)

Cada módulo é um **pacote Python independente** com sua própria camada de application, sem acoplar diretamente no outro. A comunicação entre módulos é **via domínio + repositório**, nunca chamada direta entre controllers.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INTERFACES LAYER                            │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────────┐  │
│  │  HTTP API    │  │  WhatsApp        │  │   Dashboard/CRM      │  │
│  │  /webhook    │  │  Webhook         │  │   (futuro)           │  │
│  └──────┬───────┘  └────────┬────────┘  └──────────────────────┘  │
└─────────┼───────────────────┼─────────────────────────────────────┘
          │                   │
          ▼                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       APPLICATION LAYER                             │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │            [M1] Orquestrador Conversacional                │    │
│  │         application/conversation_orchestrator.py           │    │
│  │   (coordena todos os outros módulos por mensagem)          │    │
│  └───┬──────────┬────────────┬────────────┬──────────────────┘    │
│      │          │            │            │                         │
│      ▼          ▼            ▼            ▼                         │
│  ┌────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐ ┌─────────────┐  │
│  │[M2]    │ │[M3]    │ │[M4]     │ │[M5]      │ │[M6]         │  │
│  │Leads   │ │Catálogo│ │Conhecim.│ │Follow-up │ │Observab.    │  │
│  │/CRM    │ │/Imóveis│ │/RAG     │ │/Automação│ │/Analytics   │  │
│  └────────┘ └────────┘ └─────────┘ └──────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE LAYER                            │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐  │
│  │PostgreSQL│ │LLM       │ │WhatsApp │ │Vector DB │ │File Stor.│  │
│  │(SQLAlch.)│ │(OpenAI + │ │Cloud API│ │(pgvector)│ │(legado)  │  │
│  │          │ │Anthropic)│ │         │ │          │ │          │  │
│  └──────────┘ └──────────┘ └─────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Responsabilidades de Cada Módulo

### [M1] Orquestrador Conversacional
**Arquivo:** `application/conversation_orchestrator.py`

Responsável por coordenar o fluxo completo de uma mensagem recebida. É o único ponto de entrada de mensagens no sistema.

**Entradas:** `lead_id`, `conversation_id`, `message_text`, `channel`, `trace_id`
**Saídas:** `response_text`, `next_action`, `decision_log`

**Etapas internas:**
1. Busca/cria Lead e Conversation
2. Persiste Message (com deduplicação)
3. Extrai critérios e detecta intenção
4. Atualiza perfil do Lead
5. Calcula score
6. Consulta catálogo (se necessário)
7. Consulta base de conhecimento (se FAQ)
8. Decide próxima ação (NextBestAction)
9. Gera resposta via LLM
10. Persiste DecisionLog
11. Agenda follow-ups (se necessário)
12. Retorna resposta

---

### [M2] Leads / CRM
**Arquivo:** `application/crm.py`

Gerencia o ciclo de vida completo do lead.

**Casos de uso:**
- `QualifyLead` — atualiza perfil e recalcula score
- `AssignToBroker` — encontra melhor corretor e registra assignment
- `UpdateLeadStatus` — muda status (NEW → QUALIFIED → ASSIGNED → etc.)
- `RecordHandoff` — registra handoff para humano com contexto completo
- `GetLeadSummary` — gera resumo executivo do lead para corretor

---

### [M3] Catálogo / Imóveis
**Arquivo:** `application/catalog.py`

Busca e recomenda imóveis com base no perfil do lead.

**Casos de uso:**
- `SearchProperties` — filtros estruturados (cidade, bairro, faixa de preço, tipo)
- `RecommendProperties` — matching semântico perfil ↔ imóvel + ranking
- `ExplainRecommendation` — gera pitch de venda para cada imóvel recomendado
- `IngestProperty` — adiciona/atualiza imóvel no catálogo
- `ArchiveProperty` — remove imóvel do catálogo ativo

---

### [M4] Conhecimento / RAG
**Arquivo:** `application/knowledge.py`

Responde perguntas operacionais usando base de conhecimento da imobiliária.

**Casos de uso:**
- `AnswerOperationalQuestion` — busca em FAQ, políticas, scripts comerciais
- `IngestDocument` — indexa PDF/DOCX/HTML na base de conhecimento
- `CheckGroundedness` — valida se resposta está ancorada no contexto recuperado

---

### [M5] Automações / Follow-up
**Arquivo:** `application/followup.py`

Gerencia o ciclo de follow-ups automáticos.

**Casos de uso:**
- `ScheduleFollowUp` — agenda follow-up baseado em estágio do lead
- `CancelFollowUps` — cancela follow-ups pendentes quando lead responde
- `ExecuteFollowUp` — dispara mensagem de follow-up no canal do lead
- `GetPendingFollowUps` — lista tasks a executar (para o scheduler)

---

### [M6] Observabilidade / Analytics
**Arquivo:** `application/analytics.py`

Centraliza métricas de negócio e produto.

**Casos de uso:**
- `RecordBusinessEvent` — registra evento de produto (lead qualificado, visita, etc.)
- `GetFunnelMetrics` — taxa por estágio do funil
- `GetBrokerPerformance` — métricas por corretor
- `GetAIQualityMetrics` — groundedness, latência, custo LLM

---

## 4. Fluxo Ponta a Ponta (E2E)

```
1. ENTRADA DE MENSAGEM
   └─ WhatsApp Cloud API envia POST /webhook/whatsapp
   └─ Web Chat envia POST /webhook

2. CAMADA DE INTERFACES (interfaces/)
   ├─ TraceMiddleware injeta trace_id, request_id
   ├─ Valida assinatura HMAC (WhatsApp) ou API Key (web)
   └─ Deserializa payload para MessageInput

3. NORMALIZAÇÃO
   ├─ Extrai: lead_phone/session_id, message_text, channel, timestamp
   ├─ Normaliza diferenças entre WhatsApp e Web Chat
   └─ Gera external_message_id para deduplicação

4. PERSISTÊNCIA DO EVENTO BRUTO
   ├─ Salva RawEvent com payload original (para auditoria e replay)
   └─ Persiste Message com external_message_id (idempotência)

5. ORQUESTRAÇÃO (application/conversation_orchestrator.py)
   ├─ Busca Lead por phone/session_id (cria se novo)
   └─ Busca Conversation ativa (cria se nova)
   └─ set_trace_context(lead_id=..., conversation_id=...)

6. CONSULTA A MEMÓRIA
   ├─ Carrega últimas N mensagens da Conversation
   ├─ Carrega LeadPreferences atuais
   └─ Carrega ConversationSummary (para contexto do LLM)

7. EXTRAÇÃO + CLASSIFICAÇÃO
   ├─ Extração regex determinística (campos imobiliários)
   ├─ Classificação de intenção via LLM (DetectedIntent)
   └─ Atualização incremental de LeadPreferences

8. SCORE
   └─ Recalcula LeadScore (completude, urgência, engajamento, compatibilidade)

9. CONSULTA A CATÁLOGO / CONHECIMENTO
   ├─ Se intent = BUY/RENT → SearchProperties + RecommendProperties
   └─ Se intent = FAQ → AnswerOperationalQuestion (RAG)

10. DECISÃO (NextBestAction)
    ├─ Regras determináticas (campo faltante crítico? → perguntar)
    ├─ Score alto? → avaliar handoff
    └─ LLM decide ação final com contexto completo

11. GERAÇÃO DE RESPOSTA
    ├─ LLM gera resposta com tom comercial
    ├─ Quality gate: verifica coerência e guardrails
    └─ Formata para o canal (WhatsApp markdown vs HTML)

12. PERSISTÊNCIA DA DECISÃO
    ├─ Salva DecisionLog (ação, reasoning, model, tokens, latência)
    ├─ Atualiza Lead (status, score, perfil)
    └─ Atualiza Conversation (última mensagem, resumo se necessário)

13. RESPOSTA
    └─ Envia mensagem pelo canal (WhatsApp API ou response HTTP)

14. LOGGING
    ├─ Todos os passos com trace_id, lead_id, conversation_id
    └─ Métricas: latência total, tokens, custo, action tomada

15. AUTOMAÇÕES POSTERIORES (async, fora do request principal)
    ├─ Agenda/cancela follow-ups conforme status do lead
    ├─ Atualiza ConversationSummary se conversa mudou significativamente
    └─ Publica EventEnvelope (ex: "lead.qualified", "handoff.initiated")
```

---

## 5. Contratos de Entrada e Saída dos Módulos

### MessageInput (entrada do orquestrador)
```python
class MessageInput(BaseModel):
    session_id: str           # ID da sessão (phone ou UUID web)
    message_text: str         # Texto da mensagem
    channel: Channel          # whatsapp | web
    external_message_id: str  # ID no canal externo (dedup)
    sender_name: Optional[str]
    trace_id: Optional[str]
    timestamp: datetime
```

### OrchestratorResult (saída do orquestrador)
```python
class OrchestratorResult(BaseModel):
    reply: str                # Resposta a enviar ao lead
    next_action: NextAction   # Ação escolhida
    lead_id: str
    conversation_id: str
    trace_id: str
    human_handoff: bool       # True = deve notificar corretor
    handoff_reason: Optional[HandoffReason]
    lead_score: int
    latency_ms: int
```

---

## 6. Independência de Módulos — Regras

| Regra | Motivo |
|---|---|
| Módulos não se importam diretamente | Evita acoplamento circular |
| Comunicação via entidades do `domain/` | Contratos estáveis |
| Cada módulo usa repositórios via port | Troca de implementação sem reescrita |
| Nenhum módulo acessa banco diretamente | Só via repository |
| Eventos entre módulos via `EventEnvelope` | Preparação para extração futura |

---

## 7. Roadmap de Extração para Microsserviços (V2+)

Quando o volume justificar, a extração segue esta ordem de prioridade:

1. **[M5] Follow-up / Automações** — é naturalmente assíncrono, candidato a worker separado
2. **[M4] RAG / Conhecimento** — latência de embeddings impacta o fluxo principal
3. **[M3] Catálogo** — pode ter API própria para integração com outros sistemas
4. **[M2] CRM** — evoluir para produto próprio quando time comercial crescer
5. **[M1] Orquestrador** — último a extrair, pois depende de todos os outros

---

*Última atualização: 2026-03-30*
*Decisão revisada quando: volume > 500 conversas/dia simultâneas ou time > 3 devs*
