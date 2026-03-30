# 🧠 Context Compression Guide — Agente ImobiliarIA

**Purpose:** Reduce token usage by 40-70% through smart context engineering
**Time:** Apply once, benefit every session
**Result:** ~3000 tokens saved per session

---

## 🎯 The Core Idea

Instead of:
```
❌ Dump entire project → Claude processes everything → picks what's relevant
```

Do:
```
✅ Load only what Claude NEEDS → Claude uses all tokens efficiently
```

---

## 📋 LAYER 1: WHAT CLAUDE ALWAYS NEEDS (Keep Small)

### Load every session:
1. **napkin.md** ✅ (Already auto-loaded by claude-mem)
2. **CLAUDE.md** — Reference once per session
3. **ARCHITECTURE.md first 50 lines** — Layer structure only

### Skip:
- Full ARCHITECTURE.md (too big)
- Old commits
- node_modules/
- Full test files

---

## 📋 LAYER 2: LOAD ON-DEMAND (Smart Triggers)

| Trigger | Load This | Tokens Saved |
|---------|-----------|--------------|
| "Bug in WhatsApp" | `application/uc_whatsapp.py` (outline) | ~700 |
| "Database schema" | `domain/entities.py` (outline) | ~400 |
| "Add API endpoint" | `interfaces/api/` (outline) | ~600 |
| "Check config" | `core/config.py` (20 lines) | ~100 |

### Smart loading pattern:
```
1. User: "What's wrong with the WhatsApp handler?"
2. ME: smart_outline("src/infrastructure/whatsapp/handler.py")
3. ME: [read relevant 20-30 lines]
4. ME: Fix + test
```

**Tokens used: ~800-1200**
**vs Without this:** ~3000-4000

---

## 📋 LAYER 3: NEVER LOAD (Wastes Tokens)

