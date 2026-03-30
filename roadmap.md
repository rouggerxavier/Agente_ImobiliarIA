# Roadmap — Evolução do Projeto de IA Imobiliário

> Documento operacional em formato de checklist para transformar o projeto atual em um sistema imobiliário com IA, memória persistente, motor de decisão, integração real de canais, CRM operacional, observabilidade e capacidade de escalar em produção.

## Como usar este documento

- Use este arquivo como backlog principal.
- Marque cada item com `[x]` quando concluído.
- Não avance de fase sem fechar os critérios de saída.
- Se um item depender de outro, trate o item pai como bloqueante.
- Sempre que possível, associe cada item a uma issue, branch ou PR.

---

## 1) Estado atual assumido

Este roadmap parte do estado atual visível no repositório:

- O projeto já possui API FastAPI, controlador central, estado de sessão, extração de dados da mensagem, scoring de lead, roteamento de corretor, quality gate, follow-up e testes automatizados.
- A persistência atual está baseada em arquivo (`data/leads.jsonl`) e cadastro de corretores em JSON.
- Existe base local de imóveis em JSON e modo `TRIAGE_ONLY`, no qual o sistema qualifica o lead e encaminha para corretor, sem necessariamente listar imóveis.
- O projeto já conversa com LLM com fallback, mas ainda não está organizado como plataforma operacional completa com banco transacional, fila de eventos, RAG especializado, CRM próprio, métricas de negócio e integração real de canal ponta a ponta.

---

## 2) Objetivo final do produto

Construir um **copiloto comercial imobiliário production-grade** capaz de:

- qualificar leads por WhatsApp e web;
- manter memória persistente por lead e por conversa;
- recomendar imóveis com base em perfil, catálogo e contexto;
- responder objeções usando base de conhecimento da operação;
- decidir próxima ação ideal (`next best action`);
- priorizar e rotear leads automaticamente;
- encaminhar atendimento humano com contexto completo;
- automatizar follow-ups;
- instrumentar custo, latência, qualidade e conversão;
- operar com segurança, auditoria, testes e deploy confiável.

---

## 3) Princípios de implementação

### 3.1 Princípios de produto
- [x] Definir claramente se o produto é **triagem-first**, **recomendação-first** ou **copiloto completo de vendas**.
- [x] Definir o público principal do sistema: imobiliária pequena, operação multi-corretor, incorporadora, house de lançamentos ou operação híbrida.
- [x] Definir quais canais são escopo oficial da V1 e V2: WhatsApp, web chat, dashboard interno, e-mail.
- [x] Definir o que a IA pode fazer sem humano e o que exige handoff.
- [x] Definir política oficial de tom de voz, postura comercial e limites de promessa ao cliente.

### 3.2 Princípios de engenharia
- [x] Separar claramente camadas de domínio, aplicação, infraestrutura e apresentação.
- [x] Remover dependência de arquivos JSON como fonte primária operacional.
- [x] Tratar cada lead, conversa, mensagem, imóvel, corretor, visita e handoff como entidades persistentes.
- [x] Garantir idempotência para eventos de mensageria.
- [x] Garantir rastreabilidade de toda decisão tomada pela IA.
- [x] Tratar LLM como componente não determinístico e sempre envolver fallback, timeout, retry e logging.
- [x] Evitar misturar regra de negócio, prompt e acesso a dados na mesma função.
- [x] Padronizar contratos de entrada e saída com Pydantic.
- [x] Definir desde o início métricas de negócio e métricas técnicas.
- [x] Projetar a arquitetura para operação assíncrona desde a base.

---

## 4) Critérios de sucesso

### 4.1 Critérios de negócio
- [x] Medir taxa de leads qualificados por canal.
- [x] Medir tempo médio até primeira resposta.
- [x] Medir taxa de handoff bem-sucedido para corretor.
- [x] Medir taxa de visita agendada.
- [x] Medir taxa de conversão por corretor.
- [x] Medir taxa de recuperação de leads frios via follow-up.
- [x] Medir taxa de resposta útil para perguntas sobre catálogo e operação.

### 4.2 Critérios técnicos
- [x] 95%+ das mensagens processadas sem erro fatal.
- [x] 99%+ de persistência consistente de eventos de mensagem.
- [x] Latência alvo definida para respostas síncronas.
- [x] Cobertura mínima de testes definida por camada.
- [x] Auditoria de decisões da IA disponível por conversa.
- [x] Observabilidade com tracing por fluxo e por nó do agente.
- [x] Ambiente de staging separado de produção.
- [x] Rollback simples de deploy.

---

## 5) Macroarquitetura alvo

- [ ] Definir arquitetura-alvo oficialmente em documento técnico.
- [ ] Validar a divisão em serviços/módulos:
  - [ ] API pública
  - [ ] orquestrador conversacional
  - [ ] serviço de catálogo / imóveis
  - [ ] serviço de leads / CRM
  - [ ] serviço de conhecimento / RAG
  - [ ] serviço de automações / follow-up
  - [ ] serviço de observabilidade / analytics
- [ ] Definir se a primeira versão continuará como monólito modular ou migrará para múltiplos serviços.
- [ ] Desenhar fluxo de ponta a ponta:
  - [ ] entrada de mensagem
  - [ ] normalização
  - [ ] persistência do evento bruto
  - [ ] orquestração
  - [ ] consulta a memória
  - [ ] consulta a catálogo / conhecimento
  - [ ] decisão
  - [ ] resposta
  - [ ] logging
  - [ ] automações posteriores

---

## 6) Fase 0 — Saneamento do projeto atual

