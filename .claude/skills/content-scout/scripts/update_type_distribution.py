#!/usr/bin/env python3
"""
update_type_distribution.py — Recount type distribution in content-scout queue.

Reads a .content-scout-queue.md file, counts each of the 8 valid candidate
types from the candidate entries, then rewrites the ## Type Distribution
section at the top of the file with the current counts.

Also prints an alert to stderr if any type has >= 3 entries while another
type has 0 entries (imbalance signal).

Exit codes:
  0 — success (distribution section updated)
  1 — file not found or unreadable
  2 — unexpected parse error

Usage:
  python update_type_distribution.py door-site/.content-scout-queue.md
  python update_type_distribution.py --help
"""

import argparse
import re
import sys
from pathlib import Path

VALID_TYPES = [
    "regulatory-explainer",
    "case-study",
    "product-comparison",
    "statistical-insight",
    "cost-comparison",
    "code-conflict",
    "scenario-guide",
    "reader-interest",
]

# Section header that marks the distribution block in the queue file
DISTRIBUTION_HEADER = "## Type Distribution"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update the Type Distribution section in a content-scout queue file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "queue_file",
        help="Path to the .content-scout-queue.md file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the new distribution section without writing to file.",
    )
    return parser.parse_args()


def count_types(text: str) -> dict[str, int]:
    """
    Count occurrences of each type from candidate entries in the queue.
    Looks for lines like:   - **type**: regulatory-explainer
    """
    counts: dict[str, int] = {t: 0 for t in VALID_TYPES}
    pattern = re.compile(
        r"^\s*-\s+\*\*type\*\*:\s*(\S+)\s*$",
        flags=re.MULTILINE | re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        found_type = match.group(1).strip()
        if found_type in counts:
            counts[found_type] += 1
        # Unknown types are silently ignored (not our job to validate here)
    return counts


def build_distribution_section(counts: dict[str, int]) -> str:
    """Build the markdown text for the ## Type Distribution section."""
    total = sum(counts.values())
    lines = [DISTRIBUTION_HEADER, ""]
    lines.append(f"_Last updated by update_type_distribution.py — {total} candidates total_")
    lines.append("")
    lines.append("| Type | Count |")
    lines.append("|------|-------|")
    for t in VALID_TYPES:
        lines.append(f"| {t} | {counts[t]} |")
    lines.append("")
    return "\n".join(lines)


def check_imbalance(counts: dict[str, int]) -> list[str]:
    """
    Return alert messages if any type has >= 3 entries while another has 0.
    """
    alerts: list[str] = []
    high_types = [t for t, c in counts.items() if c >= 3]
    zero_types = [t for t, c in counts.items() if c == 0]
    if high_types and zero_types:
        high_str = ", ".join(f"{t}({counts[t]})" for t in high_types)
        zero_str = ", ".join(zero_types)
        alerts.append(
            f"IMBALANCE ALERT: Types with >= 3 entries: {high_str} | "
            f"Types with 0 entries: {zero_str}"
        )
    return alerts


def replace_distribution_section(text: str, new_section: str) -> str:
    """
    Replace the existing ## Type Distribution section with new_section,
    or prepend new_section at the top if the section does not yet exist.
    """
    # Find the section and its end (next ## heading or end of file)
    pattern = re.compile(
        rf"^{re.escape(DISTRIBUTION_HEADER)}.*?(?=^##|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if match:
        return text[: match.start()] + new_section + text[match.end() :]
    # Section does not exist — prepend at top
    return new_section + "\n---\n\n" + text


def main() -> None:
    args = parse_args()
    queue_path = Path(args.queue_file)

    if not queue_path.exists():
        print(f"ERROR: Queue file not found: {queue_path}", file=sys.stderr)
        sys.exit(1)

    try:
        text = queue_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: Cannot read '{queue_path}': {exc}", file=sys.stderr)
        sys.exit(1)

    counts = count_types(text)
    new_section = build_distribution_section(counts)

    # Check for imbalance alerts and print to stderr
    alerts = check_imbalance(counts)
    for alert in alerts:
        print(alert, file=sys.stderr)

    if args.dry_run:
        print(new_section)
        sys.exit(0)

    updated_text = replace_distribution_section(text, new_section)

    try:
        queue_path.write_text(updated_text, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: Cannot write '{queue_path}': {exc}", file=sys.stderr)
        sys.exit(2)

    total = sum(counts.values())
    print(f"Updated: {queue_path.name} — {total} candidates, distribution recounted")
    for t in VALID_TYPES:
        if counts[t] > 0:
            print(f"  {t}: {counts[t]}")
    sys.exit(0)


if __name__ == "__main__":
    main()
