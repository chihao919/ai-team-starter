#!/usr/bin/env python3
"""
check_ai_fallback_usage.py

Validate that AI model invocations in agent S sections and Tier 1 summaries
use the /ai-fallback wrapper rather than direct raw CLI calls.

Direct raw calls (e.g., 'gemini -m ...', 'codex exec ...') without the
/ai-fallback wrapper will break when model quota exhausts — this check
flags them as FAIL.

Only flags OBVIOUS raw invocations visible in the text. Script-mediated
calls are out of scope (cannot be verified statically).

Exit codes:
    0 - no raw AI invocations found (or all wrapped via /ai-fallback)
    1 - file not found or invalid format
    2 - raw AI invocations detected
"""

import argparse
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NON_AGENT_SECTION_PATTERNS = [
    r"v3\.1",
    r"v3",
    r"Skill Invocation Map",
    r"Model Invocation Map",
    r"Brief Layering",
    r"Principle 7",
    r"Direction Seed",
    r"Alignment Verification Matrix",
    r"Wave Gate Conditions",
    r"Known Issues",
    r"Deferred Improvements",
    r"v4 擴充",
    r"新增外部 Reviewer",
    r"Team Structure",
    r"Individual OGSM",
    r"其他.*新.*agent.*降級",
    r"降級",
]

# Patterns that indicate a raw (unwrapped) AI model call
RAW_AI_PATTERNS = [
    # gemini CLI direct invocation
    (r"gemini\s+-m\s+gemini-[\w.-]+", "gemini -m <model>"),
    # codex CLI direct invocation
    (r"codex\s+exec\b", "codex exec"),
    # echo piped directly to gemini (common pattern in this codebase)
    (r'echo\s+["\'].*["\'].*\|\s*gemini\b', "echo ... | gemini"),
    # Direct model flag invocation patterns
    (r"gemini\s+--model\s+\S+", "gemini --model <model>"),
]

# Pattern for /ai-fallback wrapped calls
FALLBACK_WRAPPER_PATTERN = re.compile(
    r"/ai-fallback\b",
    re.IGNORECASE,
)

# Compiled raw patterns
RAW_AI_COMPILED = [
    (re.compile(pattern, re.IGNORECASE), label)
    for pattern, label in RAW_AI_PATTERNS
]

