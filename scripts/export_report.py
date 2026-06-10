#!/usr/bin/env python3
"""Export a deterministic Markdown report for Paper Stack progress."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from check_paper import require_valid_stack
from paperstack_common import (
    STATUSES,
    load_paper,
    markdown_table_cell,
    paper_paths,
    unchecked_count,
    write_text_output,
)


def load_impact_scores(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    if not path.is_file():
        raise SystemExit(f"Expected impact scores JSON file, got directory: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"impact scores JSON is invalid: {error.msg}") from error
    if not isinstance(raw, dict):
        raise SystemExit("impact scores JSON must be an object")
    papers = raw.get("papers", [])
    if not isinstance(papers, list):
        raise SystemExit("impact scores JSON field 'papers' must be a list")

    impact_by_id: dict[str, dict] = {}
    for index, item in enumerate(papers, start=1):
        if not isinstance(item, dict):
            raise SystemExit(f"impact score paper item {index} must be an object")
        paper_id = item.get("paper_id")
        if not isinstance(paper_id, str) or not paper_id:
            raise SystemExit(f"impact score paper item {index} missing paper_id")
        impact_by_id[paper_id] = item
    return impact_by_id


def render_report(root: Path) -> str:
    require_valid_stack(root)
    papers = [load_paper(path) for path in paper_paths(root)]
    counts = Counter(paper["status"] for paper in papers)
    impact_by_id = load_impact_scores(root / "dashboard" / "impact-scores.json")

    lines = ["# Paper Stack Report", ""]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total papers: {len(papers)}")
    for status in STATUSES:
        lines.append(f"- {status}: {counts.get(status, 0)}")
    lines.append("")
    lines.append("## Papers")
    lines.append("")
    lines.append("| Paper | Status | Open gates | Deterministic impact |")
    lines.append("| --- | --- | ---: | ---: |")
    for paper in papers:
        item = impact_by_id.get(paper["paper_id"], {})
        score = markdown_table_cell(item.get("deterministic_partial_score", "TBD"))
        paper_label = markdown_table_cell(f"{paper['paper_id']} {paper['title']}")
        status = markdown_table_cell(paper["status"])
        lines.append(f"| {paper_label} | {status} | {unchecked_count(paper['text'])} | {score} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Paper Stack Markdown report.")
    parser.add_argument("root", nargs="?", default=".paper-stack", help="Paper Stack root")
    parser.add_argument("--output", help="Output Markdown path")
    args = parser.parse_args()

    root = Path(args.root)
    output = Path(args.output) if args.output else root / "dashboard" / "report.md"
    write_text_output(output, render_report(root))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
