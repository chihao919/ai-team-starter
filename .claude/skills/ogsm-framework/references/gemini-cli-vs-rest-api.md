# Gemini CLI vs REST API — Dual-Track Usage Guide

We use TWO different mechanisms to call Gemini, for different purposes:

## Track 1: Gemini CLI via GCA (Google Cloud Auth)

**When**: Interactive human use of the `gemini` CLI (e.g., `gemini` in terminal, `gemini -p "..."` for one-off queries)

**Auth**: OAuth via `gemini auth login`, stored in `~/.gemini/oauth_creds.json`, enabled via `GOOGLE_GENAI_USE_GCA=true` in `~/.zshrc`

**Tier**: Free (1000 req/day), shared Google Cloud project queue

**Known issues**:
- G-001: Gemini 2.5 Flash deterministic hang when routed to preview model
- G-012: Gemini 2.5 Pro also hangs under free tier queue contention
- Quota shared across the whole Google account

**When to use**:
- Interactive exploration, ad-hoc queries
- Light one-off usage outside the factory
- Integration with other tools that use the CLI (like Gemini CLI skills and extensions)

## Track 2: REST API via direct curl (paid tier)

**When**: Automated factory calls inside `/ai-fallback` skill (`call_with_fallback.sh`)

**Auth**: API key via `GEMINI_API_KEY` env var (in `~/.zshrc`)

**Tier**: Paid (pay-as-you-go, billing on Google Cloud project)
- Flash: ~$0.075/M input tokens
- Pro: ~$7/M input tokens
- Estimated factory cost: $5-30/month

**Setup**:
1. Get API key from https://aistudio.google.com/
2. Enable billing on the Google Cloud project
3. `export GEMINI_API_KEY="..."` in `~/.zshrc`
4. `/ai-fallback` skill's `call_with_fallback.sh` auto-sources `~/.zshrc`

**Advantages**:
- No hang (paid tier has independent queue)
- No CLI auth complexity (just API key in header)
- Reliable for automated factory work
- Independent from your personal Google account quota

**Implementation**:
```bash
curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
  -H "Content-Type: application/json" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -d '{"contents":[{"parts":[{"text":"your prompt"}]}]}'
```

## Why dual-track

**Separation of concerns**:
- Human interactive use → CLI (convenient, logged in)
- Automated agent use → REST (reliable, billed, no auth cache)

**No conflict**: the two tracks don't interfere. CLI keeps using GCA + oauth_creds.json; REST uses API key from env var directly.

**Migration note** (2026-04-11): `/ai-fallback` skill was originally built using CLI (`echo "Y" | gemini -m ... -p "..."`). Batch 1-3 scale-up revealed that CLI path hit G-001/G-012 hang issues consistently. Rewritten to use REST API directly. See `gotchas-and-lessons.md` entries G-001, G-012, NEW-02 for details.

## Troubleshooting

### REST API returns 401 / 403
- Check `echo $GEMINI_API_KEY | wc -c` — should be 40+ chars
- Verify billing enabled on Google Cloud project
- Verify API key has "Generative Language API" enabled

### REST API works but CLI doesn't
- Normal — they're independent
- CLI uses OAuth, REST uses API key
- If CLI broken: `gemini auth login` or check `~/.gemini/oauth_creds.json`

### /ai-fallback says "no API key"
- `source ~/.zshrc` in current shell
- Restart Claude Code session (env vars loaded at session start)
- Check `~/.zshrc` has the export line

## Scope for factory

Only `/ai-fallback` skill uses REST. Everything else (interactive `gemini`, other skills, Gemini CLI extensions) stays on GCA/CLI. Don't mix.
