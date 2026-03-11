# Agente Imobiliaria IA

README tecnico completo para operacao, manutencao e evolucao do projeto.

## TL;DR (setup rapido)

### Backend (FastAPI)
```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Vite + React) opcional
```bash
npm install
npm run dev
```

### Docker (app completa)
```bash
copy .env.example .env
docker compose up --build -d
```

App disponivel em:
- `http://localhost:8000`
- Se `WEBHOOK_API_KEY` estiver preenchida no backend, preencha tambem `VITE_BACKEND_API_KEY` no `.env` antes do build do Docker.

### Testes
```bash
python -m pytest -q
```

### Deploy Render (Web Service)
`startCommand` atual:
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## 1. Visao geral do projeto

Este repositorio implementa um **agente de triagem imobiliaria** com foco em conversa via webhook.

Objetivo principal:
- Coletar perfil do lead em formato conversacional.
- Estruturar criterios (cidade, bairro, tipo, quartos, vagas, budget, prazo etc.).
- Classificar lead (score, temperatura, qualidade).
- Aplicar quality gate antes de handoff.
- Rotear para corretor com regras deterministicas.
- Persistir eventos e historico em arquivos JSON/JSONL.

Canais suportados no estado atual:
- `POST /webhook`: fluxo principal do agente (triagem completa com LLM + regras).
- `GET/POST /webhook/whatsapp`: webhook WhatsApp Cloud API.

Importante sobre WhatsApp no estado atual:
- O endpoint `POST /webhook/whatsapp` **ainda nao integra** o `agent.controller.handle_message`.
- Hoje ele extrai mensagem e responde texto fixo (`"Ola! Recebi sua mensagem."`) via `services/whatsapp_sender.py`.

---

## 2. Arquitetura (alto nivel)

### 2.1 Diagrama geral

```text
                        +-----------------------------+
                        | Frontend React (Vite)       |
                        | ChatWidget -> /webhook      |
                        +-------------+---------------+
                                      |
                                      v
+----------------------+      +-------+-----------------------------+
| WhatsApp Cloud API   |----->| FastAPI (main.py)                   |
| (Meta Graph)         |      | - CORS                              |
+----------------------+      | - Rate limit (/webhook 30/min)      |
                              | - API key check (X-API-Key)         |
                              | - Correlation ID                     |
                              +-------+------------------------------+
                                      |
                                      v
                              +-------+------------------------------+
                              | agent/controller.py                  |
                              | - confusion detector                 |
                              | - regex extraction first             |
                              | - 1 call LLM decision (ou fallback)  |
                              | - triage rules + quality gate        |
                              | - lead score + SLA                   |
                              | - router (agente/corretor)           |
                              | - persistence JSON/JSONL             |
                              +--+-----------+-----------+-----------+
                                 |           |           |
                                 v           v           v
                         +-------+--+   +----+----+  +---+-----------------+
                         | agent/llm |   | router  |  | persistence/files   |
                         | Gemini/   |   | rules   |  | leads/events/index  |
                         | OpenAI/   |   |         |  | routing_log/stats   |
                         | Groq      |   +---------+  +---------------------+
                         +-----------+
```

### 2.2 Fluxo fim-a-fim: `POST /webhook`

Ordem real executada em `agent/controller.py`:

1. Carrega/cria sessao em memoria (`agent.state.store`).
2. Aplica reset heuristico da sessao (stale ou nova conversa apos conclusao).
3. Registra turno e historico da mensagem.
4. Detecta confusao e pode responder esclarecimento imediatamente (`agent.confusion_detector`).
5. **Extract-first**:
- heuristica para respostas curtas (sim/nao, suites, banheiros etc.).
- extracao regex deterministica (`agent.extractor.enrich_with_regex`).
- normalizacao/override de cidade e intent.
- aplica updates no estado (`SessionState.apply_updates`).
6. Decide proxima acao com `agent.ai_agent.decide`:
- tenta `agent.llm.llm_decide` (maximo 1 chamada LLM por mensagem).
- fallback deterministico se LLM indisponivel/disabled/rate-limited.
7. Atualiza score do lead (`agent.scoring.compute_lead_score`).
8. Atualiza quality score (`agent.quality.compute_quality_score`).
9. Se handoff imediato por regra/LLM -> mensagem de handoff.
10. Em `TRIAGE_ONLY=true`:
- resolve conflitos.
- trata FAQ.
- pergunta proxima lacuna critica (`agent.rules`).
- aplica quality gate (`agent.quality_gate`).
- exige nome e telefone antes de concluir.
- classifica SLA (`agent.sla`).
- roteia corretor (`agent.router.route_lead`).
- persiste (leads/eventos/indice) (`agent.persistence`).
- retorna resumo final humanizado (`agent.presenter`).
11. Em `TRIAGE_ONLY=false`, fluxo "normal" (SEARCH/LIST etc.) continua disponivel.

### 2.3 Fluxo WhatsApp (`/webhook/whatsapp`)

`routes/whatsapp.py`:

1. Le body bruto.
2. Valida assinatura `X-Hub-Signature-256` se `WHATSAPP_APP_SECRET` estiver definido.
3. Parse JSON do evento.
4. Extrai mensagem texto (`services.whatsapp_sender.extract_message_from_webhook`).
5. Tenta enviar resposta fixa com `send_whatsapp_message`.
6. Retorna `{"ok": true}`.

---
## 3. Inventario do repositorio (pasta por pasta)

### 3.1 Estrutura principal

