# Quick Setup

## 1. Torne os scripts executáveis e teste

```bash
chmod +x .claude/hooks/prompt-start.sh
chmod +x .claude/hooks/test-hooks.sh
bash .claude/hooks/test-hooks.sh
```

Se tudo passar, o ambiente está validado.

## 2. Verifique o status gerado

```bash
cat .claude/runtime/session-status.md
```

Mostra quais arquivos existem e quais comandos estão disponíveis.

## 3. Leia os guias operacionais

- `CLAUDE.md` — regras do projeto, estrutura de camadas, workflows
- `.claude/napkin.md` — contexto da sessão (curar a cada sessão, 2 min)
- `.claude/commands/workflow-checklist.md` — antes de cada tarefa

## O que é automático vs. manual

| Automático (se hooks rodarem no Claude Code) | Manual |
|----------------------------------------------|--------|
| Geração de `session-status.md` | Curar `napkin.md` toda sessão |
| Alerta se `napkin.md` está grande | Pedir ao agente para usar `smart_outline` |
| Detecção de comandos no PATH | Verificar o status gerado |

**Nota:** hooks só rodam automaticamente se o Claude Code suportar `claude-code-config.json`. Para verificar, confira o timestamp em `session-status.md` após abrir o projeto.
