#!/usr/bin/env python3
"""
suggest_script_extraction.py

Advisory report: scan each agent's S and M sections for deterministic-pattern
bullets that are good candidates for extraction into standalone Python scripts.
This is NOT a PASS/FAIL gate — it produces suggestions only.

A "deterministic bullet" is one whose logic could be expressed as a repeatable
script: format validation, counting/ratio calculation, file parsing, keyword
checking, deduplication, schema checks, etc.

Exit codes:
    0 - always (advisory only, never a hard gate)
    1 - file not found or invalid format
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

# Deterministic-pattern keyword rules: (regex pattern, suggested script suffix)
DETERMINISTIC_PATTERNS = [
    # Format / schema validation
    (r"驗證.*格式", "validate_format"),
    (r"format\s+validation", "validate_format"),
    (r"schema.*check", "check_schema"),
    (r"schema\s*驗證", "check_schema"),
    (r"validate\b", "validate_data"),
    (r"驗證\b", "validate_data"),
    # Counting / ratio
    (r"計算.*比例", "count_ratio"),
    (r"calculate.*ratio", "count_ratio"),
    (r"\bcount\b", "count_items"),
    (r"促銷比例", "count_promo_ratio"),
    (r"字數", "count_words"),
    (r"word[\s_-]*count", "count_words"),
    # File parsing
    (r"解析.*檔案", "parse_file"),
    (r"parse.*file", "parse_file"),
    (r"讀.*檔案", "read_file"),
    # Keyword / grep checks
    (r"檢查.*關鍵字", "check_keywords"),
    (r"keyword\s+check", "check_keywords"),
    r"grep",
    # Deduplication
    (r"\bdedup\b", "dedup_entries"),
    (r"去重", "dedup_entries"),
    # Append operations
    (r"append.*到", "append_to_file"),
    (r"append\s+to\b", "append_to_file"),
    (r"寫入.*queue", "append_to_queue"),
    # Coverage checks
    (r"覆蓋.*是否", "check_coverage"),
    (r"coverage.*check", "check_coverage"),
    # Lint checks
    (r"\blint\b", "lint_content"),
    (r"禁用詞", "lint_banned_words"),
    # Score / rating
    (r"評分.*平均", "compute_average_score"),
    (r"average.*score", "compute_average_score"),
]

# Normalize entries that are plain strings (just the regex) to tuples
_normalized: list[tuple[str, str]] = []
for item in DETERMINISTIC_PATTERNS:
    if isinstance(item, str):
        _normalized.append((item, item.strip(r"\b").replace("\\", "")))
    else:
        _normalized.append(item)
DETERMINISTIC_PATTERNS = _normalized


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


def split_into_agent_sections(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Split document lines into (agent_name, section_lines) tuples."""
    agents: list[tuple[str, list[str]]] = []
    current_name: str | None = None
    current_lines: list[str] = []

    for line in lines:
        if re.match(r"^## ", line):
            if current_name is not None:
                agents.append((current_name, current_lines))
                current_name = None
                current_lines = []
            continue

        if re.match(r"^### ", line):
            if current_name is not None:
                agents.append((current_name, current_lines))
                current_name = None
                current_lines = []

            heading_text = line[4:].strip()
            if is_non_agent_heading(heading_text):
                continue

            current_name = heading_text
            current_lines = [line]
            continue

        if current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        agents.append((current_name, current_lines))

    return agents


def extract_s_and_m_lines(
    section_lines: list[str],
) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """
    Extract S and M section bullets with their original line numbers (1-based).

    Returns (s_bullets, m_bullets) where each entry is (line_number, line_text).
    """
    S_START = re.compile(r"\*\*S[（(]")
    M_START = re.compile(r"\*\*M[（(]")
    NEW_SUBSECTION = re.compile(r"^\*\*[A-Za-z\u4e00-\u9fff].*\*\*")
    HEADING = re.compile(r"^#{2,4} ")

    s_bullets: list[tuple[int, str]] = []
    m_bullets: list[tuple[int, str]] = []
    mode = None

    # section_lines do not carry global line numbers; we build them below
    for idx, line in enumerate(section_lines):
        stripped = line.strip()

        if HEADING.match(stripped):
            mode = None
            continue

        if S_START.search(stripped):
            mode = "s"
            continue

        if M_START.search(stripped):
            mode = "m"
            continue

        if NEW_SUBSECTION.match(stripped) and stripped.startswith("**"):
            if re.match(r"\*\*[GSM\u5c64\u7e7e\u5c0d]", stripped) or \
               re.search(r"Tier|Anti-patterns|對齊", stripped):
                mode = None

        bullet_match = re.match(r"^\s*[-*]\s+", line)
        if bullet_match:
            if mode == "s":
                s_bullets.append((idx, line.rstrip()))
            elif mode == "m":
                m_bullets.append((idx, line.rstrip()))

    return s_bullets, m_bullets