```text
.
├─ agent/                 # Nucleo de negocio conversacional
├─ app/                   # Bridge de compatibilidade app.*
├─ core/                  # Configuracao e logging
├─ routes/                # Rotas FastAPI extras (WhatsApp)
├─ services/              # Integracoes externas (envio WhatsApp)
├─ data/                  # Dados de dominio + persistencia local
├─ src/                   # Frontend React + Vite
├─ public/                # Assets estaticos frontend
├─ main.py                # Entry point backend em uso no Render
├─ app/main.py            # Entry point alternativo (compat)
├─ requirements.txt       # Dependencias Python
├─ package.json           # Dependencias/scripts frontend
├─ render.yaml            # Config do Render Web Service
├─ runtime.txt            # Pin Python local/plataforma (3.11.9)
├─ .env.example           # Exemplo completo de configuracao
├─ frontend.py            # Cliente CLI para conversar com /webhook
└─ test_*.py              # Suite extensa de testes (raiz)
```

### 3.2 Mapa detalhado de modulos backend

#### `main.py` (entrypoint principal)
- O que faz:
  - Inicializa FastAPI, CORS, rate limit, logging, rotas.
  - Exponibiliza `GET /health` e `POST /webhook`.
  - Inclui router WhatsApp (`routes.whatsapp`).
  - Monta `dist/` como estatico em `/` **se a pasta existir**.
- Principais funcoes/classes:
  - `WebhookRequest` (Pydantic).
  - `verify_api_key` (header `X-API-Key`).
  - `health`.
  - `webhook`.
- Entrada/Saida:
  - Entrada JSON `{session_id, message, name?}`.
  - Saida JSON `{"reply": "..."}`.
- Dependencias:
  - `agent.controller.handle_message`.
  - `slowapi`, `dotenv`, `core.config/settings`.
- ENV usada:
  - `FRONTEND_ORIGINS`, `PORT`, `WEBHOOK_API_KEY`, `LOG_LEVEL`, `APP_ENV`, WhatsApp envs.

#### `app/main.py` (entrypoint alternativo)
- O que faz:
  - Mesma API base, mas com `GET /` retornando HTML status page.
  - Imports via namespace `app.*`.
- Observacao:
  - `render.yaml` atual usa `main:app`, nao `app.main:app`.

#### `core/config.py`
- O que faz:
  - Centraliza leitura de envs da aplicacao.
  - Valida configuracao WhatsApp em startup.
- Classe:
  - `Settings`.
- Metodo chave:
  - `validate_whatsapp_config()` -> lista warnings/errors.

#### `core/logging.py`
- O que faz:
  - Configura logger global.
  - Sanitiza segredos em mensagens e args (tokens, secrets, authorization etc.).
- Classe:
  - `SanitizingFormatter`.
- Funcao:
  - `setup_logging()`.

#### `routes/whatsapp.py`
- O que faz:
  - Webhook GET/POST para WhatsApp Cloud API.
- Funcoes:
  - `verify_signature` (HMAC SHA256).
  - `whatsapp_verify` (`GET /webhook/whatsapp`).
  - `whatsapp_webhook` (`POST /webhook/whatsapp`).
- Dependencias:
  - `core.config.settings`, `services.whatsapp_sender`.

#### `services/whatsapp_sender.py`
- O que faz:
  - Envia mensagem para Graph API (`v21.0`).
  - Extrai mensagem texto de payload WhatsApp.
- Funcoes:
  - `send_whatsapp_message` (async).
  - `extract_message_from_webhook`.
- Comportamento importante:
  - Se `DISABLE_WHATSAPP_SEND=true`, nao envia de fato (modo teste).

#### `faq.py`
- O que faz:
  - Detecta intencao de FAQ e responde sem quebrar funil de triagem.
- Elementos:
  - `FAQIntent` enum.
  - `detect_faq_intent`.
  - `answer_faq`.

#### `frontend.py`
- O que faz:
  - Cliente CLI para testar conversa com o backend sem navegador.
- Funcoes:
  - `send_message`.
  - `run_cli`.

### 3.3 Mapa detalhado `agent/` (arquivo por arquivo)

#### `agent/state.py`
- Responsabilidade:
  - Modelo de sessao em memoria (`SessionState`) + normalizacao + detecao de conflitos.
- Classes principais:
  - `LeadCriteria`, `LeadScore`, `SessionState`, `InMemoryStore`.
- Entradas/Saidas:
  - Entrada: updates extraidos/LLM.
  - Saida: estado publico e conflitos detectados.
- Dependencias:
  - Sem dependencias externas alem stdlib.
- ENV:
  - Nao le env diretamente.

#### `agent/controller.py`
- Responsabilidade:
  - Orquestrador principal do fluxo conversacional.
- Funcao principal:
  - `handle_message(session_id, message, name, correlation_id)`.
- Dependencias internas:
  - `ai_agent`, `extractor`, `rules`, `quality`, `quality_gate`, `sla`, `router`, `persistence`, `presenter`, `faq`.
- Entradas/Saidas:
  - Entrada: texto do usuario + estado.
  - Saida: dict com `reply`, `state`, e em fluxo final `summary/handoff`.
- ENV indireta:
  - Depende de flags lidas por outros modulos (`TRIAGE_ONLY`, `USE_LLM`, etc.).

#### `agent/ai_agent.py`
- Responsabilidade:
  - Facade do agente de IA e decisao unificada.
- Classe:
  - `RealEstateAIAgent`.
- Metodo chave:
  - `decide(...)` -> chama `llm.llm_decide`.

#### `agent/llm.py`
- Responsabilidade:
  - Integracao multi-provider + cache + retry + rate-limit local + degraded mode (circuit breaker).