### 6.1 Leitura do legado
- [ ] Revisar e mapear todos os módulos existentes do projeto.
- [ ] Identificar acoplamentos perigosos no `controller.py`.
- [ ] Mapear onde regras de negócio estão espalhadas e sem centralização.
- [ ] Mapear funções com múltiplas responsabilidades.
- [ ] Mapear pontos em que o estado fica apenas em memória.
- [ ] Mapear todos os locais com acesso direto a arquivos JSON.
- [ ] Mapear endpoints atuais e comportamento real de cada um.
- [ ] Mapear variáveis de ambiente existentes e padronizar nomenclatura.

### 6.2 Refatoração mínima preparatória
- [ ] Criar diretório ou pacote `domain/` para entidades e regras centrais.
- [ ] Criar diretório ou pacote `application/` para casos de uso.
- [ ] Criar diretório ou pacote `infrastructure/` para banco, fila, LLM, provedores externos.
- [ ] Criar diretório ou pacote `interfaces/` para HTTP, webhooks e jobs.
- [ ] Criar módulo único de configurações com versionamento claro.
- [ ] Padronizar tratamento de exceções por tipo.
- [ ] Padronizar resposta de erro da API.
- [ ] Padronizar logs estruturados desde agora.
- [ ] Adicionar `request_id`, `conversation_id`, `lead_id` e `trace_id` em todo fluxo.

### 6.3 Critério de saída da fase
- [ ] O projeto compila e roda após a reorganização estrutural.
- [ ] Nenhuma funcionalidade atual crítica foi quebrada.
- [ ] Existe documentação da arquitetura atual e da arquitetura desejada.
- [ ] Existe lista objetiva de dívidas técnicas priorizadas.

---

## 7) Fase 1 — Modelo de domínio e persistência real

### 7.1 Banco de dados transacional
- [ ] Escolher banco principal: PostgreSQL.
- [ ] Definir estratégia de migrations.
- [ ] Configurar ORM ou camada de acesso a dados.
- [ ] Criar ambiente local com Docker Compose.
- [ ] Criar ambiente de staging com banco separado.
- [ ] Criar política de backup e restore.
- [ ] Criar estratégia de seed para dados iniciais.

### 7.2 Entidades principais
- [ ] Modelar entidade `Lead`.
- [ ] Modelar entidade `Conversation`.
- [ ] Modelar entidade `Message`.
- [ ] Modelar entidade `Property`.
- [ ] Modelar entidade `Broker` / `Agent`.
- [ ] Modelar entidade `Assignment`.
- [ ] Modelar entidade `FollowUpTask`.
- [ ] Modelar entidade `Visit`.
- [ ] Modelar entidade `KnowledgeDocument`.
- [ ] Modelar entidade `DecisionLog`.
- [ ] Modelar entidade `LeadScoreSnapshot`.
- [ ] Modelar entidade `Recommendation`.
- [ ] Modelar entidade `ChannelAccount` / `ContactPoint`.
- [ ] Modelar entidade `Attachment`.
- [ ] Modelar entidade `EventEnvelope`.

### 7.3 Campos mínimos por entidade
- [ ] Definir status e enumerações oficiais para `Lead`.
- [ ] Definir estágios do funil.
- [ ] Definir status de conversa.
- [ ] Definir tipos de mensagem.
- [ ] Definir tipos de intenção detectada.
- [ ] Definir schema de preferências imobiliárias do lead.
- [ ] Definir schema de orçamento, prazo e contexto familiar.
- [ ] Definir schema de tags comerciais.
- [ ] Definir schema de resultado de roteamento.
- [ ] Definir schema de score com justificativas.

### 7.4 Repositórios e serviços
- [ ] Criar `LeadRepository`.
- [ ] Criar `ConversationRepository`.
- [ ] Criar `MessageRepository`.
- [ ] Criar `PropertyRepository`.
- [ ] Criar `BrokerRepository`.
- [ ] Criar `AssignmentRepository`.
- [ ] Criar `KnowledgeRepository`.
- [ ] Criar `DecisionLogRepository`.
- [ ] Criar `FollowUpRepository`.

### 7.5 Migração do legado
- [ ] Criar script de importação de `data/leads.jsonl` para o banco.
- [ ] Criar script de importação de `data/agents.json`.
- [ ] Criar script de importação de `properties.json`.
- [ ] Validar consistência dos dados migrados.
- [ ] Criar estratégia de rollback de migração.
- [ ] Remover dependência operacional do append-only em arquivo.

### 7.6 Critério de saída da fase
- [ ] Toda operação relevante grava no banco.
- [ ] É possível reconstruir a conversa inteira de um lead.
- [ ] É possível consultar histórico, score, corretor atribuído e mensagens via banco.
- [ ] Nenhum fluxo crítico depende mais de JSON como storage primário.

---

## 8) Fase 2 — Integração real de canais e entrada de eventos

### 8.1 Contrato de entrada de mensagens
- [ ] Definir payload canônico de mensagem recebida.
- [ ] Mapear campos de canal: telefone, nome, timestamp, mídia, id externo.
- [ ] Normalizar diferenças entre web chat e WhatsApp.
- [ ] Criar deduplicação por `external_message_id`.
- [ ] Garantir idempotência no processamento.

### 8.2 Integração WhatsApp
- [ ] Escolher gateway oficial de integração.
- [ ] Implementar verificação de assinatura / autenticidade do webhook.
- [ ] Persistir evento bruto antes de processar.
- [ ] Persistir anexo, áudio, localização e documentos recebidos.
- [ ] Tratar mensagens duplicadas ou fora de ordem.
- [ ] Implementar envio de resposta pelo provedor escolhido.
- [ ] Implementar tratamento de falha no envio.
- [ ] Registrar status de entrega, lida e erro.
- [ ] Implementar modo sandbox para testes.

