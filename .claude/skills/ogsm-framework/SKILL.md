---
name: ogsm-framework
description: Apply the OGSM strategic planning framework (張敏敏老師方法論) to AI agent teams. Use when the user wants to plan a multi-agent project using OGSM, define team goals, set up measurement layers, or align agents with strategic objectives. Triggers on "OGSM", "張敏敏", "策略規劃", "團隊目標", "定義目標", "align the team", "strategic planning".
---

## Before modifying OGSM content

**This skill has an executable enforcement component.** Before you modify any OGSM plan (`WTR-HSW-*-OGSM-*.md`), run:

```bash
python ~/.claude/skills/ogsm-framework/scripts/validate_s_to_m_coverage.py path/to/plan.md
```

This validates the OGSM strictness rule: **every S that references a skill invocation must have a matching M that verifies the invocation succeeded**. If you add a skill call to an agent's S and forget the corresponding M, this script catches it.

**Use the skill = run the script + address any gaps it reports.** Reading the principles in this file is necessary but not sufficient — running the script is what actually enforces structural completeness.

**When to run:**
- Before committing changes to any OGSM plan
- After adding or modifying an agent's S section
- After adding a new skill to the Skill Invocation Map
- After adding a new model to the Model Invocation Map
- When reviewing a colleague's OGSM plan

**Exit codes:**
- `0` — PASS (all S-skill/S-model invocations have matching M verification)
- `1` — file error (not found, invalid format)
- `2` — GAPS detected (script prints which agents have unverified invocations)

**Verbose mode** for debugging: `--verbose`
**Quiet mode** for CI: `--quiet`

---

## Before starting any agent optimization factory run

**Learnings from the mini-agent validation run (3 teams x 3 cycles) AND Batch 1-4 scale-up (16/19 agents validated on real production inputs) are captured in references/ and MUST be consulted before starting fresh iteration cycles.** These are not passive documents — they are queryable via scripts designed for subprocess agent use (Principle 7 compliant).

### Scale-up status (updated 2026-04-11)

- **16/19 agents validated** across Batches 1-4 on real production-scale inputs
- Factory "polishing" phase complete; agents ready for production use
- G-016 parser bug fixed — v5 validator results are now trustworthy
- `/ai-fallback` rewritten to use Gemini REST API (eliminates G-001/G-012 hangs); see `references/gemini-cli-vs-rest-api.md`

### Knowledge base

Located in `~/.claude/skills/ogsm-framework/references/`:

- **`patterns-library.md`** — 18 discovered patterns classified as UNIVERSAL (3/3 teams), LIKELY UNIVERSAL (2/3), or ARCHETYPE-SPECIFIC (1/3). Each pattern has evidence, metric impact, and scaling recommendation.
  - P-014: Pre-dispatch granular flag format pinning in BDD
  - P-015: WebSearch as tool-level escape hatch for research archetype (CONFIRMED after REST rewrite — recommended PRIMARY for open-ended discovery)
  - P-016: Paywall workaround via AHJ adoption channels
  - P-017: Reviewer-override post-processing layer
  - P-018: Fresh Eyes Reviewer 3-axis override scoring
- **`scaling-playbook.md`** — how to scale factory from 3 mini-agents to 12-19 production agents. Batches by archetype, budget estimation, risk points, known good patterns.
- **`gotchas-and-lessons.md`** — 16 pitfalls documented (expanded from original ~10). Key additions:
  - G-011: ICC/NFPA paywall via AHJ workaround
  - G-012: Gemini Pro hang (extension of G-001 to Pro model)
  - G-013: Raw models don't autonomously enforce spec anti-patterns
  - G-014: Wrapper misclassifies Pro quota as hang (FIXED via REST rewrite)
  - G-015: Flash-Lite 90s timeout too tight for long prompts
  - G-016: `validate_ogsm_completeness` ANTI_START premature match (FIXED)
  - NEW-02: Wrapper vacuous success on Codex trust check (FIXED)
- **`unified-strategy.md`** — cross-team consolidated strategy.
- **`skill-invocation-map.md`** — central skill invocation reference (queried via get_skills_for_role.sh).
- **`gemini-cli-vs-rest-api.md`** — dual-track Gemini usage guide. CLI (GCA/OAuth, free tier, interactive) vs REST API (API key, paid tier, automated factory). `/ai-fallback` now uses REST exclusively.

### REST API migration note

`/ai-fallback` skill was rewritten (2026-04-11) to call Gemini via REST API (`curl` + `GEMINI_API_KEY` from `~/.zshrc`) instead of CLI. This eliminates the G-001/G-012 hang issues that blocked Batch 1-3 scale-up. Paid tier via Google AI Studio API key. See `references/gemini-cli-vs-rest-api.md` for full explanation.