- Funcoes principais:
  - `call_llm`, `llm_decide`, `_get_fallback_decision`, `prewarm_llm`, `normalize_llm_error`.
- Provider order:
  - `GEMINI_API_KEY` -> Gemini native.
  - `OPENAI_API_KEY` -> OpenAI/OpenRouter (ou Gemini compat se base_url apontar para Google).
  - `GROQ_API_KEY` -> Groq.
  - Nenhuma chave -> fallback deterministico.
- Guardrails:
  - Em triagem, bloqueia SEARCH/LIST quando nao permitido.
  - Cache TTL 300s para mesma mensagem + estado.
  - Circuit breaker por sessao para erros transitorios.

#### `agent/extractor.py`
- Responsabilidade:
  - Extracao deterministica regex/heuristica de criterios.
- Destaques:
  - Parser de budget com suporte a range (`budget_min`/`budget_max`).
  - Detecta cidade/bairro/tipo/quartos/vagas/pet/mobiliado/proximidade praia etc.

#### `agent/rules.py`
- Responsabilidade:
  - Ordem de campos criticos, banco de perguntas e politica de proxima pergunta.
- Campos criticos:
  - Inclui `suites`, `bathrooms_min`, `micro_location`, `leisure_required`, `lead_name`, `lead_phone`.
- ENV:
  - `TRIAGE_ONLY`, `QUESTION_SEED`.

#### `agent/confusion_detector.py`
- Responsabilidade:
  - Detecta pedido de esclarecimento e gera respostas explicativas.
- Mecanismo anti-loop:
  - Apos repeticoes, oferece opcoes estruturadas para o campo.

#### `agent/scoring.py`
- Responsabilidade:
  - Calcula `lead_score` (0-100) e temperatura (`hot/warm/cold`).

#### `agent/quality.py`
- Responsabilidade:
  - Calcula qualidade do lead (`score`, `grade A-D`, completude, confianca).

#### `agent/quality_gate.py`
- Responsabilidade:
  - Decide se pode handoff ou se precisa de mais perguntas cirurgicas.
- Regras:
  - Maximo 3 turnos extras de quality gate.

#### `agent/sla.py`
- Responsabilidade:
  - Classificacao SLA (`HOT/WARM/COLD`) e acao (`immediate/normal/nurture`).
- ENV:
  - `SLA_HOT_THRESHOLD`, `SLA_WARM_THRESHOLD`.

#### `agent/router.py`
- Responsabilidade:
  - Roteamento deterministico para corretor.
- Inputs:
  - `data/agents.json`, `data/agent_stats.json`, estado do lead.
- Output:
  - `RoutingResult`.
- Persistencia extra:
  - Log JSONL de roteamento (`ROUTING_LOG_PATH`).
- ENV:
  - `EXPOSE_AGENT_CONTACT`, `ROUTING_LOG_PATH`.

#### `agent/presenter.py`
- Responsabilidade:
  - Formatar resposta final e payload de resumo.
- Observacao:
  - Numero de contato no texto final e **ficticio estavel**, nao o real.

#### `agent/persistence.py`
- Responsabilidade:
  - Persistir leads, indice por nome e eventos em JSON/JSONL.
- Paths dinamicos:
  - Prefere `/mnt/data/...` se existir (ambiente com disco montado), senao `data/...`.
- ENV:
  - `LEADS_LOG_PATH`, `LEADS_INDEX_PATH`, `EVENTS_PATH`, `PERSIST_RAW_TEXT`.

#### `agent/tools.py`
- Responsabilidade:
  - Carregar base de imoveis (`data/properties.json`) e fazer busca filtrada.

#### `agent/followup.py`
- Responsabilidade:
  - Encontrar leads para nutricao e registrar follow-up enviado.
- ENV:
  - `FOLLOWUP_META_PATH`.

#### `agent/intent.py`
- Responsabilidade:
  - Classificador simples de intencao por palavras-chave (fallback).

#### `agent/dialogue.py`
- Responsabilidade:
  - Estrutura `Plan` e validacao/sanitizacao do plano de acao.

#### `agent/prompts.py`
- Responsabilidade:
  - Prompts completos e prompt unificado para decisao.

#### `agent/unified_llm.py`
- Responsabilidade:
  - Implementacao alternativa antiga de decisao unificada.
- Observacao:
  - Fluxo atual usa `agent.llm.llm_decide`; este arquivo permanece como legado/utilitario.

### 3.4 Namespace bridge `app/`

Arquivos:
- `app/__init__.py`
- `app/agent/__init__.py`
- `app/core/__init__.py`
- `app/routes/__init__.py`
- `app/services/__init__.py`
- `app/faq.py`

Papel:
- Manter compatibilidade de imports `app.*` apontando para modulos da raiz.

### 3.5 Frontend `src/`

Arquivos-chave:
- `src/main.tsx`: bootstrap React.
- `src/App.tsx`: router principal (`/` e fallback 404).
- `src/pages/Index.tsx`: monta landing page + `ChatWidget`.
- `src/components/ChatWidget.tsx`:
  - envia `POST ${VITE_BACKEND_URL}/webhook`.
  - envia `X-API-Key` se `VITE_BACKEND_API_KEY` definido.
- `src/components/ui/*`: componentes UI genericos (Radix/shadcn).

### 3.6 Dados em `data/`

Arquivos-chave:
- `properties.json`: catalogo de imoveis (campos como `id`, `titulo`, `cidade`, `bairro`, `preco_venda`, `preco_aluguel` etc.).
- `agents.json`: cadastro de corretores e capacidades.
- `agent_stats.json`: contadores diarios de atribuicao.
- `leads.jsonl`: historico append-only de leads.
- `leads_index.json`: indice nome -> lead_ids.
- `events.jsonl`: eventos (inclui HOT_LEAD).
- `routing_log.jsonl`: eventos de roteamento.

