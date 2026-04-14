# Background Agent Execution & Permission Whitelist

How to run AI agents in the background for parallel execution, and how to configure permissions so they can operate autonomously.

## run_in_background Parameter

When dispatching subagents via the Agent tool or running long-running Bash commands, set `run_in_background: true` to avoid blocking the main conversation.

This is critical for teams with 12+ agents where Wave parallelism is the difference between a 30-minute run and a 3-hour run.

### When to use background execution
- Dispatching multiple Wave 1 agents in parallel (after the pilot passes)
- Running research tasks that may take 60+ seconds
- Executing scripts that call external APIs (Gemini, Codex)
- Any task where you don't need the result immediately

### When NOT to use background execution
- Pilot dispatches (you need to evaluate the output before proceeding)
- Gate reviews (Commander needs results before deciding)
- Sequential dependencies (task B needs task A's output)

## Permission Whitelist in settings.json

By default, Claude Code asks for permission before running tools. For autonomous agent execution, configure `settings.json` to allow specific tools without prompting.

### Configuration
```json
{
  "permissions": {
    "defaultMode": "dontAsk",
    "allow": [
      "Read",
      "Write",
      "Edit",
      "Bash(git *)",
      "Bash(python *)",
      "Bash(bash *)",
      "Glob",
      "Grep",
      "Skill"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(git push --force *)",
      "Bash(curl * | bash)"
    ]
  }
}
```

### Security considerations
- Always deny destructive operations (`rm -rf`, `git push --force`)
- Always deny arbitrary code execution from remote sources
- Scope Bash permissions to specific prefixes when possible
- Review the whitelist periodically — remove permissions no longer needed

## generate_permissions.py Script

Use the helper script to generate a permission whitelist based on your project's needs:

```bash
python ~/.claude/skills/ai-team-architecture/scripts/generate_permissions.py \
  --project my-project \
  --output .claude/settings.json
```

The script:
1. Scans the project's OGSM spec for skill and model invocations
2. Identifies which tools each agent needs
3. Generates a minimal permission whitelist
4. Outputs a `settings.json` file

### Options
```
--project    Project name (used for path resolution)
--output     Output path for settings.json
--strict     Only allow explicitly listed commands (no wildcards)
--dry-run    Print the generated config without writing
```

## Anti-Patterns

### Anti-pattern 0: Dispatching AI for script-solvable tasks

**Wrong**: Dispatch Codex to convert markdown to HTML.
**Right**: Run `python scripts/md_to_blog.py input.md --output output.html`.

**Wrong**: Dispatch Gemini to check for broken links.
**Right**: Run `python scripts/check_links.py path/to/skill/`.

**Wrong**: Dispatch AI to validate an OGSM schema.
**Right**: Run `python scripts/validate_schema.py path/to/plan.md`.

AI models are for judgment and creativity. If a deterministic script exists in `scripts/`, use it. This is faster, cheaper, and more reliable than dispatching an AI model for mechanical work.

### Anti-pattern 1: Doing work yourself instead of dispatching

**Wrong**: Commander reads all research files, synthesizes, writes the summary.
**Right**: Commander dispatches Investigator agents, waits for results, reviews against O.

The Commander's job is judgment and coordination, not execution. If the Commander is doing the work, the team structure is wrong.

### Anti-pattern 2: Artificial wave gates for parallel tasks

**Wrong**:
```
Wave 1: Investigator A (wait) -> Investigator B (wait) -> Investigator C
```

**Right**:
```
Wave 1: Pilot Investigator A (wait for sanity check)
         -> Then parallel: Investigator A, B, C (all run_in_background: true)
```

The only legitimate sequential gates are:
1. Pilot dispatch (1 agent, then the rest)
2. Cross-wave dependencies (Wave 2 needs Wave 1 outputs)
3. Gate reviews (Commander evaluates before next wave)

Everything else should run in parallel.

### Anti-pattern 3: Polling for background results

**Wrong**:
```
# Dispatch agent in background
# Sleep 10 seconds
# Check if done
# Sleep 10 seconds...
```

**Right**: The background execution system notifies you when the task completes. Do not poll. Do not sleep. Start other work and wait for the notification.

## Practical Workflow Example

A 3-wave, 12-agent course rewrite:

```
Wave 1 (Research):
  1. Dispatch Pilot Investigator (foreground, wait)
  2. Review pilot output against O
  3. Fix briefing if needed
  4. Dispatch Investigators A, B, C (background, parallel)
  5. Dispatch Fact Checker (background, parallel with investigators)
  -> Wait for all Wave 1 to complete
  -> Gate review: Commander evaluates research quality

Wave 2 (Review):
  6. Dispatch Pilot Reviewer (foreground, wait)
  7. Review pilot against O
  8. Dispatch Persona Reviewers x3 (background, parallel)
  9. Dispatch Source Reviewer (background, parallel)
  -> Wait for all Wave 2 to complete
  -> Gate review: Commander integrates feedback

Wave 3 (Build):
  10. Dispatch Writer (foreground — sequential, needs all feedback)
  11. Dispatch Engineer (background, after writer output)
  12. Dispatch SEO Engineer (background, parallel with Engineer)
  -> Final gate: Quality Auditor reviews assembled output
```

Total wall-clock time with background execution: ~15-20 minutes.
Without background execution (all sequential): ~60-90 minutes.