### 8.3 Web chat
- [ ] Definir widget oficial de chat web.
- [ ] Criar endpoint seguro para conversa web.
- [ ] Implementar criação de sessão anônima e conversão para lead identificado.
- [ ] Persistir origem da conversa (`whatsapp`, `web`, `dashboard`, etc.).
- [ ] Sincronizar histórico entre canal e CRM interno.

### 8.4 Mensagens multimodais
- [ ] Decidir escopo da V1 para áudio.
- [ ] Implementar transcrição de áudio.
- [ ] Persistir texto transcrito e arquivo original.
- [ ] Tratar documentos enviados pelo cliente.
- [ ] Tratar compartilhamento de localização.
- [ ] Criar política para anexos inválidos ou maliciosos.

### 8.5 Critério de saída da fase
- [ ] Mensagens reais entram por webhook com segurança.
- [ ] Mensagens são processadas exatamente uma vez ou de forma idempotente.
- [ ] O sistema responde pelo canal real.
- [ ] O histórico do canal fica preservado.

---

## 9) Fase 3 — Estado conversacional e memória persistente

### 9.1 Memória de curto prazo
- [ ] Persistir todas as mensagens da conversa.
- [ ] Criar janela de contexto configurável.
- [ ] Implementar montagem de contexto com últimas mensagens relevantes.
- [ ] Filtrar mensagens redundantes ou irrelevantes.
- [ ] Tratar retomada de conversa após horas ou dias.

### 9.2 Memória de longo prazo do lead
- [ ] Criar perfil consolidado do lead separado da conversa bruta.
- [ ] Persistir preferências estáveis do lead:
  - [ ] finalidade (`comprar`, `alugar`, `investir`)
  - [ ] ticket
  - [ ] bairros
  - [ ] tipo de imóvel
  - [ ] quartos
  - [ ] urgência
  - [ ] forma de pagamento
  - [ ] restrições especiais
- [ ] Implementar atualização incremental do perfil.
- [ ] Implementar resolução de conflitos quando o lead muda de ideia.
- [ ] Implementar timestamp e fonte de cada atributo.
- [ ] Implementar noção de confiança por campo do perfil.

### 9.3 Resumo operacional da conversa
- [ ] Criar resumo executivo para handoff humano.
- [ ] Criar resumo técnico para o agente continuar depois.
- [ ] Atualizar resumo automaticamente a cada mudança relevante.
- [ ] Salvar versões do resumo para auditoria.

### 9.4 Critério de saída da fase
- [ ] O sistema consegue retomar conversa antiga com contexto correto.
- [ ] O perfil do lead é persistente e reutilizável.
- [ ] O corretor recebe histórico consolidado e não só mensagens cruas.

---

## 10) Fase 4 — Orquestração séria com grafo de estados

### 10.1 Decisão arquitetural
- [ ] Definir formalmente a adoção de LangGraph ou outra engine de workflow.
- [ ] Desenhar o estado do grafo.
- [ ] Definir contratos claros entre nós.
- [ ] Definir nós síncronos e nós assíncronos.

### 10.2 Estado do orquestrador
- [ ] Criar schema de estado com:
  - [ ] `lead_id`
  - [ ] `conversation_id`
  - [ ] `channel`
  - [ ] `message_input`
  - [ ] `lead_profile`
  - [ ] `conversation_summary`
  - [ ] `detected_intent`
  - [ ] `retrieval_context`
  - [ ] `property_candidates`
  - [ ] `lead_score`
  - [ ] `routing_decision`
  - [ ] `next_action`
  - [ ] `confidence`
  - [ ] `guardrail_flags`
  - [ ] `human_handoff_required`

### 10.3 Nós do fluxo
- [ ] Criar nó de ingestão e normalização.
- [ ] Criar nó de recuperação de contexto do lead.
- [ ] Criar nó de classificação de intenção.
- [ ] Criar nó de extração de dados estruturados.
- [ ] Criar nó de atualização de perfil.
- [ ] Criar nó de recuperação de conhecimento.
- [ ] Criar nó de recuperação de imóveis.
- [ ] Criar nó de score do lead.
- [ ] Criar nó de decisão da próxima ação.
- [ ] Criar nó de geração de resposta.
- [ ] Criar nó de verificação de qualidade.
- [ ] Criar nó de persistência de decisão.
- [ ] Criar nó de handoff.
- [ ] Criar nó de agendamento de follow-up.

### 10.4 Regras de roteamento do grafo
- [ ] Se o cliente pedir catálogo, seguir para recuperação de imóveis.
- [ ] Se o cliente fizer pergunta operacional, seguir para conhecimento / FAQ.
- [ ] Se faltar critério essencial, seguir para pergunta de qualificação.
- [ ] Se o score ultrapassar limiar, considerar handoff imediato.
- [ ] Se confiança do LLM estiver baixa, reduzir autonomia.
- [ ] Se houver erro de provedor, acionar fallback.
- [ ] Se o conteúdo violar guardrails, responder com fluxo seguro.
- [ ] Se houver necessidade humana, interromper fluxo com handoff.

### 10.5 Resiliência do fluxo
- [ ] Implementar timeout por nó.
- [ ] Implementar retries com política diferenciada por tipo de erro.
- [ ] Implementar checkpoints de estado.
- [ ] Implementar reprocessamento a partir de checkpoint.
- [ ] Implementar logs por transição de nó.
- [ ] Implementar limites de custo por execução.

