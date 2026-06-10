#!/usr/bin/env python3
"""Create the next Paper Stack markdown paper."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_DIR / "assets" / "paper-template.md"


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "untitled"


def next_id(papers_dir: Path) -> str:
    highest = 0
    for path in papers_dir.glob("PAPER-*.md"):
        match = re.match(r"PAPER-(\d{4})", path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"PAPER-{highest + 1:04d}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Paper Stack paper.")
    parser.add_argument("root", nargs="?", default=".paper-stack", help="Paper Stack root directory")
    parser.add_argument("--title", required=True, help="Paper title")
    parser.add_argument("--status", default="Draft", help="Initial paper status")
    args = parser.parse_args()

    root = Path(args.root)
    papers_dir = root / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)

    paper_id = next_id(papers_dir)
    today = dt.date.today().isoformat()
    title = args.title.strip()
    output = papers_dir / f"{paper_id}-{slugify(title)}.md"

    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("PAPER-0000", paper_id)
    text = text.replace("Untitled Paper", title)
    text = text.replace("status: Draft", f"status: {args.status}")
    text = text.replace("created: YYYY-MM-DD", f"created: {today}")
    text = text.replace("updated: YYYY-MM-DD", f"updated: {today}")

    output.write_text(text, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
