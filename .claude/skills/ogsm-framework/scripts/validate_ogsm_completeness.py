#!/usr/bin/env python3
"""
validate_ogsm_completeness.py

Validate that every agent section in an OGSM plan document contains all
required structural components: G, S, M sections; audience keyword in G;
path+why bullets in S; adequate M bullet count; Tier 1 summary block;
Anti-patterns block with minimum items.

Exit codes:
    0 - all agents pass completeness checks
    1 - file not found or invalid format
    2 - completeness gaps detected
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

# Audience keywords that should appear in the G section
AUDIENCE_KEYWORDS = [
    "建築師", "architect", "project architect", "design architect",
    "contractor", "承包商", "業主", "owner", "educator", "教師",
]

# Path+Why connectors: bullet contains a method AND a reason/justification
PATH_WHY_CONNECTORS = [
    "—", "因為", "because", " for ", "讓", "所以", "since", "to ",
    "為了", "才能", "以便",
]

# Markers for Tier 1 summary sub-block
TIER1_MARKERS = [
    r"\*\*Tier 1 摘要",
    r"\*\*Tier 1 summary",
    r"\*\*Tier\s*1",
]

# Markers for Anti-patterns sub-block.
# These must match only actual section headings (bold markers at line start),
# NOT inline references like "觸發 Anti-pattern #1 時" inside M bullets.
# Use anchored patterns so they only trigger at the start of a line.
ANTIPATTERN_MARKERS = [
    r"^\*\*Anti-patterns 標準清單",
    r"^\*\*Anti-patterns",
    r"^\*\*anti-patterns",
    r"^\s{0,3}\*\*Anti-pattern",
]

# Anti-pattern bullet prefixes
ANTIPATTERN_BULLET_PATTERNS = [
    r"^\s*-\s+NOT:",
    r"^\s*-\s+不[要應]",
    r"^\s*-\s+避免",
]

# Minimum M bullet count threshold
MIN_M_BULLETS = 3


# ---------------------------------------------------------------------------
# Parsing helpers (same pattern as validate_s_to_m_coverage.py)
# ---------------------------------------------------------------------------

# Unicode ranges that cover common emoji characters used in agent headings
# (Miscellaneous Symbols and Pictographs, Emoticons, Transport, etc.)
EMOJI_UNICODE_RANGES = re.compile(
    "[\U0001F300-\U0001F9FF"   # Misc symbols, emoticons, transport, etc.
    "\U00002702-\U000027B0"    # Dingbats
    "\U0000FE00-\U0000FE0F"    # Variation Selectors
    "\U00002600-\U000026FF"    # Misc symbols
    "\U0001FA00-\U0001FA6F"    # Chess symbols, etc.
    "\U0001FA70-\U0001FAFF]"   # Symbols and Pictographs Extended-A
)


def is_agent_heading(heading_text: str) -> bool:
    """
    Return True if the heading looks like an actual agent section.

    Agent headings start with an emoji character, e.g.:
      👑 Commander (A君)
      🔍 Investigator A — Cases & Data

    Non-agent headings (document structure, gates, issues) do NOT start with emoji.
    This positive-match approach is more robust than a growing denylist.
    """
    stripped = heading_text.strip()
    if not stripped:
        return False
    # Check if the very first character is in a common emoji range
    first_char = stripped[0]
    if EMOJI_UNICODE_RANGES.match(first_char):
        return True
    # Also allow headings that match the older denylist-passed format (emoji not in
    # BMP ranges, e.g. some regional indicators) — fall through to denylist below.
    return False


def is_non_agent_heading(heading_text: str) -> bool:
    """Return True if a ### heading should be skipped (not an agent section)."""
    # Primary gate: only agent headings start with emoji
    if not is_agent_heading(heading_text):
        return True
    # Secondary: explicit denylist for edge cases
    for pattern in NON_AGENT_SECTION_PATTERNS:
        if re.search(pattern, heading_text, re.IGNORECASE):
            return True
    return False


def split_into_agent_sections(lines: list[str]) -> list[tuple[str, list[str]]]:
    """
    Split document lines into agent sections.

    Returns a list of (agent_name, section_lines) tuples.
    Agent sections start at '### ' headings that pass the denylist check.
    Sections end at the next '### ' or '## ' heading.
    """
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


