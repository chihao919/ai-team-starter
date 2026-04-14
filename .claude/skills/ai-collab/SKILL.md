---
name: ai-collab
description: "Task-type-aware multi-model router for delegating work between Claude, Gemini, and Codex. Routes by task type (research/verify/persona/seo/code/review/html-build) with embedded fallback chains. Use when planning multi-AI workflows, deciding which model to use for a task, or dispatching work to non-Claude models. Triggers on \"派 Gemini\", \"用 Codex\", \"delegate to AI\", \"多 AI 協作\", \"用什麼模型\", \"/ai-collab\"."
---

# Multi-AI Task-Type Router (v5.2-copilot)

Redesigned from single-model-with-fallback to **multi-model task-type routing**.
Each task type maps to the best primary model with a defined fallback chain.

## Task-Type Routing Table

| Task Type | Primary Model | Fallback Chain | Rationale |
|-----------|--------------|----------------|-----------|
| `research` | Gemini 2.5 Pro (Max) | -> Codex -> WebSearch | Google Search grounding, best for discovery |
| `verify` | Gemini 2.5 Flash (Max) | -> WebSearch -> Claude native | Web grounding for fact verification |
| `persona` | Gemini 2.5 Pro (Max) | -> Codex | Different model family = independent perspective |
| `seo` | Gemini 2.5 Flash (Max) | -> Codex | Google search insight |
| `code` | Codex (Max) | -> Claude native | Code generation, HTML/CSS/JS |
| `review` | Codex (Max) | -> Gemini -> Claude native | Systematic checking, citation cross-verification |
| `html-build` | Codex (Max) | -> Claude native | Structured output |
| `writing` | **Claude (native)** | -- | Creative, emotional arc, architect voice |
| `judgment` | **Claude (native)** | -- | Complex decisions, conflict resolution |
| `chinese` | **Claude (native)** | -- | Best Chinese quality |

## CLI Interface

### Task-type routing (primary use)
```bash
# Research task -> routes to Gemini 2.5 Pro
/ai-collab --task research "Find healthcare door failure cases post-2020"

# Code task -> routes to Codex
/ai-collab --task code "Build HTML slide template with ARIA landmarks"

# Verify task -> routes to Gemini 2.5 Flash
/ai-collab --task verify "Is NFPA 80 §6.4.1.4 verbatim correct?"

# Persona task -> routes to Gemini 2.5 Pro
/ai-collab --task persona "Read this course as a 12-year architect. Answer 6 decision questions."

# Review task -> routes to Codex
/ai-collab --task review "Check all citations in course-002-final.md for accuracy"

# SEO task -> routes to Gemini 2.5 Flash
/ai-collab --task seo "Analyze top 10 ranking pages for 'spring hinge vs self-closing hinge'"
```

### Explicit model override (escape hatch)
```bash
# Force a specific model regardless of task type
/ai-collab --model gemini-2.5-pro "specific prompt requiring Pro"
/ai-collab --model codex "specific prompt for Codex"
```

### Dry-run mode (see routing without executing)
```bash
/ai-collab --dry-run --task research "test prompt"
# Output: Task type: research | Chain: gemini-2.5-pro,codex,websearch
```

### List all task types
```bash
/ai-collab --list-tasks
```

## When NOT to use /ai-collab

**For writing/judgment/chinese tasks, do NOT call /ai-collab -- Claude handles these natively without CLI overhead.**

These three task types are Claude's core strengths:
- **writing**: Creative writing, emotional arc design, architect voice -- Claude's native language ability is superior
- **judgment**: Complex decisions, conflict resolution, OGSM compliance -- Claude has full context
- **chinese**: Chinese language content -- Claude produces the highest quality Chinese text

Calling CLI for these would add latency with no quality improvement.

## Script Location

```
~/.claude/skills/ai-collab/scripts/collab_router.sh
```

