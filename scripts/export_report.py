#!/usr/bin/env python3
"""Export a deterministic Markdown report for Paper Stack progress."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from check_paper import require_valid_stack
from paperstack_common import STATUSES, load_paper, paper_paths, unchecked_count, write_text_output


def load_json(path: Path, default: dict) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def render_report(root: Path) -> str:
    require_valid_stack(root)
    papers = [load_paper(path) for path in paper_paths(root)]
    counts = Counter(paper["status"] for paper in papers)
    impact = load_json(root / "dashboard" / "impact-scores.json", {"papers": []})
    impact_by_id = {item["paper_id"]: item for item in impact.get("papers", [])}

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
        score = item.get("deterministic_partial_score", "TBD")
        lines.append(f"| {paper['paper_id']} {paper['title']} | {paper['status']} | {unchecked_count(paper['text'])} | {score} |")
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