### 3.7 Testes

- Suite Python na raiz com padrao `test_*.py`.
- `pytest.ini` configura descoberta.
- Coleta atual: **215 testes** (`pytest --collect-only`).
- Cobertura por tema (arquivos principais):
  - `test_flow.py`, `test_triage_*`, `test_quality_*`, `test_router*`, `test_sla.py`, `test_degraded_mode.py`, `test_endpoints.py`, `test_whatsapp_flow.py`, `test_confusion_handling.py`.

---

## 4. Stack e dependencias

### 4.1 Backend

- Linguagem: Python.
- Runtime pinado em arquivos:
  - `runtime.txt`: `python-3.11.9`.
  - `render.yaml`: `pythonVersion: "3.12.3"`.

Observacao importante:
- Ha **mismatch de versao** entre `runtime.txt` e `render.yaml`.
- Recomenda-se padronizar para evitar diferencas de comportamento.

Dependencias (`requirements.txt`):
- `fastapi==0.115.0`
- `uvicorn[standard]==0.32.0`
- `pydantic==2.10.0`
- `python-dotenv==1.0.1`
- `slowapi==0.1.9`
- `openai==1.58.1`
- `google-genai>=1.20.0`
- `requests>=2.32.0`
- `pytest==8.3.0`

### 4.2 Frontend

- React 18 + TypeScript + Vite 5.
- UI stack: Tailwind + componentes shadcn/Radix.
- Scripts em `package.json`:
  - `npm run dev`
  - `npm run build`
  - `npm run test` (Vitest)
  - `npm run lint`

### 4.3 Integracoes externas

- LLM:
  - Google Gemini (SDK nativo `google-genai`) quando `GEMINI_API_KEY`.
  - OpenAI/OpenRouter quando `OPENAI_API_KEY`.
  - Groq quando `GROQ_API_KEY`.
- WhatsApp:
  - WhatsApp Cloud API via Meta Graph (`https://graph.facebook.com/v21.0/...`).
- Banco/fila/cache gerenciado externo:
  - Nao ha banco SQL/NoSQL dedicado.
  - Nao ha fila dedicada.
  - Cache de LLM e em memoria de processo.
- RAG:
  - Nao implementado hoje.

### 4.4 Gerenciamento de dependencias

- Python: `pip + requirements.txt`.
- Frontend: `npm + package-lock.json`.
- Nao ha Poetry/Pipenv/pip-tools.

---
## 5. Configuracao e Variaveis de Ambiente

### 5.1 Como o projeto carrega env

- `main.py` e `app/main.py` chamam `load_dotenv(override=True)`.
- `agent/llm.py` tambem chama `load_dotenv(override=True)`.

Impacto:
- Se existir arquivo `.env` no ambiente, seus valores podem sobrescrever envs ja setadas no processo.

### 5.2 Tabela completa de envs

