---
name: ogsm-framework
description: Apply the OGSM strategic planning framework (張敏敏老師方法論) to AI agent teams. Use when the user wants to plan a multi-agent project using OGSM, define team goals, set up measurement layers, or align agents with strategic objectives. Triggers on "OGSM", "張敏敏", "策略規劃", "團隊目標", "定義目標", "align the team", "strategic planning".
---

# OGSM Framework for AI Agent Teams

Apply the OGSM strategic planning framework (Objectives, Goals, Strategies, Measures) to coordinate AI agent teams. Based on 張敏敏 老師's OGSM methodology, adapted for multi-agent workflows.

## The OGSM Philosophy (The Most Important Part)

**OGSM 不是 OKR。** If you write it like OKR (task lists + checkpoints), you've missed the point.

| Layer | What it really is | Common mistake |
|-------|-------------------|----------------|
| **O** (Objective) | Final destination. Emotional + directional. | Too vague ("become the best") |
| **G** (Goal) | Integrative phase goal that **connects back to O**. Reader should feel the target audience in every G. | Writing task lists here |
| **S** (Strategy) | The path chosen for THIS audience. Must answer "why this road, not another?" | Generic methods anyone could use |
| **M** (Measure) | Tasks + acceptance criteria + quality gates | Missing or merged with G |

### The Golden Rule

**每個 G 讀起來都要能感受到目標對象的存在。**

❌ Wrong G: "Deliver 5 case studies with 3 sources each"
✅ Right G: "Architects reading this can cite the exact code section in a project meeting without fear of being corrected"

❌ Wrong S: "Use markdown format, add interactive checkpoints every 10 minutes"
✅ Right S: "Use MasterFormat chapter numbers and AIA contract language — architects recognize these as credible reference systems"

### Why OGSM Beats Pure Task Lists

- **OKR** = Google engineer style (pragmatic, metric-driven)
- **OGSM** = Normal people style (story-driven, audience-connected)
- OGSM forces you to answer: "Why does this work matter for THIS specific audience?"
- Pure task lists lose the "why" and become mechanical

## Workflow

### Step 1: Define O (with user)

O should be:
- **Emotional** (not just functional) — "make architects love this" not just "teach architects"
- **Audience-specific** — name the target audience explicitly
- **Outcome-focused** — what the audience can DO or FEEL after, not what we produced

Ask the user:
1. Who is the target audience?
2. What emotional state should they be in after?
3. What should they be able to do independently?

Propose the O. Get confirmation before proceeding.

### Step 2: Each Agent Writes Their G, S, M

Dispatch each agent (in parallel) with the confirmed O. Each agent writes:

```markdown
### [role name]

**G (Integrative phase goal — must link back to O)**
> One sentence. Reader should feel the target audience in it.

**S (Path chosen for THIS audience)**
- Strategy 1: specific method + why this works for the audience
- Strategy 2: ...
- Must answer "why not another path?"
- No generic methods.

**M (Tasks + acceptance criteria)**
- Quantitative targets (how many, how long, what sources)
- Format requirements
- Verification standard (who checks, how)

**Alignment to O**
One sentence: Why achieving this G contributes to O.
```

### Step 3: Add Measurement Layer (3 Agents Minimum)

These are separate from the "reviewers" — reviewers check quality, measurement checks progress.

1. **Performance Supervisor** — monitors G achievement rate per agent
2. **Quality Auditor** — verifies S commitments are honored
3. **Learning Outcome Validator** — directly tests whether O is achieved (persona simulation)

### Step 4: Add External Reviewers (Most Important Upgrade)

❌ **Common failure**: All reviewers are internal company roles → confirmation bias → everyone gives themselves 100%.

✅ **Correct design**: Add reviewers from OUTSIDE perspectives:

- **Audience Persona Reviewer** — Use a DIFFERENT AI model (e.g., Gemini if team uses Claude) to simulate the target audience reading it fresh
- **Adjacent Role Reviewer** — Someone with a different stake (e.g., if target is architects, add a "contractor" or "sales rep" persona)
- **Fresh Eyes Reviewer** — A reviewer with no context about the project, checking if it makes sense standalone

**Key principle**: Reviewers should NOT all be internal company roles. Use different AI models and different persona perspectives.

### Step 5: Alignment Verification Matrix

Create a table:

| Agent | Primary G | How G connects to O | O risk if G fails |
|-------|-----------|---------------------|-------------------|
| ... | ... | ... | ... |

If any row has a weak "connects to O" column, the G is wrong — rewrite it.

### Step 6: Wave Gates

Define gates between phases. Most important gate: **the final gate must verify O directly**, not just check that tasks are complete.

Example for a course:
- Gate 3 (before deployment): Learning Outcome Validator confirms 3 personas can answer 4/5 decision questions correctly. If not, no deployment.

## Anti-Patterns to Avoid

### Anti-pattern 1: G is actually M
**Symptom**: Reading G feels like reading a task list.
**Fix**: Ask "does this G mention the target audience?" If no, rewrite.

### Anti-pattern 2: S is generic method
**Symptom**: The strategy could apply to any project with any audience.
**Fix**: Add "for [audience], because [reason]" to every strategy. If you can't, it's not really a strategy.

### Anti-pattern 3: All reviewers are internal
**Symptom**: Every quality checker is a company role.
**Fix**: Add at least 2 external-perspective reviewers using different AI models or personas.

### Anti-pattern 4: No verification of O
**Symptom**: Final gate is "HTML passes W3C validation" or similar technical check.
**Fix**: Add a gate that directly tests whether the target audience can achieve the O.

### Anti-pattern 5: Self-graded homework
**Symptom**: The team checks its own work with its own standards.
**Fix**: Introduce external standards (industry benchmarks, audience personas, different AI models).

## References

- 張敏敏 老師 (Teacher Zhang Minmin) — Taiwan's leading OGSM practitioner
- **《OGSM 打造高敏捷團隊》** — classic OGSM book for teams
- **《OGSM 變革領導》** — advanced OGSM for change management
- Both published by 商業周刊 (Business Weekly, Taiwan)

## Example

See `/waterson-ai-growth-system/docs/aia-course/WTR-HSW-002-OGSM-v2.md` for a real-world example applying this framework to an AIA CEU course with 18 agents (15 workers + 3 external reviewers).

## Integration with Other Skills

- Use with `/aia-rewrite` for AIA course projects
- Use with `/publish-article` for blog article teams
- Use with `/agent-builder` when defining new agent roles — always ask "what's this agent's G in OGSM terms?"
