# Multi-Model Task-Type Routing

Route AI work by **task type**, not by agent identity. This is our key differentiator from frameworks like LangGraph or CrewAI, which bind one model to one agent permanently.

## Per-Task-Type Routing vs Per-Agent Binding

### Per-agent binding (LangGraph/CrewAI approach)
```
Agent: Investigator -> GPT-4
Agent: Writer -> Claude
Agent: Reviewer -> GPT-4
```
Problem: the Investigator uses GPT-4 for everything — research, writing notes, formatting output — even when another model would be better for a specific subtask.

### Per-task-type routing (our approach)
```
Task: research -> Gemini 2.5 Pro (Google Search grounding)
Task: writing  -> Claude (creative, emotional arc)
Task: code     -> Codex (structured output)
```
The same agent (e.g., Investigator) uses Gemini for research, Claude for writing notes, and Codex for formatting. The **task** determines the model, not the agent's identity.

### Why this matters
- Each model has genuine strengths (Gemini for search grounding, Codex for code, Claude for writing)
- Per-task routing exploits these strengths for every subtask within every agent
- Cost optimization: Gemini handles high-volume research at lower cost than Claude

## The Routing Table

| Task Type | Primary Model | Fallback Chain | Rationale |
|-----------|--------------|----------------|-----------|
| `research` | Gemini 2.5 Pro (Max) | -> Codex -> WebSearch | Google Search grounding, best for discovery |
| `verify` | Gemini 2.5 Flash (Max) | -> WebSearch -> Claude | Web grounding for fact verification |
| `persona` | Gemini 2.5 Pro (Max) | -> Codex | Different model family = independent perspective |
| `seo` | Gemini 2.5 Flash (Max) | -> Codex | Google search insight |
| `code` | Codex (Max) | -> Claude native | Code generation, HTML/CSS/JS |
| `review` | Codex (Max) | -> Gemini -> Claude | Systematic checking, citation cross-verification |
| `html-build` | Codex (Max) | -> Claude native | Structured output |
| `writing` | **Claude (native)** | -- | Creative, emotional arc, architect voice |
| `judgment` | **Claude (native)** | -- | Complex decisions, conflict resolution |
| `chinese` | **Claude (native)** | -- | Best Chinese quality |

## Using /ai-collab

The `/ai-collab` skill is the CLI interface for task-type routing.

### Basic usage
```bash
# Research -> routes to Gemini 2.5 Pro
/ai-collab --task research "Find healthcare door failure cases post-2020"

# Code -> routes to Codex
/ai-collab --task code "Build HTML slide template with ARIA landmarks"

# Verify -> routes to Gemini 2.5 Flash
/ai-collab --task verify "Is NFPA 80 §6.4.1.4 verbatim correct?"
```

### Model override (escape hatch)
```bash
/ai-collab --model gemini-2.5-pro "specific prompt requiring Pro"
```

### Dry-run (see routing without executing)
```bash
/ai-collab --dry-run --task research "test prompt"
# Output: Task type: research | Chain: gemini-2.5-pro,codex,websearch
```

### When NOT to use /ai-collab
For `writing`, `judgment`, and `chinese` tasks — Claude handles these natively. Adding CLI overhead adds latency with no quality improvement.

## Fallback Chains

When the primary model fails (quota exhaustion, timeout, hang), the router tries the next model in the chain:

| Task Type | Primary | Fallback 1 | Fallback 2 |
|-----------|---------|------------|------------|
| research | Gemini Pro | Codex | WebSearch |
| verify | Gemini Flash | WebSearch | Claude |
| persona | Gemini Pro | Codex | -- |
| seo | Gemini Flash | Codex | -- |
| code | Codex | Claude | -- |
| review | Codex | Gemini Pro | Claude |
| html-build | Codex | Claude | -- |

### Gemini REST vs CLI

The `/ai-fallback` skill was rewritten to use Gemini via REST API (`curl` + `GEMINI_API_KEY`) instead of CLI. This eliminates hang issues that blocked production scale-up. See `~/.claude/skills/ogsm-framework/references/gemini-cli-vs-rest-api.md` for details.

## Cost Model

| Model | Pricing | Best for |
|-------|---------|----------|
| Gemini 2.5 Pro (Max) | Paid tier via GEMINI_API_KEY | research, persona, complex analysis |
| Gemini 2.5 Flash (Max) | Paid tier via GEMINI_API_KEY | verify, seo, quick checks |
| Codex (Max) | $20/month subscription | code, review, html-build |
| Claude (native) | Current session | writing, judgment, chinese |
| WebSearch | Free (Claude Code built-in) | Final research fallback |

### Cost Savings

Routing research tasks to Gemini instead of keeping everything in Claude saves **40-60% on research-heavy projects**. In a 19-agent AIA course fleet:
- 6 agents use Gemini for research/verify/persona/seo
- 4 agents use Codex for code/review/html-build
- 9 agents stay on Claude for writing/judgment/chinese

The Gemini-routed research produces higher quality results (Google Search grounding) at lower cost — a win on both axes.

## OGSM Agent Mapping

Each agent in an OGSM team maps to task types, not directly to models:

| Agent Archetype | Primary Task Types | Models Used |
|----------------|-------------------|-------------|
| Investigator | research, verify | Gemini Pro, Gemini Flash |
| Reviewer (persona) | persona, verify | Gemini Pro, Gemini Flash |
| Writer | writing, chinese | Claude (native) |
| Engineer | code, html-build | Codex |
| SEO Specialist | seo, research | Gemini Flash, Gemini Pro |
| Commander | judgment | Claude (native) |
| Quality Auditor | judgment, review | Claude, Codex |

The Model Invocation Map in the OGSM spec documents the exact mapping for each agent, with full command format and trigger conditions.

## Connection to v5.2-copilot Spec

The routing table and cost model are documented in the v5.2-copilot OGSM specification. The `/ai-collab` skill (at `~/.claude/skills/ai-collab/SKILL.md`) contains the full implementation including the router script.