| Variavel | Obrigatoria | Exemplo (sem segredo) | Onde e usada | Impacto se ausente |
|---|---|---|---|---|
| `APP_ENV` | nao | `development` | `core/config.py -> Settings.APP_ENV` | default `production` |
| `LOG_LEVEL` | nao | `INFO` | `core/config.py`, `core/logging.py` | default `INFO` |
| `PORT` | nao (Render injeta) | `8000` | `main.py`, `app/main.py`, `core/config.py` | default `8000` |
| `FRONTEND_ORIGINS` | nao | `https://frontend.exemplo.com` | `main.py`, `app/main.py` (CORS) | usa allowlist localhost |
| `WEBHOOK_API_KEY` | recomendado | `hex_64_chars` | `main.py verify_api_key`, `frontend.py` | `/webhook` fica sem autenticacao por header |
| `DISABLE_WHATSAPP_SEND` | nao | `true` | `core/config.py`, `services/whatsapp_sender.py` | default `true` (modo teste) |
| `WHATSAPP_VERIFY_TOKEN` | sim para validar GET do webhook Meta | `token_verificacao` | `core/config.py`, `routes/whatsapp.py` | `GET /webhook/whatsapp` retorna erro 500 |
| `WHATSAPP_APP_SECRET` | recomendado em prod | `app_secret` | `core/config.py`, `routes/whatsapp.verify_signature` | assinatura nao e validada |
| `WHATSAPP_ACCESS_TOKEN` | sim se envio real WhatsApp | `EAAX...` | `core/config.py`, `services/whatsapp_sender.py` | sem envio real (`WhatsAppSendError`) |
| `WHATSAPP_PHONE_NUMBER_ID` | sim se envio real WhatsApp | `1234567890` | `core/config.py`, `services/whatsapp_sender.py` | sem envio real |
| `USE_LLM` | nao | `true` | `agent/llm.py`, `agent/unified_llm.py` | fallback deterministico |
| `TRIAGE_ONLY` | nao | `true` | `agent/llm.py`, `agent/rules.py` | default `false` no codigo |
| `LLM_TIMEOUT` | nao | `120` | `agent/llm.py` | default dinamico (30 remoto / 120 local) |
| `GEMINI_API_KEY` | sim se usar Gemini | `AIza...` | `agent/llm.py` | pula provider Gemini |
| `GEMINI_MODEL` | nao | `gemini-2.5-flash` | `agent/llm.py` | default `gemini-2.5-flash` |
| `OPENAI_API_KEY` | sim se usar OpenAI/OpenRouter | `sk-...` | `agent/llm.py` | pula provider OpenAI |
| `OPENAI_MODEL` | nao | `gpt-4o-mini` | `agent/llm.py` | default `gpt-4o-mini` |
| `OPENAI_BASE_URL` | nao | `https://api.openai.com/v1` | `agent/llm.py` | default OpenAI oficial |
| `GROQ_API_KEY` | sim se usar Groq | `gsk_...` | `agent/llm.py` | pula provider Groq |
| `GROQ_MODEL` | nao | `llama-3.3-70b-versatile` | `agent/llm.py` | default do codigo |
| `GROQ_BASE_URL` | nao | `https://api.groq.com/openai/v1` | `agent/llm.py` | default do codigo |
| `LLM_KEEP_ALIVE` | nao | `5m` | `agent/llm.py` (extra body local) | ignorado |
| `LLM_NUM_CTX` | nao | `8192` | `agent/llm.py` | default `0` |
| `LLM_NUM_THREADS` | nao | `8` | `agent/llm.py` | default `0` |
| `LLM_USE_MMAP` | nao | `true` | `agent/llm.py` | default `true` |
| `LLM_PREWARM` | nao | `false` | `agent/llm.py` | default `false` |
| `LEADS_LOG_PATH` | nao | `data/leads.jsonl` | `agent/persistence.py` | default `/mnt/data` se existir, senao `data/leads.jsonl` |
| `LEADS_INDEX_PATH` | nao | `data/leads_index.json` | `agent/persistence.py` | default dinamico |
| `EVENTS_PATH` | nao | `data/events.jsonl` | `agent/persistence.py` | default dinamico |
| `PERSIST_RAW_TEXT` | nao | `false` | `agent/persistence.py` | remove `raw_text` por padrao |
| `ROUTING_LOG_PATH` | nao | `data/routing_log.jsonl` | `agent/router.py` | default dinamico |
| `FOLLOWUP_META_PATH` | nao | `data/followups.jsonl` | `agent/followup.py` | default `data/followups.jsonl` |
| `EXPOSE_AGENT_CONTACT` | nao | `false` | `agent/router.py`, `agent/tools.py` | contato real nao exposto |
| `QUESTION_SEED` | nao | `seed123` | `agent/rules.py` | usa `default` |
| `SLA_HOT_THRESHOLD` | nao | `80` | `agent/sla.py` | default `80` |
| `SLA_WARM_THRESHOLD` | nao | `50` | `agent/sla.py` | default `50` |
| `BACKEND_URL` | nao (CLI local) | `http://localhost:8000` | `frontend.py` | default localhost |
| `VITE_BACKEND_URL` | sim para frontend separado | `https://api.exemplo.com` | `src/components/ChatWidget.tsx` | vira `""` e usa path relativo |
| `VITE_BACKEND_API_KEY` | opcional | `mesmo_valor_WEBHOOK_API_KEY` | `src/components/ChatWidget.tsx` | sem header `X-API-Key` |

### 5.3 Arquivo `.env.example`

O repositorio contem `.env.example` atualizado com **todas** as variaveis acima.

---
## 6. Endpoints e contratos

### 6.1 `GET /health`

- Auth: nenhuma.
- Uso: healthcheck.
- Resposta 200:
```json
{
  "status": "ok",
  "timestamp": "2026-03-04T12:34:56.123456"
}
```

### 6.2 `POST /webhook`

- Auth:
  - Se `WEBHOOK_API_KEY` estiver configurada, exige header `X-API-Key` valido.
  - Se nao estiver configurada, endpoint aceita sem auth e loga warning.
- Rate limit:
  - `30/minute` por IP (`slowapi`).
- Body JSON:
```json
{
  "session_id": "lead-001",
  "message": "quero comprar apartamento em Manaira",
  "name": "Maria"
}
```
- Validacoes:
  - `session_id`: 1..128 chars
  - `message`: 1..5000 chars
  - `name` opcional: max 128
- Resposta 200 tipica:
```json
{
  "reply": "...texto do assistente..."
}
```
- Status relevantes:
  - `200`: sucesso
  - `401`: API key invalida/ausente (quando obrigatoria)
  - `422`: body invalido
  - `429`: rate limit

### 6.3 `GET /webhook/whatsapp`

- Auth:
  - Token via query (`hub.verify_token`) comparado com `WHATSAPP_VERIFY_TOKEN`.
- Query esperada (Meta):
  - `hub.mode`
  - `hub.verify_token`
  - `hub.challenge`
- Respostas:
  - `200` com texto do `hub.challenge` se validado.
  - `403` se token invalido.
  - `500` se `WHATSAPP_VERIFY_TOKEN` nao configurado.

### 6.4 `POST /webhook/whatsapp`

- Auth:
  - Assinatura `X-Hub-Signature-256` validada **somente** se `WHATSAPP_APP_SECRET` configurado.
- Body:
  - Payload padrao WhatsApp Cloud API.
- Comportamento atual:
  - Extrai texto e envia resposta fixa via Graph API (ou modo teste).
- Respostas:
  - `200` `{ "ok": true }`
  - `400` payload invalido
  - `403` assinatura invalida

### 6.5 Endpoints automaticos FastAPI

- `GET /docs`
- `GET /openapi.json`

---

## 7. Execucao local (zero to hero)

### 7.1 Pre-requisitos

- Python 3.11+ (idealmente alinhar com versao de deploy).
- Node 18+ para frontend.
- Chave de um provider LLM (Gemini/OpenAI/Groq) para fluxo com IA.

