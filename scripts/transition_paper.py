#!/usr/bin/env python3
"""Deterministically transition a Paper Stack paper between allowed states."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from check_closed_loop_paper import prior_research_errors, validate_paper
from check_paper import check_file, check_paths, result_details
from paperstack_common import (
    ALLOWED_TRANSITIONS,
    REQUIRED_SECTIONS,
    STATUSES,
    extract_relations,
    load_paper,
    paper_id_from_path,
    paper_paths,
    read_paper_text,
    write_paper_text,
    paper_root_from_path,
    replace_frontmatter,
    section_has_checked,
    today,
    validation_not_run,
)


BEFORE_PHASE_TARGETS = {"Plan Ready", "Implementing", "Implemented"}
AFTER_PHASE_TARGETS = {"AI Validated", "Accepted"}
FORCE_FORBIDDEN_TARGETS = {"AI Validated", "Accepted"}
RESEARCH_READY_TARGETS = {"Research Ready", "Plan Ready", "Implementing", "Implemented", "AI Validated", "Accepted"}


def structural_errors(paper: dict) -> list[str]:
    errors = []
    current_path = Path(paper["path"])
    if current_path.parent.name != "papers":
        structural = check_file(current_path)
        if not structural["ok"]:
            errors.append("Paper structure check failed: " + "; ".join(result_details(structural)))
        return errors

    root = paper_root_from_path(current_path)
    stack_results = check_paths(paper_paths(root), validate_relationships=True)
    structural = next(
        (result for result in stack_results if Path(result["path"]) == current_path),
        None,
    )
    if structural is None:
        errors.append(f"Paper is not under a recognized papers directory: {current_path}")
        structural = {"ok": True, "missing_sections": [], "empty_sections": [], "warnings": []}
    if not structural["ok"]:
        errors.append("Paper structure check failed: " + "; ".join(result_details(structural)))
    return errors


def gate_errors(paper: dict, target: str) -> list[str]:
    sections = paper["sections"]
    errors = []
    missing = [section for section in REQUIRED_SECTIONS if section not in sections or not sections[section].strip()]
    if target not in {"Draft", "Rejected", "Superseded"} and missing:
        errors.append("Missing or empty required sections: " + ", ".join(missing))
    if target in RESEARCH_READY_TARGETS:
        prior = sections.get("Prior Research", "")
        refs = sections.get("References", "")
        errors.extend(prior_research_errors(sections))
        if "BEFORE_REQUIRED" in prior or "BEFORE_REQUIRED" in refs:
            errors.append("Research Ready requires Prior Research and References placeholders to be resolved")
    if target in {"Plan Ready", "Implementing", "Implemented", "AI Validated", "Accepted"}:
        if not section_has_checked(sections.get("Implementation Plan", "")):
            errors.append("Implementation Plan has no checked gate")
        if not section_has_checked(sections.get("Validation Plan", "")):
            errors.append("Validation Plan has no checked gate")
    if target in {"AI Validated", "Accepted"}:
        if validation_not_run(sections):
            errors.append("Validation still says Not run")
        if not section_has_checked(sections.get("Validation", "")):
            errors.append("Validation has no checked evidence gate")
    if target in BEFORE_PHASE_TARGETS:
        errors.extend(validate_paper(Path(paper["path"]), "before"))
    if target in AFTER_PHASE_TARGETS:
        errors.extend(validate_paper(Path(paper["path"]), "after"))
    if target == "Rejected":
        errors.extend(validate_paper(Path(paper["path"]), "rejected"))
    if target == "Superseded":
        errors.extend(inbound_supersedes_errors(paper))
    return errors


def inbound_supersedes_errors(paper: dict) -> list[str]:
    path = Path(paper["path"])
    if path.parent.name != "papers":
        return []
    paper_id = paper["paper_id"]
    for other in paper_paths(paper_root_from_path(path)):
        if other == path:
            continue
        relations = extract_relations(
            read_paper_text(other), paper_id_from_path(other)
        )
        if paper_id in relations["supersedes"]:
            return []
    return [f"Superseded requires another paper declaring Supersedes: {paper_id}"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Transition a Paper Stack paper status.")
    parser.add_argument("paper", help="Path to PAPER-*.html")
    parser.add_argument("status", choices=STATUSES, help="Target status")
    parser.add_argument("--force", action="store_true", help="Bypass gate checks, but still require valid status")
    args = parser.parse_args()

    path = Path(args.paper)
    paper = load_paper(path)
    current = paper["status"]
    target = args.status
    if args.force and target != current and target in FORCE_FORBIDDEN_TARGETS:
        print(f"FAIL --force cannot bypass gates into {target}", file=sys.stderr)
        return 1
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target != current and target not in allowed and not args.force:
        print(f"FAIL invalid transition: {current} -> {target}", file=sys.stderr)
        return 1

    structure_failures = structural_errors(paper)
    if structure_failures:
        for error in structure_failures:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    errors = gate_errors(paper, target)
    if errors and not args.force:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    metadata = dict(paper["metadata"])
    metadata["paper_id"] = paper["paper_id"]
    metadata["title"] = paper["title"]
    metadata["status"] = target
    metadata["updated"] = today()
    write_paper_text(path, replace_frontmatter(paper["text"], metadata))
    print(f"{paper['paper_id']} {current} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
