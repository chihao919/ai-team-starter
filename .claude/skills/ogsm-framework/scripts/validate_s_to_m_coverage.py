#!/usr/bin/env python3
"""
validate_s_to_m_coverage.py

Validate that every OGSM plan document meets the S-to-M coverage rule:
every agent S section that invokes a skill or model must have a matching
M section bullet that verifies the invocation succeeded.

Exit codes:
    0 - all S-skill/S-model invocations have matching M verification
    1 - file not found or invalid format
    2 - S-to-M gaps detected
"""

import argparse
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Section headings that are NOT agent sections (denylist)
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

# Verification indicator keywords (must appear in M bullet alongside skill/model name)
VERIFICATION_KEYWORDS = [
    "驗證", "verify", "確認", "抽檢", "記錄", "附", "appended",
    "check", "audit", "確認", "validated", "confirmed",
]

# Skill invocation patterns
SKILL_PATTERNS = [
    (r"/content-scout(?:\s+\S+)*", "content-scout"),
    (r"/post-test-designer(?:\s+\S+)*", "post-test-designer"),
    (r"/aia-rewrite(?:\s+--\S+)*", "aia-rewrite"),
    (r"/research-topic(?:\s+\S+)*", "research-topic"),
    (r"/new-course(?:\s+\S+)*", "new-course"),
    # Generic skill pattern — requires at least one hyphen to avoid false positives
    # like /CSI /submittal /SPC from body text (e.g. "CSC/CSI", "RFI/submittal")
    (r"/([a-z][a-z0-9]+-[a-z0-9-]+)", None),
]

# Model invocation patterns  (regex, canonical_name)
MODEL_PATTERNS = [
    (r"gemini\s+-m\s+gemini-2\.5-flash", "Gemini Flash"),
    (r"gemini\s+-m\s+gemini-2\.5-pro", "Gemini 2.5 Pro"),
    (r"codex\s+exec", "Codex"),
    (r"\bGemini Flash\b", "Gemini Flash"),
    (r"\bGemini 2\.5 Pro\b", "Gemini 2.5 Pro"),
    (r"\bGemini 2\.5 Flash\b", "Gemini Flash"),
    (r"\bCodex\b", "Codex"),
]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def is_non_agent_heading(heading_text: str) -> bool:
    """Return True if a ### heading should be skipped (not an agent section)."""
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
        # Check for ## heading (section boundary, always ends current agent)
        if re.match(r"^## ", line):
            if current_name is not None:
                agents.append((current_name, current_lines))
                current_name = None
                current_lines = []
            continue

        # Check for ### heading
        if re.match(r"^### ", line):
            # Save previous agent section if any
            if current_name is not None:
                agents.append((current_name, current_lines))
                current_name = None
                current_lines = []

            # Extract the heading text (strip "### " prefix)
            heading_text = line[4:].strip()

            if is_non_agent_heading(heading_text):
                # Skip this section
                continue

            current_name = heading_text
            current_lines = [line]
            continue

        # Regular line: accumulate into current agent section
        if current_name is not None:
            current_lines.append(line)

    # Flush the last section
    if current_name is not None:
        agents.append((current_name, current_lines))

    return agents