### 7.2 Backend local

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edite `.env` com pelo menos:
- `USE_LLM=true`
- `TRIAGE_ONLY=true`
- um provider (`GEMINI_API_KEY`, ou OpenAI, ou Groq)

Subir API:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 7.3 Frontend local (opcional)

```bash
npm install
npm run dev
```

Configure para frontend:
- `VITE_BACKEND_URL=http://localhost:8000`
- `VITE_BACKEND_API_KEY=<mesmo WEBHOOK_API_KEY se aplicavel>`

### 7.4 Servir frontend via backend (modo single service)

`main.py` monta `dist/` em `/` se existir.

Build frontend:
```bash
npm run build
```

Depois rode backend (`uvicorn main:app ...`) e acesse `http://localhost:8000`.

Observacao:
- Sem `dist/`, o backend nao expoe landing page em `/` (apenas API).

### 7.5 Testes

Rodar suite:
```bash
python -m pytest -q
```

Coleta apenas (rapido):
```bash
python -m pytest --collect-only -q
```

### 7.6 Simulacao por `curl`

#### Health
```bash
curl -X GET http://localhost:8000/health
```

#### Webhook principal sem API key
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"lead-001\",\"message\":\"quero comprar apartamento em Manaira\",\"name\":\"Maria\"}"
```

#### Webhook principal com API key
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: SEU_TOKEN" \
  -d "{\"session_id\":\"lead-001\",\"message\":\"procuro apto 3 quartos em Joao Pessoa\"}"
```

Resposta esperada (exemplo):
```json
{
  "reply": "...pergunta de triagem ou resumo final..."
}
```

#### Verificacao WhatsApp (GET)
```bash
curl "http://localhost:8000/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=TOKEN&hub.challenge=12345"
```

---
## 8. Deploy no Render (producao)

### 8.1 Estado atual do repo (`render.yaml`)

```yaml
services:
  - type: web
    name: agente-imobiliaria
    runtime: python
    pythonVersion: "3.12.3"
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Observacoes operacionais

- O app le `PORT` e o comando usa `$PORT` (correto para Render).
- Build atual instala apenas Python deps.
- Se quiser servir frontend por `main.py` (montagem de `dist/`), o build precisa gerar `dist`.

### 8.2 Passo a passo de deploy

1. Criar Web Service no Render apontando para este repo.
2. Confirmar:
- Runtime Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Preencher env vars (minimo recomendado):
- `APP_ENV=production`
- `LOG_LEVEL=INFO`
- `USE_LLM=true`
- `TRIAGE_ONLY=true`
- `GEMINI_API_KEY=...` (ou provider equivalente)
- `DISABLE_WHATSAPP_SEND=true` (se so teste)
- `WEBHOOK_API_KEY=<token forte>`
- `FRONTEND_ORIGINS=https://seu-frontend.onrender.com` (se frontend separado)
4. Deploy.
5. Validar:
- `GET /health`
- `POST /webhook`

### 8.3 Redeploy

- Via painel Render: `Manual Deploy -> Deploy latest commit`.
- A cada alteracao de env, Render reinicia servico automaticamente.

### 8.4 Logs e eventos no Render

- Use aba `Logs` para acompanhar startup e requests.
- Procure por marcadores:
  - `Application started`
  - `USER` / `AGENT`
  - `LEAD`, `QUAL`, `SLA`
  - `DEGRADED_MODE`
  - `ROUTER`

---

## 9. Observabilidade, debug e troubleshooting

### 9.1 Logs

Origem:
- `core/logging.py` configura logger raiz.