The router script supports:
- `--task <type> "<prompt>"` -- task-type routing with automatic fallback
- `--model <model> "<prompt>"` -- explicit model override
- `--dry-run` -- show routing decision without executing
- `--list-tasks` -- display full routing table
- Logging to `/tmp/collab-router-logs/collab-router.log`

## Fallback Chains (detailed)

When the primary model for a task type fails (quota exhaustion, timeout, hang):

| Task Type | Primary | Fallback 1 | Fallback 2 | Final |
|-----------|---------|------------|------------|-------|
| research | Gemini 2.5 Pro | Codex | WebSearch | -- |
| verify | Gemini 2.5 Flash | WebSearch | Claude native | -- |
| persona | Gemini 2.5 Pro | Codex | -- | (different model family maintained) |
| seo | Gemini 2.5 Flash | Codex | -- | -- |
| code | Codex | Claude native | -- | -- |
| review | Codex | Gemini 2.5 Pro | Claude native | -- |
| html-build | Codex | Claude native | -- | -- |
| writing | Claude native | -- | -- | (no fallback needed) |
| judgment | Claude native | -- | -- | (no fallback needed) |
| chinese | Claude native | -- | -- | (no fallback needed) |

## Relationship to /ai-fallback

`/ai-collab` **replaces** `/ai-fallback` for normal OGSM agent use:
- `/ai-fallback` was model-chain-centric: you specified a chain of models directly
- `/ai-collab` is task-type-centric: you specify what you're doing, the router picks the model

`/ai-fallback` remains available as a low-level escape hatch for cases where explicit chain control is needed, but OGSM agents should use `/ai-collab --task <type>` as their standard invocation.

## OGSM Agent Mapping

| Agent | Task Type | CLI Command |
|-------|-----------|-------------|
| Investigator A | research | `/ai-collab --task research "..."` |
| Investigator B | research + verify | `/ai-collab --task research "..."` + `/ai-collab --task verify "..."` |
| Fact Checker | verify | `/ai-collab --task verify "..."` |
| Source Reviewer | review | `/ai-collab --task review "..."` |
| Compliance Reviewer | persona | `/ai-collab --task persona "..."` |
| PA Advisor | persona | `/ai-collab --task persona "..."` |
| Sales Rep Advisor | persona | `/ai-collab --task persona "..."` |
| Fresh Eyes Reviewer | persona | `/ai-collab --task persona "..."` |
| LO Validator | persona | `/ai-collab --task persona "..."` |
| Engineer (HTML) | code + html-build | `/ai-collab --task code "..."` + `/ai-collab --task html-build "..."` |
| SEO/AEO Engineer | seo | `/ai-collab --task seo "..."` |
| Writer A/B | writing | Claude native (no CLI) |
| Content Director | judgment | Claude native (no CLI) |
| Engagement Designer | writing | Claude native (no CLI) |
| Copy Editor | writing | Claude native (no CLI) |
| Commander | judgment | Claude native (no CLI) |
| Bilingual Publisher | chinese + html-build | Claude native + `/ai-collab --task html-build "..."` |
| Quality Auditor | judgment | Claude native (no CLI) |
| Performance Supervisor | review | `/ai-collab --task review "..."` |
| Candidate Collector | judgment | Claude native (no CLI) |
| Post-Test Designer | persona + review | `/ai-collab --task persona "..."` + `/ai-collab --task review "..."` |

## Cost Model

| Model | Pricing | Best for |
|-------|---------|----------|
| Gemini 2.5 Pro (Max) | Paid tier via GEMINI_API_KEY | research, persona, complex analysis |
| Gemini 2.5 Flash (Max) | Paid tier via GEMINI_API_KEY | verify, seo, quick checks |
| Codex (Max) | $20/month subscription | code, review, html-build |
| Claude (native) | Current session | writing, judgment, chinese |
| WebSearch | Free (Claude Code built-in) | Final research fallback |

**Key principle**: Task type determines model, not the other way around. The router abstracts away model selection so agents think in terms of "what am I doing" not "which model should I use."