### Query scripts (Principle 7 — subprocess-safe)

Instead of loading full references into context, query specific entries:

```bash
# Patterns relevant to a specific failure type
bash ~/.claude/skills/ogsm-framework/scripts/get_patterns_for_failure.sh <failure-type>

# Gotchas for a specific context
bash ~/.claude/skills/ogsm-framework/scripts/get_gotchas_for_context.sh <context-keyword>

# Skill commands for a role
bash ~/.claude/skills/ogsm-framework/scripts/get_skills_for_role.sh <role-name>
```

### Mandatory query triggers (per robot role)

- **Factory bootstrap** (Commander): read `scaling-playbook.md` fully via Read tool
- **Writing BDD scenarios** (Spec Verifier): `get_patterns_for_failure.sh bdd`
- **On any FAIL** (Iterator): BOTH `get_patterns_for_failure.sh <failure-type>` AND `get_gotchas_for_context.sh <context>`
- **Before proposing a diff**: `get_gotchas_for_context.sh <area>` to check known pitfalls
- **On Gemini-related failure**: check `references/gemini-cli-vs-rest-api.md` — distinguish CLI vs REST track before debugging

### Direction Seed integration

Every Iteration Team subagent's Direction Seed briefing MUST include in field 5 (Embedded Skill + Model Invocations):

```
Knowledge queries (run before proposing any diff):
- bash ~/.claude/skills/ogsm-framework/scripts/get_patterns_for_failure.sh <type>
- bash ~/.claude/skills/ogsm-framework/scripts/get_gotchas_for_context.sh <keyword>
```

This is Principle 7 applied: subprocess agents cannot see parent memory, so the knowledge access pattern must be embedded in the briefing.

### Why this exists

The mini-agent factory run discovered real patterns (structural header mismatch, skill discovery via central map, rotating test inputs) and real gotchas (Gemini hang, validator silent PASS, pointer additive-not-substitutive). The Batch 1-4 scale-up added 7 more gotchas and 5 more patterns on top of that, plus the REST API migration. Without this references/ + query scripts setup, future Iteration Teams would re-discover these learnings, wasting cycles. With this setup, they inherit the knowledge automatically.

---

# OGSM Framework for AI Agent Teams

**Skill version:** v2 (2026-04-10) — integrates HSW-002 v4 round 2 learnings: Principle 7, Skill/Agent boundary, Skill+Model Invocation Maps, Direction Seed 9 fields, Brief Layering, Pilot Dispatch, per-agent Anti-patterns, "don't fight LLM nature", "monitor don't preempt".

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

### Step 2: Each Agent Writes Their G, S, M — and Classify as Agent vs Skill First

**Before defining a new agent, ask: is this a role or a repeatable process?**

- **Agent** = a persistent noun with a cross-time G that requires situational/contextual judgment accumulated across waves.
- **Skill** = a repeatable verb-process callable from any agent's S section, driven by rule-based logic.

Forcing a repeatable process into agent shape causes: (1) role count inflation, (2) per-wave context coordination overhead, (3) skill reusability buried in a single project.

**Diagnostic question**: "Is this judgment rule-based (format check, classification, template application) or situational (depends on accumulated state or relationships across multiple waves)?"
- Rule-based → skill. Define it as a skill; let agents call it from their S.
- Situational → agent. Scope it tightly; make sure its G reflects the cross-time accumulation.

**Counter-check warning**: when a skill grows too stateful or begins making judgment calls based on history, it is secretly an agent. Re-evaluate the boundary if a skill's complexity grows.

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

**M (Tasks + acceptance criteria — must verify that S resources were actually used)**
- Quantitative targets (how many, how long, what sources)
- Format requirements
- Verification standard (who checks, how)
- **Resource verification**: Did the team actually use the sources S committed to?

