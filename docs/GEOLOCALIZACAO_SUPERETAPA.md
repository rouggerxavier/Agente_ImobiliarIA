# Superetapa de Geolocalizacao (Legado -> Novo Site)

## Resumo
- Objetivo: replicar localizacoes do legado `grankasa.com.br` para os imoveis ja persistidos no novo sistema, com matching auditavel, persistencia segura e validacao E2E com evidencias.
- Resultado consolidado: ver [`docs/evidencias/geolocalizacao_auditoria.json`](./evidencias/geolocalizacao_auditoria.json).

## Arquitetura operacional
- Orquestrador: [`agent/multiagent/geolocation_pipeline.py`](../agent/multiagent/geolocation_pipeline.py)
- Subagentes implementados no pipeline:
  - `legacy_discovery_subagent`: carrega catalogo legado enriquecido e tenta completar `mapa_url` faltante.
  - `matching_subagent`: faz conciliacao por `codigo` (exato) e fallback por similaridade (provavel/ambiguo/nao_encontrado).
  - `persistence_subagent`: aplica enrichment e persiste localizacao sem quebrar contratos existentes.
  - `validation_e2e_subagent`: cruza persistencia com evidencias E2E (screenshots por imovel).
- Handoff controlado:
  - quando `mapa_url` esta ausente no legado enriquecido, o fluxo delega correcao para descoberta HTTP no detalhe do imovel legado.

## Matching e confianca
- Status suportados:
  - `exato`
  - `provavel`
  - `ambiguo`
  - `nao_encontrado`
- Politica conservadora:
  - persistencia padrao apenas para `exato`;
  - `provavel` so persiste com `--persist-probable`.

## Persistencia e schema
- Modelo expandido em [`models/imovel.py`](../models/imovel.py) com campos de localizacao:
  - `uf`, `endereco`, `endereco_formatado`, `logradouro`, `numero`, `complemento`, `cep`, `ponto_referencia`
  - `latitude`, `longitude`
  - `localizacao_precisao`, `localizacao_origem`, `localizacao_status`, `localizacao_score`, `localizacao_raw_*`
- Migração incremental sem quebra:
  - [`db.py`](../db.py) adiciona colunas ausentes via `ALTER TABLE ... ADD COLUMN` e preserva dados.

## Renderizacao no frontend
- API cliente e formatacao de localizacao:
  - [`src/lib/imoveis-api.ts`](../src/lib/imoveis-api.ts)
- Listagem:
  - [`src/components/ImovelListingCard.tsx`](../src/components/ImovelListingCard.tsx)
- Detalhe do imovel:
  - [`src/pages/ImovelDetalhe.tsx`](../src/pages/ImovelDetalhe.tsx)

## Validacao E2E e evidencias
- Screenshots por imovel:
  - pasta [`docs/evidencias/screenshots`](./evidencias/screenshots)
- Mapa de screenshots:
  - [`docs/evidencias/geolocalizacao_screenshots.json`](./evidencias/geolocalizacao_screenshots.json)
- Auditoria final por imovel:
  - [`docs/evidencias/geolocalizacao_auditoria.json`](./evidencias/geolocalizacao_auditoria.json)

## Como reproduzir
1. Sincronizar geolocalizacao:
```bash
python scripts/run_geolocation_superstage.py \
  --screenshots-json docs/evidencias/geolocalizacao_screenshots.json
```

2. Rodar testes principais da superetapa:
```bash
python -m pytest tests/test_imovel_geo_sync.py tests/test_geolocation_pipeline.py tests/test_imoveis_api.py tests/test_catalog_stability.py -q
npm test -- src/lib/imoveis-api.test.ts src/components/ImoveisListPage.test.tsx src/pages/ImovelDetalhe.test.tsx
npm run build
```

## Limitacoes atuais
- Coordenadas (`latitude/longitude`) so sao preenchidas quando a fonte as expuser no `mapa_url`/query; nao ha geocoding inventado.
- Parte da base legado entrega localizacao textual (endereco aproximado) sem ponto exato.
- O fluxo prioriza seguranca: nao promove match ambiguo como confirmado.
