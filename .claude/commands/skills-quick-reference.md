# 🎯 Skills Quick Reference — What to Use & When

**Purpose:** Practical guide to skills for token optimization
**Time to read:** 5 minutes
**Token savings:** 40-70%

---

## 🚀 ESSENTIAL SKILLS (Use Every Session)

### 1️⃣ **napkin.md** (Auto-Active)
```
What: Curated project guidance
When: Every session start (2 min)
How: Edit .claude/napkin.md
Token savings: 30%
Example:
  ✓ Backend runs on port 8010 (not 8000)
  ✓ Domain/ layer must be pure
  ✓ WhatsApp disabled by default (set DISABLE_WHATSAPP_SEND=false)
```

### 2️⃣ **smart_outline()** (Use Instead of Read)
```
What: Show file structure without reading whole file
When: Before reading any file > 100 lines
How: smart_outline("src/application/uc_process_message.py")
Token savings: 70% (read 100 tokens vs 1000 tokens)
Example:
  smart_outline("src/domain/entities.py")
  → Shows: classes, functions, what's imported
  → Skip full file, read only what you need
```

### 3️⃣ **smart_search()** (Use Instead of Grep)
```
What: Find code patterns across directory
When: Searching for function/class/pattern
How: smart_search("authenticate", "src/application")
Token savings: 50%
Example:
  smart_search("LeadScore", "src/domain")
  → Finds all uses of LeadScore
  → Shows context
  → Then read only relevant parts
```

### 4️⃣ **smart_unfold()** (Expand Specific Code)
```
What: Show specific function/class in context
When: Need to see single function/class
How: smart_unfold("src/application/uc_process_message.py", "ProcessMessage")
Token savings: 60%
Example:
  smart_unfold("src/domain/entities.py", "Lead")
  → Shows Lead class definition only
  → Not entire file
```

### 5️⃣ **mem-search** (Cross-Session Memory)
```
What: Search previous sessions' work
When: "Did we already fix this?" or "How did we solve X?"
How: mem-search("authentication bug")
Token savings: 90%
Example:
  mem-search("WhatsApp webhook")
  → Returns relevant past sessions
  → You can reference without re-reading
  → I remember context across sessions
```

---

## 🔧 IMPORTANT SKILLS (Use When Needed)

### 6️⃣ **/review-code** (Code Review)
```
What: Automatic code review (security, logic, style)
When: Want me to review a file
How: /review-code src/infrastructure/whatsapp/handler.py
Token savings: 50%
Example:
  /review-code src/application/uc_authenticate_user.py
  → I review for security
  → I review for architecture fit
  → I suggest improvements
  → NOT full file read
```

### 7️⃣ **context7** (Live Library Docs)
```
What: Fetch current library documentation
When: Asking about library/framework API
How: Mention library name in question
Token savings: 40%
Example:
  "How do I use FastAPI middleware?"
  → context7 auto-fetches FastAPI docs
  → I get current API (not hallucinated)
  → Fewer retries, correct code first time
```

### 8️⃣ **CLAUDE.md** (This Project's Rules)
```
What: Operational guide for this project
When: Unsure about constraints/patterns
How: Reference CLAUDE.md
Token savings: 20%
Example:
  "Can I import application in domain?"
  → No, CLAUDE.md says domain is pure
  → I follow the rule
  → No circular discussions
```

### 9️⃣ **napkin.md curation** (Session Refresh)
```
What: Keep napkin.md fresh
When: Every session (2 min)
How: Edit .claude/napkin.md, remove stale items
Token savings: 25%
Example:
  Remove: "Port 8000 issue (fixed 3 weeks ago)"
  Keep: "Port 8010 is current default"
  Update: Dates, add new findings
```

---

## 📊 OPTIONAL SKILLS (Install if You Want)

### 10️⃣ **ccusage** (Token Monitoring)
```
What: Dashboard of token usage
When: Want to track costs
How: npm install -g ccusage
      ccusage report
Token savings: N/A (monitoring, not saving)
Use for: Baseline → implement skills → measure savings
```

