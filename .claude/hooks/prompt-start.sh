#!/bin/bash
# prompt-start.sh — Validação de ambiente para sessão Claude Code
# O que este script FAZ: valida arquivos críticos, detecta comandos disponíveis,
#                        gera relatório de status em .claude/runtime/session-status.md
# O que este script NÃO FAZ: não ativa smart tools, não controla decisões do modelo,
#                             não garante economia de tokens

set -euo pipefail

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNTIME_DIR="$PROJECT_ROOT/.claude/runtime"
STATUS_FILE="$RUNTIME_DIR/session-status.md"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

mkdir -p "$RUNTIME_DIR"

# ==============================================================================
# INICIALIZA RELATÓRIO
# ==============================================================================
cat > "$STATUS_FILE" <<EOF
# Session Status
Generated: $TIMESTAMP

## Critical Files
EOF

# ==============================================================================
# VALIDA ARQUIVOS CRÍTICOS
# ==============================================================================
FILES_OK=0
FILES_MISSING=0

check_file() {
  local path="$1"
  local label="$2"
  if [ -f "$PROJECT_ROOT/$path" ]; then
    echo "- [OK] $label ($path)" >> "$STATUS_FILE"
    FILES_OK=$((FILES_OK + 1))
  else
    echo "- [MISSING] $label ($path)" >> "$STATUS_FILE"
    FILES_MISSING=$((FILES_MISSING + 1))
  fi
}

check_file ".claude/napkin.md"            "napkin.md"
check_file "CLAUDE.md"                    "CLAUDE.md"
check_file ".claude/hooks/claude-code-config.json" "hook config"

# ==============================================================================
# VALIDA NAPKIN.MD — avisa se muito grande
# ==============================================================================
NAPKIN_PATH="$PROJECT_ROOT/.claude/napkin.md"
if [ -f "$NAPKIN_PATH" ]; then
  LINE_COUNT=$(wc -l < "$NAPKIN_PATH" 2>/dev/null || echo "0")
  echo "" >> "$STATUS_FILE"
  echo "## napkin.md" >> "$STATUS_FILE"
  echo "- Lines: $LINE_COUNT" >> "$STATUS_FILE"
  if [ "$LINE_COUNT" -gt 100 ]; then
    echo "- Warning: file is large (>100 lines). Consider curating to keep it focused." >> "$STATUS_FILE"
    echo "⚠️  napkin.md has $LINE_COUNT lines — consider curating before working." >&2
  fi
fi

# ==============================================================================
# DETECTA COMANDOS DISPONÍVEIS
# ==============================================================================
cat >> "$STATUS_FILE" <<EOF

## Available Commands
EOF

check_cmd() {
  local cmd="$1"
  if command -v "$cmd" > /dev/null 2>&1; then
    echo "- [AVAILABLE] $cmd" >> "$STATUS_FILE"
  else
    echo "- [NOT FOUND] $cmd" >> "$STATUS_FILE"
  fi
}

check_cmd "smart_outline"
check_cmd "smart_search"
check_cmd "mem-search"
check_cmd "npx"
check_cmd "python3"
check_cmd "pytest"

# ==============================================================================
# RESUMO FINAL
# ==============================================================================
cat >> "$STATUS_FILE" <<EOF

## Summary
- Files OK: $FILES_OK
- Files Missing: $FILES_MISSING
- Status: $([ "$FILES_MISSING" -eq 0 ] && echo "READY" || echo "DEGRADED — some files missing")

## Notes
- This script validates environment only.
- smart_outline/smart_search availability does NOT mean they will be used automatically.
- Token optimization depends on how the agent behaves during the session.
- To verify hooks ran: check timestamp above matches your session start time.
EOF

# Saída visível somente se há problemas
if [ "$FILES_MISSING" -gt 0 ]; then
  echo "⚠️  $FILES_MISSING critical file(s) missing. See .claude/runtime/session-status.md" >&2
fi

exit 0
