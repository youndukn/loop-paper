#!/usr/bin/env python3
"""Check Paper Stack markdown files for required structure and gate issues."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from paperstack_common import (
    RELATION_LABELS,
    REQUIRED_SECTIONS,
    STATUSES,
    extract_relations,
    parse_frontmatter,
    paper_paths,
    relation_key,
    split_sections,
)


PAPER_ID_RE = re.compile(r"^PAPER-\d{4}$")


def paper_id_from_filename(path: Path) -> str | None:
    match = re.search(r"PAPER-\d{4}", path.name)
    return match.group(0) if match else None


def check_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    sections = split_sections(text)
    metadata, _ = parse_frontmatter(text)
    missing = [section for section in REQUIRED_SECTIONS if section not in sections]
    empty = [
        section
        for section in REQUIRED_SECTIONS
        if section in sections and not sections[section].strip()
    ]
    warnings = []

    validation = sections.get("Validation", "")
    if "Not run" in validation and metadata.get("status") in {"AI Validated", "Accepted"}:
        warnings.append("Advanced status conflicts with validation evidence marked Not run.")
    status = metadata.get("status", "Draft")
    if status not in STATUSES:
        warnings.append(f"Invalid status: {status}")
    filename_id = paper_id_from_filename(path)
    declared_id = metadata.get("paper_id")
    if not filename_id:
        warnings.append("Filename must contain canonical PAPER-NNNN ID")
    if not declared_id:
        warnings.append("Missing paper_id frontmatter")
    elif not PAPER_ID_RE.fullmatch(declared_id):
        warnings.append(f"Invalid paper_id: {declared_id}")
    elif filename_id and declared_id != filename_id:
        warnings.append(f"paper_id {declared_id} does not match filename {filename_id}")

    return {
        "path": str(path),
        "paper_id": declared_id or path.stem.split("-")[0],
        "title": metadata.get("title", path.stem),
        "status": status,
        "missing_sections": missing,
        "empty_sections": empty,
        "warnings": warnings,
        "ok": not missing and not empty and not warnings,
    }


def check_paths(paths: list[Path], *, validate_relationships: bool = False) -> list[dict]:
    results = [check_file(path) for path in paths]
    if not validate_relationships:
        return results

    known_ids = {
        result["paper_id"]
        for result in results
        if PAPER_ID_RE.fullmatch(result["paper_id"])
    }
    by_path = {result["path"]: result for result in results}
    for path in paths:
        result = by_path[str(path)]
        text = path.read_text(encoding="utf-8")
        relations = extract_relations(text, result["paper_id"])
        for label in RELATION_LABELS:
            key = relation_key(label)
            for target in relations[key]:
                if target not in known_ids:
                    result["warnings"].append(f"Dangling relationship target: {label} -> {target}")
        result["ok"] = (
            not result["missing_sections"]
            and not result["empty_sections"]
            and not result["warnings"]
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Paper Stack papers.")
    parser.add_argument("target", nargs="?", default=".paper-stack", help="Paper file or Paper Stack root")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    target = Path(args.target)
    if target.is_dir():
        paths = paper_paths(target)
        validate_relationships = True
    else:
        paths = [target]
        validate_relationships = False

    results = check_paths(paths, validate_relationships=validate_relationships)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for result in results:
            status = "OK" if result["ok"] else "FAIL"
            print(f"{status} {result['paper_id']} {result['title']} ({result['status']})")
            for key in ("missing_sections", "empty_sections", "warnings"):
                for item in result[key]:
                    print(f"  - {key}: {item}")

    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
