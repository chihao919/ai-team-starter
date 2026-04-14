#!/usr/bin/env python3
"""
check_skill_architecture.py

Validate that an OGSM plan document follows the 3-layer skill architecture:
  Layer 1 (Tier 1): lightweight always-loaded summary < ~200 words
  Layer 2 (Tier 2): full S/M content referenced by path or anchor
  Layer 3: Skill Invocation Map / Model Invocation Map at document level

Checks:
  Document-level:
    - Skill Invocation Map section present
    - Model Invocation Map section present
    - Brief Layering section present

  Per-agent:
    - Has Tier 1 summary
    - Tier 1 summary is < ~200 words (heuristic for lightweight briefing)
    - Has skill references in S (via /skill-name pattern)
    - Tier 2 content exists (S/M section is substantial)

Exit codes:
    0 - all checks pass
    1 - file not found or invalid format
    2 - architecture gaps detected
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

# Tier 1 word count threshold (heuristic)
TIER1_WORD_LIMIT = 200

# Minimum Tier 2 (S+M) character count to be considered "substantial"
TIER2_MIN_CHARS = 300

# Skill invocation pattern: /skill-name (must have at least one hyphen)
SKILL_INVOCATION_PATTERN = re.compile(r"/([a-z][a-z0-9]+-[a-z0-9-]+)", re.IGNORECASE)

# Document-level section markers
SKILL_MAP_PATTERN = re.compile(r"^## .*Skill Invocation Map", re.IGNORECASE)
MODEL_MAP_PATTERN = re.compile(r"^## .*Model Invocation Map", re.IGNORECASE)
BRIEF_LAYERING_PATTERN = re.compile(r"^## .*Brief Layering", re.IGNORECASE)

# Tier 1 sub-block markers
TIER1_START_PATTERN = re.compile(
    r"\*\*Tier\s*1\s*(摘要|summary)", re.IGNORECASE
)

# Markers for Tier 2 (S and M sections)
S_START = re.compile(r"\*\*S[（(]")
M_START = re.compile(r"\*\*M[（(]")


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


# ---------------------------------------------------------------------------
# Document-level checks
# ---------------------------------------------------------------------------

def check_document_sections(lines: list[str]) -> dict[str, bool]:
    """
    Check whether the document contains the required top-level ## sections.

    Returns a dict: {'skill_map': bool, 'model_map': bool, 'brief_layering': bool}
    """
    has_skill_map = False
    has_model_map = False
    has_brief_layering = False

    for line in lines:
        if SKILL_MAP_PATTERN.match(line):
            has_skill_map = True
        if MODEL_MAP_PATTERN.match(line):
            has_model_map = True
        if BRIEF_LAYERING_PATTERN.match(line):
            has_brief_layering = True

    return {
        "skill_map": has_skill_map,
        "model_map": has_model_map,
        "brief_layering": has_brief_layering,
    }


# ---------------------------------------------------------------------------
# Per-agent checks
# ---------------------------------------------------------------------------

def extract_tier1_text(section_lines: list[str]) -> str:
    """
    Extract the Tier 1 summary sub-block text from an agent section.
    Tier 1 starts at the Tier 1 heading and ends at the next ** heading or ## heading.
    """
    NEW_SUBSECTION = re.compile(r"^\*\*[A-Za-z\u4e00-\u9fff].*\*\*")
    HEADING = re.compile(r"^#{2,4} ")

    tier1_lines: list[str] = []
    in_tier1 = False

    for line in section_lines:
        stripped = line.strip()

        if HEADING.match(stripped):
            if in_tier1:
                break
            continue

        if TIER1_START_PATTERN.search(stripped):
            in_tier1 = True
            tier1_lines.append(line)
            continue

        if in_tier1:
            # Detect boundary: another bold OGSM heading
            if NEW_SUBSECTION.match(stripped) and stripped.startswith("**"):
                if re.match(r"\*\*[GSM\u5c64\u7e7e\u5c0d]", stripped) or \
                   re.search(r"Tier|Anti-patterns|對齊", stripped):
                    # Only break if it's NOT another Tier section we're already in
                    if not TIER1_START_PATTERN.search(stripped):
                        break
            tier1_lines.append(line)

    return "\n".join(tier1_lines)


def count_words(text: str) -> int:
    """Count words in text (split on whitespace)."""
    return len(text.split())


def extract_sm_text(section_lines: list[str]) -> str:
    """Extract combined S + M section text from an agent section."""
    NEW_SUBSECTION = re.compile(r"^\*\*[A-Za-z\u4e00-\u9fff].*\*\*")
    HEADING = re.compile(r"^#{2,4} ")

    sm_lines: list[str] = []
    mode = None

    for line in section_lines:
        stripped = line.strip()

        if HEADING.match(stripped):
            mode = None
            continue

        if S_START.search(stripped):
            mode = "sm"
            sm_lines.append(line)
            continue

        if M_START.search(stripped):
            mode = "sm"
            sm_lines.append(line)
            continue

        if NEW_SUBSECTION.match(stripped) and stripped.startswith("**"):
            if re.match(r"\*\*[GSM\u5c64\u7e7e\u5c0d]", stripped) or \
               re.search(r"Tier|Anti-patterns|對齊", stripped):
                # Only exit sm mode if it's not S or M starting
                if not S_START.search(stripped) and not M_START.search(stripped):
                    mode = None

        if mode == "sm":
            sm_lines.append(line)

    return "\n".join(sm_lines)


def find_skill_refs_in_s(section_lines: list[str]) -> list[str]:
    """
    Find skill invocations (/skill-name) in the S section of an agent.
    Returns list of skill names found.
    """
    NEW_SUBSECTION = re.compile(r"^\*\*[A-Za-z\u4e00-\u9fff].*\*\*")
    HEADING = re.compile(r"^#{2,4} ")

    skill_refs: list[str] = []
    seen: set[str] = set()
    mode = None

    for line in section_lines:
        stripped = line.strip()

        if HEADING.match(stripped):
            mode = None
            continue

        if S_START.search(stripped):
            mode = "s"
            # Also scan the heading line itself for embedded skill refs
            for m in SKILL_INVOCATION_PATTERN.finditer(line):
                if m.group(1) not in seen:
                    seen.add(m.group(1))
                    skill_refs.append(m.group(1))
            continue

        if M_START.search(stripped):
            mode = None
            continue

        if NEW_SUBSECTION.match(stripped) and stripped.startswith("**"):
            if re.match(r"\*\*[GSM\u5c64\u7e7e\u5c0d]", stripped) or \
               re.search(r"Tier|Anti-patterns|對齊", stripped):
                if not S_START.search(stripped):
                    mode = None

        if mode == "s":
            for m in SKILL_INVOCATION_PATTERN.finditer(line):
                if m.group(1) not in seen:
                    seen.add(m.group(1))
                    skill_refs.append(m.group(1))

    return skill_refs


def validate_agent_architecture(agent_name: str, section_lines: list[str]) -> dict:
    """
    Run 3-layer architecture checks for one agent.

    Returns a dict with: agent, pass, checks (list of (bool, str)), gaps (list of str).
    """
    checks = []
    gaps = []

    # Check 1: Tier 1 summary exists
    tier1_text = extract_tier1_text(section_lines)
    has_tier1 = bool(tier1_text.strip())
    checks.append((has_tier1, "Tier 1 summary block: " + ("present" if has_tier1 else "MISSING")))
    if not has_tier1:
        gaps.append(
            "Add a **Tier 1 摘要（Direction Seed 必帶）** sub-block with G/S/M one-liners, "
            "Skill commands, Model commands, Anti-patterns reference."
        )

    # Check 2: Tier 1 word count within limit
    if has_tier1:
        tier1_words = count_words(tier1_text)
        tier1_slim = tier1_words <= TIER1_WORD_LIMIT
        checks.append((
            tier1_slim,
            f"Tier 1 word count: {tier1_words} words "
            f"({'within limit' if tier1_slim else f'exceeds ~{TIER1_WORD_LIMIT} word heuristic'})"
        ))
        if not tier1_slim:
            gaps.append(
                f"Tier 1 summary is {tier1_words} words — exceeds ~{TIER1_WORD_LIMIT} word heuristic. "
                "Move detailed rationale and background to Tier 2 (S/M). "
                "Keep only immediate action triggers and decision points in Tier 1."
            )

    # Check 3: Skill references in S
    skill_refs = find_skill_refs_in_s(section_lines)
    has_skill_refs = len(skill_refs) > 0
    # Note: no skill refs is NOT necessarily a failure — some agents (e.g. Commander)
    # don't invoke skills directly. We flag it as info only.
    checks.append((
        True,  # always pass — informational
        f"Skill references in S: {len(skill_refs)} found"
        + (f" ({', '.join(skill_refs[:3])}{'...' if len(skill_refs) > 3 else ''})"
           if skill_refs else " (none — judgment-only agent or Commander role)")
    ))

    # Check 4: Tier 2 (S+M) content is substantial
    sm_text = extract_sm_text(section_lines)
    sm_chars = len(sm_text.strip())
    has_tier2 = sm_chars >= TIER2_MIN_CHARS
    checks.append((
        has_tier2,
        f"Tier 2 content (S+M): {sm_chars} chars "
        f"({'substantial' if has_tier2 else f'too thin — < {TIER2_MIN_CHARS} chars'})"
    ))
    if not has_tier2:
        gaps.append(
            f"S+M content is only {sm_chars} characters. "
            "Expand S with concrete strategy bullets (method + reason). "
            "Expand M with measurable verification items."
        )

    passed = all(ok for ok, _ in checks)
    return {
        "agent": agent_name,
        "pass": passed,
        "checks": checks,
        "gaps": gaps,
    }


# ---------------------------------------------------------------------------
# Main validation logic
# ---------------------------------------------------------------------------

def validate_file(file_path: Path, verbose: bool = False, quiet: bool = False) -> int:
    """
    Run 3-layer skill architecture check on the given OGSM file.

    Returns exit code: 0 (pass), 1 (file error), 2 (gaps found).
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

    # Document-level checks
    doc_checks = check_document_sections(lines)

    # Per-agent checks
    agent_results = [
        validate_agent_architecture(name, sec_lines)
        for name, sec_lines in agent_sections
    ]

    # Determine overall pass/fail
    doc_all_pass = all(doc_checks.values())
    agent_with_gaps = [r for r in agent_results if not r["pass"]]
    total_gaps = sum(len(r["gaps"]) for r in agent_with_gaps)
    doc_gaps = sum(1 for v in doc_checks.values() if not v)
    all_pass = doc_all_pass and not agent_with_gaps

    overall_gaps = total_gaps + doc_gaps
    pass_fail = (
        "PASS"
        if all_pass
        else f"FAIL ({overall_gaps} gap{'s' if overall_gaps != 1 else ''})"
    )

    if quiet:
        print(f"Result: {pass_fail}")
        return 0 if all_pass else 2

    # Full report
    print("3-Layer Skill Architecture Check")
    print("=================================")
    print(f"File: {file_path}")
    print()
    print("Document-level checks:")
    for key, present in [
        ("skill_map", "Skill Invocation Map section"),
        ("model_map", "Model Invocation Map section"),
        ("brief_layering", "Brief Layering section"),
    ]:
        symbol = "✓" if doc_checks[key] else "✗"
        print(f"  {symbol} {present}: {'present' if doc_checks[key] else 'MISSING'}")

    print()
    print("Per-agent checks:")

    for r in agent_results:
        status = "[PASS]" if r["pass"] else "[FAIL]"
        print(f"  {status} {r['agent']}")

        if verbose or not r["pass"]:
            for ok, msg in r["checks"]:
                symbol = "✓" if ok else "✗"
                print(f"    {symbol} {msg}")

        if r["gaps"]:
            for gap in r["gaps"]:
                print(f"    Fix: {gap}")

    print()
    print(f"Result: {pass_fail}")
    return 0 if all_pass else 2


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse CLI arguments and run architecture check."""
    parser = argparse.ArgumentParser(
        prog="check_skill_architecture",
        description=(
            "Validate that an OGSM plan document follows the 3-layer skill architecture: "
            "Tier 1 lightweight summary, Tier 2 full S/M content, and document-level "
            "Skill/Model Invocation Maps."
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
        help="Print all check results including passing agents",
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
