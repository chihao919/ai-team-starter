#!/usr/bin/env bash
# Query the central Skill Invocation Map for a specific role.
# Usage: get_skills_for_role.sh <role-name>
#
# Returns the skill commands relevant to that role.
# If role not found, prints available roles and exits 2.

set -euo pipefail

MAP_FILE="${OGSM_SKILL_MAP:-$HOME/.claude/skills/ogsm-framework/references/skill-invocation-map.md}"
ROLE="${1:-}"

if [ -z "$ROLE" ]; then
  echo "Usage: $0 <role-name>" >&2
  echo "" >&2
  echo "Available roles:" >&2
  grep -E '^## Role: ' "$MAP_FILE" | sed 's/^## Role: /  - /' >&2
  exit 1
fi

if [ ! -f "$MAP_FILE" ]; then
  echo "Error: skill map not found at $MAP_FILE" >&2
  exit 1
fi

# Extract the section for this role
EXTRACTED="$(awk -v role="## Role: $ROLE" '
  $0 == role { printing = 1; print; next }
  printing && /^## / { exit }
  printing { print }
' "$MAP_FILE")"

# Check if anything was found
if [ -z "$EXTRACTED" ]; then
  echo "" >&2
  echo "Role '$ROLE' not found in map." >&2
  echo "Available roles:" >&2
  grep -E '^## Role: ' "$MAP_FILE" | sed 's/^## Role: /  - /' >&2
  exit 2
fi

printf '%s\n' "$EXTRACTED"
