# OGSM Quick Start for AI Agent Teams

Based on 張敏敏老師's OGSM methodology, adapted for multi-agent AI workflows.

## What is OGSM?

OGSM stands for **Objective, Goals, Strategies, Measures**. Unlike OKR (task lists + checkpoints), OGSM is story-driven and audience-connected.

| Layer | What it is | Common mistake |
|-------|-----------|----------------|
| **O** (Objective) | Final destination. Emotional + directional. | Too vague ("become the best") |
| **G** (Goal) | Integrative phase goal that connects back to O. | Writing task lists |
| **S** (Strategy) | The path chosen for THIS audience. Answers "why this road?" | Generic methods |
| **M** (Measure) | Tasks + acceptance criteria + quality gates | Missing or merged with G |

### The Golden Rule

**Every G should make the reader feel the target audience's presence.**

- Wrong G: "Deliver 5 case studies with 3 sources each"
- Right G: "Architects reading this can cite the exact code section in a project meeting without fear of being corrected"

## How OGSM Maps to Agent Definition

### O -> Team-wide Objective
Defined once by the Commander with the user. Must be:
- **Emotional** — "make architects love this" not just "teach architects"
- **Audience-specific** — name the target audience explicitly
- **Outcome-focused** — what the audience can DO or FEEL after

### G -> Each Agent's Integrative Goal
Every agent writes one G sentence that links back to O. The G represents what this agent uniquely contributes to the team's objective.

### S -> Each Agent's Chosen Path
Strategies must explain *why this approach works for this audience*. Must include:
- Specific methods (not generic)
- Skill invocations (from the Skill Invocation Map)
- Model invocations (from the Model Invocation Map)
- Anti-patterns (what NOT to do)

### M -> Verification That S Was Actually Used
Measures verify resource commitments, not just deliverable counts.

- Wrong M: "Document 4 code sections" (deliverable count)
- Right M: "Every citation cross-checked against both ICC and NFPA sources? How many corrections found?" (resource verification)

### Agent vs Skill Boundary
Before defining a new agent, ask: **is this a role or a repeatable process?**

- **Agent** = persistent noun, cross-time judgment, accumulated context
- **Skill** = repeatable verb-process, rule-based logic, callable from any agent

Diagnostic: "Is this judgment rule-based or situational?"
- Rule-based -> Skill
- Situational -> Agent

## Direction Seed — 9-Field Template

Every subagent dispatch must include all 9 fields. Missing any field is a briefing failure.

```
Field 1: Course/Project ID + Role Name
  e.g., HSW-002 / Investigator A

Field 2: Target Audience Persona
  Concrete description: years of experience, daily workflow,
  pressures, what they actually do vs assumed.

Field 3: O (Objective) — quoted in full
  Never abbreviate. The subagent must see both the emotional
  goal and the practical outcome.

Field 4: This agent's G/S/M
  Copied from the OGSM doc. Tier 1 (~150 words) in the
  briefing; Tier 2 (full detail) by file reference.

Field 5: Embedded Skill + Model Invocations
  Copied from both Invocation Maps with full command format
  and trigger conditions. This is Principle 7 at dispatch.

Field 6: Hard Constraints
  e.g., promotional ratio < 20%, must cite two independent
  sources, no fabricated data.

Field 7: Tone + Voice Requirements
  e.g., peer-to-peer with a 12-year practitioner; direct;
  never condescend.

Field 8: Deliverable Format + File Path
  Exact filename, section structure, output path.

Field 9: Anti-patterns to avoid
  At least 3 items in "NOT: X — INSTEAD: Y" format.
  Source: agent's pre-written Anti-patterns Standard List.
```

### Why Field 9 Matters

Subprocess agents run in isolated context. What is "obvious" to the parent who designed the system is invisible to the fresh subprocess. The anti-patterns list forces the parent to ask: "What would this subagent do if it interpreted the briefing charitably but incorrectly?"

## Pilot Dispatch Pattern

For each wave: dispatch **1 subagent first** (the pilot), wait for output, sanity-check against the O, then dispatch the rest in parallel.

**Why**: Most briefing gaps are systematic — from the parent's assumptions, not the agent's quirks. If the pilot output is wrong, updating the briefing costs 1 extra round-trip. If 4 agents go parallel with a flawed briefing, fixing requires 4 re-dispatches.

**Implementation**:
1. Wave 1: dispatch one investigator as pilot -> pass gate -> dispatch all Wave 1 agents
2. Wave 2: dispatch one reviewer as pilot -> pass gate -> dispatch remaining reviewers
3. Wave 3: dispatch engineer as pilot -> pass gate -> continue

Pilot sanity-check is Commander's job — it requires cross-agent judgment.

## Canonical Example

The v5.2 OGSM spec (`WTR-HSW-*-OGSM-v5.2.md`) is the canonical reference implementation. It includes:
- 19 agents across 3 waves
- Full Skill Invocation Map + Model Invocation Map
- Direction Seed examples for every agent archetype
- Per-agent Anti-patterns Standard Lists
- Brief Layering (Tier 1 / Tier 2)

See also: `~/.claude/skills/ogsm-framework/SKILL.md` for the complete OGSM skill with validation scripts.

## Anti-Patterns in OGSM Design

| Anti-pattern | Correct approach |
|-------------|-----------------|
| Writing G as a task list | Write G as an audience outcome |
| All reviewers from internal perspectives | Add external persona reviewers using different AI models |
| M counts deliverables only | M verifies resource commitments from S |
| Skipping field 9 in Direction Seed | Always include 3+ anti-patterns per dispatch |
| Dispatching all agents at once | Pilot Dispatch: 1 first, then parallel |
| Putting full detail in every briefing | Brief Layering: Tier 1 (~150 words) + Tier 2 (file ref) |
