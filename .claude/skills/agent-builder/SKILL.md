---
name: agent-builder
description: Create or modify AI agent roles in the team. Use when the user wants to add a new agent, change an existing agent's behavior, or review the current team roster. Triggers on "add agent", "new role", "modify agent", "change the writer", "list agents", "加角色", "改一下", "列出 agent".
---

# Agent Builder

## When to use
- User wants to add a new agent role
- User wants to modify an existing agent's behavior
- User wants to see the current team roster

## Step 1: Clarify before building

**Never create or modify a role immediately.** Ask these questions first:

### For new roles:
1. **Scope**: What does this role do? (be specific)
2. **Collaboration**: Work with other roles or independently?
3. **Tools**: Which AI? (Gemini=free search / Codex=code / Sonnet=writing)
4. **Output**: What format? (report / edit files / suggestion list)

### For modifications:
1. **Which role**: Which agent to change?
2. **What to change**: Tone? Scope? Tools?
3. **Why**: What was wrong with the last result?
4. **Expected**: What should be different after the change?

## Step 2: Confirm

Summarize and wait for user confirmation before proceeding.

## Step 3: Build

- New role in existing skill → update that skill's SKILL.md
- New standalone skill → create skill directory + SKILL.md
- Modification → edit the relevant SKILL.md
- Update CATALOG.md if needed

## Step 4: Test

Offer to run a test after building.
