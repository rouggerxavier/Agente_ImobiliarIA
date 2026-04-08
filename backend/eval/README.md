# Dataset sintetico de avaliacao

Arquivo principal: `eval/conversations.jsonl`

## Runner

Executa a avaliacao com:

```bash
python eval/run_eval.py --limit 100 --strict
```

Opcoes uteis:

- `--use-llm`: avalia com LLM ligado.
- `--allow-search`: desliga `TRIAGE_ONLY` durante o run.
- `--output eval/report.json`: salva relatorio JSON.
- `--baseline eval/baseline.json --strict`: aplica gate por baseline e falha se regredir.

## Preparacao (proximas camadas)

- Backfill canônico de base legada (preview):
  - `python scripts/geo_backfill_preview.py`
  - `python scripts/geo_backfill_preview.py --write`
- Comparativo lexical vs embeddings (quando tiver `OPENAI_API_KEY`):
  - `python scripts/compare_retrieval_modes.py --limit 100`

## Objetivo

- Validar roteamento entre `TRIAGE` e `QA_INTERRUPT`.
- Validar atualizacao de slots criticos.
- Validar selecao de dominio/topico esperado para busca de conhecimento.

## Schema por linha (JSONL)

- `id`: identificador do caso.
- `intent`: `comprar` ou `alugar`.
- `messages`: lista de mensagens do usuario (ordem conversacional).
- `expected.route`: `TRIAGE` ou `QA_INTERRUPT`.
- `expected.slots_should_update`: slots esperados apos as mensagens.
- `expected.topics_should_use`: topicos que deveriam ser buscados.
- `expected.domain_should_use`: `institutional`, `geo` ou `none`.
- `expected.city`: cidade esperada (quando houver).
- `expected.neighborhood`: bairro esperado (quando houver).
- `expected.should_use_sources`: fontes internas esperadas.