### 10.6 Critério de saída da fase
- [ ] O fluxo principal roda por grafo, não por lógica espalhada.
- [ ] Cada etapa possui entrada, saída e observabilidade próprias.
- [ ] É possível depurar uma conversa vendo a trajetória exata do fluxo.

---

## 11) Fase 5 — Catálogo imobiliário e motor de busca/recomendação

### 11.1 Modelagem do catálogo
- [x] Definir schema completo de imóvel.
- [x] Incluir campos estruturados:
  - [x] preço
  - [x] finalidade
  - [x] bairro
  - [x] cidade
  - [x] tipologia
  - [x] quartos
  - [x] banheiros
  - [x] vagas
  - [x] metragem
  - [x] amenidades
  - [x] status comercial
  - [x] corretor responsável
  - [x] data de atualização
- [x] Definir campos textuais ricos para busca semântica.
- [x] Definir campos privados que não podem vazar ao cliente (`internal_notes`, `cost_price`, `owner_name`, `owner_phone`, `commission_pct` + método `public_dict()`).
- [x] Definir política de imóveis indisponíveis (`unavailable_reason`, `unavailable_since`, método `is_showable()`).

### 11.2 Ingestão de catálogo
- [x] Criar pipeline de ingestão do catálogo (`application/catalog_ingestion.py`).
- [x] Suportar importação via JSON/CSV/API (`ingest_dicts`, `ingest_json_string`, `ingest_csv_string`).
- [x] Validar qualidade dos dados antes de publicar (`validate_property_data` com erros bloqueantes e warnings).
- [x] Normalizar bairros, cidades e tipologias (`normalize_city`, `normalize_property_type`, `normalize_purpose`).
- [x] Detectar duplicidade de imóveis (upsert por `external_ref`).
- [x] Criar rotina de atualização incremental (upsert preserva `id` e `created_at`).
- [x] Criar rotina de arquivamento de imóveis desativados (`full_replace=True` em `ingest_dicts`).

### 11.3 Busca estruturada
- [x] Implementar filtros exatos por finalidade, bairro, faixa de preço, tipologia e quartos.
- [x] Implementar ordenação por relevância e compatibilidade (`order_by="relevance"` com relevance scoring).
- [x] Implementar busca por intervalo de orçamento (`budget_min` + `budget_max`).
- [x] Implementar filtros flexíveis para budget aproximado (tolerância 20% na compatibilidade e alternativas).
- [x] Implementar tratamento de ausência de resultados (`fallback_message`).

### 11.4 Busca semântica e híbrida
- [x] Definir se haverá vetor local ou serviço externo — **vetor local TF-IDF** (`application/catalog_semantic.py`).
- [x] Criar embeddings para descrições e amenidades (índice TF-IDF sobre texto rico do imóvel).
- [x] Implementar busca híbrida: filtro estruturado + semântica (`hybrid_search` em `CatalogService`).
- [x] Implementar reranking (score combinado ponderado em `SemanticCatalogSearch.hybrid_search`).
- [x] Criar política de score de recomendação (`HybridResult` com `structural_score`, `semantic_score`, `combined_score`).
- [ ] Medir qualidade de recuperação do catálogo (benchmark pendente — Fase 6).

### 11.5 Recomendação de imóveis
- [x] Criar algoritmo de matching entre perfil do lead e imóvel (`_score_match` com pesos por dimensão).
- [x] Explicar por que um imóvel foi recomendado (`match_reasons` detalhados).
- [x] Incluir justificativas orientadas a venda (`_build_pitch` com destaques de amenidades e diferenciais).
- [x] Limitar quantidade de imóveis por resposta (parâmetro `limit` em `recommend`).
- [x] Evitar recomendar imóvel incompatível com perfil (`_check_incompatibilities` com tolerância 20%).
- [x] Criar fallback quando não houver match exato (`fallback_message`).
- [x] Oferecer alternativas próximas de forma controlada (`_search_alternatives` com flexibilização progressiva).

### 11.6 Critério de saída da fase
- [x] O sistema recomenda imóveis com base em dados reais e filtros confiáveis.
- [x] A recomendação é auditável (`RecommendationRepository` + `JsonRecommendationRepository`).
- [x] O sistema não sugere imóvel indisponível ou fora do escopo sem aviso (`is_showable()` + `_check_incompatibilities`).

---

## 12) Fase 6 — Base de conhecimento e RAG comercial/operacional

### 12.1 Escopo da base de conhecimento
- [x] Definir fontes de conhecimento:
  - [x] FAQs da imobiliária
  - [x] políticas comerciais
  - [x] processos de visita
  - [x] documentação de financiamento
  - [x] objeções comuns
  - [x] scripts comerciais
  - [x] regras de atendimento
  - [x] informações por empreendimento
- [x] Separar conhecimento público, interno e sensível.
- [x] Criar classificação de permissões por documento.

### 12.2 Pipeline de ingestão de conhecimento
- [x] Criar pipeline de upload e indexação.
- [x] Fazer parsing de PDF/DOCX/HTML/txt.
- [x] Criar chunking adequado ao domínio.
- [x] Preservar metadados de origem e versão.
- [x] Criar política de atualização de documentos.
- [x] Criar política de exclusão de documentos obsoletos.

### 12.3 Motor de recuperação
- [x] Implementar busca vetorial.
- [x] Implementar busca lexical quando fizer sentido.
- [x] Implementar reranking.
- [x] Implementar filtros por tipo de documento.
- [x] Implementar filtros por validade temporal.
- [x] Implementar citação ou referência interna da origem.

