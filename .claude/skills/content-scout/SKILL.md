---
name: content-scout
description: Extract blog article ideas from technical content being reviewed (AIA courses, product docs, code standards). Use when reviewing AIA course HTML/markdown, technical documentation, or any Waterson content — proactively identifies topics suitable for watersonusa.ai blog articles. Trigger with "/content-scout", "scout articles", "find article ideas", or automatically during AIA course review loops. Also handles the "flag-candidate" subcommand used by AIA course production subagents to append queue entries to door-site/.content-scout-queue.md.
---

# Content Scout

Extract publishable article ideas from technical content being reviewed. Runs alongside review agents to capture content opportunities that would otherwise be lost.

For AIA course production, see the `flag-candidate` subcommand section below — called by subagents (Investigator A/B, Writer A/B, Project Architect Advisor) to append queue entries during course production.

## Differs from /content-suggest

- `/content-suggest` = analyzes crawler data + search trends to suggest topics
- `/content-scout` = mines existing technical content (courses, docs) for article-worthy material

## Workflow

### 1. Identify Source Material

Read the specified files. Common sources:
- AIA course HTML: `door-site/aia/*/index.html`
- AIA course drafts: `waterson-ai-growth-system/docs/aia-course/*.md`
- Product documentation, technical specs

### 2. Scan for Article-Worthy Content

Look for these content types:

| Type | Example | Blog Value |
|------|---------|-----------|
| **Regulatory explainer** | ADA 5 lbf exemption for fire doors | High — architects search for this |
| **Case study** | $18M Texas pool gate settlement | High — compelling + shareable |
| **Product comparison** | 304 vs 316 stainless steel | High — purchase decision content |
| **Statistical insight** | 4,000+ annual drownings, 75% under age 5 | Medium — supports authority |
| **Industry trend** | CT 2025 pool barrier law change | Medium — timely + newsworthy |
| **Code conflict** | NFPA 80 vs ADA opening force | High — architects need clarity |
| **Cost comparison** | Swing-clear hinge $300 vs structural $15K | High — spec decision driver |
| **Checklist/guide** | Healthcare door 9-item compliance checklist | High — practical + bookmarkable |

### 3. Score and Rank

For each idea, assess:
- **SEO potential**: Would architects/specifiers search for this?
- **Uniqueness**: Is this already covered on watersonusa.ai?
- **Waterson angle**: Can it naturally feature Waterson products (without being promotional)?
- **Completeness**: Is there enough source material to write 800-1500 words?

### 4. Output Format

Present a ranked table:

```
| # | Type | Title | Source | Keywords | Est. Words |
|---|------|-------|--------|----------|-----------|
| 1 | Regulatory | ADA Fire Door Exemption: Why 5 lbf Doesn't Apply | HSW-003 Slide 26-30 | ADA fire door, 5 lbf exemption, NFPA 80 | 1,200 |
| 2 | Case Study | $18M Pool Gate Lawsuit: What Architects Must Know | HSW-004 Slide 11-13 | pool gate liability, drowning lawsuit | 1,000 |
```

### 5. Next Steps

After presenting ideas, ask the user:
1. Which articles to pursue?
2. For approved articles, trigger `/publish-article` with the title and source material
3. For "maybe later" articles, add to `content-plan.md` via `/content-suggest` format

## flag-candidate — Subcommand for AIA course agents

### 1. When this subcommand is called

This subcommand is invoked by subagents during AIA course production. The authorized callers are:

- **Investigator A** — when a discovered case study is strong enough to support an independent blog article
- **Investigator B** — when a code/regulatory topic is strong enough to support an independent blog article
- **Writer A** — when a technical concept encountered during slide writing deserves 800+ words of independent treatment
- **Writer B** — when a scenario or spec resource path deserves independent treatment
- **Project Architect Advisor** — when reviewing the finished course, finds a topic architects want but the course could not cover in depth

Source of truth for which agents call this command and when: `WTR-HSW-002-OGSM-v4.md` Skill Invocation Map section.