def extract_subsections(section_lines: list[str]) -> dict[str, str]:
    """
    Extract named subsections from an agent section.

    Returns a dict with keys: 'g', 's', 'm', 'tier1', 'antipatterns', 'full'.
    Each value is the raw text of that subsection.
    """
    G_START = re.compile(r"\*\*G[（(]")
    S_START = re.compile(r"\*\*S[（(]")
    M_START = re.compile(r"\*\*M[（(]")
    TIER1_START = re.compile("|".join(TIER1_MARKERS), re.MULTILINE)
    # ANTIPATTERN_MARKERS are anchored to line start (^) to prevent false matches
    # on inline references like "- 觸發 Anti-pattern #1 時..." inside M bullets.
    ANTI_START = re.compile("|".join(ANTIPATTERN_MARKERS), re.MULTILINE)
    NEW_SUBSECTION = re.compile(r"^\*\*[A-Za-z\u4e00-\u9fff].*\*\*")
    HEADING = re.compile(r"^#{2,4} ")

    g_lines: list[str] = []
    s_lines: list[str] = []
    m_lines: list[str] = []
    tier1_lines: list[str] = []
    anti_lines: list[str] = []

    mode = None  # None | 'g' | 's' | 'm' | 'tier1' | 'anti'

    for line in section_lines:
        stripped = line.strip()

        if HEADING.match(stripped):
            mode = None
            continue

        if G_START.search(stripped):
            mode = "g"
            g_lines.append(line)
            continue

        if S_START.search(stripped):
            mode = "s"
            s_lines.append(line)
            continue

        if M_START.search(stripped):
            mode = "m"
            m_lines.append(line)
            continue

        if TIER1_START.search(stripped):
            mode = "tier1"
            tier1_lines.append(line)
            continue

        if ANTI_START.search(stripped):
            mode = "anti"
            anti_lines.append(line)
            continue

        # Detect new subsection boundary.
        # Use anchored "Anti-patterns" (plural, bold heading) to avoid matching
        # inline "Anti-pattern" references (e.g. "- NOT: 觸發 Anti-pattern #1 時...")
        # that can appear as list bullets inside the M section.
        if NEW_SUBSECTION.match(stripped) and stripped.startswith("**"):
            if re.match(r"\*\*[GSM\u5c64\u7e7e\u5c0d\u5c0d\u9f4a]", stripped) or \
               re.search(r"Tier|\*\*Anti-patterns|對齊", stripped):
                mode = None

        if mode == "g":
            g_lines.append(line)
        elif mode == "s":
            s_lines.append(line)
        elif mode == "m":
            m_lines.append(line)
        elif mode == "tier1":
            tier1_lines.append(line)
        elif mode == "anti":
            anti_lines.append(line)

    return {
        "g": "\n".join(g_lines),
        "s": "\n".join(s_lines),
        "m": "\n".join(m_lines),
        "tier1": "\n".join(tier1_lines),
        "antipatterns": "\n".join(anti_lines),
        "full": "\n".join(section_lines),
    }


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

def check_has_section(text: str, label: str) -> tuple[bool, str]:
    """Check whether a section exists (non-empty after stripping)."""
    exists = bool(text.strip())
    if exists:
        return True, f"{label}: present"
    return False, f"{label}: MISSING"


def check_audience_in_g(g_text: str) -> tuple[bool, str]:
    """Check whether G section contains an audience keyword."""
    g_lower = g_text.lower()
    for kw in AUDIENCE_KEYWORDS:
        if kw.lower() in g_lower:
            return True, f"Audience keyword in G: '{kw}'"
    return False, "Audience keyword in G: MISSING (no audience keyword found)"


def check_path_why_in_s(s_text: str) -> tuple[bool, str, int]:
    """
    Check whether S section has at least one bullet with path+why pattern.
    Returns (pass, message, matching_count).
    """
    bullet_pattern = re.compile(r"^\s*[-*]\s+(.+)$", re.MULTILINE)
    bullets = bullet_pattern.findall(s_text)
    matching = 0
    for bullet in bullets:
        for connector in PATH_WHY_CONNECTORS:
            if connector in bullet:
                matching += 1
                break
    if matching > 0:
        return True, f"Path+Why bullets in S: {matching} found", matching
    return False, "Path+Why bullets in S: MISSING (no bullet with method+reason connector)", 0


