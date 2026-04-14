---
name: AI Team Architecture
description: Design AI agent teams using OGSM framework + 3-layer architecture (CLAUDE.md/Memory/Skills) + multi-model task-type routing (Claude/Codex/Gemini). Use when setting up new agent teams, configuring multi-model collaboration, or teaching the architecture to others. Triggers on "設計 agent 團隊", "建 AI 團隊", "multi-model routing", "OGSM agent", "三層架構".
---

# AI Team Architecture — Skill Package

Design, deploy, and manage AI agent teams using the OGSM framework, 3-layer claude code skill architecture, and multi-model routing (Claude, Gemini, Codex).

## Script-First Principle

**If a task can be done by a script, run the script. Do NOT dispatch an AI model.**

AI models are for judgment and creativity. Deterministic tasks have scripts:

| Wrong | Right |
|-------|-------|
| Dispatch Codex to generate HTML | Run `md_to_blog.py` |
| Dispatch Gemini to check 404s | Run `check_links.py` |
| Dispatch AI to validate schema | Run `validate_schema.py` |
| Dispatch AI to scaffold project | Run `setup_team.sh` |
| Dispatch AI to generate permissions | Run `generate_permissions.py` |

**Rule**: Check `scripts/` first. Only route to an AI model when the task requires judgment, creativity, or contextual reasoning that no script can handle.

## Quick Start

### Step 1: Scaffold the team

```bash
bash ~/.claude/skills/ai-team-architecture/scripts/setup_team.sh <project-name>
```

Creates: `CLAUDE.md`, `memory/MEMORY.md`, `skills/` scaffold, and a starter OGSM plan.

### Step 2: Configure OGSM

Define your team's Objective, then let each agent write their G/S/M. See [OGSM Quick Start](references/ogsm-quick-start.md) for the full methodology.

Key decisions at this stage:
- Who is the target audience?
- What is the emotional + practical outcome (the O)?
- Which roles are **agents** (persistent, judgment-based) vs **skills** (repeatable, rule-based)?

### Step 3: Set routing

Map each agent's tasks to the best model using the routing table:

| Task Type | Primary Model | Fallback |
|-----------|--------------|----------|
| research | Gemini 2.5 Pro | Codex -> WebSearch |
| verify | Gemini 2.5 Flash | WebSearch -> Claude |
| persona | Gemini 2.5 Pro | Codex |
| seo | Gemini 2.5 Flash | Codex |
| code | Codex | Claude |
| review | Codex | Gemini -> Claude |
| html-build | Codex | Claude |
| writing | **Claude (native)** | -- |
| judgment | **Claude (native)** | -- |
| chinese | **Claude (native)** | -- |

See [Multi-Model Routing](references/multi-model-routing.md) for fallback chains and cost model.

## When to Use This Skill

- **Designing a new agent team** from scratch (new project, new course, new product)
- **Configuring multi-model collaboration** — deciding which model handles which task type
- **Teaching the architecture** to others — the references/ folder is the curriculum
- **Auditing an existing team** — check if OGSM alignment holds, routing is optimal, layers are clean

## 3 Core Concepts

### 1. OGSM for Agent Goals

Every agent team needs an Objective that is emotional, audience-specific, and outcome-focused. Goals (G) connect back to O. Strategies (S) explain *why this path*. Measures (M) verify that S resources were actually used — not just that deliverables exist.

Direction Seed (9-field briefing template) ensures subprocess agents get full context despite running in isolation.

-> [Full reference: OGSM Quick Start](references/ogsm-quick-start.md)

### 2. 3-Layer Architecture

| Layer | Purpose | Persistence | When to use |
|-------|---------|-------------|-------------|
| CLAUDE.md | Project instructions | Always loaded | Rules needed every conversation |
| Memory | Cross-session state | Persistent, auto-loaded | Feedback, preferences, project state |
| Skills | Modular capabilities | On-demand | Reusable workflows, reference docs |

-> [Full reference: Three-Layer Setup](references/three-layer-setup.md)

### 3. Multi-Model Task-Type Routing

Route by *what you're doing*, not *which model you like*. Research goes to Gemini (Google grounding). Code goes to Codex. Writing stays with Claude. This per-task-type approach (vs per-agent binding) saves 40-60% on research costs while maintaining quality.

-> [Full reference: Multi-Model Routing](references/multi-model-routing.md)

## Available Scripts

All scripts live in `~/.claude/skills/ai-team-architecture/scripts/`.

### setup_team.sh
Scaffold a new agent team project with CLAUDE.md, memory, and skills structure.
```bash
bash scripts/setup_team.sh my-new-project
```

### check_links.py
Validate all internal cross-references between SKILL.md, references, and OGSM plans.
```bash
python scripts/check_links.py ~/.claude/skills/ai-team-architecture/
```

### validate_schema.py
Validate an OGSM plan against the required schema (O/G/S/M sections, Direction Seed fields, Anti-patterns).
```bash
python scripts/validate_schema.py path/to/OGSM-plan.md
```

### generate_permissions.py
Generate a `settings.json` permission whitelist for background agent execution.
```bash
python scripts/generate_permissions.py --project my-project --output .claude/settings.json
```

### md_to_blog.py
Convert markdown reference docs to blog-ready HTML (for publishing architecture articles).
```bash
python scripts/md_to_blog.py references/ogsm-quick-start.md --output /tmp/blog-post.html
```

## Background Execution

Agents dispatched via the Agent tool can run in background using `run_in_background: true`. This enables parallel Wave execution — critical for teams with 12+ agents.

**Permission whitelist**: Configure `settings.json` with `defaultMode: "dontAsk"` for tools agents need (Read, Write, Bash, Glob, Grep). Use `generate_permissions.py` to create the whitelist.

**Anti-patterns**:
- Do NOT do work yourself when you should dispatch subagents
- Do NOT create artificial wave gates for tasks that can run in parallel

-> [Full reference: Background Execution](references/background-execution.md)

## Storyboard Tool Integration

The [Storyboard Tool](https://watersonusa.ai/tools/storyboard/) provides a visual editor for course content that syncs to Supabase. When edits are saved, `/aia-rewrite` reads the changes and dispatches the 12-role agent fleet to rewrite course HTML.

This is the primary content editing interface for the agent team workflow — humans edit in storyboard, agents execute the rewrite.

-> [Full reference: Storyboard Tool](references/storyboard-tool.md)

## Quick Reference — Routing Table

| Task Type | Model | CLI Command | Cost Tier |
|-----------|-------|-------------|-----------|
| research | Gemini 2.5 Pro | `/ai-collab --task research "..."` | Paid (API key) |
| verify | Gemini 2.5 Flash | `/ai-collab --task verify "..."` | Paid (API key) |
| persona | Gemini 2.5 Pro | `/ai-collab --task persona "..."` | Paid (API key) |
| seo | Gemini 2.5 Flash | `/ai-collab --task seo "..."` | Paid (API key) |
| code | Codex | `/ai-collab --task code "..."` | $20/mo subscription |
| review | Codex | `/ai-collab --task review "..."` | $20/mo subscription |
| html-build | Codex | `/ai-collab --task html-build "..."` | $20/mo subscription |
| writing | Claude (native) | Direct (no CLI) | Current session |
| judgment | Claude (native) | Direct (no CLI) | Current session |
| chinese | Claude (native) | Direct (no CLI) | Current session |

**Key principle**: Task type determines model, not the other way around. Agents think in terms of "what am I doing" — the router picks the model.
