#!/usr/bin/env python3
"""
validate_candidate.py — Validate a content-scout candidate entry.

Reads a markdown block from stdin or a file and checks that all 9 required
fields are present and that the `type` field is one of the 8 allowed values.

Exit codes:
  0 — valid
  2 — invalid (error description written to stderr)

Usage:
  echo "### Candidate #1 ..." | python validate_candidate.py
  python validate_candidate.py candidate_block.md
  python validate_candidate.py --help
"""

import argparse
import re
import sys

REQUIRED_FIELDS = [
    "id",
    "source-agent",
    "source-file",
    "title",
    "type",
    "keywords",
    "research-data",
    "why-worth-writing",
    "timestamp",
]

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a content-scout candidate markdown block.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to a markdown file containing the candidate block. "
        "If omitted, reads from stdin.",
    )
    return parser.parse_args()


def read_input(file_path: str | None) -> str:
    """Read content from a file path or stdin."""
    if file_path:
        try:
            with open(file_path, encoding="utf-8") as fh:
                return fh.read()
        except OSError as exc:
            print(f"ERROR: Cannot read file '{file_path}': {exc}", file=sys.stderr)
            sys.exit(2)
    return sys.stdin.read()


def extract_field_value(text: str, field: str) -> str | None:
    """
    Extract the value of a markdown list field like:
      - **id**: 3
      - **source-agent**: investigator-a
    Returns the stripped value string, or None if the field is not found.
    """
    pattern = rf"^\s*-\s+\*\*{re.escape(field)}\*\*:\s*(.+)$"
    match = re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def validate(text: str) -> list[str]:
    """
    Validate the candidate block. Returns a list of error strings.
    An empty list means the candidate is valid.
    """
    errors: list[str] = []

    # Check all required fields are present and non-empty
    for field in REQUIRED_FIELDS:
        value = extract_field_value(text, field)
        if value is None:
            errors.append(f"Missing required field: '{field}'")
        elif not value:
            errors.append(f"Field '{field}' is present but has no value")

    # Check type is one of the 8 allowed values
    type_value = extract_field_value(text, "type")
    if type_value is not None and type_value not in VALID_TYPES:
        valid_list = ", ".join(sorted(VALID_TYPES))
        errors.append(
            f"Invalid type '{type_value}'. "
            f"Must be one of: {valid_list}"
        )

    return errors


def main() -> None:
    args = parse_args()
    text = read_input(args.file)
    errors = validate(text)

    if errors:
        for error in errors:
            print(f"INVALID: {error}", file=sys.stderr)
        sys.exit(2)

    print("VALID: candidate passes all field checks")
    sys.exit(0)


if __name__ == "__main__":
    main()