def count_m_bullets(m_text: str) -> int:
    """Count bullet items in the M section."""
    bullet_pattern = re.compile(r"^\s*[-*]\s+", re.MULTILINE)
    return len(bullet_pattern.findall(m_text))


def check_tier1_block(full_text: str) -> tuple[bool, str]:
    """Check whether the Tier 1 summary sub-block exists anywhere in the agent section."""
    pattern = re.compile("|".join(TIER1_MARKERS), re.IGNORECASE)
    if pattern.search(full_text):
        return True, "Tier 1 summary block: present"
    return False, "Tier 1 summary block: MISSING"


def check_antipatterns_block(full_text: str) -> tuple[bool, str]:
    """Check whether Anti-patterns sub-block exists in the agent section.
    re.MULTILINE is required so that ^ anchors in ANTIPATTERN_MARKERS match
    the start of each line, not just the start of the whole string.
    """
    pattern = re.compile("|".join(ANTIPATTERN_MARKERS), re.IGNORECASE | re.MULTILINE)
    if pattern.search(full_text):
        return True, "Anti-patterns block: present"
    return False, "Anti-patterns block: MISSING"


def count_antipattern_items(antipatterns_text: str, full_text: str) -> int:
    """
    Count Anti-pattern items.
    Looks for bullets starting with 'NOT:' or similar negation patterns.
    Falls back to counting any bullets in the antipatterns section.
    """
    # First try strict NOT: pattern across full text (common in this doc)
    strict = re.compile(r"^\s*-\s+NOT:", re.MULTILINE)
    count = len(strict.findall(full_text))
    if count > 0:
        return count

    # Fallback: count any bullets in the antipatterns sub-section
    if antipatterns_text.strip():
        bullet_pattern = re.compile(r"^\s*[-*]\s+", re.MULTILINE)
        return len(bullet_pattern.findall(antipatterns_text))

    return 0


# ---------------------------------------------------------------------------
# Per-agent validation
# ---------------------------------------------------------------------------

def validate_agent(agent_name: str, section_lines: list[str]) -> dict:
    """
    Run all completeness checks for one agent.

    Returns a dict with keys:
        'agent': str
        'pass': bool
        'checks': list of (passed: bool, message: str)
        'gaps': list of str (fix suggestions)
    """
    subs = extract_subsections(section_lines)

    checks = []
    gaps = []

    # G section present
    g_ok, g_msg = check_has_section(subs["g"], "G section")
    checks.append((g_ok, g_msg))
    if not g_ok:
        gaps.append("Add a **G（...）** section describing the agent's goal tied back to O.")

    # S section present
    s_ok, s_msg = check_has_section(subs["s"], "S section")
    checks.append((s_ok, s_msg))
    if not s_ok:
        gaps.append("Add a **S（...）** section with strategy bullets.")

    # M section present
    m_ok, m_msg = check_has_section(subs["m"], "M section")
    checks.append((m_ok, m_msg))
    if not m_ok:
        gaps.append("Add a **M（...）** section with measurable verification bullets.")

    # Audience keyword in G
    aud_ok, aud_msg = check_audience_in_g(subs["g"])
    checks.append((aud_ok, aud_msg))
    if not aud_ok:
        gaps.append(
            "G section should reference the target audience "
            "(e.g. '建築師', 'Project Architect', 'architect')."
        )

    # Path+Why in S
    pw_ok, pw_msg, pw_count = check_path_why_in_s(subs["s"])
    checks.append((pw_ok, pw_msg))
    if not pw_ok:
        gaps.append(
            "S section should have ≥ 1 bullet with method + reason "
            "(connector: '—', '因為', 'because', 'for', '讓', etc.)."
        )

    # M bullet count
    m_bullet_count = count_m_bullets(subs["m"])
    m_bullets_ok = m_bullet_count >= MIN_M_BULLETS
    checks.append((
        m_bullets_ok,
        f"M ≥ {MIN_M_BULLETS} bullets: {'✓' if m_bullets_ok else '✗'} ({m_bullet_count} bullets)"
    ))
    if not m_bullets_ok:
        gaps.append(
            f"M section has only {m_bullet_count} bullet(s). "
            f"Add ≥ {MIN_M_BULLETS} measurable verification bullets."
        )

    # Tier 1 summary
    t1_ok, t1_msg = check_tier1_block(subs["full"])
    checks.append((t1_ok, t1_msg))
    if not t1_ok:
        gaps.append(
            "Add a **Tier 1 摘要（Direction Seed 必帶）** sub-block with G/S/M one-liners, "
            "Skill commands, Model commands."
        )

    # Anti-patterns sub-block
    anti_ok, anti_msg = check_antipatterns_block(subs["full"])
    checks.append((anti_ok, anti_msg))
    if not anti_ok:
        gaps.append(
            "Add an **Anti-patterns 標準清單** sub-block with ≥ 3 "
            "'NOT: X — 應該: Y' items."
        )

    # Anti-patterns item count (only check if block exists)
    if anti_ok:
        anti_count = count_antipattern_items(subs["antipatterns"], subs["full"])
        anti_count_ok = anti_count >= 3
        checks.append((
            anti_count_ok,
            f"Anti-patterns ≥ 3 items: {'✓' if anti_count_ok else '✗'} ({anti_count} items)"
        ))
        if not anti_count_ok:
            gaps.append(
                f"Anti-patterns block has only {anti_count} item(s). "
                "Add ≥ 3 'NOT: X — 應該: Y' bullets."
            )

    passed = all(ok for ok, _ in checks)
    return {
        "agent": agent_name,
        "pass": passed,
        "checks": checks,
        "gaps": gaps,
        "m_bullet_count": m_bullet_count,
    }


