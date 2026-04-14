#!/usr/bin/env bash
# get_gotchas_for_context.sh
#
# Query gotchas-and-lessons.md for gotchas matching a context keyword.
#
# Usage:
#   bash get_gotchas_for_context.sh <context-keyword>
#
# Examples:
#   bash get_gotchas_for_context.sh gemini
#   bash get_gotchas_for_context.sh validator

set -euo pipefail

LIB_FILE="${OGSM_GOTCHAS_LIB:-$HOME/.claude/skills/ogsm-framework/references/gotchas-and-lessons.md}"
QUERY="${1:-}"

if [ -z "$QUERY" ]; then
  echo "Usage: $0 <context-keyword>" >&2
  echo "" >&2
  echo "Available gotcha IDs (G-NNN):" >&2
  grep -E '^### G-[0-9]+' "$LIB_FILE" | sed 's/^### /  - /' >&2 || true
  exit 1
fi

if [ ! -f "$LIB_FILE" ]; then
  echo "Error: gotchas library not found at $LIB_FILE" >&2
  exit 1
fi

# Extract gotcha blocks where any line (case-insensitive) contains the query.
# Flush each block when encountering the next G-NNN heading (not just non-G headings).
MATCHED=$(awk -v q="$(echo "$QUERY" | tr '[:upper:]' '[:lower:]')" '
  /^### G-[0-9]+/ {
    if (in_block && match_found) { print block; printed_any = 1 }
    block = $0
    in_block = 1
    match_found = 0
    next
  }
  /^### / && !/^### G-[0-9]+/ {
    if (in_block && match_found) { print block; printed_any = 1 }
    in_block = 0
    block = ""
    match_found = 0
    next
  }
  /^## / {
    if (in_block && match_found) { print block; printed_any = 1 }
    in_block = 0
    block = ""
    match_found = 0
    next
  }
  in_block {
    block = block "\n" $0
    line_lower = tolower($0)
    if (index(line_lower, q) > 0) match_found = 1
  }
  END {
    if (in_block && match_found) { print block; printed_any = 1 }
    if (!printed_any) exit 2
  }
' "$LIB_FILE")

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ] || [ -z "$MATCHED" ]; then
  echo "No gotchas matched query '$QUERY'." >&2
  echo "" >&2
  echo "Available gotcha IDs (G-NNN):" >&2
  grep -E '^### G-[0-9]+' "$LIB_FILE" | sed 's/^### /  - /' >&2 || true
  exit 2
fi

echo "$MATCHED"
