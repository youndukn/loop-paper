#!/usr/bin/env python3
"""Record or refresh the Agent Review section on a Paper Stack paper."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from check_paper import check_file, check_paths
from paperstack_common import (
    STATUSES,
    load_paper,
    markdown_inline,
    paper_paths,
    paper_root_from_path,
    replace_frontmatter,
    require_paper_file,
    today,
)


DEFAULT_SECTION = """## Agent Review

Agent reviewer:
Review date:
Decision: Pending
Notes:

- [ ] Agent reviewed paper structure
- [ ] Agent confirmed evidence backs the recorded verdict

"""


def ensure_section(text: str) -> str:
    if re.search(r"^## Agent Review\s*$", text, flags=re.MULTILINE):
        return text
    marker = re.search(r"^## Impact Score\s*$", text, flags=re.MULTILINE)
    if not marker:
        return text.rstrip() + "\n\n" + DEFAULT_SECTION
    return text[: marker.start()] + DEFAULT_SECTION + text[marker.start() :]


def replace_section(text: str, reviewer: str, decision: str, notes: str) -> str:
    text = ensure_section(text)
    reviewer = markdown_inline(reviewer)
    decision = markdown_inline(decision)
    notes = markdown_inline(notes)
    section = f"""## Agent Review

Agent reviewer: {reviewer}
Review date: {today()}
Decision: {decision}
Notes: {notes}

- [x] Agent reviewed paper structure
- [x] Agent confirmed evidence backs the recorded verdict

"""
    pattern = r"^## Agent Review\s*\n.*?(?=^## |\Z)"
    return re.sub(pattern, section, text, count=1, flags=re.MULTILINE | re.DOTALL)


def require_reviewable_file(path: Path) -> None:
    require_paper_file(path)
    if path.parent.name == "papers":
        root = paper_root_from_path(path)
        results = check_paths(paper_paths(root), validate_relationships=True)
        result = next((item for item in results if Path(item["path"]) == path), None)
        if result is None:
            raise SystemExit(f"Paper is not under a recognized papers directory: {path}")
    else:
        result = check_file(path)
    blocking = []
    for key in ("missing_sections", "empty_sections", "warnings"):
        for detail in result[key]:
            if key in {"missing_sections", "empty_sections"} and detail == "Agent Review":
                continue
            blocking.append(detail)
    if blocking:
        raise SystemExit("Paper structure check failed: " + "; ".join(blocking))


def main() -> int:
    parser = argparse.ArgumentParser(description="Record an agent review on a Paper Stack paper.")
    parser.add_argument("paper", help="Path to PAPER-*.md")
    parser.add_argument("--reviewer", default="Codex", help="Agent reviewer name")
    parser.add_argument(
        "--decision",
        choices=STATUSES,
        default="AI Validated",
        help="Agent review decision",
    )
    parser.add_argument("--notes", default="Structure reviewed; paper remains on the autonomous loop.", help="Review notes")
    args = parser.parse_args()

    path = Path(args.paper)
    require_reviewable_file(path)
    paper = load_paper(path)
    updated = replace_section(paper["text"], args.reviewer, args.decision, args.notes)
    metadata = dict(paper["metadata"])
    metadata["updated"] = today()
    path.write_text(replace_frontmatter(updated, metadata), encoding="utf-8")
    print(f"{paper['paper_id']} agent review recorded by {args.reviewer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