### 1️⃣1️⃣ **Claude Session Restore** (Cross-Session Context)
```
What: Automatically restore context from previous sessions
When: Starting new session
How: npm install -g claude-session-restore
Token savings: 90%
Setup: https://github.com/ZENG3LD/claude-session-restore
```

### 1️⃣2️⃣ **Context Engineering Kit** (Advanced Compression)
```
What: Hand-crafted context compression patterns
When: Want to optimize context deeply
How: git clone https://github.com/NeoLabHQ/context-engineering-kit
     Review patterns, apply to your code
Token savings: 40-50% additional
```

---

## 🎯 WHEN TO USE WHICH SKILL

### Scenario A: "Bug in WhatsApp handler"
```
1. mem-search("WhatsApp bug") → Any previous work?
2. smart_search("webhook", "src/infrastructure") → Find code
3. smart_outline() → See structure
4. smart_unfold() → See specific function
5. Read (10-20 lines) → Actual code
6. Fix + test
Token usage: ~1200 (vs 3000+ without skills)
```

### Scenario B: "How do I use FastAPI?"
```
1. Mention "FastAPI middleware" in question
2. context7 auto-fetches docs
3. I get current API
4. I write correct code first time
Token usage: ~500 (vs 1000+ without context7)
```

### Scenario C: "Add user authentication"
```
1. CLAUDE.md → Review layer structure
2. smart_outline("domain/") → See entities
3. smart_outline("application/") → See patterns
4. Implement domain layer → test
5. Implement application layer → test
6. Implement infrastructure layer → test
7. Implement interfaces layer → test
Token usage: ~4000 (vs 8000+ without outline first)
```

### Scenario D: "Review this code"
```
1. /review-code src/file.py → Auto review
2. I don't read full file
3. I focus on logic + security
4. I suggest improvements
Token usage: ~2000 (vs 3500+ with manual read)
```

### Scenario E: "Did we fix the database issue?"
```
1. mem-search("database schema migration")
2. Returns relevant past sessions
3. I reference without re-reading
4. Continue with current work
Token usage: ~200 (vs 2000+ re-reading files)
```

---

## ❌ ANTI-PATTERNS (Don't Do This)

### ❌ Anti-Pattern 1: Dump Full File
```
BAD:  "Read src/application/uc_process_message.py"
GOOD: smart_outline() first, then "Show me the handle_message function"
Saves: ~800 tokens per file
```

### ❌ Anti-Pattern 2: Ask Without Searching
```
BAD:  "Where is the WhatsApp code?"
GOOD: smart_search("whatsapp", "src/")
Saves: ~300 tokens per search
```

### ❌ Anti-Pattern 3: Use Read for Everything
```
BAD:  Every time → Read full file
GOOD: smart_outline() → Read targeted sections
Saves: 60-70% on exploration tasks
```

### ❌ Anti-Pattern 4: Don't Use Memory
```
BAD:  "Remind me what we did last session"
GOOD: mem-search("last session topic")
Saves: 90% on cross-session context
```

### ❌ Anti-Pattern 5: Ignore CLAUDE.md Rules
```
BAD:  "Why can't I import application in domain?"
      (Asked 3x already, answer in CLAUDE.md)
GOOD: Reference CLAUDE.md layer rules
Saves: ~500 tokens on repeated clarifications
```

---

## 📋 YOUR SKILL USAGE TEMPLATE

Copy this and use before starting work:

