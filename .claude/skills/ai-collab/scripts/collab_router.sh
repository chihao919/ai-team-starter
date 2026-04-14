#!/usr/bin/env bash
# collab_router.sh — Task-type-aware multi-model router
#
# v5.2-copilot: Replaces single-model-with-fallback pattern.
# Routes tasks to the best model based on task type, with fallback chains.
#
# Usage:
#   collab_router.sh --task <type> "<prompt>"
#   collab_router.sh --model <model> "<prompt>"     # explicit override
#   collab_router.sh --dry-run --task <type> "<prompt>"  # show routing without executing
#   collab_router.sh --list-tasks                    # show all task types + routing
#
# Task types:
#   research, verify, persona, seo, code, review, html-build
#   (writing, judgment, chinese → Claude native, no CLI needed)
#
# Environment variables:
#   GEMINI_API_KEY       — required for Gemini REST API calls
#   OGSM_MODEL_TIMEOUT   — default per-model timeout (default: 120s)
#   OGSM_CODEX_CWD       — working directory for codex (default: $HOME)
#   COLLAB_LOG_DIR       — log directory (default: /tmp/collab-router-logs)
#
# Exit codes:
#   0  — success
#   1  — bad invocation
#   2  — task type is Claude-native (writing/judgment/chinese)
#   3  — all models exhausted

set -euo pipefail

# Load env
[ -f ~/.zshrc ] && source ~/.zshrc 2>/dev/null || true

# ---------------------------------------------------------------------------
# Configuration: Task-Type Routing Table
# ---------------------------------------------------------------------------

# Returns: model chain (comma-separated) for a given task type
get_chain_for_task() {
  local task="$1"
  case "$task" in
    research)    echo "gemini-2.5-pro,codex,websearch" ;;
    verify)      echo "gemini-2.5-flash,websearch,claude-native" ;;
    persona)     echo "gemini-2.5-pro,codex" ;;
    seo)         echo "gemini-2.5-flash,codex" ;;
    code)        echo "codex,claude-native" ;;
    review)      echo "codex,gemini-2.5-pro,claude-native" ;;
    html-build)  echo "codex,claude-native" ;;
    writing|judgment|chinese)
      echo "claude-native"
      return 2  # Signal: this is Claude-native, no CLI call needed
      ;;
    *)
      echo ""
      return 1
      ;;
  esac
  return 0
}

# Returns human-readable description of task type
get_task_description() {
  local task="$1"
  case "$task" in
    research)    echo "Discovery + Google Search grounding" ;;
    verify)      echo "Fact verification with web grounding" ;;
    persona)     echo "Role-play simulation (independent model family)" ;;
    seo)         echo "SEO/AEO optimization with Google search insight" ;;
    code)        echo "Code generation (HTML/CSS/JS)" ;;
    review)      echo "Systematic checking + citation cross-verification" ;;
    html-build)  echo "Structured HTML output generation" ;;
    writing)     echo "Creative writing, emotional arc (Claude native)" ;;
    judgment)    echo "Complex decisions, conflict resolution (Claude native)" ;;
    chinese)     echo "Chinese language content (Claude native)" ;;
    *)           echo "Unknown task type" ;;
  esac
}

# ---------------------------------------------------------------------------
# Model callers (reuses logic from call_with_fallback.sh)
# ---------------------------------------------------------------------------

