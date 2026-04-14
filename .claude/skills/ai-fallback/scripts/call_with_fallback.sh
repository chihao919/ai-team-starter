#!/usr/bin/env bash
# Quota-aware, hang-resilient multi-model fallback caller
#
# Usage:
#   call_with_fallback.sh "prompt text" [chain]
#
# Arguments:
#   $1  PROMPT  — the text prompt to send to the model
#   $2  CHAIN   — comma-separated list of model identifiers (optional)
#                 default: gemini-2.5-flash-lite,gemini-2.5-pro,codex
#
# Environment variables:
#   GEMINI_API_KEY       — required for Gemini REST API calls (loaded from ~/.zshrc automatically)
#   OGSM_MODEL_TIMEOUT   — default per-model timeout in seconds (default: 120)
#                          e.g. OGSM_MODEL_TIMEOUT=60 for faster fail-fast
#   OGSM_PRO_TIMEOUT     — override for gemini-2.5-pro (default: 150)
#   OGSM_LITE_TIMEOUT    — override for gemini-2.5-flash-lite (default: 90)
#   OGSM_CODEX_TIMEOUT   — override for codex (default: 90)
#   OGSM_CODEX_CWD       — working directory for codex invocation (default: $HOME)
#                          must be a trusted directory for codex to accept the call
#
# Exit codes:
#   0  — success; stdout contains "=== Model used: <name> ===" header + model output
#   1  — bad invocation (no prompt supplied)
#   2  — single-model failure (edge case, kept for compatibility)
#   3  — all models in chain exhausted; caller should use WebSearch as final fallback
#
# Quota / rate-limit signals detected (case-insensitive):
#   "429", "quota", "rate limit", "rate_limit", "exhausted", "resource_exhausted"
#
# Hang detection (INT-001 fix):
#   Each model call is wrapped with `timeout`. If a model does not produce output
#   within the per-model timeout seconds, the process is killed and the next model
#   in the chain is tried. Exit code 124 = SIGTERM, 137 = SIGKILL (--kill-after).
#
# REST API mode (Gemini):
#   Gemini models now call Google REST API directly (paid tier via GEMINI_API_KEY),
#   bypassing the `gemini` CLI and GCA free-tier routing hangs. See SKILL.md for details.

set -euo pipefail

# Load env vars (especially GEMINI_API_KEY from ~/.zshrc)
[ -f ~/.zshrc ] && source ~/.zshrc 2>/dev/null || true

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------
PROMPT="${1:-}"
CHAIN="${2:-gemini-2.5-flash-lite,gemini-2.5-pro,codex}"

# Default per-model timeout in seconds; individual models may override via get_timeout_for_model
TIMEOUT_SEC="${OGSM_MODEL_TIMEOUT:-120}"

if [ -z "$PROMPT" ]; then
  echo "Usage: $0 \"prompt\" [chain]" >&2
  echo "  chain example: \"gemini-2.5-flash,gemini-2.5-flash-lite,codex\"" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Returns per-model timeout in seconds.
# Allows individual models to have different timeouts without affecting others.
# Override via environment variables:
#   OGSM_PRO_TIMEOUT   — gemini-2.5-pro (default: 150s; needs more time for large responses)
#   OGSM_LITE_TIMEOUT  — gemini-2.5-flash-lite (default: 90s)
#   OGSM_CODEX_TIMEOUT — codex (default: 90s)
#   OGSM_MODEL_TIMEOUT — fallback for any other model (default: 120s)
get_timeout_for_model() {
  local model="$1"
  case "$model" in
    gemini-2.5-pro)        echo "${OGSM_PRO_TIMEOUT:-150}" ;;
    gemini-2.5-flash-lite) echo "${OGSM_LITE_TIMEOUT:-90}" ;;
    codex)                 echo "${OGSM_CODEX_TIMEOUT:-90}" ;;
    *)                     echo "${OGSM_MODEL_TIMEOUT:-120}" ;;
  esac
}