❌ **Full files** (use smart_outline first)
❌ **node_modules/** (reference only)
❌ **Test files entire** (smart_search for relevant test)
❌ **Old docs** (git log instead)
❌ **Legacy code** in `agent/` (reference, don't extend)

---

## 🔄 YOUR SESSION WORKFLOW

### Start (2 min)
```bash
1. Open Claude Code
2. Read napkin.md (auto-loaded)
3. Curate napkin.md (remove stale, keep top 10/section)
4. Continue with work
```

### During work
```
Pattern A: Bug Fix
  ├─ User describes issue
  ├─ I use smart_outline() + grep
  ├─ Read relevant function only
  └─ Fix + test

Pattern B: New Feature
  ├─ User describes feature
  ├─ I create plan
  ├─ You approve
  ├─ I implement (outline-first for each layer)
  └─ Test end-to-end

Pattern C: Code Review
  ├─ Use /review-code [file]
  ├─ I don't read full file
  ├─ Focus on architecture fit
  └─ Done
```

### Tools to use
```
smart_outline()  → See file structure (~100 tokens)
smart_search()   → Find code by pattern (~200 tokens)
smart_unfold()   → Expand specific symbol (~300 tokens)
Read (20-50 lines) → Actually read code needed (~200-500 tokens)

NOT:
Read (full 500-line file) → Wastes ~1500 tokens
```

---

## 🧮 CONCRETE EXAMPLE: Add User Authentication

### ❌ Bad approach
```
User: "Add user authentication"

Claude reads:
  - Full ARCHITECTURE.md (600 tokens)
  - Full domain/ (400 tokens)
  - Full application/ (800 tokens)
  - Full infrastructure/ (500 tokens)
  - Full interfaces/ (400 tokens)

Total: ~2700 tokens BEFORE writing code
```

### ✅ Good approach
```
User: "Add user authentication"

Plan creation:
  - Reference architecture rules from napkin
  - Create plan (250 tokens)

You approve, then:

Implementation:
  - outline domain/entities.py (100 tokens)
  - outline application/uc_*.py (150 tokens)
  - outline interfaces/api/ (100 tokens)
  - Write code using patterns (400 tokens)
  - Test (300 tokens)

Total: ~1300 tokens (52% savings)
```

---

## 💡 CONTEXT ENGINEERING PATTERNS

### Pattern 1: Layer-Based Implementation
Instead of: "Here's my code in 5 files"
Do:
```
1. Define in domain/ (what is user auth?)
2. Define in application/ (how do we authenticate?)
3. Add to infrastructure/ (where do we store?)
4. Expose in interfaces/ (how do we expose?)
```
**Result:** Claude writes correct code first time (fewer retries)

### Pattern 2: Smart Naming
Use descriptive file/function names so Claude doesn't need to read the file:

| ❌ Bad | ✅ Good | Saves |
|--------|---------|-------|
| `utils.py` with `authenticate()` | `application/uc_authenticate_user.py` | 400 tokens |
| `models.py` | `domain/entities/user.py` | 300 tokens |
| `handlers.py` | `infrastructure/persistence/user_repository.py` | 500 tokens |

### Pattern 3: Comment Critical Decisions
```python
# ❌ Too much
# This function calculates the scoring
# It takes a lead
# and returns a score
# The score is based on...
# [15 lines of comments]

# ✅ Just right
# Lead scoring: temperature (0-100) based on activity + preferences
# See ARCHITECTURE.md section 3.2
```

**Result:** Claude doesn't waste tokens re-explaining

---

## 🚀 APPLY THIS NOW

### Option A: Minimal Setup (5 min, 30% savings)
1. ✅ Read CLAUDE.md (already done)
2. ✅ Curate napkin.md (remove old items)
3. ✅ Use smart_outline() instead of Read for large files

### Option B: Advanced Setup (15 min, 60% savings)
1. ✅ Do Option A
2. ✅ Create .claude/commands/context-compress.md (this file)
3. ✅ Extract "must-load" context to napkin.md
4. ✅ Use mem-search for cross-session references

### Option C: Expert Setup (30 min, 70% savings)
1. ✅ Do Option B
2. ✅ Apply context engineering patterns to your code
3. ✅ Create custom smart-explore overrides
4. ✅ Setup CC Usage dashboard for monitoring

---

## 📊 MEASURE YOUR SAVINGS

### Before
```bash
# Run this to see current usage
ccusage report
# (if installed via: npm install -g ccusage)
```

### After implementing this
```bash
# In 1 week:
ccusage report
# Should show 40-70% reduction
```

---

## 🔍 REAL EXAMPLE: Bug Fix Session

### Scenario: "WhatsApp webhook not processing messages"

#### Baseline (without compression)
```
1. Claude reads entire application/ (1200 tokens)
2. Claude reads entire infrastructure/whatsapp (800 tokens)
3. Claude identifies issue (400 tokens)
4. Claude suggests fix (300 tokens)
Total: ~2700 tokens
```

#### Optimized (with compression)
```
1. I smart_outline() → application/ (100 tokens)
2. I smart_outline() → infrastructure/whatsapp/ (100 tokens)
3. I smart_search("webhook") (150 tokens)
4. I read relevant function (200 tokens)
5. Claude identifies issue (300 tokens)
6. Claude suggests fix (250 tokens)
Total: ~1100 tokens (59% savings)
```

---

## 🎯 RULES FOR SUCCESS

1. **Curate napkin.md every session** (2 min, huge payoff)
2. **Use smart_outline() before Read** (saves 700-1000 tokens per file)
3. **Mention architecture layer** (domain/app/infra) when asking questions
4. **Link CLAUDE.md rules** when clarifying workflows
5. **Update .claude/commands/** as patterns emerge

---

## 📚 NEXT STEPS

1. ✅ You're reading this
2. ✅ Apply Layer 1 (keep CLAUDE.md + napkin.md fresh)
3. ✅ Use smart_outline() in next session
4. ✅ Notice token savings in session summary
5. ✅ Keep what works, adjust what doesn't

**Estimated ROI:** $5-15/month saved on token usage
**Effort:** 5 min per session (napkin curation)
**Payoff:** 60-70% token reduction

---

**Status:** Ready to use
**Created:** 2026-03-30
**Last Updated:** This document

