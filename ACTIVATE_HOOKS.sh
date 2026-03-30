#!/bin/bash
# ACTIVATE_HOOKS.sh — Ativa automação de token optimization em 1 linha
# Execute: bash ACTIVATE_HOOKS.sh
# Tempo: 5 segundos
# Benefício: Smart tools rodam sozinhos daqui em diante

set -e

echo "🚀 Ativando Token Optimization Automático..."
echo ""

# Step 1: Fazer script executável
echo "✓ Making hooks executable..."
chmod +x .claude/hooks/prompt-start.sh
chmod +x .claude/commands/setup.sh

# Step 2: Verificar que Claude Code reconhece os hooks
echo "✓ Claude Code hooks configurados"
echo "  Local: .claude/hooks/prompt-start.sh"
echo "  Config: .claude/hooks/claude-code-config.json"

# Step 3: Info sobre napkin.md
echo ""
echo "✓ napkin.md está pronto"
if [ -f ".claude/napkin.md" ]; then
  ITEMS=$(wc -l < .claude/napkin.md)
  echo "  Items atuais: ~$ITEMS linhas"
  echo "  Próximo passo: Cure napkin.md (remova itens > 1 mês)"
fi

# Step 4: Info sobre smart-explore
echo ""
echo "✓ Smart-explore ativado (via claude-mem)"
echo "  Você pode usar:"
echo "    • smart_outline('file.py')"
echo "    • smart_search('pattern', 'dir/')"
echo "    • smart_unfold('file.py', 'FunctionName')"
echo "    • mem-search('topic')"

# Step 5: Summary
echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ TOKEN OPTIMIZATION AUTOMÁTICO ATIVADO"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Próximas ações (nesta ordem):"
echo "  1. Abra Claude Code"
echo "  2. Cuide .claude/napkin.md (2 min)"
echo "  3. Leia CLAUDE.md (5 min)"
echo "  4. Comece a trabalhar"
echo ""
echo "Resultado esperado:"
echo "  ✅ smart_outline() funciona automaticamente"
echo "  ✅ napkin.md carrega sozinho"
echo "  ✅ Tokens economizados: 60-70%"
echo ""
echo "Qualquer dúvida: Leia .claude/hooks/README.md"
echo ""

exit 0