def measure_context_pressure(section_lines: list[str]) -> int:
    """
    Count total characters in the S + M sections of an agent section.
    Used as a rough proxy for context pressure.
    """
    S_START = re.compile(r"\*\*S[（(]")
    M_START = re.compile(r"\*\*M[（(]")
    NEW_SUBSECTION = re.compile(r"^\*\*[A-Za-z\u4e00-\u9fff].*\*\*")
    HEADING = re.compile(r"^#{2,4} ")

    total_chars = 0
    mode = None

    for line in section_lines:
        stripped = line.strip()
        if HEADING.match(stripped):
            mode = None
            continue
        if S_START.search(stripped):
            mode = "sm"
            total_chars += len(line)
            continue
        if M_START.search(stripped):
            mode = "sm"
            total_chars += len(line)
            continue
        if NEW_SUBSECTION.match(stripped) and stripped.startswith("**"):
            if re.match(r"\*\*[GSM\u5c64\u7e7e\u5c0d]", stripped) or \
               re.search(r"Tier|Anti-patterns|對齊", stripped):
                mode = None
        if mode == "sm":
            total_chars += len(line)

    return total_chars


# ---------------------------------------------------------------------------
# Suggestion logic
# ---------------------------------------------------------------------------

def suggest_script_name(bullet_text: str, matched_suffix: str) -> str:
    """
    Derive a plausible script filename from the bullet text and the matched suffix.
    Strips common filler words and uses the suffix as the base.
    """
    return f"scripts/{matched_suffix}.py"


def find_deterministic_bullets(
    bullets: list[tuple[int, str]],
) -> list[tuple[int, str, str, str]]:
    """
    Scan bullet lines for deterministic patterns.

    Returns list of (line_idx, bullet_text, matched_pattern, suggested_script).
    """
    results = []
    seen_indices: set[int] = set()

    for idx, text in bullets:
        if idx in seen_indices:
            continue
        for pattern, script_suffix in DETERMINISTIC_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                results.append((idx, text.strip(), pattern, suggest_script_name(text, script_suffix)))
                seen_indices.add(idx)
                break  # One match per bullet is enough

    return results


# ---------------------------------------------------------------------------
# Main advisory logic
# ---------------------------------------------------------------------------

def analyze_file(file_path: Path, verbose: bool = False, quiet: bool = False) -> int:
    """
    Produce script extraction suggestions for the given OGSM file.

    Returns exit code: 0 (always — advisory only), 1 (file error).
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

    # Per-agent analysis
    per_agent_results = []

    for agent_name, section_lines in agent_sections:
        pressure_chars = measure_context_pressure(section_lines)
        s_bullets, m_bullets = extract_s_and_m_lines(section_lines)

        all_bullets = s_bullets + m_bullets
        suggestions = find_deterministic_bullets(all_bullets)

        total_bullets = len(all_bullets)
        ratio = (len(suggestions) / total_bullets * 100) if total_bullets > 0 else 0.0

        per_agent_results.append({
            "agent": agent_name,
            "pressure_chars": pressure_chars,
            "total_bullets": total_bullets,
            "suggestions": suggestions,
            "ratio": ratio,
        })

    total_agents = len(per_agent_results)
    agents_with_candidates = sum(1 for r in per_agent_results if r["suggestions"])
    total_suggestions = sum(len(r["suggestions"]) for r in per_agent_results)

    if quiet:
        print(f"Total suggestions: {total_suggestions} across {agents_with_candidates} agents")
        return 0

    print("Script Extraction Suggestions")
    print("=============================")
    print(f"File: {file_path}")
    print()
    print("Per-agent analysis:")

    for r in per_agent_results:
        pressure_k = r["pressure_chars"] / 1000
        print(f"  {r['agent']}")
        print(f"    Context pressure: {pressure_k:.1f} k-chars (S+M)")
        print(f"    Deterministic bullets found: {len(r['suggestions'])}")

        if r["suggestions"]:
            print("    Suggestions:")
            for i, (line_idx, text, pattern, script) in enumerate(r["suggestions"], 1):
                # Truncate long bullets for readability
                short_text = text[:80] + "..." if len(text) > 80 else text
                print(f"      {i}. \"{short_text}\" (pattern: {pattern!r})")
                print(f"         → consider {script}")

            est_pct = int(r["ratio"])
            print(f"    Estimated reduction: ~{est_pct}% of S+M bullets are script-candidates")
        else:
            print(
                "    No extraction candidates "
                "(this agent's work is judgment-heavy or purely narrative)"
            )

        print()

    print("Overall:")
    print(f"  Total agents analyzed: {total_agents}")
    print(f"  Agents with extraction candidates: {agents_with_candidates}")
    print(f"  Total suggestions: {total_suggestions}")

    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse CLI arguments and run advisory analysis."""
    parser = argparse.ArgumentParser(
        prog="suggest_script_extraction",
        description=(
            "Advisory report: scan OGSM agent S+M sections for deterministic-pattern "
            "bullets that are candidates for extraction into standalone scripts. "
            "Always exits 0 — this is a suggestion tool, not a gate."
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
        help="Show all bullets scanned, not just matches",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only totals summary",
    )

    args = parser.parse_args()

    if args.verbose and args.quiet:
        print("ERROR: --verbose and --quiet are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    exit_code = analyze_file(args.file, verbose=args.verbose, quiet=args.quiet)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
