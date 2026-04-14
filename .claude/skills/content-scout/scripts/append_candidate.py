#!/usr/bin/env python3
"""
append_candidate.py — Append a validated candidate to the content-scout queue.

Auto-generates `id` (next integer) and `timestamp` (ISO 8601). Validates the
entry via validate_candidate.py before appending. Calls
update_type_distribution.py after a successful append.

Exit codes:
  0 — candidate appended successfully
  1 — missing required argument or queue file not found
  2 — validation failed (see stderr for details)

Usage:
  python append_candidate.py \\
    --queue door-site/.content-scout-queue.md \\
    --source-agent investigator-a \\
    --source-file "docs/aia-course/WTR-HSW-006.md#slide-22" \\
    --title "ADA Fire Door 5 lbf Exemption Explained" \\
    --type regulatory-explainer \\
    --keywords "ADA fire door, 5 lbf exemption, NFPA 80" \\
    --research-data "NFPA 80 Section 6.3.1.2 states..." \\
    --why-worth-writing "Architects frequently confuse the ADA opening force rule with fire door specs." \\
    --collector-notes "Appeared twice in Investigator A research segments"
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

VALID_TYPES = {
    "regulatory-explainer",
    "case-study",
    "product-comparison",
    "statistical-insight",
    "cost-comparison",
    "code-conflict",
    "scenario-guide",
    "reader-interest",
}

VALID_SOURCE_AGENTS = {
    "investigator-a",
    "investigator-b",
    "writer-a",
    "writer-b",
    "project-architect-advisor",
    "candidate-collector",
    "engagement-designer",
}

RESEARCH_DATA_MIN_CHARS = 200


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append a validated candidate to the content-scout queue file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--queue",
        default="door-site/.content-scout-queue.md",
        help="Path to the queue file (default: door-site/.content-scout-queue.md)",
    )
    parser.add_argument("--source-agent", required=True, help="One of the 7 authorized agent names")
    parser.add_argument("--source-file", required=True, help="File path with optional #anchor")
    parser.add_argument("--title", required=True, help="Candidate title (max 120 chars)")
    parser.add_argument(
        "--type",
        required=True,
        dest="candidate_type",
        help="One of the 8 valid type values",
    )
    parser.add_argument("--keywords", required=True, help="3-5 comma-separated keywords")
    parser.add_argument("--research-data", required=True, help="Raw research material (200+ chars)")
    parser.add_argument(
        "--why-worth-writing",
        required=True,
        help="2-sentence explanation of article value",
    )
    parser.add_argument(
        "--collector-notes",
        default=None,
        help="Optional descriptive notes (no prescriptive language)",
    )
    return parser.parse_args()


def get_next_id(queue_text: str) -> int:
    """Find the highest existing candidate id and return id + 1."""
    matches = re.findall(r"^\s*-\s+\*\*id\*\*:\s*(\d+)", queue_text, flags=re.MULTILINE)
    if not matches:
        return 1
    return max(int(m) for m in matches) + 1


def validate_inputs(args: argparse.Namespace) -> list[str]:
    """Validate all required inputs. Return list of error messages."""
    errors: list[str] = []

    if args.source_agent not in VALID_SOURCE_AGENTS:
        valid = ", ".join(sorted(VALID_SOURCE_AGENTS))
        errors.append(f"Invalid source-agent '{args.source_agent}'. Must be one of: {valid}")

    if len(args.title) > 120:
        errors.append(f"Title exceeds 120 characters ({len(args.title)} chars)")

    if args.candidate_type not in VALID_TYPES:
        valid = ", ".join(sorted(VALID_TYPES))
        errors.append(f"Invalid type '{args.candidate_type}'. Must be one of: {valid}")

    keyword_list = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if not (3 <= len(keyword_list) <= 5):
        errors.append(
            f"Keywords must be a comma-separated list of 3-5 items. Got {len(keyword_list)}."
        )

    return errors


def run_banned_word_lint(text: str) -> bool:
    """
    Run banned_word_lint.py on the given text.
    Returns True if clean, False if banned phrases found.
    Prints lint output to stderr transparently.
    """
    lint_script = SCRIPTS_DIR / "banned_word_lint.py"
    result = subprocess.run(
        [sys.executable, str(lint_script), "--text", text],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr, end="")
        return False
    return True


def run_validate_candidate(candidate_block: str) -> bool:
    """
    Run validate_candidate.py on the formatted candidate block.
    Returns True if valid, False if invalid.
    """
    validate_script = SCRIPTS_DIR / "validate_candidate.py"
    result = subprocess.run(
        [sys.executable, str(validate_script)],
        input=candidate_block,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr, end="")
        return False
    return True


def build_candidate_block(
    candidate_id: int,
    timestamp: str,
    args: argparse.Namespace,
) -> str:
    """Build the markdown candidate section string."""
    lines = [
        f"### Candidate #{candidate_id} — {args.title}",
        "",
        f"- **id**: {candidate_id}",
        f"- **timestamp**: {timestamp}",
        f"- **source-agent**: {args.source_agent}",
        f"- **source-file**: {args.source_file}",
        f"- **title**: {args.title}",
        f"- **type**: {args.candidate_type}",
        f"- **keywords**: {args.keywords}",
        f"- **research-data**: {args.research_data}",
        f"- **why-worth-writing**: {args.why_worth_writing}",
    ]
    if args.collector_notes:
        lines.append(f"- **collector-notes**: {args.collector_notes}")
    lines.append("")
    return "\n".join(lines)


def run_update_distribution(queue_path: str) -> None:
    """Run update_type_distribution.py on the queue file after appending."""
    update_script = SCRIPTS_DIR / "update_type_distribution.py"
    result = subprocess.run(
        [sys.executable, str(update_script), queue_path],
        capture_output=True,
        text=True,
    )
    # Print any imbalance alerts from stderr
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    if result.stdout:
        print(result.stdout, end="")


def main() -> None:
    args = parse_args()

    queue_path = Path(args.queue)
    if not queue_path.exists():
        print(
            f"ERROR: Queue file not found: {queue_path}\n"
            "Expected: door-site/.content-scout-queue.md (relative to cwd)\n"
            "Fix: ensure you are running from the waterson-ai-growth-system root, "
            "or that the queue file has been initialized.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate inputs before reading the queue
    input_errors = validate_inputs(args)
    if input_errors:
        for err in input_errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(2)

    # Lint collector_notes if provided
    if args.collector_notes:
        if not run_banned_word_lint(args.collector_notes):
            sys.exit(2)

    # Read current queue and determine next id
    queue_text = queue_path.read_text(encoding="utf-8")
    candidate_id = get_next_id(queue_text)
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")

    # Build the candidate block
    candidate_block = build_candidate_block(candidate_id, timestamp, args)

    # Validate the block through validate_candidate.py
    if not run_validate_candidate(candidate_block):
        print("ERROR: Candidate failed validation. Aborting append.", file=sys.stderr)
        sys.exit(2)

    # Warn if research_data is very short (likely a summary, not raw data)
    if len(args.research_data) < RESEARCH_DATA_MIN_CHARS:
        print(
            f"WARNING: research-data is {len(args.research_data)} characters — "
            "this looks like a summary rather than raw material. "
            "Consider expanding before the Blog Writer Fleet uses this candidate.",
            file=sys.stderr,
        )

    # Append to queue file
    with queue_path.open("a", encoding="utf-8") as fh:
        fh.write("\n---\n\n")
        fh.write(candidate_block)

    # Update type distribution
    run_update_distribution(str(queue_path))

    print(
        f"Candidate #{candidate_id} appended\n"
        f"  Title : {args.title}\n"
        f"  Type  : {args.candidate_type}\n"
        f"  Source: {args.source_agent} from {args.source_file}\n"
        f"  Queue : {queue_path}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