# ---------------------------------------------------------------------------
# Main validation logic
# ---------------------------------------------------------------------------

def validate_file(file_path: Path, verbose: bool = False, quiet: bool = False) -> int:
    """
    Run OGSM completeness validation on the given file.

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

    results = [validate_agent(name, sec_lines) for name, sec_lines in agent_sections]

    complete = [r for r in results if r["pass"]]
    with_gaps = [r for r in results if not r["pass"]]
    total_gaps = sum(len(r["gaps"]) for r in with_gaps)

    pass_fail = "PASS" if not with_gaps else f"FAIL ({total_gaps} gap{'s' if total_gaps != 1 else ''})"

    if quiet:
        print(f"Result: {pass_fail}")
        return 0 if not with_gaps else 2

    # Full report
    print("OGSM Completeness Report")
    print("========================")
    print(f"File: {file_path}")
    print(f"Total agents: {len(results)}")
    print()
    print("Summary:")
    print(f"  - Fully complete agents: {len(complete)}")
    print(f"  - Agents with gaps: {len(with_gaps)}")
    print()
    print("Details per agent:")

    for r in results:
        status = "[PASS]" if r["pass"] else "[FAIL]"
        print(f"  {status} {r['agent']}")

        if verbose or not r["pass"]:
            for ok, msg in r["checks"]:
                symbol = "✓" if ok else "✗"
                print(f"    {symbol} {msg}")

        if r["gaps"]:
            for gap in r["gaps"]:
                print(f"    Missing/Fix: {gap}")

        if r["pass"] and not verbose:
            # Compact summary for passing agents
            g_ok = any("G section" in m and ok for ok, m in r["checks"])
            s_ok = any("S section" in m and ok for ok, m in r["checks"])
            m_ok = any("M section" in m and ok for ok, m in r["checks"])
            print(
                f"    G: {'✓' if g_ok else '✗'} / S: {'✓' if s_ok else '✗'} / "
                f"M: {'✓' if m_ok else '✗'} / "
                f"M bullets: {r['m_bullet_count']}"
            )

    print()
    print(f"Result: {pass_fail}")
    return 0 if not with_gaps else 2


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse CLI arguments and run validation."""
    parser = argparse.ArgumentParser(
        prog="validate_ogsm_completeness",
        description=(
            "Validate that every agent section in an OGSM plan document contains "
            "all required structural components: G/S/M sections, audience keyword, "
            "path+why bullets, M bullet count, Tier 1 summary, and Anti-patterns block."
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