**Alignment to O**
One sentence: Why achieving this G contributes to O.
```

**M must verify S's resource commitments — not just count deliverables.**

Wrong M:
- S: Use ICC Digital Codes as the primary reference
- M: Document 4 code sections ← this is a deliverable, not a measure

Right M:
- S: Cross-verify using ICC Digital Codes AND NFPA official publications
- M:
  - Every citation cross-checked against both sources?
  - How many corrections found through cross-verification?
  - Any citation relying on a single source only?

The test: M should read as "Did the team actually use the resources S committed to?" — not "How many things did the team produce?"

### Step 2b: Create Skill Invocation Map + Model Invocation Map

After drafting all agents' S sections, build two central tables as a single source of truth.

**Why**: Subprocess agents (dispatched via the Agent tool) run in an isolated context. They cannot see the parent Claude's CLAUDE.md, memory, or conversation history. Any skill or external LLM call that an agent needs must be written directly into that agent's S section — or into a central map that the Commander copies into every dispatch briefing.

**Skill Invocation Map** — one row per agent-skill pair:

| Agent | Wave | Skill | Trigger Condition | Command Format (full params) |
|-------|------|-------|-------------------|------------------------------|
| Investigator A | Wave 1 | `/content-scout flag-candidate` | Found a case study rich enough for a standalone blog post | `/content-scout flag-candidate --source-agent investigator-a --source-file [path] --title "..." --type case-study --keywords "..."  --research-data "..." --why-worth-writing "..."` |
| Engineer (HTML) | Wave 3 | `/post-test-designer` | Before converting course content to HTML | `/post-test-designer --course [ID] --course-file [path] --distribution 4/4/2` |

**Model Invocation Map** — parallel structure for multi-LLM delegation:

| Agent | Wave | Model | Purpose | Command Format |
|-------|------|-------|---------|----------------|
| Investigator A | Wave 1 | Gemini Flash | Search for real post-2020 cases, fact-check DHI sources | `echo "Y" \| gemini -m gemini-2.5-flash -p "Search [X] cases after 2020, return source URLs" --output-format text` |
| Project Architect Advisor | Wave 2 | Gemini 2.5 Pro | Simulate target audience persona reading the course cold | `echo "Y" \| gemini -m gemini-2.5-pro -p "Role-play 12-year Project Architect. Answer 6 decision questions: [list]"` |
| Fact Checker | Wave 2 | Gemini Flash | Verify numbers, check source accessibility | `echo "Y" \| gemini -m gemini-2.5-flash -p "Verify: [claim]. Return VERIFIED/CORRECTED/UNVERIFIABLE + source"` |
| Source Reviewer | Wave 2 | Codex | Cross-verify citations, flag single-source claims | `codex exec --full-auto -C [repo] "Review citations in [file]. Flag: missing source, single-source claims"` |

**Division of labor principle** (from memory rule `feedback_multi_ai`):
- Claude Sonnet/Opus: core writing, integration, cross-wave coordination, decisions
- Gemini Flash: search grounding, fact-check, SEO, proofreading, persona simulation (fast)
- Gemini 2.5 Pro: complex persona simulation, auditor roleplay, tone scoring
- Codex: code review, accessibility audit, citation cross-verification

**Why both maps**: Skill defines capability (what to do); Model defines which LLM executes it. They are independent optimization axes. Keep them in separate maps.

**Update discipline**: Update these maps in one place. Commander copies the relevant row into Direction Seed field 5 at dispatch. Updates propagate to all future dispatches automatically.

---

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

## Direction Seed — Commander Dispatch Template (9 Fields)

Before dispatching any subagent via the Agent tool, Commander must provide a briefing with all 9 fields. Missing any field is a briefing failure — the subagent's output cannot be used in gate review.

### The 9 Fields

1. **Course/Project ID + Role Name** — e.g., `HSW-002 / Investigator A`
2. **Target Audience Persona** — not an abstract label. A concrete description: years of experience, daily workflow, what pressures they face, what they actually do vs. what they are assumed to do.
3. **O (Objective) — quoted in full** — never abbreviate. The subagent must see both the emotional goal and the practical outcome. Without the full O, the subagent sees its G but doesn't understand why the G exists.
4. **This agent's G/S/M** — copy from the OGSM doc: the agent's integrative goal, chosen path, and verifiable measures.
5. **Embedded Skill + Model Invocations** — copied from the Skill Invocation Map AND Model Invocation Map, with full command format and trigger conditions for this agent's role. This is Principle 7 at the dispatch layer.
6. **Hard Constraints** — e.g., promotional ratio < 20%, must cite two independent sources, no fabricated data.
7. **Tone + Voice Requirements** — e.g., peer-to-peer with a 12-year practitioner; not marketing; direct; never condescend.
8. **Deliverable Format + File Path** — exact filename, section structure expected, path to write output.
9. **Anti-patterns to avoid** — at least 3 items in "NOT: X — INSTEAD: Y" format. Source: the agent's pre-written Anti-patterns Standard List in the OGSM definition. Commander copies this at dispatch, adding any project-specific items.

### Why Field 9 Is Non-Negotiable

The "obvious reverse" problem: the parent writes a briefing assuming the subagent will naturally avoid the wrong thing. The subagent has no such assumption. What is obvious to a human who designed the system is invisible to a fresh subprocess.

Forcing the parent to write the anti-patterns list requires the parent to ask: "What would this subagent do if it interpreted the briefing charitably but incorrectly?" That question surfaces the most common briefing gaps.

### Per-Agent Anti-patterns Standard List

Each agent's OGSM definition should include an `**Anti-patterns Standard List**` sub-block with ≥ 3 items:

```
**Anti-patterns Standard List (source for Direction Seed field 9)**
- NOT: [wrong action] — INSTEAD: [correct action]
- NOT: [wrong action] — INSTEAD: [correct action]
- NOT: [wrong action] — INSTEAD: [correct action]
```

**Examples from real agents:**

Investigator role:
- NOT: Use pre-2020 cases as the primary source without version annotation — INSTEAD: At least one primary case from 2020+; older cases must carry a version-year flag.
- NOT: Cite a secondary news summary and consider it verified — INSTEAD: Every claim needs two independent primary sources (e.g., official database + court document); single-source claims must be flagged.

Reviewer role (persona-simulating external reviewer):
- NOT: Accept that the course "covers the right topics" as confirmation of the O — INSTEAD: Run the actual persona decision questions; score each answer against the O's practical outcome, not against the content outline.

Writer role:
- NOT: Start with the technical mechanism and add audience context later — INSTEAD: Start from the audience's decision point; work backward to the mechanism only when it explains a risk the audience already feels.

Commander copies the standard list into field 9, then appends any wave-specific or course-specific items.

---

## Pilot Dispatch — Validate Before Parallelizing

For each wave: dispatch 1 subagent first (the "pilot"), wait for its output, sanity-check against the O spirit, then dispatch the rest in parallel.

**Why this works**: Most briefing gaps are systematic (the parent's assumptions, not the agent's individual quirks). If the pilot output is wrong, updating the briefing and re-dispatching costs one extra round-trip. If 4 agents go parallel with a flawed briefing, fixing requires 4 re-dispatches.

**Implementation**:
- Wave 1: dispatch one investigator as pilot; pass gate; then dispatch all Wave 1 agents in parallel.
- Wave 2: dispatch one internal reviewer as pilot; pass gate; then dispatch remaining reviewers.
- Wave 3: dispatch the integration/engineer agent as pilot; pass gate; then continue.
- Pilot sanity-check is Commander's job — it requires cross-subagent judgment that no subagent can perform on itself.

**Known limitation**: Pilot Dispatch catches the pilot agent's blind spots. Other parallel agents may have their own blind spots that the pilot doesn't share. Accept this as a known monitoring item; do not over-engineer a fix until you observe divergence ≥ 2 times across real production runs.

---

## Brief Layering — Tier 1 and Tier 2

Direction Seed briefings that carry the full G/S/M for 15+ agents accumulate massive briefing length. Map this to a layered approach:

**Tier 1 (always in the briefing — target ~150 words for the G/S/M portion)**:
- G in one sentence
- S in one sentence summary
- 2–3 critical M gates (the "must not miss" acceptance criteria)
- Embedded skill commands (from Skill Invocation Map)
- Embedded model commands (from Model Invocation Map)
- Anti-patterns Standard List (3 items)

**Tier 2 (reference on demand)**:
- Full S rationale (why this path was chosen, what alternatives were rejected)
- Complete M list including edge cases
- Historical context (prior course failures, past iteration decisions)
- Cross-course patterns

**Implementation**: Commander's Direction Seed field 4 carries Tier 1. Tier 2 is referenced by file path and section anchor (e.g., `see WTR-HSW-002-OGSM-v4.md#investigator-a — full G/S/M`). The subagent reads on demand if it needs deeper rationale.