call_gemini_rest() {
  local model="$1"
  local prompt="$2"
  local timeout_sec="${3:-120}"

  if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "ERROR: GEMINI_API_KEY not set" >&2
    return 1
  fi

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

call_codex() {
  local prompt="$1"
  local timeout_sec="${2:-90}"

  if ! command -v codex >/dev/null 2>&1; then
    echo "codex CLI not installed" >&2
    return 1
  fi

  local CODEX_CWD="${OGSM_CODEX_CWD:-$HOME}"
  local OUTPUT=""
  local EXIT_CODE=0

  OUTPUT=$(cd "$CODEX_CWD" && timeout --kill-after=5s "${timeout_sec}s" \
    codex exec --full-auto --skip-git-repo-check -C "$CODEX_CWD" "$prompt" \
    2>&1) || EXIT_CODE=$?

  if [ "$EXIT_CODE" -eq 124 ] || [ "$EXIT_CODE" -eq 137 ]; then
    echo "TIMEOUT after ${timeout_sec}s" >&2
    return 2
  fi

  if echo "$OUTPUT" | grep -qiE "(not inside a trusted directory|trust check failed)"; then
    echo "TRUST_CHECK_FAILED" >&2
    return 3
  fi

  if [ -z "$OUTPUT" ]; then
    echo "EMPTY_RESPONSE" >&2
    return 4
  fi

  echo "$OUTPUT"
  return 0
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR="${COLLAB_LOG_DIR:-/tmp/collab-router-logs}"
mkdir -p "$LOG_DIR" 2>/dev/null || true

log_call() {
  local task="$1"
  local model="$2"
  local status="$3"
  local timestamp
  timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  echo "${timestamp} | task=${task} | model=${model} | status=${status}" >> "${LOG_DIR}/collab-router.log"
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

TASK=""
MODEL_OVERRIDE=""
PROMPT=""
DRY_RUN=false
LIST_TASKS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task)
      TASK="$2"
      shift 2
      ;;
    --model)
      MODEL_OVERRIDE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --list-tasks)
      LIST_TASKS=true
      shift
      ;;
    -h|--help)
      echo "Usage: collab_router.sh --task <type> \"<prompt>\""
      echo "       collab_router.sh --model <model> \"<prompt>\""
      echo "       collab_router.sh --dry-run --task <type> \"<prompt>\""
      echo "       collab_router.sh --list-tasks"
      echo ""
      echo "Task types: research, verify, persona, seo, code, review, html-build"
      echo "Claude-native (no CLI): writing, judgment, chinese"
      exit 0
      ;;
    *)
      PROMPT="$1"
      shift
      ;;
  esac
done

# ---------------------------------------------------------------------------
# --list-tasks mode
# ---------------------------------------------------------------------------

if [ "$LIST_TASKS" = true ]; then
  echo "=== Task-Type Routing Table (v5.2-copilot) ==="
  echo ""
  printf "%-12s %-35s %s\n" "TASK" "CHAIN" "DESCRIPTION"
  printf "%-12s %-35s %s\n" "----" "-----" "-----------"
  for t in research verify persona seo code review html-build writing judgment chinese; do
    chain=$(get_chain_for_task "$t" 2>/dev/null || true)
    desc=$(get_task_description "$t")
    printf "%-12s %-35s %s\n" "$t" "$chain" "$desc"
  done
  echo ""
  echo "Note: writing/judgment/chinese = Claude native. No CLI call needed."
  exit 0
fi

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

if [ -z "$TASK" ] && [ -z "$MODEL_OVERRIDE" ]; then
  echo "ERROR: Must specify --task <type> or --model <model>" >&2
  echo "Run with --help for usage." >&2
  exit 1
fi

if [ -z "$PROMPT" ]; then
  echo "ERROR: No prompt provided." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Resolve model chain
# ---------------------------------------------------------------------------

if [ -n "$MODEL_OVERRIDE" ]; then
  # Explicit model override — single model, no fallback
  CHAIN="$MODEL_OVERRIDE"
  TASK="${TASK:-override}"
else
  CHAIN_EXIT=0
  CHAIN=$(get_chain_for_task "$TASK") || CHAIN_EXIT=$?

  if [ $CHAIN_EXIT -eq 2 ]; then
    echo "=== Task type '$TASK' is Claude-native ===" >&2
    echo "For writing/judgment/chinese tasks, Claude handles these natively." >&2
    echo "No CLI call needed — just do the work directly in Claude." >&2
    log_call "$TASK" "claude-native" "SKIPPED_NATIVE"
    exit 2
  fi

  if [ $CHAIN_EXIT -eq 1 ] || [ -z "$CHAIN" ]; then
    echo "ERROR: Unknown task type '$TASK'" >&2
    echo "Valid types: research, verify, persona, seo, code, review, html-build, writing, judgment, chinese" >&2
    exit 1
  fi
