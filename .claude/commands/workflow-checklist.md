# 📋 Workflow Checklists — Token-Optimized

Use estes checklists para manter o trabalho eficiente e economizar tokens.

---

## 🐛 WORKFLOW A: Bug Fix

**Expected tokens:** 1500-2500 | **Time:** 20-40 min

### Phase 1: Diagnose (5 min)
```
□ User describes bug
□ I use smart_search() to find related code
□ I use smart_outline() to see file structure
□ I identify root cause location
□ STOP: Do NOT read full files yet
```

### Phase 2: Locate (10 min)
```
□ I use smart_unfold() to expand specific function
□ I read ONLY the relevant 20-30 lines
□ I understand the bug
□ I identify fix location
```

### Phase 3: Fix (10 min)
```
□ I write minimal fix (not refactoring)
□ I create test that reproduces bug
□ I verify fix passes test
□ STOP: Do NOT clean up surrounding code
```

### Phase 4: Verify (5 min)
```
□ I run full test suite locally (you run)
□ Tests pass ✓
□ No new warnings
□ Done
```

### ❌ Anti-Patterns for This Workflow
```
❌ "Read the whole file to understand context"
✅ "Use smart_outline() first, then read what's needed"

❌ "While fixing bug X, also refactor Y"
✅ "Fix bug X, refactor Y is separate task"

❌ "I'll read all related files to be thorough"
✅ "I'll use smart_search() to find dependencies"
```

---

## ✨ WORKFLOW B: New Feature

**Expected tokens:** 4000-6000 | **Time:** 2-4 hours

### Phase 1: Plan (20 min)
```
□ User describes feature
□ I create implementation plan (outline only, no code)
□ Plan follows: domain → application → infrastructure → interfaces
□ You review & approve plan
□ STOP: Do NOT start coding yet
```

### Phase 2: Domain Layer (30 min)
```
□ I smart_outline("domain/entities.py")
□ I identify what new entity/enum needed
□ I edit domain/entities.py or create domain/entities/new_feature.py
□ I keep domain/ pure (no external imports)
□ Tests pass ✓
```

### Phase 3: Application Layer (40 min)
```
□ I smart_outline("application/")
□ I identify pattern from existing use-cases
□ I create application/uc_new_feature.py
□ I import only from domain/
□ I define business logic
□ Tests pass ✓
```

### Phase 4: Infrastructure Layer (40 min)
```
□ I smart_outline("infrastructure/")
□ I identify what adapters needed
□ I create infrastructure/new_feature/ adapters
□ Tests pass ✓
```

### Phase 5: Interfaces Layer (20 min)
```
□ I smart_outline("interfaces/api/")
□ I identify API pattern
□ I create new endpoint(s)
□ I wire up application/ use-case
□ Tests pass ✓
```

### Phase 6: Integration Test (10 min)
```
□ I create end-to-end test
□ I run full test suite
□ Tests pass ✓
□ Done
```

### ❌ Anti-Patterns for This Workflow
```
❌ "Skip planning, just code"
✅ "Plan first, you approve, then code"

❌ "Import application code in domain/"
✅ "Domain/ is pure, application/ calls domain/"

❌ "Write 500 lines then test"
✅ "Write layer → test → commit → next layer"

❌ "Add features while fixing bugs in same session"
✅ "One task per session (or at least per branch)"
```

---

## 🔍 WORKFLOW C: Code Review

**Expected tokens:** 2000-3000 | **Time:** 15-30 min

### Phase 1: High-Level (5 min)
```
□ Use /review-code [file] (NOT manual read)
□ I summarize purpose of file
□ I check architecture fit
□ I verify layer-appropriate (domain/app/infra)
```

### Phase 2: Security (5 min)
```
□ I check for SQL injection, XSS, etc
□ I review authentication/authorization logic
□ I flag sensitive data handling
□ I suggest if needed
```

### Phase 3: Logic (10 min)
```
□ I check for off-by-one errors
□ I review loop conditions
□ I check error handling
□ I suggest improvements
```

### Phase 4: Style (5 min)
```
□ I check naming consistency
□ I check type hints (if Python)
□ I check documentation
□ I flag if needed
```

### ❌ Anti-Patterns for This Workflow
```
❌ "Read full file, spend 20 min re-explaining what it does"
✅ "Use /review-code, get structured review"

❌ "Review every line, suggest 50 changes"
✅ "Review critical paths, suggest 3-5 changes"

❌ "Rewrite code while reviewing"
✅ "Suggest improvements, user decides"
```

---

## 📝 WORKFLOW D: Documentation

**Expected tokens:** 1000-2000 | **Time:** 30-60 min

### Phase 1: Identify (5 min)
```
□ User specifies what needs docs
□ I identify file/feature
□ I use smart_outline() to understand structure
□ STOP: Do NOT read full files
```

### Phase 2: Draft (20 min)
```
□ I write high-level explanation
□ I add example code (20-30 lines)
□ I link to ARCHITECTURE.md if needed
□ I keep under 500 words
```

### Phase 3: Review (10 min)
```
□ You review docs
□ You suggest improvements
□ I revise
```

### Phase 4: Update (10 min)
```
□ I update relevant docs (usually napkin.md)
□ I commit docs
□ Done
```

