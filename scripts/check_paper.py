#!/usr/bin/env python3
"""Check Paper Stack markdown files for required structure and gate issues."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from paperstack_common import (
    REQUIRED_SECTIONS,
    STATUSES,
    parse_frontmatter,
    split_sections,
)


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

    return {
        "path": str(path),
        "paper_id": metadata.get("paper_id", path.stem.split("-")[0]),
        "title": metadata.get("title", path.stem),
        "status": status,
        "missing_sections": missing,
        "empty_sections": empty,
        "warnings": warnings,
        "ok": not missing and not empty and not warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Paper Stack papers.")
    parser.add_argument("target", nargs="?", default=".paper-stack", help="Paper file or Paper Stack root")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    target = Path(args.target)
    if target.is_dir():
        paper_paths = sorted((target / "papers").glob("PAPER-*.md"))
    else:
        paper_paths = [target]

    results = [check_file(path) for path in paper_paths]
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
