# Three-Layer Architecture for Claude Code

The 3-layer architecture (CLAUDE.md / Memory / Skills) is the foundation of how Claude Code agents organize persistent knowledge and reusable capabilities.

## Layer 1: CLAUDE.md — Project Instructions (Always Loaded)

CLAUDE.md is automatically loaded at the start of every conversation. It contains rules, conventions, and instructions that apply to every interaction.

### What belongs here
- Development principles and workflow rules
- Git configuration and deployment settings
- Agent role definitions and intent detection tables
- Communication style preferences
- Cross-project conventions (e.g., "use Chinese to discuss, English for code")

### What does NOT belong here
- Reference data that changes frequently (put in Memory)
- Reusable workflows with multiple steps (put in Skills)
- Large datasets or lookup tables (put in Skills references/)

### Structure example
```markdown
# Project Name — Agent Role

## Intent Detection Table
| User action | Skill to invoke |
|------------|----------------|
| ...        | /skill-name    |

## Core Principles
1. Understand before acting
2. Small task: confirm -> fix -> verify -> report
3. Large task: Plan Mode -> subtasks

## Git Configuration
- user: ...
- email: ...
```

### Key property
Always loaded = always costs context tokens. Keep it concise. Move detail to Skills.

## Layer 2: Memory — Persistent Cross-Session State (Auto-Loaded)

Memory files (`MEMORY.md` and related files in `memory/`) persist across conversations. They store learned preferences, feedback, and project state.

### What belongs here
- User feedback and behavioral rules (e.g., "先理解再動手")
- Design preferences (e.g., "美式大字 16-20px")
- Active project index and status
- Learned anti-patterns from past mistakes
- Cross-reference indexes to other files

### Structure example
```markdown
# Memory Index

## Behavioral Rules
- feedback_agent_workflow — understand before acting
- feedback_auto_approve_reads — read operations: just do it

## Design Preferences
- feedback_ui_style — large text 16-20px

## Active Projects
- projects_active — project index
```

### Key property
Auto-loaded but indexed. Use short keys with descriptive values. The index pattern (`key — description`) lets the agent scan quickly without reading full detail.

## Layer 3: Skills — Modular, On-Demand, Reusable

Skills are self-contained packages with a `SKILL.md` descriptor, optional `scripts/`, and optional `references/`. They are loaded on-demand when triggered by user intent.

### Skill package structure
```
~/.claude/skills/<skill-name>/
├── SKILL.md            # Descriptor (YAML frontmatter + instructions)
├── scripts/            # Executable scripts (bash, python)
│   ├── main_script.sh
│   └── helper.py
└── references/         # Reference docs for deep detail
    ├── concept-a.md
    └── concept-b.md
```

### SKILL.md anatomy
```yaml
---
name: skill-name
description: When to use this skill. Trigger phrases. Purpose.
---

# Skill Title

## Quick instructions (what the agent should do)
## Available scripts (with usage examples)
## Reference links (to references/ docs)
```

### What belongs here
- Reusable workflows (article publishing, course rewriting, security scanning)
- Domain knowledge (OGSM framework, payment integration, shipping)
- Tool integrations (FedEx API, Shopify, PayPal)
- Reference documentation that agents need on-demand

### Key property
On-demand = zero context cost until triggered. This is where large reference material goes.

## Decision Framework: Where Does This Go?

| Question | Answer | Layer |
|----------|--------|-------|
| Is this a rule needed every conversation? | Yes | CLAUDE.md |
| Is this learned feedback or preference? | Yes | Memory |
| Is this a reusable workflow? | Yes | Skill |
| Is this reference data for a specific domain? | Yes | Skill (references/) |
| Does it change based on user feedback? | Yes | Memory |
| Is it a one-time project note? | Yes | Memory |
| Will multiple projects use this? | Yes | Skill |

### The Litmus Test

1. "Do I need this in EVERY conversation?" -> CLAUDE.md
2. "Did I learn this from a past mistake?" -> Memory
3. "Can another project reuse this?" -> Skill
4. "Is this a large reference doc?" -> Skill references/

## How the Layers Interact

```
Conversation Start
  └── Load CLAUDE.md (always)
  └── Load MEMORY.md (always)
  └── User says something
       └── Match intent -> Trigger Skill (on-demand)
            └── Skill reads references/ (on-demand)
            └── Skill runs scripts/ (on-demand)
```

### Subprocess Agent Isolation (Principle 7)

When dispatching subagents via the Agent tool, they run in isolated context:
- They **cannot** see the parent's CLAUDE.md
- They **cannot** see the parent's Memory
- They **cannot** see the current conversation

This means: any knowledge a subagent needs must be explicitly passed in the Direction Seed briefing, or the subagent must be told to read specific file paths.

## Connection to OGSM Brief Layering

The 3-layer architecture philosophy maps directly to OGSM Brief Layering:

| Architecture Layer | Brief Layer | Loading |
|-------------------|-------------|---------|
| CLAUDE.md | Tier 1 briefing (~150 words) | Always in dispatch |
| Memory | Tier 2 reference (file path) | On-demand read |
| Skills | Skill invocations in S section | Triggered by agent |

This parallel structure means teams who understand the 3-layer architecture intuitively understand Brief Layering — and vice versa.

## Original Source

This architecture was first described in the [Series Hub article](https://watersonusa.ai/blog/claude-code-skill-architecture/) and refined through production use in the AIA course agent fleet (19 agents, v5.2 OGSM spec).
