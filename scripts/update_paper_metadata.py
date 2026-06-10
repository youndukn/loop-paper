#!/usr/bin/env python3
"""Synchronize Paper Stack frontmatter with deterministic paper contents."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from paperstack_common import load_paper, paper_paths, replace_frontmatter, today


def title_from_heading(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(PAPER-\d{4}\s+)?(.+?)\s*$", text, flags=re.MULTILINE)
    return match.group(2).strip() if match else fallback


def sync_file(path: Path, write: bool) -> dict:
    paper = load_paper(path)
    metadata = dict(paper["metadata"])
    metadata["paper_id"] = paper["paper_id"]
    metadata["title"] = title_from_heading(paper["text"], paper["title"])
    metadata.setdefault("status", paper["status"])
    metadata.setdefault("created", today())
    metadata["updated"] = today()
    metadata.setdefault("owners", "[]")
    metadata.setdefault("reviewers", "[]")
    metadata.setdefault("impact_score", "TBD")

    changed = metadata != paper["metadata"]
    if write and changed:
        path.write_text(replace_frontmatter(paper["text"], metadata), encoding="utf-8")
    return {"path": str(path), "paper_id": metadata["paper_id"], "changed": changed}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Paper Stack frontmatter.")
    parser.add_argument("target", nargs="?", default=".paper-stack", help="Paper Stack root or paper file")
    parser.add_argument("--check", action="store_true", help="Fail if metadata would change")
    args = parser.parse_args()

    target = Path(args.target)
    paths = paper_paths(target) if target.is_dir() else [target]
    results = [sync_file(path, write=not args.check) for path in paths]
    for result in results:
        status = "CHANGED" if result["changed"] else "OK"
        print(f"{status} {result['paper_id']} {result['path']}")
    return 1 if args.check and any(result["changed"] for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