### 12.4 Uso do RAG no fluxo
- [x] Identificar quando a pergunta exige conhecimento operacional.
- [x] Identificar quando a pergunta exige catálogo e não FAQ.
- [x] Identificar quando a pergunta exige resposta curta e objetiva.
- [x] Injetar trechos recuperados no prompt final.
- [x] Implementar groundedness check.
- [x] Bloquear resposta quando o contexto recuperado for insuficiente.
- [x] Gerar resposta com postura comercial e precisão factual.

### 12.5 Avaliação do RAG
- [x] Criar conjunto de perguntas reais da operação.
- [x] Medir recall da recuperação.
- [x] Medir groundedness.
- [x] Medir taxa de alucinação.
- [x] Medir aderência do conteúdo à política da empresa.
- [x] Comparar diferentes estratégias de chunking e reranking.

### 12.6 Critério de saída da fase
- [x] O sistema responde perguntas sobre operação e vendas com base em fontes rastreáveis.
- [x] O RAG não conflita com a busca de imóveis.
- [x] Existe benchmark mínimo para avaliar qualidade.

---

## 13) Fase 7 — Score de lead, classificação e motor de decisão

### 13.1 Modelo de score
- [ ] Definir score total e sub-scores:
  - [ ] completude do perfil
  - [ ] compatibilidade com catálogo
  - [ ] urgência
  - [ ] intenção de compra
  - [ ] capacidade financeira
  - [ ] engajamento
  - [ ] qualidade do canal
- [ ] Formalizar pesos iniciais.
- [ ] Registrar justificativas do score.
- [ ] Versionar a fórmula de score.
- [ ] Permitir recalcular score quando o perfil mudar.

### 13.2 Classificadores
- [ ] Implementar classificador de intenção principal.
- [ ] Implementar classificador de temperatura do lead.
- [ ] Implementar classificador de estágio do funil.
- [ ] Implementar classificador de risco de abandono.
- [ ] Implementar classificador de necessidade de humano.
- [ ] Medir performance de cada classificador.

### 13.3 Next Best Action
- [ ] Definir catálogo de ações possíveis:
  - [ ] perguntar dado faltante
  - [ ] sugerir imóveis
  - [ ] esclarecer objeção
  - [ ] convidar para visita
  - [ ] solicitar documento
  - [ ] encaminhar corretor
  - [ ] agendar follow-up
  - [ ] encerrar com retomada futura
- [ ] Criar política de decisão baseada em regras + LLM.
- [ ] Garantir que a ação proposta tenha justificativa.
- [ ] Persistir decisão e contexto usado.
- [ ] Criar proteção contra ações inconsistentes.

### 13.4 Critério de saída da fase
- [ ] O sistema não apenas responde; ele decide o próximo passo comercial.
- [ ] O score influencia roteamento, follow-up e priorização.
- [ ] As decisões ficam explicáveis.

---

## 14) Fase 8 — Roteamento, handoff humano e operação comercial

### 14.1 Roteamento inteligente
- [ ] Modelar disponibilidade dos corretores no banco.
- [ ] Modelar capacidade diária e fila de atendimento.
- [ ] Modelar especialidade por região, faixa de ticket e perfil.
- [ ] Criar algoritmo de matching lead-corretor.
- [ ] Considerar balanceamento de carga.
- [ ] Considerar prioridade de leads quentes.
- [ ] Considerar round-robin apenas como fallback.

### 14.2 Handoff humano
- [ ] Definir gatilhos oficiais de handoff.
- [ ] Implementar geração automática de resumo do lead.
- [ ] Enviar contexto consolidado ao corretor:
  - [ ] perfil do lead
  - [ ] resumo da conversa
  - [ ] score
  - [ ] imóveis sugeridos
  - [ ] objeções já levantadas
  - [ ] próxima ação recomendada
- [ ] Permitir o corretor assumir a conversa.
- [ ] Registrar quando a conversa saiu da IA para humano.
- [ ] Permitir devolver para a IA quando fizer sentido.

### 14.3 Pós-handoff
- [ ] Registrar resultado do atendimento humano.
- [ ] Registrar visita marcada, visita realizada, proposta e fechamento.
- [ ] Fechar o loop de aprendizado com outcomes reais.
- [ ] Alimentar analytics com resultados do corretor.

### 14.4 Critério de saída da fase
- [ ] O handoff deixa de ser apenas encaminhamento; vira transferência operacional completa.
- [ ] O corretor recebe contexto suficiente para continuar sem retrabalho.
- [ ] O sistema sabe o que aconteceu depois do handoff.

---

## 15) Fase 9 — Automação de follow-up e reengajamento

### 15.1 Estratégia de follow-up
- [ ] Definir cadências de follow-up por estágio.
- [ ] Definir follow-up para lead frio.
- [ ] Definir follow-up para lead morno.
- [ ] Definir follow-up pós-visita.
- [ ] Definir follow-up pós-proposta.
- [ ] Definir follow-up para imóvel indisponível.
- [ ] Definir follow-up para ausência de resposta.

### 15.2 Motor de automação
- [ ] Criar scheduler de tarefas de follow-up.
- [ ] Criar fila de execução de follow-ups.
- [ ] Permitir cancelamento automático se o lead responder.
- [ ] Permitir revisão humana de mensagens sensíveis.
- [ ] Registrar status de cada follow-up.