### ❌ Anti-Patterns for This Workflow
```
❌ "Write 2000-word documentation"
✅ "Write 300-word summary + link to code"

❌ "Auto-generate docs from comments"
✅ "Write docs for people, not tools"

❌ "Document every method"
✅ "Document public API + tricky logic"
```

---

## 🏗️ WORKFLOW E: Refactoring

**Expected tokens:** 5000-10000 | **Time:** 3-6 hours

**Important:** Only refactor if:
- Code is blocking progress
- Tests exist for this code
- You explicitly requested it
- Not "premature optimization"

### Phase 1: Baseline (10 min)
```
□ Tests exist for this code ✓
□ Tests pass ✓
□ I understand current code (smart_outline)
□ STOP: Do NOT refactor yet
```

### Phase 2: Plan (15 min)
```
□ I create refactoring plan
□ I identify: what changes, why, how to verify
□ You approve plan
□ STOP: Do NOT start coding
```

### Phase 3: Implement (60 min)
```
□ I make small changes (1-2 at a time)
□ I run tests after each change
□ Tests pass ✓
□ No new warnings
□ Continue to next small change
```

### Phase 4: Verify (10 min)
```
□ Full test suite passes ✓
□ Performance metrics (if applicable) ✓
□ Code review from team (if applicable) ✓
□ Commit with clear message
```

### ❌ Anti-Patterns for This Workflow
```
❌ "Refactor everything at once"
✅ "Refactor small section → test → commit"

❌ "Refactor without tests"
✅ "Only refactor code with test coverage"

❌ "Refactor while adding features"
✅ "Refactor is separate task"

❌ "Change behavior while refactoring"
✅ "Refactoring should NOT change behavior"
```

---

## 🚀 WORKFLOW F: Spike / Investigation

**Expected tokens:** 2000-4000 | **Time:** 1-3 hours

### Phase 1: Question (5 min)
```
□ User asks question or requests investigation
□ I clarify scope
□ I define what "done" looks like
□ STOP: Do NOT read 50 files blindly
```

### Phase 2: Search (10 min)
```
□ I use smart_search() to find relevant code
□ I use Grep to find patterns
□ I identify 2-3 most relevant files
□ STOP: Do NOT read everything
```

### Phase 3: Analyze (20 min)
```
□ I smart_outline() relevant files
□ I read specific sections
□ I understand the pattern/issue
□ I document findings
```

### Phase 4: Report (10 min)
```
□ I summarize findings
□ I suggest next steps (new feature? refactor? nothing?)
□ You decide what to do
□ Done
```

### ❌ Anti-Patterns for This Workflow
```
❌ "Investigate means read every file"
✅ "Investigate = smart search → outline → read targeted"

❌ "Write 10-page investigation report"
✅ "Write 1-page summary + findings"

❌ "Investigate then immediately implement"
✅ "Investigate, report, user decides next step"
```

---

## ⚡ WORKFLOW G: Urgent Bug (Production)

**Expected tokens:** 800-1500 | **Time:** 5-15 min

**Use this for critical issues only.**

### Phase 1: Triage (2 min)
```
□ User reports bug
□ I verify it's real
□ I identify severity (critical/high/medium)
□ STOP: Do NOT plan/design yet
```

### Phase 2: Locate (3 min)
```
□ I use grep to find error message
□ I use smart_search() to find related code
□ I identify likely file
□ I do NOT read full file
```

### Phase 3: Fix (5 min)
```
□ I read specific lines (10-30)
□ I write minimal fix
□ I verify with quick test
□ NO refactoring, NO design improvements
```

### Phase 4: Verify (2 min)
```
□ User tests fix in environment
□ Issue resolved ✓
□ Commit with message "fix: [bug]"
□ Done
□ Schedule proper refactoring later (new task)
```

### ❌ Anti-Patterns for This Workflow
```
❌ "While fixing critical bug, also refactor"
✅ "Fix bug, refactor is separate task"

❌ "Spend 30 min designing proper solution"
✅ "Fix now, improve later"

❌ "No tests for emergency fix"
✅ "Write quick test, add to test suite later"
```

---

## 📊 QUICK TOKEN COMPARISON

| Workflow | Bad Approach | Good Approach | Savings |
|----------|-------------|---------------|---------|
| Bug fix | Read full module | smart_outline + smart_unfold | 60% |
| Feature | Plan in chat | Write plan doc + approval | 40% |
| Review | Read + summarize | /review-code | 50% |
| Docs | Auto-generate | Write for humans | 30% |
| Refactor | Change all at once | Small changes + test cycle | 40% |
| Spike | Read every file | smart_search + targeted read | 70% |
| Urgent | Design first | Minimal fix now | 80% |

---

## 🎯 CHECKLIST SUMMARY

Before starting ANY task:
```
□ Read this checklist for your workflow type
□ Follow the phases (do NOT skip)
□ Use smart_outline() before reading files
□ Test after each change
□ Commit frequently
□ When done, move to next task
```

**Result:** Consistent, efficient work with 40-70% token savings

---

**Status:** Ready to use
**Created:** 2026-03-30
**Use:** Reference when starting a new task

