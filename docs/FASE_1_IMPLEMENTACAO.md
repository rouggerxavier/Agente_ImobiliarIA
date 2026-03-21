# Fase 1 - Implementacao (Paridade Base)

## Objetivo
Estabelecer a base de paridade funcional entre o projeto e o site de referencia, sem quebrar compatibilidade dos endpoints existentes.

## Escopo da Fase 1
1. Catalogo:
- ampliar base de imoveis usando auditoria (`data/grankasa_catalog_audit.json`);
- normalizar campos essenciais para busca e listagem (`codigo`, `tipo_negocio`, `bairro`, `cidade`, `categoria`, `finalidade`, `preco`).

2. Busca e listagem:
- adicionar filtros utilitarios no backend;
- expor endpoint de facetas para frontend.

3. Contato:
- substituir mock de formularios por persistencia real em backend.

4. Runtime web:
- corrigir fallback SPA para evitar 404 em rotas client-side diretas.

## Implementado nesta fase
1. Backend de imoveis:
- filtros adicionais em `/imoveis`, `/imoveis/locacao`, `/imoveis/venda`, `/imoveis/busca`;
- novo endpoint: `GET /imoveis/filtros`.

2. Modelagem/persistencia:
- novos campos no modelo `Imovel`: `categoria`, `finalidade`, `fonte_url`, `video_url`, `mapa_url`;
- ajuste de reset de schema SQLite para suportar novas colunas.

3. Seed catalogo:
- seed passa a priorizar arquivo auditado;
- normalizacao de dados em `seeds/imoveis_seed.py` (inclui ajustes de cidade/finalidade nesta fase).

4. Contato/newsletter:
- novos endpoints:
  - `POST /contato`
  - `POST /newsletter`
- persistencia em:
  - `data/contact_messages.jsonl`
  - `data/newsletter_subscriptions.jsonl`

5. Frontend:
- rotas alias para paridade de navegacao (`/a-empresa`, `/vendas`);
- busca com filtros e paginacao;
- formularios conectados aos endpoints reais.

6. Fallback SPA:
- `main.py` com `SPAStaticFiles` para servir `index.html` em rotas desconhecidas do cliente.

## Endpoints legados preservados
- `POST /webhook`
- `GET /health`
- `GET/POST /webhook/whatsapp`
- `GET /imoveis`
- `GET /imoveis/locacao`
- `GET /imoveis/venda`
- `GET /imoveis/busca`
- `GET /imoveis/codigo/{codigo}`
- `GET /imoveis/{imovel_id}`
- `POST /imoveis`

## Validacao executada
1. `pytest -q tests/test_imoveis_api.py tests/test_endpoints.py`
2. `npm run build`
3. `npm run test -- --run`
4. smoke de endpoints impactados via `TestClient` (`/health`, `/imoveis/filtros`, `/imoveis/busca`, `/contato`, `/newsletter`)

## Fora da Fase 1 (proxima fase)
1. Enriquecimento completo do detalhe de imovel por scraping aprofundado de cada pagina.
2. Refino de conteudo institucional para equivalencia textual completa.
3. Ajustes de deploy (Render) e validacao E2E em ambiente publico.