### 15.3 Personalização
- [ ] Personalizar follow-up pelo estágio do funil.
- [ ] Personalizar follow-up pelo perfil do imóvel desejado.
- [ ] Personalizar follow-up pela última objeção do lead.
- [ ] Evitar repetição de mensagens.
- [ ] Implementar limite de insistência para não degradar a experiência.

### 15.4 Critério de saída da fase
- [ ] O sistema reengaja leads com estratégia consistente.
- [ ] Toda automação é auditável e cancelável.
- [ ] A automação melhora o funil sem virar spam.

---

## 16) Fase 10 — Dashboard, CRM e experiência operacional

### 16.1 CRM interno mínimo
- [ ] Criar listagem de leads.
- [ ] Criar filtros por estágio, temperatura, canal, corretor e período.
- [ ] Criar página de detalhe do lead.
- [ ] Mostrar timeline da conversa.
- [ ] Mostrar score atual e histórico de score.
- [ ] Mostrar imóveis sugeridos.
- [ ] Mostrar decisões tomadas pela IA.
- [ ] Mostrar follow-ups futuros agendados.

### 16.2 Ações do operador
- [ ] Permitir reatribuir corretor.
- [ ] Permitir editar dados do lead.
- [ ] Permitir marcar lead como perdido, em negociação ou fechado.
- [ ] Permitir agendar visita.
- [ ] Permitir registrar feedback do corretor.
- [ ] Permitir pausar automações.
- [ ] Permitir corrigir extrações erradas da IA.

### 16.3 Painel gerencial
- [ ] Criar visão do funil por período.
- [ ] Criar visão por corretor.
- [ ] Criar visão por canal.
- [ ] Criar visão por bairro/tipologia/faixa de ticket.
- [ ] Criar visão de conversão e SLA.
- [ ] Criar visão de motivos de perda.
- [ ] Criar visão de performance da IA.

### 16.4 Critério de saída da fase
- [ ] O sistema já pode ser usado internamente como ferramenta operacional.
- [ ] O time comercial consegue acompanhar leads sem depender de logs técnicos.
- [ ] O gerente consegue medir resultado.

---

## 17) Fase 11 — Observabilidade, tracing e telemetria

### 17.1 Logs
- [ ] Implementar logs estruturados em JSON.
- [ ] Incluir `lead_id`, `conversation_id`, `message_id`, `trace_id`, `channel`.
- [ ] Logar início e fim de cada caso de uso.
- [ ] Logar decisões do grafo.
- [ ] Logar chamadas a LLM.
- [ ] Logar chamadas a banco e integrações externas.
- [ ] Remover dados sensíveis desnecessários dos logs.

### 17.2 Métricas técnicas
- [ ] Medir latência por endpoint.
- [ ] Medir latência por nó do grafo.
- [ ] Medir taxa de erro por tipo.
- [ ] Medir retries e timeouts.
- [ ] Medir custo por execução de LLM.
- [ ] Medir uso de fallback.
- [ ] Medir tamanho médio de contexto.

### 17.3 Métricas de produto
- [ ] Medir score médio de leads por canal.
- [ ] Medir distribuição de intenções.
- [ ] Medir taxa de resposta do cliente.
- [ ] Medir taxa de handoff.
- [ ] Medir taxa de follow-up concluído.
- [ ] Medir taxa de visita e conversão.
- [ ] Medir performance por corretor.

### 17.4 Tracing
- [ ] Instrumentar tracing de ponta a ponta.
- [ ] Correlacionar trace técnico com lead/conversa.
- [ ] Visualizar passo a passo do fluxo.
- [ ] Permitir inspeção de prompts e saídas quando apropriado.
- [ ] Criar dashboard de tracing para debug.

### 17.5 Alertas
- [ ] Alertar quando taxa de erro subir.
- [ ] Alertar quando provedor de LLM falhar.
- [ ] Alertar quando webhook quebrar.
- [ ] Alertar quando fila acumular.
- [ ] Alertar quando latência explodir.
- [ ] Alertar quando custo diário ultrapassar limiar.

### 17.6 Critério de saída da fase
- [ ] Você consegue diagnosticar produção sem adivinhar.
- [ ] Existe visibilidade suficiente para otimizar custo e qualidade.
- [ ] Incidentes ficam investigáveis.

---

## 18) Fase 12 — Avaliação, testes e confiabilidade

### 18.1 Testes unitários
- [ ] Cobrir extração de campos.
- [ ] Cobrir cálculo de score.
- [ ] Cobrir regras de roteamento.
- [ ] Cobrir normalização de payload.
- [ ] Cobrir montagem de contexto.
- [ ] Cobrir serviços de catálogo.
- [ ] Cobrir guardrails.

### 18.2 Testes de integração
- [ ] Cobrir fluxo de mensagem recebida até persistência.
- [ ] Cobrir fluxo de recomendação de imóvel.
- [ ] Cobrir fluxo de RAG operacional.
- [ ] Cobrir fluxo de handoff.
- [ ] Cobrir fluxo de follow-up.
- [ ] Cobrir integrações externas simuladas.

### 18.3 Testes end-to-end
- [ ] Simular conversa completa de compra.
- [ ] Simular conversa completa de aluguel.
- [ ] Simular lead que muda de ideia.
- [ ] Simular cliente sem orçamento definido.
- [ ] Simular cliente com pergunta sobre financiamento.
- [ ] Simular falta de resultados no catálogo.
- [ ] Simular falha no LLM.
- [ ] Simular falha no WhatsApp provider.
- [ ] Simular mensagens duplicadas.