Formato:
- `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

Sanitizacao:
- Remove padroes de token/secret em strings e dicts.

Correlation:
- `main.py` gera `correlation_id` por request `/webhook`.
- Esse id e passado ao controller e aparece em logs relevantes.

### 9.2 Artefatos de observabilidade em disco

- `data/leads.jsonl`
- `data/leads_index.json`
- `data/events.jsonl`
- `data/routing_log.jsonl`
- `data/agent_stats.json`

### 9.3 Playbook de problemas comuns

| Sintoma | Causa provavel | Acao recomendada |
|---|---|---|
| `401` em `/webhook` | `WEBHOOK_API_KEY` setada e header ausente/invalido | enviar header `X-API-Key` correto |
| `429 Too Many Requests` | limite `30/minute` por IP | reduzir burst, aguardar janela |
| `/webhook/whatsapp` retorna `500` no GET | `WHATSAPP_VERIFY_TOKEN` nao setado | configurar token |
| `/webhook/whatsapp` retorna `403` no POST | assinatura invalida com secret setado | validar `X-Hub-Signature-256` |
| Agente caiu em fallback | sem API key, rate limit, timeout ou erro provider | revisar `GEMINI/OPENAI/GROQ` envs e logs `LLM_ERROR` |
| "DEGRADED_MODE" ativo | erro transitorio LLM acionou circuit breaker | aguardar cooldown; validar provider |
| Sem frontend em `/` | `dist/` inexistente no servidor | gerar build frontend ou usar service separado |
| WhatsApp nao envia mensagem | `DISABLE_WHATSAPP_SEND=true` ou token/phone id ausentes | ajustar envs de envio |

### 9.4 Como ativar debug

- Definir `LOG_LEVEL=DEBUG`.
- Em debug, webhook WhatsApp loga payload (sanitizado).

---

## 10. Seguranca

### 10.1 Estado atual

- `POST /webhook`:
  - Protecao por API key opcional (`WEBHOOK_API_KEY`).
  - Se nao setada, endpoint fica aberto.
- `POST /webhook/whatsapp`:
  - Valida assinatura **apenas** se `WHATSAPP_APP_SECRET` definido.
  - Sem secret, aceita payload sem assinatura.
- Rate limiting:
  - Ativo apenas em `/webhook` (`30/minute` por IP).
- Logs:
  - Sanitizacao basica de segredos implementada.

### 10.2 Recomendacoes de hardening

1. Tornar `WEBHOOK_API_KEY` obrigatoria em producao.
2. Tornar `WHATSAPP_APP_SECRET` obrigatorio em producao.
3. Exigir assinatura valida sempre no endpoint WhatsApp.
4. Implementar idempotencia por `message_id` WhatsApp (evitar duplicatas).
5. Criar allowlist por origem/IP quando aplicavel.
6. Aumentar validacao estrita de payload (schema Pydantic para WhatsApp).
7. Separar segredo frontend/backend (nao expor token sensivel no browser).
8. Persistir sessoes em store externo (evitar perda em restart e escalabilidade).

---
## 11. Fluxos de negocio e pontos de falha

### 11.1 FAQ vs funil

- `faq.detect_faq_intent` pode responder pergunta pontual.
- Se ainda faltam campos criticos, controller emenda proxima pergunta do funil.

### 11.2 Conflitos de informacao

- `SessionState.apply_updates` detecta contradicoes em campos confirmados.
- Controller pede confirmacao explicita antes de continuar.

### 11.3 Fallback e degradacao LLM

- Sem chave ou `USE_LLM=false` -> fallback deterministico.
- Rate limit/problemas transitorios -> fallback + circuito degradado por sessao.

### 11.4 Persistencia e memoria

- Sessao de conversa em memoria (`InMemoryStore`): perde em restart.
- Leads/eventos ficam em arquivo (JSON/JSONL).

---

## 12. Faltando implementar (issues tecnicas abertas)

1. Integrar `POST /webhook/whatsapp` ao fluxo real de triagem (`handle_message`), com session_id por numero e resposta contextual.
2. Padronizar entrypoint unico (`main.py` vs `app/main.py`) para reduzir ambiguidade.
3. Padronizar versao Python (`runtime.txt` vs `render.yaml`).
4. Substituir `@app.on_event("startup")` por lifespan FastAPI (deprecado).
5. Definir estrategia oficial de build frontend no deploy (single service com `dist` ou service separado).

---

## 13. Proximas melhorias (backlog priorizado)

### 13.1 Alta prioridade

1. WhatsApp E2E real (entrada -> controller -> resposta)
- Esforco: 2-4 dias.
- Entrega: substituir resposta fixa por fluxo de triagem completo.

2. Persistencia de sessao em Redis/Postgres
- Esforco: 3-5 dias.
- Entrega: sessao sobrevive restart e escala horizontal.

3. Hardening de seguranca em producao
- Esforco: 1-2 dias.
- Entrega: assinatura obrigatoria, API key obrigatoria, payload schema forte.

4. Build/deploy frontend definido
- Esforco: 0.5-1 dia.
- Entrega: pipeline unica clara (ou separar static site).

### 13.2 Media prioridade

1. Tracing (OpenTelemetry)
- Esforco: 2-3 dias.
- Entrega: spans por request e por chamada LLM.

2. Fila para envio WhatsApp
- Esforco: 3-6 dias.
- Entrega: resiliencia, retry assinc, desacoplamento.

3. Idempotencia de mensagens WhatsApp
- Esforco: 1-2 dias.
- Entrega: evitar respostas duplicadas por reentrega webhook.

4. Testes de contrato API (OpenAPI snapshot)
- Esforco: 1-2 dias.
- Entrega: regressao de schema detectada cedo.

### 13.3 Baixa prioridade

1. Painel admin de leads e handoff
- Esforco: 1-2 semanas.

2. Exportacao BI (CSV/Parquet)
- Esforco: 2-4 dias.

3. Feature flags formais (ex.: LaunchDarkly/OpenFeature)
- Esforco: 2-3 dias.

### 13.4 Divida tecnica identificada

- Duplicidade de entrypoints (`main.py` e `app/main.py`).
- Mismatch de versao Python em arquivos de deploy/runtime.
- Estado de conversa apenas em memoria.
- `agent/unified_llm.py` legado paralelo ao fluxo atual.
- Endpoint WhatsApp ainda sem uso do motor principal de triagem.

### 13.5 Ideias de evolucao

1. RAG para FAQ e politicas comerciais (base documental versionada).
2. Memoria conversacional longa por lead (estado persistente e contexto resumido).
3. Testes automatizados de conversa com cenarios gerados (LLM-as-judge com guardrails).
4. Observabilidade avancada (OpenTelemetry + dashboard + alertas).
5. Filas/event streaming para handoff e notificacoes.
6. Painel para corretor aceitar/recusar lead e medir SLA real.

---

## 14. Comandos uteis de operacao

```bash
# backend dev
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# backend entrypoint alternativo
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# testes
python -m pytest -q

# coletar testes
python -m pytest --collect-only -q

# frontend dev
npm run dev

# frontend build
npm run build

# frontend lint
npm run lint
```

---

## 15. Como funciona o roteamento (triage vs QA)

### 15.1 Fluxo de roteamento de cada mensagem

```
mensagem do usuario
        |
        v
[1] confusion_detector  → se confusao detectada: responde esclarecimento e retorna
        |
        v
[2] extract-first (regex deterministico)
    - _short_reply_updates: interpreta "2", "sim", "não" via pending_slot
    - enrich_with_regex: detecta quartos, suites, vagas, budget, lazer, temporada etc.
    - aplica updates ao estado (confirmed)
        |
        v