def extract_s_and_m_subsections(section_lines: list[str]) -> tuple[str, str]:
    """
    Extract the S and M subsection text from an agent's lines.

    S starts at a line containing **S（...）** or **S (...)**
    M starts at a line containing **M（...）** or **M (...)**
    Both end at next **X（...）** heading, ### or ## heading.

    Additionally, the Tier 1 summary lines for "Skill commands" and "Model commands"
    are appended to the S text, because in v4+ OGSM plans these lines represent the
    official embedded invocation registry for the agent (per Principle 7).

    Returns (s_text, m_text) as raw strings.
    """
    S_START = re.compile(r"\*\*S[（(]")
    M_START = re.compile(r"\*\*M[（(]")
    # Tier 1 Skill commands / Model commands lines
    TIER1_SKILL_CMD = re.compile(r"\*\*Skill commands\*\*")
    TIER1_MODEL_CMD = re.compile(r"\*\*Model commands\*\*")
    # Any bold heading that signals a new sub-section (Tier 1, G, S, M, Anti-patterns, etc.)
    NEW_SUBSECTION = re.compile(r"^\*\*[A-Za-z\u4e00-\u9fff].*\*\*")
    HEADING = re.compile(r"^#{2,4} ")

    s_lines: list[str] = []
    m_lines: list[str] = []
    tier1_skill_lines: list[str] = []

    mode = None  # None | 's' | 'm'

    for line in section_lines:
        stripped = line.strip()

        # Detect section boundaries
        if HEADING.match(stripped):
            mode = None
            continue

        # Tier 1 Skill commands / Model commands → treat as part of S for invocation detection
        if TIER1_SKILL_CMD.search(stripped) or TIER1_MODEL_CMD.search(stripped):
            tier1_skill_lines.append(line)
            continue

        if S_START.search(stripped):
            mode = "s"
            s_lines.append(line)
            continue

        if M_START.search(stripped):
            mode = "m"
            m_lines.append(line)
            continue

        # Detect new subsection heading (e.g., **G（...）**, **Anti-patterns...**, **Tier 1...**, **對齊 O...** )
        if NEW_SUBSECTION.match(stripped) and stripped.startswith("**"):
            # Only reset if this looks like a top-level OGSM label (G/S/M/Tier/Anti)
            if re.match(r"\*\*[GSM\u5c64\u7e7e\u5c0d]", stripped) or re.search(r"Tier|Anti-patterns|對齊", stripped):
                mode = None

        if mode == "s":
            s_lines.append(line)
        elif mode == "m":
            m_lines.append(line)

    # Append Tier 1 Skill/Model command lines to S for invocation scanning
    combined_s = "\n".join(s_lines + tier1_skill_lines)
    return combined_s, "\n".join(m_lines)


def extract_skill_invocations(text: str) -> list[str]:
    """
    Extract unique skill names from text.

    Returns a list of canonical skill names (e.g., 'content-scout', 'post-test-designer').
    """
    found: list[str] = []
    seen: set[str] = set()

    for pattern, canonical in SKILL_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if canonical is not None:
                name = canonical
            else:
                # Generic pattern: use the captured group
                name = match.group(1)

            if name not in seen:
                seen.add(name)
                found.append(name)

    return found


def extract_model_invocations(text: str) -> list[str]:
    """
    Extract unique model names from text.

    Returns a list of canonical model names (e.g., 'Gemini Flash', 'Codex').
    """
    found: list[str] = []
    seen: set[str] = set()

    for pattern, canonical in MODEL_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            name = canonical
            if name not in seen:
                seen.add(name)
                found.append(name)

    return found


def has_verification_in_m(m_text: str, invocation_name: str) -> bool:
    """
    Return True if m_text contains at least one bullet/line that:
    1. Mentions invocation_name (case-insensitive substring)
    2. Contains at least one verification indicator keyword
    """
    # Build a search name — strip leading '/' if present for flexible matching
    search_name = invocation_name.lstrip("/").lower()

    for line in m_text.splitlines():
        line_lower = line.lower()
        if search_name not in line_lower:
            continue
        # Check for at least one verification keyword
        for keyword in VERIFICATION_KEYWORDS:
            if keyword.lower() in line_lower:
                return True

    return False


# ---------------------------------------------------------------------------
# Main validation logic
# ---------------------------------------------------------------------------

