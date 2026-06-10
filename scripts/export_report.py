#!/usr/bin/env python3
"""Export a deterministic Markdown report for Paper Stack progress."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from check_paper import require_valid_stack, valid_paper_id
from paperstack_common import (
    STATUSES,
    load_paper,
    markdown_table_cell,
    paper_paths,
    refuse_papers_directory_output,
    unchecked_count,
    write_text_output,
)


def is_score_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 10


def validate_impact_score_item(item: dict, *, index: int) -> None:
    if "deterministic_score" not in item:
        raise SystemExit(f"impact score paper item {index} missing deterministic_score")
    score = item["deterministic_score"]
    if score != "TBD" and not is_score_number(score):
        raise SystemExit(
            f"impact score paper item {index} deterministic_score must be TBD or a number from 0 to 10"
        )
    if "deterministic_partial_score" not in item:
        raise SystemExit(f"impact score paper item {index} missing deterministic_partial_score")
    partial_score = item["deterministic_partial_score"]
    if not is_score_number(partial_score):
        raise SystemExit(
            f"impact score paper item {index} deterministic_partial_score must be a number from 0 to 10"
        )


def load_impact_scores(path: Path, known_ids: set[str]) -> dict[str, dict]:
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
        if not valid_paper_id(paper_id):
            raise SystemExit(f"impact score paper item {index} has invalid paper_id: {paper_id}")
        if paper_id not in known_ids:
            raise SystemExit(f"impact score references unknown paper_id: {paper_id}")
        if paper_id in impact_by_id:
            raise SystemExit(f"duplicate impact score paper_id: {paper_id}")
        validate_impact_score_item(item, index=index)
        impact_by_id[paper_id] = item
    missing = sorted(known_ids - set(impact_by_id))
    if missing:
        raise SystemExit("impact scores missing current paper_id: " + ", ".join(missing))
    return impact_by_id


def render_report(root: Path) -> str:
    require_valid_stack(root)
    papers = [load_paper(path) for path in paper_paths(root)]
    counts = Counter(paper["status"] for paper in papers)
    known_ids = {paper["paper_id"] for paper in papers}
    impact_by_id = load_impact_scores(root / "dashboard" / "impact-scores.json", known_ids)

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
        score = item.get("deterministic_score", "TBD")
        if score == "TBD" and "deterministic_partial_score" in item:
            score = f"TBD (partial {item['deterministic_partial_score']})"
        score = markdown_table_cell(score)
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
    refuse_papers_directory_output(root, output, label="output")
    write_text_output(output, render_report(root))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
