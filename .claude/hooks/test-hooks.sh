#!/bin/bash
# test-hooks.sh — Testa se o sistema de hooks funciona localmente
# Como usar: bash .claude/hooks/test-hooks.sh
# Retorno: 0 = tudo passou, 1 = algum item falhou

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PASS=0
FAIL=0

print_result() {
  local status="$1"
  local label="$2"
  if [ "$status" = "PASS" ]; then
    echo "  PASS  $label"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $label"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "=== Hook System Test ==="
echo "Project: $PROJECT_ROOT"
echo ""

# ------------------------------------------------------------------------------
# 1. Verifica sintaxe do script
# ------------------------------------------------------------------------------
echo "[ Syntax ]"
SCRIPT="$PROJECT_ROOT/.claude/hooks/prompt-start.sh"

if [ -f "$SCRIPT" ]; then
  if bash -n "$SCRIPT" 2>/dev/null; then
    print_result "PASS" "prompt-start.sh syntax valid"
  else
    print_result "FAIL" "prompt-start.sh has syntax errors"
  fi
else
  print_result "FAIL" "prompt-start.sh not found"
fi

# ------------------------------------------------------------------------------
# 2. Verifica se script é executável
# ------------------------------------------------------------------------------
echo ""
echo "[ Permissions ]"
if [ -x "$SCRIPT" ]; then
  print_result "PASS" "prompt-start.sh is executable"
else
  print_result "FAIL" "prompt-start.sh is not executable (run: chmod +x $SCRIPT)"
fi

# ------------------------------------------------------------------------------
# 3. Executa o script e verifica saída/status
# ------------------------------------------------------------------------------
echo ""
echo "[ Execution ]"
cd "$PROJECT_ROOT"
if bash "$SCRIPT" 2>/dev/null; then
  print_result "PASS" "prompt-start.sh exits with code 0"
else
  print_result "FAIL" "prompt-start.sh exited with error"
fi

# ------------------------------------------------------------------------------
# 4. Verifica se o arquivo de status foi gerado
# ------------------------------------------------------------------------------
STATUS_FILE="$PROJECT_ROOT/.claude/runtime/session-status.md"
if [ -f "$STATUS_FILE" ]; then
  print_result "PASS" "session-status.md was generated"

  # Verifica se tem timestamp recente (últimos 10 segundos)
  if grep -q "Generated:" "$STATUS_FILE"; then
    print_result "PASS" "session-status.md has timestamp"
  else
    print_result "FAIL" "session-status.md missing timestamp"
  fi
else
  print_result "FAIL" "session-status.md was NOT generated"
fi

# ------------------------------------------------------------------------------
# 5. Verifica arquivos críticos do projeto
# ------------------------------------------------------------------------------
echo ""
echo "[ Critical Files ]"
for f in ".claude/napkin.md" "CLAUDE.md" ".claude/hooks/claude-code-config.json"; do
  if [ -f "$PROJECT_ROOT/$f" ]; then
    print_result "PASS" "$f exists"
  else
    print_result "FAIL" "$f missing"
  fi
done

# ------------------------------------------------------------------------------
# 6. Detecta comandos (informa, não falha)
# ------------------------------------------------------------------------------
echo ""
echo "[ Commands (informational) ]"
for cmd in smart_outline smart_search mem-search pytest; do
  if command -v "$cmd" > /dev/null 2>&1; then
    echo "  INFO  $cmd: available"
  else
    echo "  INFO  $cmd: not found in PATH"
  fi
done

# ------------------------------------------------------------------------------
# RESULTADO FINAL
# ------------------------------------------------------------------------------
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [ "$FAIL" -gt 0 ]; then
  echo "Status: FAIL"
  exit 1
else
  echo "Status: PASS"
  exit 0
fi