**Candidate Collector (agent #19) does NOT call this subcommand.** Its role is cross-wave type balance judgment — it reads the queue and writes `## Type Distribution`, but collection is the responsibility of the five research/writing agents listed above.

### 2. Target queue file

Path: `door-site/.content-scout-queue.md` — resolve from the current working directory's door-site repo.

If the file does not exist:
```
❌ /content-scout flag-candidate error

Problem: content-scout queue file not found
Expected: door-site/.content-scout-queue.md (relative to cwd)
Got: file not present at that path
Fix: ensure you are running from the waterson-ai-growth-system root, or that door-site/.content-scout-queue.md has been initialized
```

### 3. Field schema validation

Each call must provide 9 mandatory fields plus 1 optional field. Validate in this order before proceeding:

| # | Field | Required | Validation rule |
|---|-------|----------|-----------------|
| 1 | `--source-agent` | yes | Must be one of: `investigator-a`, `investigator-b`, `writer-a`, `writer-b`, `project-architect-advisor`, `candidate-collector`, `engagement-designer` |
| 2 | `--source-file` | yes | Non-empty string; should be a file path with optional `#anchor` |
| 3 | `--title` | yes | Non-empty, 120 characters or fewer |
| 4 | `--type` | yes | Must be one of the 8 valid types listed in section 4 |
| 5 | `--keywords` | yes | Comma-separated list of 3–5 keywords |
| 6 | `--research-data` | yes | Non-empty raw material; warn (do not block) if fewer than 200 characters — likely a summary rather than raw data |
| 7 | `--why-worth-writing` | yes | Non-empty; recommend 2 sentences or fewer |
| 8 | `id` | auto | Read queue file, find max existing candidate id, increment by 1. If queue has no existing candidates, start at 1 |
| 9 | `timestamp` | auto | ISO 8601 local time at moment of call |
| 10 | `--collector-notes` | optional | If present, run banned-phrase lint described in section 5 |

Missing any mandatory field (1–7) → report error with the specific field name. Do not proceed with appending.

### 4. Eight valid type values

`--type` must be exactly one of:

- `regulatory-explainer` — explains a code or standard section that architects find confusing
- `case-study` — a real case (court record, DHI incident, published case) with 2+ independent sources
- `product-comparison` — compares hardware categories or specific products objectively
- `statistical-insight` — a data point or statistic that reveals an industry pattern
- `cost-comparison` — TCO, lifecycle cost, or spec cost analysis
- `code-conflict` — two codes or standards that appear to conflict (e.g., NFPA 80 vs ADA)
- `scenario-guide` — "when to use X" decision framework for a specific scenario
- `reader-interest` — a topic architects repeatedly ask about but the course could not cover

If the provided value is not in this list, report an error that enumerates all 8 valid types.

### 5. Banned-phrase lint for --collector-notes

If `--collector-notes` is provided, scan the value for prescriptive language. The following phrases are banned (case-insensitive):

**Chinese banned phrases:**
- 建議、應該、最好、推薦、可以考慮、值得優先、優先寫、必須寫

**English banned phrases:**
- "we should", "should write", "recommend writing", "priority", "must write", "best to write"

If any banned phrase is found, report an error with the specific phrase found, its approximate position, and this hint:

> collector_notes should be descriptive, not prescriptive. See banned phrase list.

**Allowed alternatives (descriptive language):**
- 「這個主題出現 3 次」
- 「已累積 5 段原始資料」
- 「屬於已稀缺的 case-study 類型」
- "appeared 3 times"
- "accumulated 5 research segments"
- "this is the only case-study candidate so far"

### 6. Append format

On successful validation, append a new candidate section to `door-site/.content-scout-queue.md` using this format:

```markdown
### Candidate #N — [Title]

- **id**: N
- **timestamp**: [ISO 8601 local time]
- **source-agent**: [value]
- **source-file**: [value]
- **title**: [value]
- **type**: [value]
- **keywords**: [value]
- **research-data**: [value]
- **why-worth-writing**: [value]
- **collector-notes**: [value, or omit this line if not provided]
```

After appending the candidate, also update the `## Type Distribution` section at the top of the queue file: find the line for this candidate's type and increment its count by 1. If the `## Type Distribution` section does not yet exist, create it with all 8 types initialized to 0, then increment the relevant type.

### 7. Error format

All errors use this structure:

```
❌ /content-scout flag-candidate error

Problem: [what is wrong]
Expected: [what is expected]
Got: [what was provided]
Fix: [how to correct it]
```

### 8. Success output

```
✅ Candidate #N flagged
  Title: [title]
  Type: [type]
  Source: [source-agent] from [source-file]
  Queue file: door-site/.content-scout-queue.md
  Type Distribution updated: [type] count is now [N]
```

If `--research-data` was fewer than 200 characters, also append this warning after the success block:

```
⚠️  research-data is [X] characters — this looks like a summary rather than raw material. Consider expanding with the full source text before the Phase 3 Blog Writer Fleet uses this candidate.
```

### 9. Implementation note

This subcommand can be executed either procedurally (Claude follows the rules above) or via the scripts in `scripts/` for deterministic automation:

```bash
# Validate a candidate block from stdin
echo "- **id**: 1 ..." | python ~/.claude/skills/content-scout/scripts/validate_candidate.py

# Lint collector_notes for banned phrases
python ~/.claude/skills/content-scout/scripts/banned_word_lint.py --text "appeared 3 times"

# Append a validated candidate (auto-generates id + timestamp, calls lint + validate + distribute)
python ~/.claude/skills/content-scout/scripts/append_candidate.py \
  --queue door-site/.content-scout-queue.md \
  --source-agent investigator-a \
  --source-file "docs/aia-course/WTR-HSW-006.md#slide-22" \
  --title "ADA Fire Door 5 lbf Exemption Explained" \
  --type regulatory-explainer \
  --keywords "ADA fire door, 5 lbf exemption, NFPA 80" \
  --research-data "NFPA 80 Section 6.3.1.2 states that self-closing devices on fire doors must..." \
  --why-worth-writing "Architects frequently confuse the ADA opening force rule with fire door specs." \
  --collector-notes "Appeared in 2 separate Investigator A research segments"

# Recount and update Type Distribution section
python ~/.claude/skills/content-scout/scripts/update_type_distribution.py door-site/.content-scout-queue.md
```

Scripts are in `~/.claude/skills/content-scout/scripts/`:
- `validate_candidate.py` — 9-field schema + type validation (exit 0=valid, 2=invalid)
- `banned_word_lint.py` — prescriptive language lint for collector_notes (exit 0=clean, 2=banned)
- `append_candidate.py` — full pipeline: validate + lint + append + update distribution
- `update_type_distribution.py` — recount all 8 types and rewrite ## Type Distribution section

All scripts use stdlib only (Python 3, no external deps). Each has `--help`.

---

## Multi-Agent Collaboration

Use Gemini and Codex to enhance scouting:

### Gemini (research + validation)
```bash
# Validate SEO potential of a topic
echo "Y" | gemini -m gemini-2.5-flash -p "Search Google for this topic. Report: monthly search volume estimate, top 3 competing articles, content gap opportunities. Topic: 'ADA fire door 5 lbf exemption'" --output-format text

# Check if topic is already covered on watersonusa.ai
echo "Y" | gemini -m gemini-2.5-flash -p "Search site:watersonusa.ai for articles about: pool gate stainless steel 304 vs 316. Report what exists and what's missing." --output-format text
```

### Codex (competitive analysis)
```bash
# Analyze competitor content on same topic
codex exec --full-auto -C /path/to/project "Search the web for the top 5 articles about 'ADA door closing force requirements'. For each, report: title, URL, word count estimate, key topics covered. Identify gaps we can fill."
```

### Workflow with collaborators
1. **Claude (A君)** reads source material, identifies raw topic candidates
2. **Gemini Flash** validates SEO potential + checks for duplicates on watersonusa.ai
3. **Codex** does competitive gap analysis (quota permitting)
4. **Claude** synthesizes findings, ranks ideas, presents to user

Fallback: If Gemini/Codex quota exhausted, Claude Sonnet agents handle research.

## Usage

```
# Standalone
/content-scout

# With specific files
/content-scout door-site/aia/ada-compliant-door-closing/index.html

# During a review loop (A君 dispatches as background agent)
Agent: content-scout scanning HSW-003 and HSW-004 for article ideas
```