### 18.4 Avaliação de IA
- [ ] Montar dataset de conversas reais/anônimas.
- [ ] Criar rubrica de qualidade da resposta.
- [ ] Criar rubrica de qualidade da extração.
- [ ] Criar rubrica de qualidade do score.
- [ ] Criar rubrica de qualidade da decisão da próxima ação.
- [ ] Criar benchmark de recuperação do catálogo.
- [ ] Criar benchmark do RAG comercial.
- [ ] Rodar avaliações automaticamente em CI quando possível.

### 18.5 Confiabilidade
- [ ] Definir SLOs mínimos.
- [ ] Criar testes de carga.
- [ ] Criar testes de concorrência.
- [ ] Criar testes de idempotência.
- [ ] Criar chaos tests para falhas de provedores externos.
- [ ] Criar runbooks de incidentes.

### 18.6 Critério de saída da fase
- [ ] O sistema é previsível em cenários normais e degradados.
- [ ] Existe confiança para operar com tráfego real.
- [ ] Existe mecanismo de validação contínua da IA.

---

## 19) Fase 13 — Segurança, privacidade e governança

### 19.1 Segurança de aplicação
- [ ] Proteger endpoints com autenticação adequada.
- [ ] Separar autenticação de usuários internos e webhooks externos.
- [ ] Validar origem e assinatura dos webhooks.
- [ ] Implementar rate limiting.
- [ ] Implementar proteção contra payload malicioso.
- [ ] Validar uploads e anexos.
- [ ] Sanitizar entradas antes de logs e processamento.

### 19.2 Segredos e ambientes
- [ ] Remover qualquer segredo hardcoded.
- [ ] Centralizar gestão de segredos.
- [ ] Separar `.env` por ambiente.
- [ ] Criar checklist de variáveis obrigatórias para deploy.
- [ ] Rotacionar chaves quando necessário.

### 19.3 Privacidade e governança
- [ ] Definir política de retenção de dados.
- [ ] Definir anonimização para datasets de avaliação.
- [ ] Definir o que pode e o que não pode ser enviado ao LLM.
- [ ] Definir acesso por perfil no CRM.
- [ ] Registrar auditoria de alterações manuais em leads.
- [ ] Registrar auditoria de decisões da IA.
- [ ] Criar termo de uso ou aviso de atendimento assistido por IA, se necessário.

### 19.4 Critério de saída da fase
- [ ] O sistema opera com controles mínimos de segurança e auditoria.
- [ ] Dados de leads e operação não ficam expostos de forma indevida.
- [ ] Você sabe quem fez o quê e quando.

---

## 20) Fase 14 — Infraestrutura, deploy e operação

### 20.1 Containers e ambientes
- [ ] Criar Dockerfile confiável.
- [ ] Criar docker-compose para desenvolvimento local.
- [ ] Criar perfis separados para API, banco, worker e fila.
- [ ] Criar ambiente de staging.
- [ ] Criar ambiente de produção.

### 20.2 CI/CD
- [ ] Rodar lint em pipeline.
- [ ] Rodar testes unitários em pipeline.
- [ ] Rodar testes de integração quando possível.
- [ ] Rodar migrations automaticamente com segurança.
- [ ] Fazer deploy automático para staging.
- [ ] Exigir validação manual antes de produção, se fizer sentido.
- [ ] Criar rollback simples.

### 20.3 Workers e fila
- [ ] Escolher fila de eventos.
- [ ] Criar worker para follow-up.
- [ ] Criar worker para ingestão de documentos.
- [ ] Criar worker para reprocessamento.
- [ ] Criar dead-letter queue.
- [ ] Criar painel mínimo de jobs.

### 20.4 Operação contínua
- [ ] Criar health checks.
- [ ] Criar readiness/liveness checks.
- [ ] Criar jobs de manutenção.
- [ ] Criar rotina de backup.
- [ ] Criar rotina de limpeza de dados temporários.
- [ ] Criar runbook de deploy.
- [ ] Criar runbook de rollback.
- [ ] Criar runbook de incidente.

### 20.5 Critério de saída da fase
- [ ] O projeto pode subir localmente e em nuvem de forma reprodutível.
- [ ] O deploy deixa de ser artesanal.
- [ ] Há caminho claro para escalar.

---

## 21) Fase 15 — Experimentação, analytics e melhoria contínua

### 21.1 Instrumentação para produto
- [ ] Registrar eventos de produto relevantes.
- [ ] Padronizar nomenclatura de eventos.
- [ ] Construir funil analítico.
- [ ] Medir quedas por etapa da jornada.
- [ ] Medir efeito de prompts, regras e estratégias no negócio.

### 21.2 Experimentação
- [ ] Definir mecanismo de feature flags.
- [ ] Permitir testar novas regras de score.
- [ ] Permitir testar novas estratégias de follow-up.
- [ ] Permitir testar novos prompts.
- [ ] Permitir comparar rankings de imóveis.
- [ ] Registrar versão da estratégia usada em cada conversa.

### 21.3 Aprendizado com operação
- [ ] Capturar feedback do corretor sobre qualidade da IA.
- [ ] Capturar motivo de correção manual.
- [ ] Capturar motivo de perda do lead.
- [ ] Alimentar backlog com base nos dados reais.
- [ ] Recalibrar score e regras com base em outcomes reais.

### 21.4 Critério de saída da fase
- [ ] O produto evolui guiado por dados e não só por feeling.
- [ ] Você consegue provar melhoria ao longo do tempo.

---

## 22) Fase 16 — Funcionalidades avançadas e diferenciais