[3] LLM decision (ou fallback deterministico)
    - maximo 1 chamada por mensagem
    - se JSON truncado/invalido → repair ou fallback vazio → funil continua
        |
        v
[4] Triage mode (TRIAGE_ONLY=true)
    ├─ conflito de campos? → pergunta de desambiguacao
    ├─ FAQ detectado?      → responde + "Agora, pra eu te indicar: <proxima pergunta>"
    ├─ QA interrupt?       → responde curto + retorna ao funil com pending_slot
    ├─ campos criticos faltantes? → proxima pergunta (CRITICAL_ORDER)
    ├─ quality gate?       → pergunta cirurgica de gap
    ├─ nome faltando?      → pede nome
    ├─ telefone faltando?  → pede telefone
    └─ tudo completo?      → SLA + routing + summary humanizado + handoff
```

### 15.2 pending_slot e respostas curtas

Ao fazer uma pergunta, o controller seta sempre:
- `state.last_question_key` — nome do campo perguntado
- `state.pending_field` — idem (alias para clareza)
- `state.field_ask_count[key]` — contador para detectar confusao

Na proxima mensagem, `_short_reply_updates()` interpreta a resposta no contexto do slot pendente:
- "2" → se pending=bathrooms_min → bathrooms_min=2 (confirmed)
- "sim" → se pending=leisure_required → leisure_required=yes (confirmed)
- "tanto faz" → qualquer campo → value=indifferent (confirmed)

### 15.3 QA interrupt e retorno ao funil

Detectado quando:
- mensagem contem `?`, OU
- comeca com palavra interrogativa ("como", "quanto", "aceita", "tem", "pode"...)

Comportamento:
1. Tenta FAQ lookup (`faq.detect_faq_intent`)
2. Tenta resposta generica curta (`_qa_answer_generic`)
3. Retorna ao funil: `<resposta>\n\nAgora, pra eu te indicar opcoes certas: <proxima pergunta>`
4. Seta `pending_field` para a proxima pergunta feita

---

## 16. Campos do estado (SessionState / LeadCriteria)

### 16.1 Campos criticos (CRITICAL_ORDER)

| Campo | Tipo | Valores | Descricao |
|-------|------|---------|-----------|
| `intent` | str | `comprar`, `alugar` | Intencao do lead |
| `city` | str | livre | Cidade buscada |
| `neighborhood` | str | livre | Bairro preferido |
| `property_type` | str | `apartamento`, `casa`, `cobertura`, `studio`, `flat`, `kitnet`, `terreno` | Tipo de imovel |
| `bedrooms` | int | 0-N | Minimo de quartos |
| `suites` | int\|"indifferent" | 0-N ou indiferente | Minimo de suites |
| `bathrooms_min` | int\|"indifferent" | 0-N ou indiferente | Minimo de banheiros |
| `parking` | int | 0-N | Minimo de vagas |
| `budget` | int | R$ | Orcamento maximo |
| `timeline` | str | `30d`, `3m`, `6m`, `12m`, `flexivel` | Prazo para fechar |
| `micro_location` | str | `beira-mar`, `1_quadra`, `2-3_quadras`, `>3_quadras`, `indifferent` | Proximidade da praia |
| `leisure_required` | str | `yes`, `no`, `indifferent` | Exige area de lazer |
| `lead_name` | str | livre | Nome do lead |
| `lead_phone` | str | livre | Telefone do lead |

### 16.2 Campos extras (PREFERENCE_ORDER)

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `allows_short_term_rental` | str | `yes`, `no`, `unknown` — condominio permite Airbnb/temporada |
| `budget_min` | int | Orcamento minimo |
| `condo_max` | int | Teto de condominio mensal |
| `leisure_level` | str | `simple`, `ok`, `full`, `indifferent` — nivel do lazer |
| `floor_pref` | str | `baixo`, `medio`, `alto`, `indifferent` |
| `sun_pref` | str | `nascente`, `poente`, `indifferent` |
| `leisure_features` | list[str] | Features especificas: `piscina`, `academia`, `gourmet` etc. |
| `furnished` | bool | Mobiliado |
| `pet` | bool | Aceita pet |

### 16.3 Status dos campos

Cada campo em `triage_fields` tem um `status`:
- `confirmed` — informado explicitamente pelo usuario (nao sera reperguntado)
- `inferred` — deduzido pelo agente (pode ser reperguntado se critico)

### 16.4 Regra anti-confusao: temporada vs intenção

**"aluguel por temporada" / "Airbnb" / "temporada" → `allows_short_term_rental=yes`**

Esses padroes NAO alteram `intent`. Para definir `intent=alugar`, o usuario precisa dizer
explicitamente "quero alugar", "procuro aluguel", etc. sem contexto de temporada.

Exemplos:
- "quero comprar apto que libera Airbnb" → `intent=comprar`, `allows_short_term_rental=yes`
- "locação por temporada" → `allows_short_term_rental=yes`, `intent` nao muda
- "quero alugar" → `intent=alugar` (sem temporada)

---

## 15. Referencias internas

Arquivos para ler primeiro:
1. `main.py`
2. `agent/controller.py`
3. `agent/llm.py`
4. `agent/state.py`
5. `agent/rules.py`
6. `agent/quality.py` e `agent/quality_gate.py`
7. `agent/router.py`
8. `routes/whatsapp.py` e `services/whatsapp_sender.py`
9. `render.yaml`

Este README foi escrito para ser suficiente mesmo sem acesso ao codigo, mas os arquivos acima sao a fonte primaria para qualquer alteracao arquitetural.
