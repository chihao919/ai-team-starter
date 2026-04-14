# Central Skill Invocation Map

This is the single source of truth for skill invocations across all OGSM projects (HSW courses, Iteration Team, etc.). Instead of embedding full commands in every agent's Tier 1, agents call `get_skills_for_role.sh <role>` before acting to retrieve relevant commands.

**Query usage**:
```bash
bash ~/.claude/skills/ogsm-framework/scripts/get_skills_for_role.sh investigator-a
```

Returns the skill commands relevant to that role.

---

## Role: investigator-a

### Skill: /content-scout flag-candidate

**When to call**: When you find a research case that is self-contained enough to support an 800–1500 word blog article (case study type).

**Command template**:
```bash
/content-scout flag-candidate \
  --source-agent investigator-a \
  --source-file <path> \
  --title "<title>" \
  --type case-study \
  --keywords "<3-5 keywords>" \
  --research-data "<verbatim material — complete, not summarized>" \
  --why-worth-writing "<1-2 sentences>"
```

### Skill: /ai-fallback (model research)

**When to call**: Every search and grounding call — DHI database queries, court document searches, case verification. Never call gemini or codex directly.

**Command template**:
```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "Search for [topic] failure cases post-2020, DHI database preferred, return source URLs and incident summaries"
```

---

## Role: investigator-b

### Skill: /content-scout flag-candidate

**When to call**: When a regulatory update, cost comparison, or cost analysis is self-contained enough to support an 800–1500 word blog article.

**Command template**:
```bash
/content-scout flag-candidate \
  --source-agent investigator-b \
  --source-file <path> \
  --title "<title>" \
  --type regulatory-explainer \
  --keywords "<3-5 keywords>" \
  --research-data "<verbatim material — include section numbers and version years>" \
  --why-worth-writing "<1-2 sentences>"
```

Note: `--type` may also be `cost-comparison` depending on the material.

### Skill: /ai-fallback (model research)

**When to call**: Code section version verification, ICC/NFPA cross-verification. Never call gemini or codex directly.

**Command template**:
```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "Verify [IBC section X] current version and cross-reference with NFPA 80 [section Y], return exact section number and version year"
```

---

## Role: writer-a

### Skill: /content-scout flag-candidate

**When to call**: When a technical concept encountered during writing merits an 800+ word standalone article that cannot be fully covered in the course slide.

**Command template**:
```bash
/content-scout flag-candidate \
  --source-agent writer-a \
  --source-file <path> \
  --title "<title>" \
  --type product-comparison \
  --keywords "<3-5 keywords>" \
  --research-data "<full verbatim material>" \
  --why-worth-writing "<1-2 sentences>"
```

Note: `--type` may also be `regulatory-explainer` depending on the concept.

---

## Role: writer-b

### Skill: /content-scout flag-candidate

**When to call**: When a scenario-recognition case or independent spec resource is self-contained enough to support a standalone article.

**Command template**:
```bash
/content-scout flag-candidate \
  --source-agent writer-b \
  --source-file <path> \
  --title "<title>" \
  --type scenario-guide \
  --keywords "<3-5 keywords>" \
  --research-data "<full verbatim material — include resource contact info and neutrality notes>" \
  --why-worth-writing "<1-2 sentences>"
```

---

## Role: project-architect-advisor

### Skill: /content-scout flag-candidate

**When to call**: After reading the full course, when you identify topics the architect would want to explore further but the course cannot expand on.

**Command template**:
```bash
/content-scout flag-candidate \
  --source-agent project-architect-advisor \
  --source-file <course-path> \
  --title "<title>" \
  --type reader-interest \
  --keywords "<3-5 keywords>" \
  --research-data "<why architect wants this + quotable course sections>" \
  --why-worth-writing "<1-2 sentences>"
```

### Skill: /ai-fallback (persona simulation)

**When to call**: To run the 12-year Project Architect persona simulation via Gemini 2.5 Pro.

**Command template**:
```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "Role-play 12-year Project Architect. Read: [course]. Answer 6 decision questions: [list]" gemini-2.5-pro
```

---

## Role: candidate-collector

### Skill: /content-scout flag-candidate