**Tie to layered memory architecture** (from the "三層架構" principle in v2.html): the same philosophy that governs CLAUDE.md (always-loaded) vs. Memory files (load on demand) vs. Skills (callable) applies to agent briefings. Tier 1 = always-loaded. Tier 2 = on-demand.

**Known limitation**: Complex agents with many M gates may struggle to stay within the 150-word Tier 1 budget. Monitor actual briefing length in production. If an agent consistently requires > 250 words in Tier 1, move some M items to Tier 2 or enforce the discipline to separate "critical gates" from "complete checklist."

---

## Principle 7 — Embedded Skill + Model Invocation Required

**Why Principles 1–6 are not enough for multi-agent OGSM**: Principles 1–6 address goal alignment and audience understanding. They assume a shared context — a single agent that can read CLAUDE.md and memory. In a multi-agent system, subprocess agents (dispatched via the Agent tool) run in isolated context. They cannot see:

- The parent Claude's CLAUDE.md
- The parent Claude's memory files
- The current conversation history
- Any skills or LLM preferences established in the parent session

**The failure mode**: An S section reads "use Gemini to verify the claim" or "call `/content-scout` when you find a blog candidate." The subprocess has no idea what command format to use, which Gemini model to use, or what parameters are required. Result: the subagent either skips the call entirely or improvises — both defeat the purpose.

