---
name: ai-fallback
description: Quota-aware, hang-resilient multi-model fallback router. Use when an agent needs to call an LLM for research, fact-checking, or persona simulation — automatically falls through model chain on quota errors OR model hangs. Triggers on "/ai-fallback", "fallback chain", "quota-aware model call", "429", "model quota", "rate limit fallback", "model hang", "timeout fallback".
type: project
---

# /ai-fallback — Quota-Aware, Hang-Resilient Model Fallback

## Purpose
When an agent calls an external LLM (Gemini Flash, Gemini Pro, Codex, etc.) and either hits a quota
error (HTTP 429) OR the model hangs with no output, automatically retry with the next model in a
pre-defined fallback chain.

## Why this exists
Two separate production failure modes drove this skill:

1. **Quota exhaustion** — Phase 4 trial of HSW-006 showed 3 agents simultaneously hitting Gemini
   Flash 429 quota. Without fallback, they would all fail together.

2. **Model hangs (INT-001)** — Team 1 integration run discovered that `gemini-2.5-flash` sometimes
   hangs for 60–360 seconds with zero output, no error code, no signal. The original quota-only
   check did not catch this, causing agent pipelines to stall silently for minutes.

This skill provides resilience against both failure modes. It is distinct from `/ai-collab`
(which handles task-delegation strategy, not runtime error recovery).

## Default fallback chain
1. `gemini-2.5-flash`       — preferred: fast, search-grounded, high daily quota
2. `gemini-2.5-flash-lite`  — smaller context cost, separate quota bucket
3. `gemini-2.5-pro`         — slower, different quota pool
4. `codex`                  — different vendor entirely (OpenAI)
5. WebSearch (degraded mode) — not an LLM; returns raw search results as last resort

## Trigger
```
/ai-fallback --prompt "QUERY" [--prefer gemini-2.5-flash] [--chain "flash,lite,pro,codex"]
```

Or called programmatically from an agent's script:
```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "Your prompt here" 2>&1
```

Custom chain example:
```bash
bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh \
  "Summarize this doc: ..." \
  "gemini-2.5-flash-lite,gemini-2.5-pro,codex"
```

## Workflow
1. Parse prompt + optional custom chain (defaults to full chain if omitted)
2. Read `OGSM_MODEL_TIMEOUT` env var (default: 60 seconds)
3. Iterate models in order
4. For each model:
   - Check if CLI is installed; skip with log entry if not
   - Invoke CLI wrapped in `timeout --kill-after=5s N s`
   - If timeout fires (exit 124 / 137): log "hang detected", advance to next model
   - If output contains quota/rate-limit signals (429, "quota", "rate limit", "exhausted"): log, advance
   - If output is non-empty and clean: print result + which model succeeded, exit 0
5. If all models exhausted: print attempt log to stderr, exit 2

## Script reference
`scripts/call_with_fallback.sh` — the actual fallback runner (bash + stdlib only)

## Integration
Agents that need LLM calls should prefer this script over raw `gemini` or `codex` commands.
This ensures graceful degradation instead of hard failure when any single model hits its quota.

Invocation pattern for sub-agents:
```bash
RESULT=$(bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "$PROMPT")
if [ $? -ne 0 ]; then
  echo "All models unavailable, aborting task" >&2
  exit 1
fi
echo "$RESULT"
```

## Error handling summary
| Condition                        | Behaviour                                        |
|----------------------------------|--------------------------------------------------|
| CLI not installed                | Skip model, log, try next                        |
| Hang / no output within timeout  | Kill process, log "hang detected", try next      |
| 429 / rate limit / quota signal  | Log attempt, try next                            |
| Non-empty clean response         | Return output + model name, exit 0               |
| Empty response                   | Log as empty, try next                           |
| All models exhausted             | Print attempt log, exit 2                        |

## Hang handling — INT-001 fix

**Problem discovered:** `gemini-2.5-flash` sometimes hangs silently for 60–360 seconds during
factory runs, producing no output and no error. The previous quota-only check could not detect this.

**Fix:** every model call is wrapped with the `timeout` command:
```bash
timeout --kill-after=5s "${TIMEOUT_SEC}s" <model-command>
```

- `SIGTERM` is sent after `TIMEOUT_SEC` seconds (default: 60)
- `SIGKILL` (`--kill-after=5s`) fires 5 seconds later if the process ignores SIGTERM
- Exit codes 124 (SIGTERM) and 137 (SIGKILL) are treated as "hang detected"
- The hang is logged in the attempt list and the script continues to the next model

### Env var: `OGSM_MODEL_TIMEOUT`

Controls the per-model timeout (in seconds). Applies to both Gemini and Codex branches.

| Usage                                | Effect                          |
|--------------------------------------|---------------------------------|
| (unset)                              | Default: 60 seconds per model   |
| `OGSM_MODEL_TIMEOUT=30`              | Fail fast on slow connections   |
| `OGSM_MODEL_TIMEOUT=120`             | Allow more time on slow networks|

Example override:
```bash
OGSM_MODEL_TIMEOUT=120 bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "Summarize..."
```

## Exit codes and caller fallback strategy

The `call_with_fallback.sh` script returns specific exit codes so callers can react appropriately:

