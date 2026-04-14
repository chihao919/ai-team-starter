#!/usr/bin/env python3
"""
banned_word_lint.py — Lint collector_notes for prescriptive language.

Scans text content (or a file) for banned phrases that indicate prescriptive
rather than descriptive writing. The collector_notes field should describe
observable facts about a candidate, not recommendations about priority.

Exit codes:
  0 — clean (no banned phrases found)
  2 — banned phrase found (exact match written to stderr)

Usage:
  echo "這個主題出現 3 次" | python banned_word_lint.py
  python banned_word_lint.py notes.txt
  python banned_word_lint.py --text "we should write this article"
  python banned_word_lint.py --help
"""

import argparse
import re
import sys

# Banned phrases: prescriptive language that tells the reader what to do
# rather than describing facts about the candidate
BANNED_PHRASES = [
    # Chinese prescriptive phrases
    "建議",
    "應該",
    "最好",
    "推薦",
    "可以考慮",
    "值得優先",
    "優先寫",
    "必須寫",
    # English prescriptive phrases
    "we should",
    "should write",
    "recommend writing",
    "priority",
    "must write",
    "best to write",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lint collector_notes text for banned prescriptive phrases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "file",
        nargs="?",
        help="Path to a text file to lint. If omitted and --text not set, reads from stdin.",
    )
    group.add_argument(
        "--text",
        help="Inline text string to lint (alternative to file or stdin).",
    )
    return parser.parse_args()


def read_input(args: argparse.Namespace) -> str:
    """Read content from --text flag, file argument, or stdin."""
    if args.text is not None:
        return args.text
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as fh:
                return fh.read()
        except OSError as exc:
            print(f"ERROR: Cannot read file '{args.file}': {exc}", file=sys.stderr)
            sys.exit(2)
    return sys.stdin.read()


def find_banned_phrases(text: str) -> list[tuple[str, int]]:
    """
    Search for all banned phrases (case-insensitive).
    Returns a list of (phrase, position) tuples for each match found.
    """
    matches: list[tuple[str, int]] = []
    text_lower = text.lower()
    for phrase in BANNED_PHRASES:
        phrase_lower = phrase.lower()
        start = 0
        while True:
            pos = text_lower.find(phrase_lower, start)
            if pos == -1:
                break
            matches.append((phrase, pos))
            start = pos + 1
    # Sort by position so output is in reading order
    matches.sort(key=lambda x: x[1])
    return matches


def format_context(text: str, position: int, window: int = 40) -> str:
    """Return a short excerpt around the match position for context."""
    start = max(0, position - window)
    end = min(len(text), position + window)
    excerpt = text[start:end].replace("\n", " ")
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(text):
        excerpt = excerpt + "..."
    return excerpt


def main() -> None:
    args = parse_args()
    text = read_input(args)
    matches = find_banned_phrases(text)

    if not matches:
        print("CLEAN: no banned phrases found in collector_notes")
        sys.exit(0)

    for phrase, position in matches:
        context = format_context(text, position)
        print(
            f"BANNED PHRASE: '{phrase}' at position {position}\n"
            f"  Context: {context}\n"
            f"  Hint: collector_notes should be descriptive, not prescriptive.\n"
            f"  Use: 'appeared N times', 'accumulated N segments', "
            f"'only case-study so far' — not priority judgments.",
            file=sys.stderr,
        )

    sys.exit(2)


if __name__ == "__main__":
    main()