**The principle**: Every skill call and every external LLM invocation that an agent needs must be written into that agent's S section with full command format, trigger condition, and parameter example. OR the S section must explicitly reference the Skill Invocation Map and Model Invocation Map (central documents in the OGSM file) and instruct the subagent to read those maps.

**Three-layer redundancy** (defense in depth):
1. Agent definition layer: each agent's S contains embedded commands or explicit map references.
2. Map layer: Skill Invocation Map + Model Invocation Map serve as the central source of truth, updated in one place.
3. Dispatch layer: Commander copies the relevant rows from both maps into Direction Seed field 5 at every dispatch.

If any one layer is missing, the other two provide recovery.

**Why this makes multi-agent OGSM fundamentally different from single-agent OGSM**: In single-agent workflows, the agent has access to shared memory and can "just know" to call a skill. In multi-agent workflows, this assumption breaks at the subprocess boundary. The OGSM architect must explicitly propagate capability knowledge into every dispatch.

---

## Principles Learned from Real Projects

### Principle 1: Audience Workflow Understanding

Defining "who the audience is" is not enough — you must understand **what they actually do** in their job.

- Wrong: Assume the audience will do the thing you want to teach them.
- Right: Research the audience's actual workflow, then position your content accordingly.

**Example (HSW-002 v3 iteration):**
We assumed architects would "write specs," so the course taught spec language. Wrong.
- Architects don't write specs — they specify brands; spec writers handle the details.
- The course should teach "situation recognition" and "how to collaborate with the spec writer."
- Not "how to write a spec."

**Diagnostic question**: Ask yourself "Would this audience **actually** do this in real life?" If unsure, interview one real audience member.

---

### Principle 2: Independent vs Incumbent Framing

If you represent a challenger brand (not the dominant incumbents), your content should **empower** the audience — not trap them in the incumbents' ecosystem.

**Example (HSW-002 v3 iteration):**
- The three major door hardware manufacturers (Allegion, ASSA ABLOY, dormakaba) control most spec writers.
- Architects who want to use independent manufacturers often don't know where to find resources.
- An independent manufacturer's course responsibility: tell architects "you have other options."
- But frame it **neutrally**: "Here are independent resource paths" — not "use us."

**Diagnostic question**: Ask yourself "After reading this, does the audience feel more free or more dependent?"
- More dependent → you wrote a sales brochure.
- More free → you did real education.

---

### Principle 3: Resource Routing as a Deliverable

Sometimes the best outcome of a course is not "teach them how to do it" but "tell them where to go."

**Example (HSW-002 v3 iteration):**
Architects don't need to learn to write specs. But they do need to know:
- Encounter this scenario → this is a Waterson scenario.
- Want to use Waterson → SpecLink, SPC Alliance can help.
- There are resources beyond the Big Three.

"Resource routing" is itself a valuable deliverable — it is not a substitute for "failed to teach well."

---

### Principle 4: Third-Party Framing Rule

Even if you benefit from the recommendation, introduce resources from a **neutral position**.

**Example:**
- Wrong: "Use Waterson! Find us on SpecLink!"
- Right: "Independent manufacturer spec resources have more than one path. SpecLink, SPC Alliance, and CSC/CSI are all options."

**Diagnostic question**: Have a **Sales Rep Advisor** (external reviewer) read it. If they say "this smells like advertising," it's not neutral enough.

---

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

### Anti-pattern 6: Misread the audience's actual job
**Symptom**: The course teaches skills the audience does not actually use in their work.
**Fix**: Research the audience's real workflow. If they don't do the thing you're teaching, change to teach what they actually do — which may be "routing to the right resource" rather than "doing it themselves."

### Anti-pattern 7: Don't fight LLM nature
**Symptom**: A rule in the agent's S forces zero synthesis — "verbatim copy only, no insights, no summaries, no recommendations." The agent resists, produces awkward output, or quietly violates the rule anyway.
**Root cause**: LLMs reflexively synthesize, connect, and generalize. Forbidding synthesis entirely fights what the model does naturally at every inference step.
**Fix**: Restructure so the natural action is allowed but does NOT replace what you actually need. Add a field for insights (e.g., `collector_notes`) alongside the mandatory raw material field (e.g., `research_data`). The agent produces what it's good at AND keeps the raw material. Both are required; neither replaces the other.
**Diagnostic question**: "Am I forbidding a cognitive action that an LLM does reflexively?" If yes, restructure the output schema rather than issuing a prohibition.

