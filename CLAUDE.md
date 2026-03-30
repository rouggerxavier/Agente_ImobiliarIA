# 🚀 Claude Code — Operational Guide for Agente ImobiliarIA V2

**Last Updated:** 2026-03-30
**Token Optimization Level:** Advanced (60-70% reduction)

---

## ⚡ QUICK START (Read This First)

### Before every session:
```bash
# 1. Ensure napkin.md is fresh (max 10 items per section)
# 2. Use smart-explore instead of reading large files
# 3. Mention library names for context7 to fetch live docs
```

### Token budget per task:
| Task | Budget | Pattern |
|------|--------|---------|
| Bug fix | 2K tokens | Search code → identify → fix → test |
| Feature | 5K tokens | Plan → implement → test |
| Refactor | 8K tokens | Analyze → plan → implement → verify |
| Code review | 3K tokens | Use `/review-code` not manual reads |

---

## 📋 PROJECT STRUCTURE & CONSTRAINTS

### Current State
- **Backend:** FastAPI @ port `8010` (NOT 8000)
- **Frontend:** Vite @ port `8080`
- **DB:** SQLite auto-initialized at `data/imoveis.db`
- **Architecture:** Hexagonal (domain → application → infrastructure → interfaces)

### DO's ✅
- Use `domain/`, `application/`, `infrastructure/`, `interfaces/` for new code
- Keep `agent/` code as legacy (do NOT extend)
- Structure as case-of-use → call logic
- Create `.md` docs → Link in napkin.md
- Test locally with `pytest` before suggesting

### DON'Ts ❌
- Do NOT import across layer boundaries (domain must stay pure)
- Do NOT modify `core/config.py` without review
- Do NOT create new top-level folders without architecture approval
- Do NOT suggest changes to already-working code (no premature refactoring)

---

## 🧠 SMART CONTEXT LOADING (Token Optimization)

### Pattern 1: Code Exploration
```
❌ OLD: "Read src/application/uc_process_message.py"
         → Wastes 800 tokens on full file

✅ NEW: smart_outline("src/application/uc_process_message.py")
        → Get structure in ~100 tokens
        → Then smart_unfold() for specific parts
```

### Pattern 2: Architecture Questions
```
❌ OLD: Ask about architecture
        → I re-read ARCHITECTURE.md every time (400 tokens wasted)

✅ NEW: I load domain/application/infrastructure layer rules
        → Reference napkin.md for constraints
        → Ask specific questions about layers
```

### Pattern 3: Config & Environment
```
❌ OLD: "What's the backend port?"
        → I search through code (300 tokens)

✅ NEW: Check napkin.md first (already has it)
        → Falls back to code search only if needed
```

### Pattern 4: Feature Requests
```
❌ OLD: "Add a new field"
        → I read ARCHITECTURE.md → domain/ → application/ → infrastructure/
        → 2000+ tokens to understand layers

✅ NEW: Use case-of-use pattern:
        1. Define intent in application/
        2. Extend domain/ entities
        3. Add infrastructure/ adapters
        4. Expose in interfaces/
```

---

## 🛠️ COMMAND REFERENCE

### Built-in Skills (Already Installed)
```bash
# Search cross-session memory
mem-search "authentication bug"

# Get file structure (token-efficient)
smart_outline("src/components/Button.tsx")

# Search code symbols
smart_search("useState", "./src")

# Quick code review
/review-code src/auth.ts

# Project history
/timeline-report
```

### Custom Commands (Create in `.claude/commands/`)
```bash
# See scripts section below
```

---

## 📊 CONTEXT ENGINEERING FOR THIS PROJECT

### What context stays ALWAYS ACTIVE
1. **napkin.md** - Loaded automatically (every session)
2. **ARCHITECTURE.md** (first 100 lines) - Reference only
3. **Layer structure** - Mental model, don't read full files

### What context loads ON-DEMAND
1. **Specific application/uc_*.py** - Load with smart_outline() first
2. **Domain entities** - Reference from memory, not re-read
3. **API routes** - smart_search() instead of full file read
4. **Tests** - Only read relevant test function

### What context NEVER loads
1. node_modules/ (except npm package.json)
2. dist/ or __pycache__/
3. Old commits (use git log instead)

---

## 🔧 YOUR WORKFLOW IN PRACTICE

### Workflow A: Bug Fix
```
1. User describes bug
2. I search code with smart_search()
3. Identify file → smart_outline() → identify function
4. Read ONLY that function (Edit tool)
5. Fix + create test
6. Verify with pytest
```
**Expected tokens: 1500-2500**

### Workflow B: New Feature
```
1. User describes feature
2. I create implementation plan (not detailed code)
3. You approve plan
4. I implement in order:
   a. Extend domain/ entity
   b. Create application/ use-case
   c. Add infrastructure/ adapter
   d. Expose in interfaces/ endpoint
5. Test end-to-end
```
**Expected tokens: 4000-6000**

### Workflow C: Code Review
```
1. Use /review-code [file] (not manual read)
2. Semgrep for security checks (if needed)
3. Focus on logic + architecture fit
```
**Expected tokens: 2000-3000**

---

## 🎯 RULES FOR TOKEN OPTIMIZATION

### Rule 1: No Re-Reading Files
- If I've read a file this session → refer to it by name
- If you modified it → ask me to re-read with smart_unfold()
- Do NOT let me just re-read files "to be sure"

