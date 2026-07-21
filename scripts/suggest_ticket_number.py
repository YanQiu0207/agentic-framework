"""Suggest the next ticket number from archived Change directories."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ASCII_DIGITS_RE = re.compile(r"[0-9]+")


def suggest_ticket_number(archive_dir: Path) -> int:
    """Return one greater than the largest numeric directory prefix.

    Only direct child directories are considered. Directory names whose first
    hyphen-separated segment is not an ASCII integer are ignored.
    """
    if not archive_dir.is_dir():
        raise ValueError(f"archive directory does not exist: {archive_dir}")

    ticket_numbers = []
    for child in archive_dir.iterdir():
        if not child.is_dir():
            continue
        prefix = child.name.split("-", 1)[0]
        if ASCII_DIGITS_RE.fullmatch(prefix):
            ticket_numbers.append(int(prefix))

    return max(ticket_numbers, default=0) + 1


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Suggest the next ticket number from an archive directory."
    )
    parser.add_argument("archive_dir", type=Path, help="Archive directory to scan")
    return parser.parse_args()


def main() -> int:
    """Run the ticket number suggestion command."""
    args = parse_args()
    try:
        suggestion = suggest_ticket_number(args.archive_dir)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(suggestion)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