def validate_file(
    file_path: Path,
    verbose: bool = False,
    quiet: bool = False,
) -> int:
    """
    Run S-to-M coverage validation on the given OGSM plan file.

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

    # Basic format check: must have at least one ### heading
    if not any(line.startswith("### ") for line in lines):
        # G-002 fix: no ### headings means 0 parseable agents — treat as FAIL, not format error
        print("")
        print("FAIL: No parseable agents found in file.")
        print("This may indicate a format mismatch (e.g., single-agent spec file")
        print("with '## G — Goal' headers vs multi-agent OGSM with '### [emoji] Name'")
        print("+ '**G（...)**' bold sub-labels expected by this validator).")
        return 2

    agent_sections = split_into_agent_sections(lines)

    if not agent_sections:
        # G-002 fix: ### headings present but none qualify as agent sections
        print("")
        print("FAIL: No parseable agents found in file.")
        print("This may indicate a format mismatch (e.g., single-agent spec file")
        print("with '## G — Goal' headers vs multi-agent OGSM with '### [emoji] Name'")
        print("+ '**G（...)**' bold sub-labels expected by this validator).")
        return 2

    # Per-agent results
    # Each entry: (agent_name, invocations, gaps)
    results: list[dict] = []

    for agent_name, section_lines in agent_sections:
        s_text, m_text = extract_s_and_m_subsections(section_lines)

        skill_invocations = extract_skill_invocations(s_text)
        model_invocations = extract_model_invocations(s_text)
        all_invocations = skill_invocations + model_invocations

        if not all_invocations:
            # No invocations in S — skip this agent
            if verbose:
                print(f"  [skip] {agent_name}: no skill/model invocations in S")
            continue

        gaps: list[str] = []
        verified: list[str] = []

        for inv in all_invocations:
            ok = has_verification_in_m(m_text, inv)
            if ok:
                verified.append(inv)
                if verbose:
                    print(f"  [ok] {agent_name}: '{inv}' verified in M")
            else:
                gaps.append(inv)
                if verbose:
                    print(f"  [GAP] {agent_name}: '{inv}' NOT verified in M")

        results.append({
            "agent": agent_name,
            "invocations": all_invocations,
            "verified": verified,
            "gaps": gaps,
        })

    # ----- Build report -----
    total_agents_found = len(agent_sections)
    agents_with_invocations = len(results)

    # G-002 fix: a document with agent sections but zero parseable skill/model
    # invocations across ALL agents is suspicious — likely a format mismatch or
    # a truly empty spec. Treat as FAIL rather than silent PASS so the author is
    # forced to confirm the document is intentionally invocation-free.
    if agents_with_invocations == 0:
        print("FAIL: No parseable agents found in file.")
        print("This may indicate format mismatch (e.g., single-agent spec vs multi-agent OGSM).")
        return 2
    complete_agents = [r for r in results if not r["gaps"]]
    gap_agents = [r for r in results if r["gaps"]]
    total_gaps = sum(len(r["gaps"]) for r in results)

    pass_fail = "PASS" if total_gaps == 0 else f"FAIL ({total_gaps} gap{'s' if total_gaps != 1 else ''})"

    if quiet:
        print(f"Result: {pass_fail}")
        return 0 if total_gaps == 0 else 2

    # Full report
    print("OGSM S-to-M Coverage Report")
    print("============================")
    print(f"File: {file_path}")
    print(f"Total agents found: {total_agents_found}")
    print(f"Agents with skill/model invocations in S: {agents_with_invocations}")
    print()
    print("Summary:")
    print(f"  - Complete (S invocations matched in M): {len(complete_agents)} agents")
    print(f"  - GAPS found: {len(gap_agents)} agents")
    print()

    if results:
        print("Details:")
        for r in results:
            agent = r["agent"]
            invocations = r["invocations"]
            gaps = r["gaps"]

            if not gaps:
                inv_str = ", ".join(invocations)
                print(f"  [PASS] {agent}")
                print(f"    S invocations: [{inv_str}]")
                print(f"    M verification: all found")
            else:
                inv_str = ", ".join(invocations)
                print(f"  [FAIL] {agent}")
                print(f"    S invocations: [{inv_str}]")
                for gap in gaps:
                    print(f"    M verification: MISSING for '{gap}'")
                    print(f"    Suggested fix: Add M bullet mentioning '{gap}' and a verification keyword (e.g. 驗證, verify, 確認, check).")
        print()

    print(f"Result: {pass_fail}")
    return 0 if total_gaps == 0 else 2


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse CLI arguments and run validation."""
    parser = argparse.ArgumentParser(
        prog="validate_s_to_m_coverage",
        description=(
            "Validate that every OGSM plan agent's S section skill/model invocations "
            "have matching M verification bullets."
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
        help="Print every S invocation checked (useful for debugging)",
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