**When to call**: When Type Distribution analysis detects a gap (a type with count = 0 while another type has count >= 3), scan existing deliverables and flag a candidate of the missing type.

**Command template**:
```bash
/content-scout flag-candidate \
  --source-agent candidate-collector \
  --source-file <original-deliverable-path> \
  --title "<title matching missing type>" \
  --type <missing-type> \
  --keywords "<3-5 keywords>" \
  --research-data "<verbatim quote from existing deliverable — do not fabricate>" \
  --why-worth-writing "<1-2 sentences citing cross-wave observation>"
```

**Constraint**: `--research-data` must be a verbatim quote from an existing deliverable. Candidate Collector never generates new content — it redistributes existing material into underrepresented types.

---

## Role: engineer-html

### Skill: /post-test-designer

**When to call**: Before converting course content to HTML — generate the 10-question post-test first.

**Command template**:
```bash
/post-test-designer --course HSW-002 --course-file <path> --distribution 4/4/2
```

### Skill: /aia-rewrite --bilingual

**When to call**: After post-test is complete — generate the English and Chinese HTML course pages.

**Command template**:
```bash
/aia-rewrite --course HSW-002 --bilingual
```

Note: This generates `/aia/{slug}/` (English) and `/aia/zh/{slug}/` (Chinese).

---

## Role: fact-checker

### Skill: /ai-fallback (fact verification)

**When to call**: Every number, date, and source URL verification. Never verify from memory.

**Command template**:
```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "Verify: [number] [claim]. Return VERIFIED/CORRECTED/UNVERIFIABLE + source URL"
```

---

## Role: source-reviewer

### Skill: /ai-fallback (citation cross-verification)

**When to call**: Citation cross-verification and source quality scoring. Prefer codex chain for structured review tasks.

**Command template**:
```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "Review all citations in [file]. Flag: missing source, pre-2018 source without version note, single-source claims. Return structured flag list." codex
```

---

## Role: compliance-reviewer

### Skill: /ai-fallback (AIA auditor simulation)

**When to call**: AIA HSW compliance audit simulation — use Gemini 2.5 Pro persona for auditor role-play.

**Command template**:
```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "Role-play AIA CES auditor. Score each Big 3 mention 1-5 for neutrality. Context: [course section]" gemini-2.5-pro
```

---

## Role: fresh-eyes-reviewer

### Skill: /ai-fallback (fresh perspective challenge)

**When to call**: External cold-read challenge — load course with no prior context and challenge assumptions.

**Command template**:
```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "You have NO prior context about this course or project. Read the following cold. Challenge anything that looks taken-for-granted. Do not use jargon. Course: [content]" gemini-2.5-pro
```

---

## Role: mini-research-agent

### Skill: /content-scout flag-candidate

**When to call**: At least once per cycle when any found case is self-contained enough to support an 800–1500 word article. If no blog-worthy material is found, explicitly state "no blog-worthy material found in this run — reason: [reason]".

**Command template**:
```bash
bash ~/.claude/skills/content-scout/scripts/flag_candidate.sh \
  --source-agent mini-research-agent \
  --source-file <path> \
  --title "<case title>" \
  --type case-study \
  --keywords "<3-5 keywords>" \
  --research-data "<full case data, not summary>" \
  --why-worth-writing "<1-2 sentences>"
```

### Skill: /ai-fallback (model research)

**When to call**: Every search and grounding call. Never call models directly.

**Command template**:
```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "Search for [topic] building cases post-2020, return URLs and summaries"
```

**Model chain**: gemini-2.5-flash → gemini-2.5-flash-lite → gemini-2.5-pro → codex (automatic via /ai-fallback).

---

## Role: mini-writer-agent

### Skill: /ai-fallback (optional writing assistance)

**When to call**: Optional — only if the upstream research file is ambiguous or incomplete and you need to verify a specific claim before writing. Do not call for general writing tasks.

**Command template**:
```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "Verify: [specific claim from research file]. Return source URL."
```

**Default behavior**: Mini-Writer Agent operates on the research output file provided by Dispatch Harness. Native Claude judgment is preferred for writing quality tasks. If upstream research file is missing: halt and report "Upstream research file not found at [expected path] — cannot write without sourced cases."

---

## Role: mini-reviewer-agent

### Skill: /ai-fallback (optional reviewer assistance)