**Example (HSW-002 v4)**: Candidate Collector originally had a "zero recommendation language" rule. In practice, the agent kept producing implicit type-balance observations. Fix: add a `collector_notes` field (descriptive observation allowed) while keeping `research_data` mandatory and verbatim. The rule changed from "don't think" to "think here, copy there."

### Anti-pattern 8: Role count inflation from misclassified skills
**Symptom**: An OGSM design adds a new agent for every new capability needed. After 2–3 iterations the team roster grows to 20+ agents, every wave requires new coordination overhead, and half the agents are doing single-pass deterministic tasks.
**Root cause**: The designer defaulted to "agent" as the unit of work without applying the Skill/Agent boundary test.
**Fix**: For every proposed new agent, ask: "Could this be a skill that an existing agent calls from its S?" If yes, create the skill and add the call to the appropriate agent's S. Reserve agents for roles with a cross-wave G and genuine situational judgment.

## Monitor, Don't Preempt — An Operational Principle

When architectural concerns are raised during review (by external AI, team members, or retrospective analysis) but there is no concrete evidence that the failure mode has actually occurred in production:

1. **Record the concern** as a monitoring item — document it in a "Known Issues / To Monitor" section of the OGSM doc.
2. **Do not fix it preemptively.** Over-engineering a fix for a hypothetical failure costs more than the failure itself in most cases.
3. **Define a trigger condition**: "If X happens ≥ N times during [next production run], then implement [fix]." This turns vague concern into an actionable threshold.
4. **Revisit after the next real run.** If the failure mode never manifested, close it as theoretical concern. If it did, you now have concrete evidence — fix it.

**Example (HSW-002 v4 Known Issues):**
- *Pilot Dispatch blind spot*: Pilot catches pilot-specific gaps but not agent-specific gaps. Not fixed preemptively. Monitor: "Does non-pilot output diverge from pilot interpretation ≥ 2 times in HSW-006?"
- *Tier 1 briefing length creep*: Complex agents may bloat Tier 1 past the 150-word target. Not fixed with automated enforcement yet. Monitor: "Does any agent's Tier 1 exceed 250 words at dispatch?"
- *Candidate Collector drift*: Collector's type-balance judgment is itself a form of recommendation. Not fixed yet. Monitor: "Do collector alerts actually change downstream agent behavior, or are they ignored?"

**Format for the Known Issues section in your OGSM doc:**

```markdown
## Known Issues / To Monitor

### Issue #N — [Short label]
**Concern**: [What could go wrong]
**Possible fixes (do NOT implement now)**: [List options]
**What to watch during [next run]**: [Specific observable signal + threshold]
```

## Skill Integration Verification Protocol

When an OGSM plan references skills (via Skill Invocation Map) or models (via Model Invocation Map), those references are promises — someone must verify the skills actually work before the plan runs in production. This protocol defines the 3-layer verification every OGSM project must do after skills are built and before the first real dispatch.

**Why this exists**: During HSW-002 v4 Phase 2a, we discovered the OGSM plan had referenced `/content-scout flag-candidate` for months while the actual skill file had no such subcommand. Five agents would have failed when first invoked. The failure mode: Skill Invocation Map is a document, skill files are code, and nothing automatically enforces they match.

### Layer 1 — Skill exists and is executable

For each row in the Skill Invocation Map and Model Invocation Map:

1. **Read the skill file** referenced by the row (e.g., `~/.claude/skills/content-scout/SKILL.md`)
2. **Verify the subcommand / flag / parameter format exists** in the skill file's documented syntax
3. **Smoke test**: construct a dry-run invocation with the exact command format from the Map, verify the skill file's workflow section explains what should happen

Pass criteria: every command in the Map has a corresponding section in its target skill file.

Fail mode: Map references `--new-flag` but skill file doesn't mention it. Fix by either updating the skill file OR removing the `--new-flag` reference from the Map.

### Layer 2 — Document-code alignment

For each referenced skill, verify the command format matches character-for-character:

1. **Extract** the command line from the Skill Invocation Map (e.g., `/content-scout flag-candidate --source-agent X --title Y ...`)
2. **Compare** against the skill file's Trigger / Input section — same flag names, same required vs optional, same parameter order
3. **Verify** the skill file's error handling describes what happens when required params are missing — this catches "the skill exists but will fail silently" cases

Pass criteria: zero character differences in flag names. Mismatches like `--source_agent` (underscore) vs `--source-agent` (hyphen) are critical failures.

