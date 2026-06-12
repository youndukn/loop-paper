#!/usr/bin/env python3
"""Record the human's interaction-review decision on an interactive paper.

Papers containing live ```html blocks block the creation of the next paper
until the human was asked to review them; this records the answer.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from paper_html import INTERACTIVE_FENCE
from paperstack_common import (
    load_paper,
    paper_paths,
    replace_frontmatter,
    validate_iso_date,
    write_paper_text,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record interaction review on a paper.")
    parser.add_argument("--root", type=Path, default=Path(".paper-stack"))
    parser.add_argument("--paper", required=True, help="Paper ID (PAPER-NNNN)")
    parser.add_argument("--status", choices=("reviewed", "waived"), required=True)
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    args.date = validate_iso_date(args.date)

    path = next(
        (p for p in paper_paths(args.root) if p.name.startswith(args.paper + "-") or p.stem == args.paper),
        None,
    )
    if path is None:
        raise SystemExit(f"Unknown paper in stack: {args.paper}")
    paper = load_paper(path)
    if INTERACTIVE_FENCE not in paper["text"]:
        raise SystemExit(f"{args.paper} has no interactive content to acknowledge")
    metadata = dict(paper["metadata"])
    metadata["interaction_review"] = f"{args.status} {args.date}"
    write_paper_text(path, replace_frontmatter(paper["text"], metadata))
    print(f"{args.paper} interaction_review: {args.status} {args.date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
