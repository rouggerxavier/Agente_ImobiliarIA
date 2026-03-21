# Fase 2 - Implementacao (Enriquecimento de Catalogo)

## Objetivo
Elevar a fidelidade dos dados de imoveis para aproximar o comportamento do sistema ao site de referencia, com foco em detalhe de catalogo.

## Escopo inicial desta fase
1. Extrair campos de detalhe por imovel a partir de `url_detalhada`:
- descricao longa
- condominio
- IPTU
- area
- salas
- ano de construcao
- numero de andares
- elevadores
- dependencias
- video e mapa (quando houver)

2. Gerar base enriquecida local:
- `data/grankasa_catalog_enriched.json`
- `data/grankasa_catalog_enriched_meta.json`

3. Fazer o seed consumir preferencialmente a base enriquecida, mantendo fallback para base auditada.

## Implementado agora
1. Script de enriquecimento:
- `scripts/enrich_grankasa_catalog.py`

2. Seed atualizado para priorizar:
- `data/grankasa_catalog_enriched.json`
- fallback: `data/grankasa_catalog_audit.json`

3. Normalizacoes adicionais no seed:
- cidade (`RJ` => `Rio de Janeiro`)
- finalidade valida (`COMERCIAL`, `MISTO`, `RESIDENCIAL`)
- parse de condominio/IPTU/salas/ano/andares/elevadores/dependencias

## Execucao desta rodada da Fase 2
1. Script executado em lote:
- `python scripts/enrich_grankasa_catalog.py --sleep 0 --timeout 10`
- saida: `data/grankasa_catalog_enriched.json` com 127 itens.
- meta: `data/grankasa_catalog_enriched_meta.json`.

2. Cobertura apos enriquecimento:
- `descricao_longa`: 119
- `condominio`: 113
- `iptu`: 118
- `area`: 119
- `ano_construcao`: 119
- `elevadores`: 119
- `dependencias`: 119
- `video_url`: 75
- `mapa_url`: 119

3. Validacao API:
- `GET /imoveis/locacao` e `GET /imoveis/venda` retornando dados enriquecidos (condominio/iptu/fonte).
- `GET /imoveis/filtros` retornando facetas.

## Proximos passos da Fase 2
1. Tratar os 8 casos com timeout da coleta para elevar cobertura.
2. Melhorar captura de `salas` e `numero_andares` (campos com baixa qualidade no HTML de origem).
3. Aplicar verificacao E2E visual do detalhe de imovel com a nova base.