Fail mode: Map uses camelCase, skill uses kebab-case. Standardize to one. Document-code alignment failures usually happen because two people updated different sides at different times.

### Layer 2.5 — Dry Run Dispatch

Layers 1 and 2 verify the skill exists and the format is consistent on paper. Layer 3 verifies real subagents actually invoke the skill in production. The gap: what if the briefing is technically correct (passes L1 + L2) but the subagent doesn't know HOW to use it — missing parameter values, ambiguous examples, or unclear when to call?

Layer 2.5 catches these "briefing is documented but not executable" failures **before** production starts. It's preventive where Layer 3 is reactive.

#### How it works

Before the first real production run, for each agent that has an Embedded Skill Invocation in its Direction Seed briefing:

1. **Prepare a throwaway test subagent** (via Agent tool) with the agent's complete Direction Seed briefing — same 9 fields as a real dispatch
2. **Ask the test subagent to do ONLY this**: read the briefing, identify the embedded skill commands in field 5, and for each command:
   - Report whether it understood the command format
   - Report whether it has enough context to fill in all required parameters
   - Report the exact command it would execute (fully substituted, not templates)
   - Do NOT actually execute the command — stop at the "ready to execute" point
3. **Commander reviews the reports**:
   - If any subagent reports "parameter X missing" → Direction Seed briefing is incomplete, fix it before real dispatch
   - If any subagent produces a command that differs from the Skill Invocation Map format → something got lost in translation, fix briefing
   - If subagent understood but has uncertainty ("should I use file path A or B?") → add an example to the briefing or the Skill Invocation Map

#### What it catches that Layer 2 doesn't

Layer 2 is static text comparison — it catches `--source-agent` vs `--source_agent` typos. Layer 2.5 is semantic — it catches:
- Briefing references `--source-file [path]` but doesn't tell the subagent what path to use for THIS course
- Briefing uses an example agent name that doesn't match the actual agent being dispatched
- Briefing assumes subagent knows which skill to call first when multiple are listed
- Briefing's "when to call" trigger is vague ("when appropriate") instead of concrete ("after reading all Wave 1 deliverables")

#### Cost vs benefit

- **Cost**: one throwaway Agent tool dispatch per agent that has skill invocations. For HSW-002 v4 that's 5-7 agents × ~1 minute each = 5-10 minutes before production starts.
- **Benefit**: prevents the "wave 1 starts, 4 parallel subagents simultaneously fail because briefing was incomplete" scenario. Commander sees all failures at once in a controlled environment, fixes briefing, then dispatches real production once.

#### Pass criteria

- Every agent with embedded skill commands produces an executable command (all parameters filled) in its dry run report
- Zero "parameter X missing" errors
- Zero "I don't know which skill to call first" uncertainty

If any agent fails dry run, FIX THE BRIEFING (not the agent, not the skill) and re-run Layer 2.5 until all pass.

#### When to skip

Layer 2.5 can be skipped ONLY if:
- The briefing has been used successfully in a previous production run AND
- No changes to briefing or skill files since that run

For the first run of any new course, Layer 2.5 is mandatory.

#### Example dry run prompt for the test subagent

```
You are a dry-run test subagent. Do NOT execute any commands. Do NOT produce deliverables.

You have received this Direction Seed briefing: [paste complete briefing]

Your only task:
1. Identify the skill commands in field 5 (Embedded Skill + Model Invocations)
2. For each command, report:
   a. The command format as written in the briefing
   b. The exact command you would execute (with all parameters filled in)
   c. Any parameters you are unsure about (what value to use)
   d. Your confidence level (HIGH / MEDIUM / LOW) that executing this command would succeed

Stop after the report. Do not execute. Do not produce the agent's normal deliverable.

Return format:
SKILL_1: [name]
  FORMAT: [as written]
  EXECUTABLE: [fully substituted]
  UNCERTAINTY: [list, or "none"]
  CONFIDENCE: [HIGH/MEDIUM/LOW]

[repeat for each skill]
```

The Commander's acceptance criteria: all skills report HIGH confidence + zero uncertainty. Anything else is a fix.

### Layer 3 — Production invocation audit

This is the only layer that requires a real run (HSW-XXX production). It verifies subagents ACTUALLY invoke the skill, not just that they were told to.

During the first wave of the first real run:

1. **Performance Supervisor** samples ≥ 1 subagent per wave and inspects its deliverable for evidence of skill invocation (e.g., queue file was written to, output file was created, specific log entry was produced)
2. **If no evidence of invocation**: either the briefing failed (Direction Seed field 5 was incomplete) OR the agent declined to execute the command (perhaps the embedded format was unclear)
3. **Escalate** to Commander: briefing failure (fix the Direction Seed template) vs agent refusal (make the command more explicit or add an example)