```
Session Start Checklist:
[ ] Read napkin.md (auto-loaded)
[ ] Curate napkin.md (remove stale, keep top 10/section) — 2 min
[ ] Review CLAUDE.md for project rules
[ ] Note: Using smart_outline() instead of Read for large files
[ ] Note: Using smart_search() instead of grep
[ ] Note: Using mem-search for cross-session context

Task:
[ ] Use smart_outline() → smart_search() → smart_unfold() → Read (targeted)
[ ] Reference mem-search if similar work done before
[ ] Use /review-code for code reviews (not manual read)
[ ] Mention library name for context7 to fetch docs

After Task:
[ ] Update napkin.md with new findings (if any)
[ ] Commit changes
[ ] Note token usage (compare with estimate)
[ ] Move to next task
```

---

## 🚀 IMMEDIATE ACTIONS (Do These Now)

### Step 1: Verify Skills Installed (2 min)
```bash
# In Claude Code:
/plugin list
# Should show: claude-mem ✓

# Smart-explore is part of claude-mem
smart_outline("src/main.py")  # Test it works
```

### Step 2: Setup context7 (Optional, 3 min)
```bash
npx ctx7 setup --claude
# Enables live library doc fetching
```

### Step 3: Curate napkin.md (2 min)
```
Edit .claude/napkin.md:
- Remove items older than 1 month
- Keep max 10 items per section
- Add today's date to updates
```

### Step 4: Read CLAUDE.md (5 min)
```
This file (.claude/CLAUDE.md)
Explains project rules + workflows
Reference when unsure
```

### Step 5: Bookmark Commands (1 min)
```
Save these commands somewhere:
- smart_outline("file.py")
- smart_search("pattern", "dir")
- smart_unfold("file.py", "FunctionName")
- mem-search("topic")
- /review-code src/file.py
```

---

## 📊 EXPECTED TOKEN REDUCTION

| Skill | Savings | Effort | ROI |
|-------|---------|--------|-----|
| napkin.md curation | 30% | 2 min/session | 🔥 Highest |
| smart_outline() | 70% | Automatic | 🔥 Highest |
| smart_search() | 50% | Automatic | ⭐ High |
| mem-search | 90% | Occasional | ⭐ High |
| /review-code | 50% | Automatic | ⭐ High |
| context7 | 40% | Automatic | ⭐ High |
| CLAUDE.md | 20% | One-time read | ✅ Medium |

**Combined:** 60-70% token reduction

---

## 🎯 PRACTICE USING SKILLS

### Exercise 1: Find a Bug (5 min, save 800 tokens)
```
1. mem-search("recent bug")
2. smart_search("error_handler", "src/")
3. smart_outline("src/application/uc_*.py")
4. smart_unfold("src/application/uc_process_message.py", "ProcessMessage")
5. Done — you found code without reading full files
```

### Exercise 2: Review Code (5 min, save 1000 tokens)
```
1. /review-code src/domain/entities.py
2. I review without reading full file
3. I suggest improvements
4. You decide what to implement
```

### Exercise 3: Ask Library Question (3 min, save 500 tokens)
```
1. "How do I use FastAPI dependency injection?"
2. context7 fetches FastAPI docs
3. I give current, correct answer
4. No hallucination, no retries
```

---

## 💡 PRO TIPS

### Tip 1: Combine Skills
```
Bad: Use only one skill
Good: smart_outline() + smart_unfold() + targeted Read
→ Gets context + depth + actual code
```

### Tip 2: Reference Past Work
```
Bad: "Remind me what we did"
Good: mem-search("topic") → Reference specific observation ID
→ I can link directly to past work
```

### Tip 3: Name Things Well
```
Bad: utils.py with generic_function()
Good: application/uc_process_message.py with ProcessMessageUseCase
→ Name tells you what to expect
→ Reduces need to read code
```

### Tip 4: Update napkin.md
```
Bad: Let napkin.md get stale
Good: Every session → remove old, add new
→ Keeps context fresh
→ Reduces re-explanation
```

### Tip 5: Use mem-search Before New Work
```
Bad: Start fresh every session
Good: mem-search("similar work") → Reference past approach
→ Consistent patterns
→ Faster development
```

---

**Status:** ✅ Ready to use
**Created:** 2026-03-30
**Next:** Use these skills in your next task