### Rule 2: Smart Tool Use
| Task | Use This | NOT This |
|------|----------|----------|
| See file structure | smart_outline() | Read full file |
| Search code | smart_search() or Grep | Read multiple files |
| Find function | smart_unfold() | Read entire module |
| Quick syntax check | smart_outline() + Read (20 lines) | Read full file |

### Rule 3: Cache Context
- Architectural decisions → mention once → I remember
- Domain entities → describe structure → I reference
- API patterns → show example → I follow pattern

### Rule 4: Compress Prompts
- Do NOT paste entire error messages → summarize
- Do NOT ask "read this whole PR" → link + ask specific question
- Do NOT ask me to "review all files" → pick 2-3 critical ones

---

## 💾 PERSISTENCE & MEMORY

### claude-mem (Cross-Session Memory)
```
✅ Already installed
✅ Activated automatically
✅ Searches previous work with mem-search

Usage:
mem-search "WhatsApp integration"
→ Returns relevant sessions + observations
→ I can reference without re-reading
```

### napkin.md (Session-Fresh Context)
```
✅ Already exists (.claude/napkin.md)
✅ Curate at START of each session (remove stale, keep top 10/section)

Sections:
1. Execution & Validation (guardrails)
2. Shell & Command Reliability
3. Domain Behavior
4. User Directives
```

---

## 🔍 FILE MAP (Don't Memorize — Reference)

```
Agente_ImobiliarIA_V2/
├── docs/
│   ├── ARCHITECTURE.md        ← Layer structure, dependencies
│   └── MACROARCHITECTURE.md   ← High-level product decisions
├── domain/                     ← Pure entities, no imports
│   ├── entities.py
│   └── ports.py
├── application/                ← Use cases (import only domain)
│   └── uc_*.py
├── infrastructure/             ← Adapters (import domain + external)
│   ├── persistence/
│   ├── llm/
│   └── whatsapp/
├── interfaces/                 ← HTTP, webhooks (import app + infra)
│   ├── api/
│   └── webhooks/
├── agent/ (legacy)             ← Old code, don't extend
├── core/                       ← Config, logging, shared
├── knowledge/                  ← FAQ, geo data
├── .claude/
│   ├── napkin.md              ← Curated guidance (update every session)
│   └── commands/              ← Custom scripts (create as needed)
└── data/
    └── imoveis.db             ← Auto-created by FastAPI startup
```

---

## 🚀 SETUP CHECKLIST (Do These Once)

### ✅ Already Done
- [x] Claude Code plugin installed
- [x] claude-mem activated
- [x] smart-explore available
- [x] napkin.md created
- [x] This file (CLAUDE.md)

### 📦 Optional (Install if You Want)

#### For real-time token monitoring
```bash
npm install -g ccusage
# Then run: ccusage report
```

#### For advanced context compression
```bash
git clone https://github.com/NeoLabHQ/context-engineering-kit ~/context-eng-kit
# Review: ~/context-eng-kit/README.md for patterns
```

---

## 📞 WHEN TO USE EACH TOOL

| Need | Tool | Command |
|------|------|---------|
| Cross-session context | claude-mem | `mem-search "topic"` |
| File structure | smart-explore | `smart_outline("path/file.py")` |
| Search code | Grep + smart | `smart_search("function", "./dir")` |
| Library docs | context7 | Mention library name |
| Architecture | napkin.md | Keep updated |
| Quick review | /review-code | `/review-code src/file.py` |
| Project history | Timeline | `/timeline-report` |

---

## ⚠️ ANTI-PATTERNS (Don't Do These)

### ❌ Anti-Pattern 1: Massive Context Dumps
```
BAD:  "Here's the entire config file, app structure, and 5 test files"
GOOD: "Config is at core/config.py. Need to add X field. What's the pattern?"
```

### ❌ Anti-Pattern 2: Re-Explaining Project Every Session
```
BAD:  Every session starts with "Remind me what this project does"
GOOD: napkin.md keeps core facts → I read it → continue
```

### ❌ Anti-Pattern 3: "Read This Whole File"
```
BAD:  "Read src/application/uc_process_message.py"
GOOD: "Check ProcessMessage use-case for X logic" → I use smart_outline first
```

### ❌ Anti-Pattern 4: No Plan, Just Code
```
BAD:  "Add user authentication" → I write 500 lines
GOOD: "Add user auth" → I create plan → you approve → I implement
```

---

## 🎯 SUCCESS METRICS

You'll know this is working when:
- ✅ Sessions start faster (claude-mem loading context)
- ✅ I ask fewer clarifying questions (napkin.md + memory)
- ✅ Code suggestions match your architecture (domain/app/infra pattern)
- ✅ Token usage is 40-60% lower than before
- ✅ You curate napkin.md every session (5 min, huge payoff)

---

## 📖 REFERENCE DOCS

- **ARCHITECTURE.md** — Technical decisions & layer structure
- **MACROARCHITECTURE.md** — Product decisions & scope
- **napkin.md** (.claude/) — Session-fresh guidance
- **This file** — Claude Code operational guide

---

**Status:** ✅ Ready to use
**Next Step:** Curate `.claude/napkin.md` at the start of each session
**Token Impact:** 60-70% reduction across typical workflows