Pass criteria: every agent whose Skill Invocation Map row applies to the current wave shows evidence of actually running the skill at least once.

Fail mode: briefing looks correct but subagent never calls the skill. Common cause: the embedded command lacks a concrete parameter example, so the subagent doesn't know what values to substitute. Fix by adding example invocations to the Skill Invocation Map — not just format specs.

### When to run this protocol

- **Layer 1 + Layer 2**: immediately after skills are built, before any production run
- **Layer 2.5**: after Layer 1 + 2 pass, before the first real production dispatch — mandatory for first run of any new course
- **Layer 3**: during the first wave of the first real production run (not a dry run — dry runs don't stress-test briefing→execution)
- **All 3 layers again**: whenever the Skill Invocation Map or Model Invocation Map is updated (not when skills are updated — skill updates trigger regression check on Layer 2 only)

### Who runs it

- **Layer 1 + Layer 2**: Commander (Opus) runs manually before dispatch, or delegates to a verification subagent
- **Layer 2.5**: Commander dispatches throwaway test subagents (one per agent with embedded skill invocations) and reviews dry run reports
- **Layer 3**: Performance Supervisor during production

#### Layer 2 automation

The S-to-M coverage check can be automated via `scripts/validate_s_to_m_coverage.py` — see the top of this file for usage. This script catches the most common Layer 2 violation: S-skill calls without matching M verification. Run it as part of Layer 2 verification.

### Output

A `skill-integration-verification-{course}.md` document recording:
- Layer 1 results per Skill Invocation Map row
- Layer 2 results (character-level format comparison)
- Layer 2.5 results (per-agent dry run confidence levels + any briefing fixes applied)
- Layer 3 results (per-wave invocation evidence)
- Any failures + fixes applied

This document becomes part of the course's OGSM retrospective.

### Diagnostic questions

Before every production run, Commander asks:
1. Are all skills in the Skill Invocation Map implemented? (Layer 1)
2. Do command formats match the skill implementations character-for-character? (Layer 2)
3. Has every agent with embedded skill commands passed dry run with HIGH confidence? (Layer 2.5)
4. Are we prepared to audit actual invocations during the first wave? (Layer 3 readiness)

If any answer is "no" or "not sure", stop and verify before dispatching.

### Anti-pattern: "we documented it so it must work"

The Skill Invocation Map is documentation, not execution. Having a row that says "Investigator A calls /foo" doesn't make `/foo` exist. This anti-pattern killed us in Phase 2a — we assumed that because the Map was carefully written, the skills were carefully built. They weren't.

**Fix**: treat the Map as a promise that must be redeemed with code before it's real. The protocol above is how you redeem it.

---

## References

- 張敏敏 老師 (Teacher Zhang Minmin) — Taiwan's leading OGSM practitioner
- **《OGSM 打造高敏捷團隊》** — classic OGSM book for teams
- **《OGSM 變革領導》** — advanced OGSM for change management
- Both published by 商業周刊 (Business Weekly, Taiwan)

## Example

**Canonical reference**: `/waterson-ai-growth-system/docs/aia-course/WTR-HSW-002-OGSM-v4.md`

This is the current authoritative example: an AIA CEU course with 19 agents (15 workers + 3 external reviewers + 1 Candidate Collector), produced through two rounds of review including a Gemini Flash architectural audit. The file (~1167 lines) contains:
- All 19 agents with full G/S/M + Tier 1 summary + Anti-patterns Standard List
- Skill Invocation Map (8 rows)
- Model Invocation Map (12 rows)
- Direction Seed 9-field template with Pilot Dispatch rules
- Brief Layering (Tier 1 / Tier 2) rationale and word budget
- Wave Gate Conditions (Gates 0–4)
- Known Issues / To Monitor section (3 issues from Gemini round 2)

The v4 file is the result of: v2 (18 agents, initial) → v3 (audience workflow and resource routing fixes) → v3.1 (23 agents, over-expansion) → v4 (Skill/Agent boundary cleanup, back to 19 agents, all round 2 patterns embedded).

For historical comparison, `WTR-HSW-002-OGSM-v2.md` is kept as a reference for the original 18-agent structure before the audience workflow and resource routing principles were applied.

## Integration with Other Skills

- Use with `/aia-rewrite` for AIA course projects
- Use with `/publish-article` for blog article teams
- Use with `/agent-builder` when defining new agent roles — always ask "what's this agent's G in OGSM terms?"