### 22.1 Funcionalidades comerciais avançadas
- [ ] Sugerir imóveis similares quando não houver match exato.
- [ ] Explicar diferenças entre imóveis comparados.
- [ ] Gerar resumo comparativo entre opções.
- [ ] Priorizar imóveis com maior chance de fechamento.
- [ ] Detectar objeções automaticamente.
- [ ] Sugerir contra-argumentação comercial segura.

### 22.2 Planejamento de visita e agenda
- [ ] Integrar agenda do corretor.
- [ ] Propor horários disponíveis.
- [ ] Confirmar visita com lead.
- [ ] Relembrar visita automaticamente.
- [ ] Registrar comparecimento.

### 22.3 Financiamento e documentos
- [ ] Criar fluxo para simulação básica de financiamento.
- [ ] Solicitar documentos de forma organizada.
- [ ] Validar checklist documental.
- [ ] Encaminhar para correspondente/financeiro quando aplicável.

### 22.4 Multimodalidade
- [ ] Processar áudio do cliente.
- [ ] Enviar respostas em áudio quando fizer sentido.
- [ ] Extrair informações de imagens/documentos simples, se houver caso de uso real.

### 22.5 Inteligência operacional
- [ ] Estimar probabilidade de conversão por lead.
- [ ] Estimar risco de churn do lead.
- [ ] Detectar momento ideal de handoff.
- [ ] Detectar corretor com melhor taxa para determinado perfil.
- [ ] Criar recomendações operacionais para gestão.

### 22.6 Critério de saída da fase
- [ ] O sistema deixa de ser apenas assistente e vira vantagem operacional.
- [ ] As funcionalidades avançadas têm dados reais para justificar existência.

---

## 23) Backlog técnico transversal

### 23.1 Qualidade de código
- [ ] Padronizar formatter e linter.
- [ ] Padronizar convenções de nome.
- [ ] Eliminar funções longas demais.
- [ ] Eliminar duplicação óbvia.
- [ ] Adicionar docstrings nos módulos críticos.
- [ ] Documentar fluxos principais.

### 23.2 Contratos e schemas
- [ ] Versionar payloads públicos.
- [ ] Versionar eventos internos.
- [ ] Versionar schema de prompts relevantes.
- [ ] Versionar schema de score e decisão.

### 23.3 Custos
- [ ] Medir custo por mensagem.
- [ ] Medir custo por conversa.
- [ ] Medir custo por lead convertido.
- [ ] Criar limites de orçamento por ambiente.
- [ ] Criar fallback para reduzir custo.

### 23.4 Prompts
- [ ] Centralizar prompts.
- [ ] Versionar prompts.
- [ ] Separar prompts por intenção.
- [ ] Separar prompts por canal.
- [ ] Criar testes para evitar regressão de prompt.
- [ ] Revisar prompts para reduzir vazamento de instrução interna.

---

## 24) Ordem recomendada de execução

### Sprint 1–2: base operacional
- [ ] Saneamento arquitetural
- [ ] Banco de dados
- [ ] entidades principais
- [ ] migração do legado
- [ ] logs estruturados
- [ ] IDs de correlação

### Sprint 3–4: canal real + memória
- [ ] webhook real do canal escolhido
- [ ] persistência de mensagens
- [ ] memória curta
- [ ] perfil persistente do lead
- [ ] resumo operacional

### Sprint 5–6: grafo + decisão
- [ ] estado do orquestrador
- [ ] nós principais
- [ ] score versionado
- [ ] next best action
- [ ] handoff controlado

### Sprint 7–8: catálogo + recomendação
- [ ] catálogo no banco
- [ ] pipeline de ingestão
- [ ] busca estruturada
- [ ] matching de imóveis
- [ ] explicação da recomendação

### Sprint 9–10: RAG comercial
- [ ] base de conhecimento
- [ ] pipeline de indexação
- [ ] recuperação
- [ ] groundedness
- [ ] benchmark inicial

### Sprint 11–12: CRM e follow-up
- [ ] dashboard de leads
- [ ] timeline
- [ ] atribuição de corretor
- [ ] agenda de follow-up
- [ ] feedback do corretor

### Sprint 13–14: observabilidade e confiabilidade
- [ ] tracing
- [ ] métricas
- [ ] alertas
- [ ] testes E2E
- [ ] testes de carga

### Sprint 15+: otimização e diferenciais
- [ ] agenda/visita
- [ ] financiamento
- [ ] similiaridade
- [ ] modelos preditivos
- [ ] experimentação

---

## 25) Itens que não devem ficar para depois

- [ ] Persistência real em banco.
- [ ] Idempotência de webhook.
- [ ] Histórico de conversa persistente.
- [ ] Logs estruturados com correlação.
- [ ] Segurança mínima de webhook e autenticação.
- [ ] Observabilidade mínima.
- [ ] Handoff com contexto.
- [ ] Testes de falha de provedor.
- [ ] Benchmark básico de qualidade da IA.

---

## 26) Definition of Done por bloco

### Um bloco só pode ser considerado concluído quando:
- [ ] existe código implementado;
- [ ] existe teste cobrindo o comportamento crítico;
- [ ] existe documentação mínima;
- [ ] existe observabilidade mínima;
- [ ] existe rollback ou fallback quando aplicável;
- [ ] existe validação manual em staging;
- [ ] existe critério de aceite de negócio.

---

## 27) Meta final

Ao concluir este roadmap, o projeto deve ter evoluído de:

**“agente de triagem com regras, score e roteamento”**

para:

**“plataforma imobiliária com IA, memória persistente, recomendação, decisão, CRM, automação, observabilidade e operação real”**.