**When to call**: Optional — only if a citation's plausibility needs external verification. Do not call for rule-matching or tone evaluation tasks.

**Command template**:
```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "Does [document reference] plausibly exist for [claimed year]? Return YES/NO + evidence."
```

**Default behavior**: Mini-Reviewer Agent uses native Claude judgment for compliance rule-matching and flag precision. No fallback chain needed for structured review. If draft file is missing: halt and report "Target draft file not found at [expected path] — cannot review."

---

## Role: iteration-team-spec-verifier

### Skill: /ai-fallback (BDD scenario generation)

**When to call**: When generating BDD Given-When-Then scenarios for agent spec validation.

**Command template**:
```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "Generate BDD Given-When-Then scenarios for: [agent spec description]. Focus on observable outputs only."
```

---

## Role: iteration-team-dispatch-harness

### Skill: /ai-fallback (mini-agent dispatch help)

**When to call**: When composing dispatch briefs for mini-agents and need to verify brief completeness or clarity.

**Command template**:
```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "Review this mini-agent dispatch brief for completeness: [brief]. Does it include all required fields: topic, input file path, output file path, cycle letter?"
```

---

## Role: iteration-team-iterator

### Note on skill usage

The Iterator does not call /ai-fallback for diff reasoning — validation scripts handle that deterministically. The Iterator runs:

```bash
python ~/.claude/skills/ogsm-framework/scripts/validate_s_to_m_coverage.py <spec-file>
python ~/.claude/skills/ogsm-framework/scripts/validate_ogsm_completeness.py <spec-file>
python ~/.claude/skills/ogsm-framework/scripts/check_skill_architecture.py <spec-file>
python ~/.claude/skills/ogsm-framework/scripts/check_ai_fallback_usage.py <spec-file>
```

No /ai-fallback needed — script output is the source of truth for iteration decisions.

---

## Role: commander

### Skill: /ai-fallback (orchestration-layer LLM judgment)

**When to call**: Commander's own orchestration-layer LLM calls — conflict
semantic judgment (internal-vs-internal tiebreaker pre-check, producer-vs-reviewer
fallback reasoning), pilot output review LLM assistance, external reviewer output
verification. NOT for content production (Commander does not produce course
content). NOT for routine dispatch (dispatch uses Agent tool directly, no LLM
helper needed).

**Command template**:
```bash
OGSM_LITE_TIMEOUT=180 bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh \
  "You are assisting Commander (A君) of [course-id] OGSM v[N]. Conflict context: [description].
   Apply Commander's 3-question escalation rubric:
   (1) spec-contract conflict? (2) >=20% wall-clock budget overrun?
   (3) answer NOT in factory gotchas/patterns?
   Return JSON: {q1, q2, q3, decision, rationale}." \
  "gemini-2.5-flash-lite,gemini-2.5-pro,codex"
```

**Mandatory log**: every Commander wrapper call must be recorded in
`dispatch-log-002-waveN.md` under `## Commander LLM Calls` with: wrapper command
string + chain + answered model + exit code + timestamp + purpose. Raw
`gemini -m ...` or `codex exec ...` invocations prohibited (G-001 / G-012 /
G-014 / NEW-02 / Principle 7).

### Knowledge queries (pre-flight before pilot sanity-check AND before every conflict resolution)

```bash
bash ~/.claude/skills/ogsm-framework/scripts/get_patterns_for_failure.sh <failure-type>
bash ~/.claude/skills/ogsm-framework/scripts/get_gotchas_for_context.sh <context>
bash ~/.claude/skills/ogsm-framework/scripts/get_skills_for_role.sh commander
```

These queries MUST run before Commander applies the 3-question rubric — Commander
answers q3 ("answer NOT in factory gotchas/patterns?") using the actual script
output, not from memory.

---

## Generic commands (no role-specific parameters)

### /ai-fallback

Universal quota-aware model router. Any agent can call it:

```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "prompt" [preferred-model]
```

Default chain: gemini-2.5-flash → gemini-2.5-flash-lite → gemini-2.5-pro → codex.

Optional second argument to prefer a specific starting model (e.g., `gemini-2.5-pro`, `codex`). Falls through to next in chain on quota exhaustion.