# Returns 0 if the given string contains a quota / rate-limit signal
is_quota_error() {
  local text="$1"
  echo "$text" | grep -qiE "429|quota|rate[_ ]?limit|exhausted|resource_exhausted"
}

# Calls a Gemini model via REST API using GEMINI_API_KEY.
# Usage: call_gemini_rest <model> <prompt> <timeout_sec>
# Returns: 0 on success (text on stdout), 1 no API key, 2 curl failed, 3 API/parse error
call_gemini_rest() {
  local model="$1"
  local prompt="$2"
  local timeout_sec="$3"

  if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "ERROR: GEMINI_API_KEY not set in env" >&2
    return 1
  fi

  # JSON-escape the prompt safely using Python (handles quotes, newlines, unicode)
  local escaped_prompt
  escaped_prompt=$(printf '%s' "$prompt" | python3 -c 'import sys, json; print(json.dumps(sys.stdin.read()))')

  local payload="{\"contents\":[{\"parts\":[{\"text\":${escaped_prompt}}]}]}"

  local response
  response=$(curl -s --max-time "$timeout_sec" -X POST \
    "https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent" \
    -H "Content-Type: application/json" \
    -H "x-goog-api-key: ${GEMINI_API_KEY}" \
    -d "$payload" 2>&1)

  local curl_exit=$?

  if [ $curl_exit -ne 0 ]; then
    echo "CURL_ERROR: exit=$curl_exit" >&2
    return 2
  fi

  # Extract text content from JSON response; exit with specific codes on error conditions
  local text
  text=$(printf '%s' "$response" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    if "error" in d:
        print("API_ERROR:", d["error"].get("message", "unknown"), file=sys.stderr)
        sys.exit(3)
    cand = d.get("candidates", [])
    if not cand:
        print("NO_CANDIDATES", file=sys.stderr)
        sys.exit(4)
    parts = cand[0].get("content", {}).get("parts", [])
    if parts:
        print(parts[0].get("text", ""))
    else:
        print("EMPTY_PARTS", file=sys.stderr)
        sys.exit(5)
except Exception as e:
    print(f"PARSE_ERROR: {e}", file=sys.stderr)
    sys.exit(6)
' 2>&1)

  local parse_exit=$?

  if [ $parse_exit -ne 0 ]; then
    return 3
  fi

  echo "$text"
  return 0
}

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
IFS=',' read -ra MODELS <<< "$CHAIN"

declare -a ATTEMPTS=()

for MODEL in "${MODELS[@]}"; do
  case "$MODEL" in

    # ------------------------------------------------------------------
    # Gemini family — use REST API directly (paid tier via GEMINI_API_KEY)
    # Bypasses GCA free-tier routing hangs (G-001 Flash hang, G-012 Pro hang).
    # ------------------------------------------------------------------
    gemini-2.5-flash|gemini-2.5-flash-lite|gemini-2.5-pro)

      MODEL_TIMEOUT=$(get_timeout_for_model "$MODEL")
      OUTPUT=$(call_gemini_rest "$MODEL" "$PROMPT" "$MODEL_TIMEOUT")
      REST_EXIT=$?

      if [ $REST_EXIT -eq 0 ] && [ -n "$OUTPUT" ]; then
        # General heuristic: if output is short AND looks like an error message, treat as failure.
        # Catches cases where the API exits 0 but returns an error-like response on stdout.
        if [ "${#OUTPUT}" -lt 150 ] && echo "$OUTPUT" | grep -qiE "(error|refused|failed|not authorized|trust|not found|permission denied)"; then
          ATTEMPTS+=("$MODEL: output looks like error (short + error keyword), fallthrough")
          continue
        fi
        echo "=== Model used: $MODEL (REST API, paid tier) ==="
        echo "$OUTPUT"
        exit 0
      fi

      # REST call failed — log reason and continue to next model in chain
      case $REST_EXIT in
        1) ATTEMPTS+=("$MODEL: no API key") ;;
        2) ATTEMPTS+=("$MODEL: curl failed / timeout") ;;
        3) ATTEMPTS+=("$MODEL: API error or parse fail") ;;
        *) ATTEMPTS+=("$MODEL: unknown error code $REST_EXIT") ;;
      esac
      continue
      ;;

    # ------------------------------------------------------------------
    # Codex CLI (OpenAI)
    # ------------------------------------------------------------------
    codex)

      if ! command -v codex >/dev/null 2>&1; then
        ATTEMPTS+=("$MODEL: codex CLI not installed, skipped")
        continue
      fi

      # codex exec requires a trusted directory context.
      # Use OGSM_CODEX_CWD (default: $HOME) which is typically in codex's trust list.
      # Running from /tmp caused "Not inside a trusted directory" silent failures.
      # Wrap in timeout to detect hangs (same pattern as Gemini branch).
      CODEX_CWD="${OGSM_CODEX_CWD:-$HOME}"
      MODEL_TIMEOUT=$(get_timeout_for_model "$MODEL")
      TIMEOUT_EXIT=0

      # NEW-02 fix: first try --skip-git-repo-check to bypass trust-check entirely.
      # This avoids the failure mode where codex exits 0 with "Not inside a trusted
      # directory" on stdout — wrapper previously classified that as SUCCESS.
      OUTPUT=$(cd "$CODEX_CWD" && timeout --kill-after=5s "${MODEL_TIMEOUT}s" \
        codex exec --full-auto --skip-git-repo-check -C "$CODEX_CWD" "$PROMPT" \
        2>&1) || TIMEOUT_EXIT=$?

      # Exit 124 = killed by SIGTERM (timeout), 137 = killed by SIGKILL (--kill-after)
      if [ "$TIMEOUT_EXIT" -eq 124 ] || [ "$TIMEOUT_EXIT" -eq 137 ]; then
        ATTEMPTS+=("$MODEL: timeout after ${MODEL_TIMEOUT}s (hang detected), fallthrough")
        continue
      fi

      if is_quota_error "$OUTPUT"; then
        ATTEMPTS+=("$MODEL: quota/rate-limit detected, fallthrough")
        continue
      fi

      # NEW-02 fix: detect codex trust-check error patterns that exit 0 with error text on stdout.
      # Codex sometimes returns a trust-check refusal on stdout with exit code 0,
      # which the wrapper previously misclassified as a successful response.
      if echo "$OUTPUT" | grep -qiE "(not inside a trusted directory|--skip-git-repo-check|refusing to run|trust check failed)"; then
        ATTEMPTS+=("$MODEL: trust-check refused (exit 0 + error on stdout), fallthrough")
        continue
      fi

      if [ -n "$OUTPUT" ]; then
        # General heuristic: if output is short AND looks like an error message, treat as failure.
        # NEW-02 class: catches any short error-looking stdout that slipped past trust-check filter.
        if [ "${#OUTPUT}" -lt 150 ] && echo "$OUTPUT" | grep -qiE "(error|refused|failed|not authorized|trust|not found|permission denied)"; then
          ATTEMPTS+=("$MODEL: output looks like error (short + error keyword), fallthrough")
          continue
        fi
        echo "=== Model used: $MODEL ==="
        echo "$OUTPUT"
        exit 0
      fi

      ATTEMPTS+=("$MODEL: empty response, fallthrough")
      ;;

    # ------------------------------------------------------------------
    # Catch-all for unknown model identifiers
    # ------------------------------------------------------------------
    *)
      ATTEMPTS+=("$MODEL: unknown model identifier, skipped")
      ;;

  esac
done

# ---------------------------------------------------------------------------
# All models exhausted
# ---------------------------------------------------------------------------
echo "ERROR: All models in chain exhausted or unavailable." >&2
echo "" >&2
echo "Attempt log:" >&2
for ENTRY in "${ATTEMPTS[@]}"; do
  echo "  - $ENTRY" >&2
done
echo "" >&2
echo "HINT: All LLM models failed. Caller should use WebSearch tool as final fallback." >&2
exit 3
