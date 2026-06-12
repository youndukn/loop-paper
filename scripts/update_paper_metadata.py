#!/usr/bin/env python3
"""Synchronize Paper Stack frontmatter with deterministic paper contents."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from check_paper import check_file, check_paths, relationship_targets, result_details
from paperstack_common import (
    load_paper,
    write_paper_text,
    paper_paths,
    paper_root_from_path,
    replace_frontmatter,
    require_paper_file,
    today,
)


REPAIRABLE_WARNINGS = {
    "Missing paper_id frontmatter",
    "Missing title frontmatter",
    "Missing status frontmatter",
    "Missing created frontmatter",
    "Missing updated frontmatter",
    "Missing impact_score frontmatter",
    "Missing paper_kind frontmatter",
    "Missing closed_loop_schema frontmatter",
}
REVIEW_SECTION_NAMES = {"Per-Target Verdicts", "Cross-Paper Findings"}


def title_from_heading(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    if not match:
        return fallback
    heading = match.group(1).strip()
    paper_match = re.match(r"^PAPER-\d{4}(?:\s+|$)", heading)
    if not paper_match:
        return heading
    title = heading[paper_match.end() :].strip()
    if not title:
        raise SystemExit("Top-level paper heading is missing a visible title")
    return title


def is_repairable_warning(message: str) -> bool:
    return (
        message in REPAIRABLE_WARNINGS
    ) or (
        message.startswith("heading title ") and message.endswith(" does not match title frontmatter")
    )


def is_inferable_review_metadata(paper: dict) -> bool:
    metadata = paper["metadata"]
    kind = metadata.get("paper_kind")
    if kind and kind != "review":
        return False
    return bool(metadata.get("review_targets") or REVIEW_SECTION_NAMES & set(paper["sections"]))


def repair_blockers(result: dict, paper: dict) -> list[str]:
    blockers: list[str] = []
    can_infer_review = is_inferable_review_metadata(paper)
    for detail in result_details(result):
        if is_repairable_warning(detail):
            continue
        if detail in {
            "review_targets requires paper_kind: review",
            "Missing review_targets for review paper",
        } and can_infer_review:
            continue
        blockers.append(detail)
    return blockers


def infer_paper_kind(metadata: dict[str, str], sections: dict[str, str]) -> str:
    if metadata.get("paper_kind"):
        return metadata["paper_kind"]
    if metadata.get("review_targets") or REVIEW_SECTION_NAMES & set(sections):
        return "review"
    return "closed_loop"


def infer_review_targets(text: str) -> str:
    targets = relationship_targets(text, "References")
    if not targets:
        raise SystemExit("Cannot repair missing review_targets for review paper: References has no targets")
    return ", ".join(targets)


def require_syncable_file(path: Path) -> None:
    require_paper_file(path)
    paper = load_paper(path)
    if path.parent.name == "papers":
        root = paper_root_from_path(path)
        results = check_paths(paper_paths(root), validate_relationships=True)
        result = next((item for item in results if Path(item["path"]) == path), None)
        if result is None:
            raise SystemExit(f"Paper is not under a recognized papers directory: {path}")
    else:
        result = check_file(path)
    blocking = repair_blockers(result, paper)
    if blocking:
        raise SystemExit("Paper structure check failed: " + "; ".join(blocking))


def sync_file(path: Path, write: bool) -> dict:
    require_syncable_file(path)
    paper = load_paper(path)
    original = dict(paper["metadata"])
    metadata = dict(original)
    metadata["paper_id"] = paper["paper_id"]
    metadata["title"] = title_from_heading(paper["text"], paper["title"])
    metadata.setdefault("status", paper["status"])
    metadata.setdefault("created", today())
    metadata.setdefault("updated", today())
    metadata.setdefault("owners", "[]")
    metadata.setdefault("reviewers", "[]")
    metadata.setdefault("impact_score", "TBD")
    metadata.setdefault("closed_loop_schema", "paper_closed_loop.v1")
    metadata["paper_kind"] = infer_paper_kind(metadata, paper["sections"])
    if metadata["paper_kind"] == "review" and not metadata.get("review_targets"):
        metadata["review_targets"] = infer_review_targets(paper["text"])

    def without_updated(data: dict) -> dict:
        return {key: value for key, value in data.items() if key != "updated"}

    if without_updated(metadata) != without_updated(original):
        metadata["updated"] = today()

    changed = metadata != original
    if write and changed:
        write_paper_text(path, replace_frontmatter(paper["text"], metadata))
    return {"path": str(path), "paper_id": metadata["paper_id"], "changed": changed}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Paper Stack frontmatter.")
    parser.add_argument("target", nargs="?", default=".paper-stack", help="Paper Stack root or paper .md file")
    parser.add_argument("--check", action="store_true", help="Fail if metadata would change")
    args = parser.parse_args()

    target = Path(args.target)
    paths = [target] if target.is_file() or target.suffix == ".md" else paper_paths(target)
    results = [sync_file(path, write=not args.check) for path in paths]
    for result in results:
        status = "CHANGED" if result["changed"] else "OK"
        print(f"{status} {result['paper_id']} {result['path']}")
    return 1 if args.check and any(result["changed"] for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
