# Estabilização Fase Atual - Catálogo e UI

## Causa raiz identificada

1. **Backend alvo incorreto no frontend**
- As telas de Home, Locação e Vendas faziam fetch para `http://localhost:8000` via `VITE_BACKEND_URL`.
- Em ambiente local, essa porta estava atendendo outro serviço, sem contrato `/imoveis/*` compatível e sem CORS esperado.
- Efeito: erro de rede/CORS, parse inválido e telas sem dados.

2. **Cliente HTTP sem proteção suficiente**
- Sem timeout de requisição (risco de loading travado em rede lenta/hang).
- Sem validação de `content-type` (HTML podia ser tratado como sucesso até falhar no parse).
- Sem fallback operacional para manter listagens essenciais.

3. **Texto corrompido em componente da Home**
- `src/components/FeaturedProperties.tsx` continha strings com mojibake (`ImÃ³veis`, `NÃ£o`, etc.).
- Causa: conteúdo já salvo corrompido no arquivo fonte.

## Correções implementadas

### Frontend API e contratos
- Reescrita de `src/lib/imoveis-api.ts` com:
  - auto-detecção de backend por probe em `/health`;
  - timeout (`VITE_API_TIMEOUT_MS`);
  - validação de JSON obrigatório;
  - classificação de erro (`network`, `timeout`, `contract`, `parse`, `http`);
  - sanitização de mojibake em campos textuais;
  - fallback seguro para catálogo quando a API principal falha.

- Novo `src/lib/catalog-fallback.ts`:
  - base de contingência derivada de `data/grankasa_catalog_enriched.json`;
  - sem dados arbitrários inventados;
  - mantém Home/Locação/Vendas navegáveis em falha de backend.

### UI/UX (UI UX PRO MAX)
- `src/components/FeaturedProperties.tsx`:
  - correção de acentuação;
  - melhoria de estados de erro/empty/loading;
  - aviso visual quando usa fallback de contingência.

- `src/components/ImoveisListPage.tsx`:
  - filtros com labels explícitos;
  - botão de limpar filtros;
  - chips de filtros ativos;
  - feedback de atualização de resultados;
  - estados de erro e vazio com CTA útil;
  - aviso de contingência quando dados vêm de fallback.

- `src/components/PropertyGridSkeleton.tsx`:
  - loading mais informativo, com `aria-busy` e label contextual.

- `src/pages/Locacao.tsx` e `src/pages/Venda.tsx`:
  - textos refinados com acentuação correta.

- `src/App.tsx`:
  - rota compatível adicional `/inicio`.

### Backend / Observabilidade
- `routes/imoveis.py`:
  - logs estruturados com tempo de resposta, filtros e contagem por endpoint.

- `main.py` e `app/main.py`:
  - `/health` com `service: agente_imobiliario_api` para validação de alvo correto.

### Banco/Seed
- `seeds/imoveis_seed.py`:
  - reforço para garantir base mínima balanceada (`locacao` e `venda`);
  - proteção para normalização de texto com possível mojibake;
  - log de origem da seed (`legacy_audit` ou `curated_default`).

- `db.py`:
  - log explícito de reset de schema legado e status de inicialização.

## Flags e toggles

- `VITE_API_TIMEOUT_MS=12000`
- `VITE_ENABLE_CATALOG_FALLBACK=true`
- `VITE_ENABLE_BACKEND_DISCOVERY=false` (padrão conservador para evitar varredura longa de portas e loading prolongado)

## Ajustes adicionais de estabilização

- `core/logging.py`:
  - correção no sanitizador de logs para preservar `record.args` quando o logger recebe argumento `dict`.
  - evita quebra de formatação de logs no pytest e em handlers compartilhados.

- `seeds/imoveis_seed.py`:
  - normalização defensiva de `ano_construcao` para bloquear valores inválidos do legado (ex.: `19880`).
  - mantém compatibilidade com o schema (`<= ano atual + 1`) sem remover endpoints nem contratos.

## Limitações conhecidas

- Se nenhum backend compatível estiver ativo e fallback estiver desativado, as telas voltam a depender exclusivamente da API.
- O fallback local não substitui integrações transacionais; ele é contingência de catálogo para navegação.

## Próximos passos recomendados

1. Padronizar porta de backend no time (ex.: 8001 ou 8010) para evitar colisão local.
2. Adicionar endpoint de observabilidade dedicado para ingestão de métricas do frontend (opcional).
3. Evoluir fallback para cache com validade temporal e invalidação automática.
