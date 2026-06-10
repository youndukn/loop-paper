#!/usr/bin/env python3
"""Check Paper Stack markdown files for required structure and gate issues."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from paperstack_common import (
    RELATION_LABELS,
    REQUIRED_SECTIONS,
    STATUSES,
    find_ids,
    frontmatter_bounds,
    parse_frontmatter,
    paper_paths,
    paper_id_from_path,
    require_paper_file,
    split_sections,
    validate_iso_date,
)


PAPER_ID_RE = re.compile(r"^PAPER-(\d{4})$")
PAPERISH_RE = re.compile(r"(?<![A-Za-z0-9_-])PAPER-[A-Za-z0-9_-]+(?![A-Za-z0-9_-])")
EXPECTED_SCHEMA = "paper_closed_loop.v1"
ALLOWED_PAPER_KINDS = {"closed_loop", "review"}


def valid_paper_id(value: str) -> bool:
    match = PAPER_ID_RE.fullmatch(value)
    return bool(match and int(match.group(1)) > 0)


def paper_id_from_filename(path: Path) -> str | None:
    value = paper_id_from_path(path)
    return value if valid_paper_id(value) else None


def parse_review_targets(value: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    targets = [item.strip() for item in value.split(",") if item.strip()]
    if not targets:
        return [], ["Missing review_targets for review paper"]

    seen: set[str] = set()
    normalized: list[str] = []
    for target in targets:
        if not valid_paper_id(target):
            errors.append(f"Invalid review_targets entry: {target}")
            continue
        if target in seen:
            errors.append(f"Duplicate review target: {target}")
            continue
        seen.add(target)
        normalized.append(target)
    return normalized, errors


def frontmatter_warnings(text: str) -> list[str]:
    if not text.startswith("---\n"):
        return ["Missing YAML frontmatter"]
    bounds = frontmatter_bounds(text)
    if bounds is None:
        return ["Unterminated YAML frontmatter"]
    start, end = bounds

    warnings: list[str] = []
    seen: set[str] = set()
    for index, line in enumerate(text[start:end].splitlines(), start=1):
        if not line.strip():
            continue
        if ":" not in line:
            warnings.append(f"Malformed frontmatter line {index}: missing ':'")
            continue
        key, _value = line.split(":", 1)
        key = key.strip()
        if not key:
            warnings.append(f"Malformed frontmatter line {index}: empty key")
            continue
        if key in seen:
            warnings.append(f"Duplicate frontmatter key: {key}")
        seen.add(key)
    return warnings


def section_warnings(text: str) -> list[str]:
    counts = Counter(
        match.group(1).strip()
        for match in re.finditer(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE)
    )
    return [
        f"Duplicate section: {name}"
        for name, count in sorted(counts.items())
        if count > 1
    ]


def heading_warnings(text: str, expected_id: str | None, expected_title: str | None) -> list[str]:
    headings = [
        match.group(1).strip()
        for match in re.finditer(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    ]
    if not headings:
        return ["Missing top-level paper heading"]

    warnings: list[str] = []
    if len(headings) > 1:
        warnings.append("Duplicate top-level paper heading")

    first = headings[0]
    match = re.match(r"^(PAPER-\d{4})(?:\s+|$)", first)
    if not match:
        warnings.append("Top-level paper heading must start with PAPER-NNNN")
        return warnings

    if expected_id and match.group(1) != expected_id:
        warnings.append(f"heading paper_id {match.group(1)} does not match {expected_id}")
    heading_title = first[match.end() :].strip()
    if expected_title and heading_title != expected_title:
        warnings.append(f"heading title {heading_title!r} does not match title frontmatter")
    return warnings


def check_file(path: Path) -> dict:
    require_paper_file(path)
    text = path.read_text(encoding="utf-8")
    sections = split_sections(text)
    metadata, _ = parse_frontmatter(text)
    missing = [section for section in REQUIRED_SECTIONS if section not in sections]
    empty = [
        section
        for section in REQUIRED_SECTIONS
        if section in sections and not sections[section].strip()
    ]
    warnings = frontmatter_warnings(text) + section_warnings(text)

    validation = sections.get("Validation", "")
    if "Not run" in validation and metadata.get("status") in {"AI Validated", "Accepted"}:
        warnings.append("Advanced status conflicts with validation evidence marked Not run.")
    status = metadata.get("status", "")
    if not status:
        warnings.append("Missing status frontmatter")
    elif status not in STATUSES:
        warnings.append(f"Invalid status: {status}")
    if not metadata.get("title"):
        warnings.append("Missing title frontmatter")
    schema = metadata.get("closed_loop_schema")
    if not schema:
        warnings.append(f"Missing closed_loop_schema frontmatter")
    elif schema != EXPECTED_SCHEMA:
        warnings.append(f"Invalid closed_loop_schema: {schema}")
    paper_kind = metadata.get("paper_kind", "closed_loop")
    review_targets: list[str] = []
    if paper_kind not in ALLOWED_PAPER_KINDS:
        warnings.append(f"Invalid paper_kind: {paper_kind}")
    elif paper_kind == "review":
        review_targets, target_errors = parse_review_targets(metadata.get("review_targets", ""))
        warnings.extend(target_errors)
    elif metadata.get("review_targets"):
        warnings.append("review_targets requires paper_kind: review")
    for date_key in ("created", "updated"):
        value = metadata.get(date_key)
        if not value:
            warnings.append(f"Missing {date_key} frontmatter")
            continue
        try:
            validate_iso_date(value, label=date_key)
        except SystemExit as error:
            warnings.append(str(error))
    filename_id = paper_id_from_filename(path)
    declared_id = metadata.get("paper_id")
    if not filename_id:
        warnings.append("Filename must contain canonical PAPER-NNNN ID")
    if not declared_id:
        warnings.append("Missing paper_id frontmatter")
    elif not valid_paper_id(declared_id):
        warnings.append(f"Invalid paper_id: {declared_id}")
    elif filename_id and declared_id != filename_id:
        warnings.append(f"paper_id {declared_id} does not match filename {filename_id}")
    expected_heading_id = declared_id if declared_id and valid_paper_id(declared_id) else filename_id
    warnings.extend(heading_warnings(text, expected_heading_id, metadata.get("title")))

    return {
        "path": str(path),
        "paper_id": declared_id or path.stem.split("-")[0],
        "title": metadata.get("title", path.stem),
        "status": status,
        "paper_kind": paper_kind,
        "review_targets": review_targets,
        "missing_sections": missing,
        "empty_sections": empty,
        "warnings": warnings,
        "ok": not missing and not empty and not warnings,
    }


def result_details(result: dict) -> list[str]:
    details: list[str] = []
    for key in ("missing_sections", "empty_sections", "warnings"):
        details.extend(result[key])
    return details


def require_valid_file(path: Path) -> dict:
    result = check_file(path)
    if not result["ok"]:
        raise SystemExit("Paper structure check failed: " + "; ".join(result_details(result)))
    return result


def require_valid_stack(root: Path) -> list[dict]:
    results = check_paths(paper_paths(root), validate_relationships=True)
    failures = []
    for result in results:
        if not result["ok"]:
            failures.append(f"{result['paper_id']} {result['path']}: {'; '.join(result_details(result))}")
    if failures:
        raise SystemExit("Paper stack check failed:\n" + "\n".join(failures))
    return results


def check_paths(paths: list[Path], *, validate_relationships: bool = False) -> list[dict]:
    results = [check_file(path) for path in paths]
    if not validate_relationships:
        return results

    known_ids = {
        result["paper_id"]
        for result in results
        if valid_paper_id(result["paper_id"])
    }
    counts = Counter(
        result["paper_id"]
        for result in results
        if valid_paper_id(result["paper_id"])
    )
    by_path = {result["path"]: result for result in results}
    for path in paths:
        result = by_path[str(path)]
        if counts[result["paper_id"]] > 1:
            result["warnings"].append(f"Duplicate paper_id in stack: {result['paper_id']}")
        text = path.read_text(encoding="utf-8")
        for label in RELATION_LABELS:
            for match in re.finditer(rf"^{re.escape(label)}:\s*(.*)$", text, flags=re.MULTILINE):
                for target in PAPERISH_RE.findall(match.group(1)):
                    if not valid_paper_id(target):
                        result["warnings"].append(f"Invalid relationship target: {label} -> {target}")
                for target in find_ids(match.group(1)):
                    if target == result["paper_id"]:
                        result["warnings"].append(f"Self relationship target: {label} -> {target}")
                    elif target not in known_ids:
                        result["warnings"].append(f"Dangling relationship target: {label} -> {target}")
        if result.get("paper_kind") == "review":
            for target in result.get("review_targets", []):
                if target == result["paper_id"]:
                    result["warnings"].append(f"Review paper cannot target itself: {target}")
                elif target not in known_ids:
                    result["warnings"].append(f"Dangling review target: {target}")
        result["ok"] = (
            not result["missing_sections"]
            and not result["empty_sections"]
            and not result["warnings"]
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Paper Stack papers.")
    parser.add_argument("target", nargs="?", default=".paper-stack", help="Paper .md file or Paper Stack root")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    target = Path(args.target)
    if target.is_file() or target.suffix == ".md":
        paths = [target]
        validate_relationships = False
    else:
        paths = paper_paths(target)
        validate_relationships = True

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
