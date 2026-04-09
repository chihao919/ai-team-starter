---
name: example-skill
description: A template skill showing how to define a multi-agent workflow. Replace this with your own skill. Triggers on "/example-skill" or when the user discusses the task this skill handles.
---

# Example Skill — [Replace with your skill name]

This is a template. Replace the content with your own workflow.

## Direction Seed Template

Before dispatching agents, define the direction seed:
```
Direction: [What we're doing and why]
Tone: [Professional / casual / technical]
Constraints: [What NOT to do]
Audience: [Who reads the output]
```

## Agent Roles

### Wave 1 — Research + Draft (parallel)

| # | Role | AI | Task |
|---|------|----|------|
| 1 | Researcher | Gemini Flash (free) | Research facts and data for the task |
| 2 | Writer | Claude Sonnet | Write the first draft based on user input |
| 3 | Designer | Claude Sonnet | Design the structure and interactive elements |

### Wave 2 — Review (parallel, after Wave 1)

| # | Role | AI | Task |
|---|------|----|------|
| 4 | Quality Reviewer | Claude Sonnet | Check overall quality and coherence |
| 5 | Fact Checker | Gemini Flash (free) | Verify every number and citation |
| 6 | Editor | Claude Sonnet | Proofread grammar and terminology |

### Wave 3 — Integrate (sequential)

| # | Role | AI | Task |
|---|------|----|------|
| 7 | Developer | Claude Sonnet | Build the final output |
| 8 | Team Leader | Claude Opus | Final decision, resolve conflicts, deploy |

## Citation Rule

Every factual claim in the output must have a source citation.
Unverifiable claims → mark `[Source needed — verify before publishing]`

## Execution

1. Read user input → identify what needs to be done
2. Set direction seed
3. Wave 1 (parallel) → collect results
4. Wave 2 (parallel) → collect reviews
5. Team leader integrates feedback
6. Wave 3: build final output → deploy
