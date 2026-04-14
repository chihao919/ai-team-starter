#!/usr/bin/env bash
# get_patterns_for_failure.sh
#
# Query patterns-library.md for patterns matching a failure type or keyword.
#
# Usage:
#   bash get_patterns_for_failure.sh <failure-type-or-keyword>
#
# Examples:
#   bash get_patterns_for_failure.sh validator
#   bash get_patterns_for_failure.sh bdd
#   bash get_patterns_for_failure.sh skill discovery

set -euo pipefail

LIB_FILE="${OGSM_PATTERNS_LIB:-$HOME/.claude/skills/ogsm-framework/references/patterns-library.md}"
QUERY="${1:-}"

if [ -z "$QUERY" ]; then
  echo "Usage: $0 <failure-type-keyword>" >&2
  echo "" >&2
  if [ -f "$LIB_FILE" ]; then
    echo "Available pattern IDs:" >&2
    grep -E '^### P-[0-9]+' "$LIB_FILE" | head -30 >&2
  fi
  exit 1
fi

if [ ! -f "$LIB_FILE" ]; then
  echo "Error: patterns library not found at $LIB_FILE" >&2
  exit 1
fi

# Extract pattern blocks where any line (case-insensitive) contains the query.
# Flush each block when encountering the next P-NNN heading (not just non-P headings).
MATCHED=$(awk -v q="$(echo "$QUERY" | tr '[:upper:]' '[:lower:]')" '
  /^### P-[0-9]+/ {
    if (in_block && match_found) { print block; printed_any = 1 }
    block = $0
    in_block = 1
    match_found = 0
    next
  }
  /^### / && !/^### P-[0-9]+/ {
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
  echo "No patterns matched query '$QUERY'." >&2
  echo "" >&2
  echo "Try a keyword from these categories:" >&2
  grep -E '^\*\*Category\*\*:' "$LIB_FILE" | sed 's/^\*\*Category\*\*: /  - /' | sort -u >&2
  exit 2
fi

echo "$MATCHED"