# Section markers
S_START = re.compile(r"\*\*S[（(]")
M_START = re.compile(r"\*\*M[（(]")
TIER1_START = re.compile(r"\*\*Tier\s*1\s*(摘要|summary)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

EMOJI_UNICODE_RANGES = re.compile(
    "[\U0001F300-\U0001F9FF"
    "\U00002702-\U000027B0"
    "\U0000FE00-\U0000FE0F"
    "\U00002600-\U000026FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF]"
)


def is_agent_heading(heading_text: str) -> bool:
    """Return True if the heading looks like an actual agent section (starts with emoji)."""
    stripped = heading_text.strip()
    return bool(stripped and EMOJI_UNICODE_RANGES.match(stripped[0]))


def is_non_agent_heading(heading_text: str) -> bool:
    """Return True if a ### heading should be skipped."""
    if not is_agent_heading(heading_text):
        return True
    for pattern in NON_AGENT_SECTION_PATTERNS:
        if re.search(pattern, heading_text, re.IGNORECASE):
            return True
    return False


def split_into_agent_sections(lines: list[str]) -> list[tuple[str, list[str], int]]:
    """
    Split document lines into agent sections with starting line numbers.

    Returns list of (agent_name, section_lines, start_line_number) tuples.
    Line numbers are 1-based global indices.
    """
    agents: list[tuple[str, list[str], int]] = []
    current_name: str | None = None
    current_lines: list[str] = []
    current_start: int = 0

    for global_idx, line in enumerate(lines, start=1):
        if re.match(r"^## ", line):
            if current_name is not None:
                agents.append((current_name, current_lines, current_start))
                current_name = None
                current_lines = []
            continue

        if re.match(r"^### ", line):
            if current_name is not None:
                agents.append((current_name, current_lines, current_start))
                current_name = None
                current_lines = []

            heading_text = line[4:].strip()
            if is_non_agent_heading(heading_text):
                continue

            current_name = heading_text
            current_lines = [line]
            current_start = global_idx
            continue

        if current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        agents.append((current_name, current_lines, current_start))

    return agents


# ---------------------------------------------------------------------------
# Line-level scanning
# ---------------------------------------------------------------------------

def extract_s_and_tier1_lines(
    section_lines: list[str],
    start_line: int,
) -> list[tuple[int, str]]:
    """
    Extract lines from the S section and Tier 1 sub-block of an agent section.
    Returns list of (global_line_number, line_text) tuples.
    Lines in Model Invocation Map sub-block are also included (Tier 1 lists commands there).
    """
    NEW_SUBSECTION = re.compile(r"^\*\*[A-Za-z\u4e00-\u9fff].*\*\*")
    HEADING = re.compile(r"^#{2,4} ")

    result: list[tuple[int, str]] = []
    mode = None  # None | 's' | 'tier1'

    for local_idx, line in enumerate(section_lines):
        global_line = start_line + local_idx
        stripped = line.strip()

        if HEADING.match(stripped):
            mode = None
            continue

        if S_START.search(stripped):
            mode = "s"
            result.append((global_line, line.rstrip()))
            continue

        if M_START.search(stripped):
            # M section: stop S scanning but don't scan M
            mode = None
            continue

        if TIER1_START.search(stripped):
            mode = "tier1"
            result.append((global_line, line.rstrip()))
            continue

        # New subsection boundary
        if NEW_SUBSECTION.match(stripped) and stripped.startswith("**"):
            if re.match(r"\*\*[GSM\u5c64\u7e7e\u5c0d]", stripped) or \
               re.search(r"Anti-patterns|對齊", stripped):
                if not S_START.search(stripped) and not TIER1_START.search(stripped):
                    mode = None

        if mode in ("s", "tier1"):
            result.append((global_line, line.rstrip()))

    return result


def scan_for_raw_calls(
    lines_with_numbers: list[tuple[int, str]],
) -> tuple[list[tuple[int, str, str]], int]:
    """
    Scan lines for raw AI invocations and /ai-fallback wrapped calls.

    Returns (raw_calls, fallback_count) where:
        raw_calls: list of (line_number, line_text, pattern_label)
        fallback_count: number of /ai-fallback references found
    """
    raw_calls: list[tuple[int, str, str]] = []
    fallback_count = 0

    for line_num, text in lines_with_numbers:
        # Check for /ai-fallback wrapper
        if FALLBACK_WRAPPER_PATTERN.search(text):
            fallback_count += 1
            # A line with /ai-fallback is treated as wrapped — skip raw check
            continue

        # Check for raw AI invocations
        for compiled_pattern, label in RAW_AI_COMPILED:
            if compiled_pattern.search(text):
                raw_calls.append((line_num, text.strip(), label))
                break  # One match per line is enough

    return raw_calls, fallback_count


# ---------------------------------------------------------------------------
# Main validation logic
# ---------------------------------------------------------------------------

def validate_file(file_path: Path, verbose: bool = False, quiet: bool = False) -> int:
    """
    Run AI fallback usage check on the given OGSM file.

    Returns exit code: 0 (pass), 1 (file error), 2 (raw calls found).
    """
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}", file=sys.stderr)
        return 1

    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: Cannot read file: {exc}", file=sys.stderr)
        return 1

    lines = content.splitlines()

    if not any(line.startswith("### ") for line in lines):
        print("ERROR: Invalid format — no '### ' agent headings found.", file=sys.stderr)
        return 1

    agent_sections = split_into_agent_sections(lines)

    if not agent_sections:
        print("ERROR: No agent sections detected.", file=sys.stderr)
        return 1

    results = []

    for agent_name, section_lines, start_line in agent_sections:
        scannable_lines = extract_s_and_tier1_lines(section_lines, start_line)
        raw_calls, fallback_count = scan_for_raw_calls(scannable_lines)

        # Skip agents with no AI model references at all
        if not raw_calls and fallback_count == 0:
            if verbose:
                print(f"  [skip] {agent_name}: no AI model invocations found in S/Tier1")
            continue

        results.append({
            "agent": agent_name,
            "raw_calls": raw_calls,
            "fallback_count": fallback_count,
            "pass": len(raw_calls) == 0,
        })

    failing_agents = [r for r in results if not r["pass"]]
    total_raw = sum(len(r["raw_calls"]) for r in failing_agents)

    pass_fail = (
        "PASS"
        if not failing_agents
        else f"FAIL ({len(failing_agents)} agent{'s' if len(failing_agents) != 1 else ''} with raw calls)"
    )

    if quiet:
        print(f"Result: {pass_fail}")
        return 0 if not failing_agents else 2

    # Full report
    print("AI Fallback Usage Check")
    print("=======================")
    print(f"File: {file_path}")
    print()
    print("Per-agent checks (agents with AI invocations only):")

    if not results:
        print("  No agents with AI model invocations detected in S or Tier 1 sections.")
    else:
        for r in results:
            status = "[PASS]" if r["pass"] else "[FAIL]"
            print(f"  {status} {r['agent']}")
            print(f"    Direct model calls: {len(r['raw_calls'])}")
            print(f"    Via /ai-fallback: {r['fallback_count']}")

            if r["raw_calls"]:
                for line_num, text, label in r["raw_calls"]:
                    # Truncate long lines for readability
                    short_text = text[:100] + "..." if len(text) > 100 else text
                    print(f"    Line {line_num}: {short_text}")
                    print(
                        f"    Fix: Wrap this call with "
                        f"/ai-fallback --prefer <model-name> instead of calling {label} directly."
                    )

            if verbose and r["pass"] and r["fallback_count"] > 0:
                print(
                    f"    All {r['fallback_count']} model invocation(s) properly "
                    "wrapped via /ai-fallback."
                )

    print()
    print(f"Result: {pass_fail}")
    return 0 if not failing_agents else 2


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse CLI arguments and run AI fallback usage check."""
    parser = argparse.ArgumentParser(
        prog="check_ai_fallback_usage",
        description=(
            "Validate that AI model invocations in agent S sections and Tier 1 summaries "
            "use /ai-fallback wrapper rather than direct raw CLI calls. "
            "Direct calls (gemini -m ..., codex exec ...) will break on quota exhaustion."
        ),
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Path to the OGSM plan Markdown file (e.g. WTR-HSW-002-OGSM-v4.md)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print details for all agents including passing ones",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only PASS/FAIL summary (useful for CI)",
    )

    args = parser.parse_args()

    if args.verbose and args.quiet:
        print("ERROR: --verbose and --quiet are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    exit_code = validate_file(args.file, verbose=args.verbose, quiet=args.quiet)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
