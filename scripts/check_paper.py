#!/usr/bin/env python3
"""Check Paper Stack markdown files for required structure and gate issues."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from paperstack_common import has_explicit_human_acceptance


REQUIRED_SECTIONS = [
    "Abstract",
    "Hypothesis",
    "Prior Research",
    "References",
    "Implementation Plan",
    "Validation Plan",
    "Validation",
    "Agent Review",
    "Human Review",
    "Impact Score",
]

HUMAN_ONLY_PATTERNS = [
    re.compile(r"- \[x\].*human", re.IGNORECASE),
    re.compile(r"Decision:\s*(Accepted|Approved)", re.IGNORECASE),
]


def split_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[start:end].strip()
    return sections


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


def human_validation_block(validation: str) -> str:
    match = re.search(r"Human validation evidence:\s*(.*)$", validation, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else ""


def check_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    sections = split_sections(text)
    metadata = parse_frontmatter(text)
    missing = [section for section in REQUIRED_SECTIONS if section not in sections]
    empty = [
        section
        for section in REQUIRED_SECTIONS
        if section in sections and not sections[section].strip()
    ]
    warnings = []

    if metadata.get("status") == "Accepted":
        human_review = sections.get("Human Review", "")
        if not any(pattern.search(human_review) for pattern in HUMAN_ONLY_PATTERNS):
            warnings.append("Accepted status requires explicit checked human review evidence.")

    validation = sections.get("Validation", "")
    human_validation = human_validation_block(validation)
    if "- [x]" in human_validation.lower() and not has_explicit_human_acceptance(sections):
        warnings.append("Check human-required validation only after explicit human approval.")
    if "Not run" in validation and metadata.get("status") in {"AI Validated", "Human Review Required", "Accepted"}:
        warnings.append("Advanced status conflicts with validation evidence marked Not run.")

    return {
        "path": str(path),
        "paper_id": metadata.get("paper_id", path.stem.split("-")[0]),
        "title": metadata.get("title", path.stem),
        "status": metadata.get("status", "Draft"),
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
