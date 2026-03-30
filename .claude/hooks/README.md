# Claude Code Hooks — Validação de Ambiente

**O que estes hooks fazem:** validam se arquivos críticos existem e geram um relatório de status.

**O que estes hooks NÃO fazem:** não ativam smart tools automaticamente, não controlam como o agente usa ferramentas, não garantem economia de tokens.

---

## Arquivos

### `prompt-start.sh`
Script de validação que roda no início da sessão (se o Claude Code reconhecer os hooks).

O que ele faz:
- Verifica se `.claude/napkin.md`, `CLAUDE.md` e `claude-code-config.json` existem
- Detecta se `smart_outline`, `smart_search`, `mem-search` estão no PATH
- Gera `.claude/runtime/session-status.md` com os resultados
- Emite aviso no stderr se napkin.md está grande (>100 linhas)
- Sai com código 0 em condições normais

O que ele não faz:
- Não "ativa" nenhuma tool
- Não injeta contexto no modelo
- Não garante que o agente vai usar smart tools

### `claude-code-config.json`
Configuração mínima de hooks. Define qual script rodar em `onSessionStart` e `onPromptSubmit`.

**Importante:** esta configuração só tem efeito se o Claude Code reconhecer e suportar o formato `claude-code-config.json`. Isso não está garantido sem teste explícito.

### `test-hooks.sh`
Script de teste local para verificar se o sistema funciona.

---

## Como ativar

```bash
chmod +x .claude/hooks/prompt-start.sh
chmod +x .claude/hooks/test-hooks.sh
```

---

## Como testar localmente

```bash
bash .claude/hooks/test-hooks.sh
```

Saída esperada:
```
=== Hook System Test ===

[ Syntax ]
  PASS  prompt-start.sh syntax valid

[ Permissions ]
  PASS  prompt-start.sh is executable

[ Execution ]
  PASS  prompt-start.sh exits with code 0

[ Status File ]
  PASS  session-status.md was generated
  PASS  session-status.md has timestamp

[ Critical Files ]
  PASS  .claude/napkin.md exists
  PASS  CLAUDE.md exists
  PASS  .claude/hooks/claude-code-config.json exists

[ Commands (informational) ]
  INFO  smart_outline: available (or not found)
  ...

=== Results: 7 passed, 0 failed ===
Status: PASS
```

---

## Como verificar se os hooks rodaram em uma sessão

1. Após abrir o Claude Code, verifique se `.claude/runtime/session-status.md` existe
2. Confira o timestamp no arquivo — deve ser próximo do horário de início da sessão
3. Se o arquivo não existir ou o timestamp for antigo, os hooks **não rodaram**

```bash
cat .claude/runtime/session-status.md
```

---

## Limitações conhecidas

| Limitação | Detalhe |
|-----------|---------|
| Hooks podem não rodar | Claude Code pode não reconhecer `claude-code-config.json` automaticamente |
| Smart tools não se ativam sozinhas | Disponibilidade no PATH ≠ uso automático pelo agente |
| Economia de tokens não é medida | O script não tem como medir tokens |
| Comportamento do agente não é controlável via shell | Decisões de usar `smart_outline` são do modelo, não do script |

---

## Troubleshooting

**Hooks não parecem rodar:**
1. Verifique se o script é executável: `ls -la .claude/hooks/prompt-start.sh`
2. Rode o teste: `bash .claude/hooks/test-hooks.sh`
3. Se o teste passa mas hooks não rodam na sessão, o Claude Code pode não suportar `claude-code-config.json` nessa versão

**session-status.md não é gerado:**
1. Rode manualmente: `bash .claude/hooks/prompt-start.sh`
2. Verifique se há erro de permissão ou PATH incorreto

**smart_outline não encontrado:**
- Verifique se `claude-mem` ou `smart-explore` está instalado globalmente
- Rode: `npm list -g` para ver packages globais
