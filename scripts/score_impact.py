#!/usr/bin/env python3
"""Calculate deterministic evidence-based impact score components."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from index_references import build_graph
from paperstack_common import (
    load_paper,
    paper_paths,
    refuse_papers_directory_output,
    section_has_checked,
    validation_not_run,
    write_text_output,
)


COMPONENT_WEIGHTS = {
    "downstream_reference_score": 0.33,
    "validation_strength_score": 0.33,
    "measured_outcome_score": 0.34,
}
MEASURED_OUTCOME_RE = re.compile(
    r"^-\s+Measured outcome:\s*(?P<value>.*?)\s*$",
    flags=re.MULTILINE,
)
EXPLICIT_SCORE_RE = re.compile(
    r"(?:^|[\s;,(])(?:score|measured_outcome_score)\s*[:=]\s*(?P<named>10(?:\.0+)?|[0-9](?:\.\d+)?)\s*(?:/10)?\b"
    r"|(?:^|[\s;,(])(?P<fraction>10(?:\.0+)?|[0-9](?:\.\d+)?)\s*/\s*10\b",
    flags=re.IGNORECASE,
)


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


def measured_outcome_score(paper: dict) -> float | str:
    impact = paper["sections"].get("Impact Score", "")
    match = MEASURED_OUTCOME_RE.search(impact)
    if not match:
        return "TBD"
    value = match.group("value").strip()
    if not value or "TBD" in value.upper():
        return "TBD"
    score_match = EXPLICIT_SCORE_RE.search(value)
    if not score_match:
        return "TBD"
    raw_score = score_match.group("named") or score_match.group("fraction")
    score = float(raw_score)
    if not 0 <= score <= 10:
        return "TBD"
    return int(score) if score.is_integer() else round(score, 2)


def is_numeric_score(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def weighted_score(components: dict[str, int | float | str], *, require_complete: bool) -> float | str:
    if require_complete and any(not is_numeric_score(value) for value in components.values()):
        return "TBD"
    known_total = sum(
        value * COMPONENT_WEIGHTS[name]
        for name, value in components.items()
        if is_numeric_score(value)
    )
    return round(known_total, 2)


def score(root: Path) -> dict:
    graph = build_graph(root)
    inbound = graph["inbound_counts"]
    results = []
    for path in paper_paths(root):
        paper = load_paper(path)
        downstream = downstream_score(inbound.get(paper["paper_id"], 0))
        validation = validation_score(paper)
        measured = measured_outcome_score(paper)
        components = {
            "downstream_reference_score": downstream,
            "validation_strength_score": validation,
            "measured_outcome_score": measured,
        }
        reason = (
            "Measured outcome score parsed from explicit 0-10 evidence in the paper body."
            if is_numeric_score(measured)
            else "Measured outcomes remain TBD unless supplied as an explicit 0-10 score in the paper body."
        )
        results.append(
            {
                "paper_id": paper["paper_id"],
                "title": paper["title"],
                "declared_impact_score": paper["metadata"].get("impact_score", "TBD"),
                "deterministic_score": weighted_score(components, require_complete=True),
                "deterministic_partial_score": weighted_score(components, require_complete=False),
                "formula": "0.33*downstream_reference_score + 0.33*validation_strength_score + 0.34*measured_outcome_score",
                "components": components,
                "reason": reason,
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
    refuse_papers_directory_output(root, output, label="output")
    write_text_output(output, json.dumps(result, indent=2))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
