# Automation Summary — O que é real vs. o que depende do agente

**Última atualização:** 2026-03-30

---

## O que está realmente implementado

### Hooks de validação (real, testável)
O script `.claude/hooks/prompt-start.sh` roda no início da sessão **se o Claude Code reconhecer o hook**.

O que ele faz de forma observável:
- Verifica se `.claude/napkin.md`, `CLAUDE.md` e `claude-code-config.json` existem
- Detecta se `smart_outline`, `smart_search`, `mem-search` estão no PATH
- Gera `.claude/runtime/session-status.md` com timestamp e resultados
- Emite aviso se `napkin.md` está grande

**Como verificar:** após abrir o projeto, rode:
```bash
cat .claude/runtime/session-status.md
```
Se o arquivo existe com timestamp recente, o hook rodou.

---

## O que NÃO está implementado (e não pode estar via shell)

| Afirmação anterior | Realidade |
|-------------------|-----------|
| "smart_outline ativa automaticamente" | Falso. O agente decide usar ou não. |
| "hooks ativam smart tools" | Falso. Shell scripts não controlam decisões do modelo. |
| "60-70% de economia automática" | Não medido. Depende do comportamento do agente. |
| "napkin.md carrega automaticamente" | Depende do `claude-mem` estar instalado e configurado. |
| "token optimization roda antes de cada prompt" | O script roda, mas não altera como o agente processa. |

---

## O que pode melhorar economia de tokens (real)

Estes são mecanismos que funcionam se você os usar ativamente:

1. **napkin.md bem curado** — contexto conciso carregado no início da sessão. Menos linhas = menos tokens lidos.
2. **CLAUDE.md como instrução operacional** — o modelo lê e segue. As regras sobre usar `smart_outline` first são instruções que o agente pode seguir.
3. **Pedir explicitamente** — dizer "use smart_outline antes de ler" funciona de forma confiável.
4. **Workflows documentados** — os checklists em `.claude/commands/` funcionam se você os seguir.

---

## Fluxo real de uma sessão

```
Você abre o Claude Code
  → (Se hooks funcionarem) prompt-start.sh roda
  → session-status.md é gerado
  → Você vê se arquivos críticos estão OK

Você começa a trabalhar
  → Agente lê CLAUDE.md (se estiver no contexto ou você mencionar)
  → Agente pode ou não usar smart_outline, dependendo das instruções
  → napkin.md está disponível, mas o agente precisa lê-lo

Você curou napkin.md antes da sessão (2 min)
  → Contexto mais conciso = menos tokens na leitura inicial
  → Isso sim tem impacto direto mensurável
```

---

## Como testar o que funciona

```bash
# 1. Teste os hooks localmente
bash .claude/hooks/test-hooks.sh

# 2. Verifique o status após abrir o projeto no Claude Code
cat .claude/runtime/session-status.md

# 3. Compare o timestamp com o horário de abertura da sessão
```

Se `session-status.md` existe com timestamp correto → hooks funcionaram.
Se não existe → hooks não rodaram (Claude Code pode não suportar o formato).

---

## Resumo honesto

| Componente | Status | Como verificar |
|------------|--------|----------------|
| `prompt-start.sh` valida ambiente | Implementado | `bash test-hooks.sh` |
| `session-status.md` gerado | Implementado | `cat .claude/runtime/session-status.md` |
| Hooks rodam no Claude Code | Não testado | Verificar timestamp após abrir sessão |
| smart tools ativam automaticamente | Não é possível via shell | — |
| Economia de tokens automática | Não mensurável via script | Curar napkin.md é o que funciona |
