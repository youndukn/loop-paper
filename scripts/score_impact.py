#!/usr/bin/env python3
"""Calculate deterministic evidence-based impact score components."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from index_references import build_graph
from paperstack_common import load_paper, paper_paths, section_has_checked, validation_not_run, write_text_output


def downstream_score(count: int) -> int:
    if count <= 0:
        return 0
    if count == 1:
        return 3
    if count <= 3:
        return 6
    return 10


def validation_score(paper: dict) -> int:
    sections = paper["sections"]
    validation = sections.get("Validation", "")
    if validation_not_run(sections):
        return 0
    if re.search(r"(test|metric|screenshot|log|evidence|passed)", validation, flags=re.IGNORECASE):
        return 6 if section_has_checked(validation) else 3
    return 3 if section_has_checked(validation) else 0


def partial_score(components: list[int | str]) -> float | str:
    known = [component for component in components if isinstance(component, int)]
    if not known:
        return "TBD"
    return round(sum(known) / len(known), 2)


def score(root: Path) -> dict:
    graph = build_graph(root)
    inbound = graph["inbound_counts"]
    results = []
    for path in paper_paths(root):
        paper = load_paper(path)
        downstream = downstream_score(inbound.get(paper["paper_id"], 0))
        validation = validation_score(paper)
        measured = "TBD"
        components = [downstream, validation, measured]
        results.append(
            {
                "paper_id": paper["paper_id"],
                "title": paper["title"],
                "declared_impact_score": paper["metadata"].get("impact_score", "TBD"),
                "deterministic_partial_score": partial_score(components),
                "components": {
                    "downstream_reference_score": downstream,
                    "validation_strength_score": validation,
                    "measured_outcome_score": measured,
                },
                "reason": "Measured outcomes remain TBD unless supplied as concrete evidence in the paper body.",
            }
        )
    return {"papers": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Score deterministic impact components.")
    parser.add_argument("root", nargs="?", default=".paper-stack", help="Paper Stack root")
    parser.add_argument("--output", help="Output JSON path")
    args = parser.parse_args()

    root = Path(args.root)
    result = score(root)
    output = Path(args.output) if args.output else root / "dashboard" / "impact-scores.json"
    write_text_output(output, json.dumps(result, indent=2))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