fi

# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------

if [ "$DRY_RUN" = true ]; then
  echo "=== DRY RUN ==="
  echo "Task type:  $TASK"
  echo "Chain:      $CHAIN"
  echo "Prompt:     ${PROMPT:0:100}..."
  echo ""
  IFS=',' read -ra MODELS <<< "$CHAIN"
  for i in "${!MODELS[@]}"; do
    echo "  Step $((i+1)): ${MODELS[$i]}"
  done
  echo ""
  echo "No actual model calls made."
  log_call "$TASK" "dry-run" "DRY_RUN"
  exit 0
fi

# ---------------------------------------------------------------------------
# Execute chain
# ---------------------------------------------------------------------------

IFS=',' read -ra MODELS <<< "$CHAIN"
declare -a ATTEMPTS=()

for MODEL in "${MODELS[@]}"; do
  case "$MODEL" in

    gemini-2.5-flash|gemini-2.5-flash-lite|gemini-2.5-pro)
      TIMEOUT="${OGSM_MODEL_TIMEOUT:-120}"
      [ "$MODEL" = "gemini-2.5-pro" ] && TIMEOUT="${OGSM_PRO_TIMEOUT:-150}"
      [ "$MODEL" = "gemini-2.5-flash" ] && TIMEOUT="${OGSM_FLASH_TIMEOUT:-90}"

      OUTPUT=$(call_gemini_rest "$MODEL" "$PROMPT" "$TIMEOUT") && {
        if [ -n "$OUTPUT" ] && ! ([ "${#OUTPUT}" -lt 150 ] && echo "$OUTPUT" | grep -qiE "(error|refused|failed)"); then
          echo "=== Model used: $MODEL (task: $TASK) ==="
          echo "$OUTPUT"
          log_call "$TASK" "$MODEL" "SUCCESS"
          exit 0
        fi
      }
      ATTEMPTS+=("$MODEL: failed or empty")
      log_call "$TASK" "$MODEL" "FAILED"
      ;;

    codex)
      OUTPUT=$(call_codex "$PROMPT" "${OGSM_CODEX_TIMEOUT:-90}") && {
        if [ -n "$OUTPUT" ]; then
          echo "=== Model used: codex (task: $TASK) ==="
          echo "$OUTPUT"
          log_call "$TASK" "codex" "SUCCESS"
          exit 0
        fi
      }
      ATTEMPTS+=("codex: failed or empty")
      log_call "$TASK" "codex" "FAILED"
      ;;

    websearch)
      # WebSearch is a Claude Code built-in tool, not a CLI command.
      # Signal to caller to use WebSearch tool instead.
      echo "=== FALLBACK: Use WebSearch tool ===" >&2
      echo "All LLM models before websearch in chain failed." >&2
      echo "Caller should use Claude Code's built-in WebSearch tool for: ${PROMPT:0:200}" >&2
      log_call "$TASK" "websearch" "REDIRECT"
      exit 3
      ;;

    claude-native)
      # Claude-native = the calling Claude instance handles it directly
      echo "=== FALLBACK: Claude native ===" >&2
      echo "All external models failed. Claude should handle this task natively." >&2
      echo "Prompt: ${PROMPT:0:200}" >&2
      log_call "$TASK" "claude-native" "REDIRECT"
      exit 3
      ;;

    *)
      ATTEMPTS+=("$MODEL: unknown model, skipped")
      log_call "$TASK" "$MODEL" "UNKNOWN_SKIPPED"
      ;;

  esac
done

# All exhausted
echo "ERROR: All models in chain exhausted." >&2
echo "Task: $TASK | Chain: $CHAIN" >&2
echo "Attempts:" >&2
for ENTRY in "${ATTEMPTS[@]}"; do
  echo "  - $ENTRY" >&2
done
log_call "$TASK" "ALL" "EXHAUSTED"
exit 3