| Exit code | Meaning | Caller action |
|-----------|---------|--------------|
| 0 | Success — output on stdout | Use the output |
| 1 | Usage error (missing prompt) | Fix invocation |
| 2 | Single-model failure (edge case) | Retry or investigate |
| 3 | **All models in chain exhausted** | **Use WebSearch tool as final fallback** |

### Codex trust check handling (NEW-02 fix)

**Problem discovered (2026-04-11):** Codex sometimes exits 0 with
`"Not inside a trusted directory and --skip-git-repo-check was not specified."` on stdout.
The wrapper previously classified this as SUCCESS (exit 0 + non-empty stdout = data).
Downstream agents received the error message as if it were research data — silent data corruption.

**Severity:** CRITICAL. Difficult to detect; no error log, no non-zero exit.

**Three-layer fix applied:**

1. **`--skip-git-repo-check` flag** — Codex branch now passes this flag by default, avoiding the
   trust-check refusal before it can happen:
   ```bash
   codex exec --full-auto --skip-git-repo-check -C "$CODEX_CWD" "$PROMPT"
   ```

2. **Stdout error pattern detection** — After capturing OUTPUT, the wrapper explicitly checks for
   codex-specific trust-check patterns that exit 0 with error text:
   ```bash
   if echo "$OUTPUT" | grep -qiE "(not inside a trusted directory|--skip-git-repo-check|refusing to run|trust check failed)"; then
     # classified as failure; continue to next model
   fi
   ```

3. **General "output looks like error" heuristic** — Applied to ALL models (Gemini + Codex):
   if output is shorter than 150 characters AND matches common error keywords, treat as failure
   rather than data. Catches NEW-02 class bugs across the whole chain.

**When to set `OGSM_CODEX_CWD`:** If `--skip-git-repo-check` is unavailable on your codex
version, ensure `OGSM_CODEX_CWD` points to a trusted directory (default: `$HOME`).

### Caller pattern for exit 3

When a subagent calls `/ai-fallback` and receives exit 3, the caller should immediately use its
WebSearch tool with the same prompt:

```bash
OUTPUT=$(bash ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh "query")
FALLBACK_EXIT=$?

if [ $FALLBACK_EXIT -eq 3 ]; then
  # All LLM models exhausted — caller uses WebSearch as final fallback
  # (caller is a Claude subagent, WebSearch is a tool it has access to)
  echo "All models exhausted, caller should now use WebSearch tool" >&2
fi
```

In Direction Seed briefings, include this pattern so subagents know what to do.

## Environment variables (for tuning)

- `OGSM_MODEL_TIMEOUT` — default per-model timeout (seconds), default 120
- `OGSM_PRO_TIMEOUT` — override for gemini-2.5-pro, default 150
- `OGSM_LITE_TIMEOUT` — override for gemini-2.5-flash-lite, default 90
- `OGSM_CODEX_TIMEOUT` — override for codex, default 90
- `OGSM_CODEX_CWD` — working directory for codex invocation (must be trusted), default `$HOME`

## Default chain change (v2)

Default fallback chain is now `gemini-2.5-flash-lite,gemini-2.5-pro,codex` (was
`gemini-2.5-flash,gemini-2.5-flash-lite,gemini-2.5-pro,codex`).

**Why removed gemini-2.5-flash**: smoke test on real Investigator A showed `gemini-2.5-flash`
deterministically hangs under production load (routed to gemini-3-flash-preview which has capacity
issues). Starting with flash-lite avoids the known-bad path.

If you need flash explicitly (e.g., for testing), pass it in the chain argument:
```bash
bash call_with_fallback.sh "prompt" "gemini-2.5-flash,gemini-2.5-flash-lite,gemini-2.5-pro,codex"
```

## REST API mode (paid tier)

As of 2026-04-11, the wrapper uses Google's REST API directly via curl
instead of the `gemini` CLI, for these reasons:

- **Bypasses GCA (Google Cloud Auth) free-tier queue issues** that caused
  G-001 Flash hang and G-012 Pro hang
- **Uses paid Gemini API** via GEMINI_API_KEY env var (must be set in
  ~/.zshrc or equivalent)
- **No CLI authentication complexity** — just API key in header
- **Supports all Gemini 2.5 models**: flash-lite, flash, pro

### Setup

1. Get API key from Google AI Studio: https://aistudio.google.com/
2. Enable billing on the Google Cloud project (for paid tier pricing)
3. Add to ~/.zshrc: `export GEMINI_API_KEY="your-key-here"`
4. Restart shell or source: `source ~/.zshrc`
5. The wrapper sources ~/.zshrc automatically on each call

### Cost

- Flash: ~$0.075/M input tokens, ~$0.30/M output tokens (very cheap)
- Pro: ~$7/M input, ~$21/M output (more expensive, use sparingly)
- Estimated monthly cost for factory usage: $5-30

### Fallback when API key missing

If `$GEMINI_API_KEY` is unset, the wrapper logs "no API key" and falls
through to the next model in the chain. If all Gemini models fail due to
missing key, the wrapper falls to Codex (if in chain), then exits 3.

### Coexistence with Gemini CLI

The wrapper does NOT use the `gemini` CLI at all. Your existing CLI
setup (GCA, cached credentials, etc.) is untouched — you can still use
`gemini` interactively for other purposes.

## Related skills
- `/ai-collab` — task-delegation strategy (which AI does what); complements this skill
- `/security-check` — run before any git push that touches these scripts
