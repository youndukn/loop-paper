#!/usr/bin/env python3
"""Validate that human-only Paper Stack gates have explicit human evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from paperstack_common import (
    has_explicit_human_acceptance,
    load_paper,
    paper_paths,
    paper_root_from_path,
    verify_human_review_password,
)


def validate(path: Path) -> dict:
    paper = load_paper(path)
    sections = paper["sections"]
    human_review = sections.get("Human Review", "")
    validation = sections.get("Validation", "")
    issues = []
    root = paper_root_from_path(path)
    password_verified, verification_message = verify_human_review_password(root, paper)
    if re.search(r"- \[x\].*human", validation, flags=re.IGNORECASE) and not has_explicit_human_acceptance(sections):
        issues.append("Human validation is checked without explicit human review evidence.")
    if paper["status"] == "Accepted" and not has_explicit_human_acceptance(sections):
        issues.append("Accepted status requires explicit human reviewer, date, decision, checked human review, and password verification.")
    if has_explicit_human_acceptance(sections) and not password_verified:
        issues.append(verification_message)
    if re.search(r"Human grade:[^\S\r\n]*(?!TBD|\r?$)\S+", sections.get("Impact Score", ""), flags=re.IGNORECASE | re.MULTILINE):
        if not has_explicit_human_acceptance(sections):
            issues.append("Human grade is present without explicit human review evidence.")
    return {
        "path": str(path),
        "paper_id": paper["paper_id"],
        "title": paper["title"],
        "issues": issues,
        "ok": not issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate human-only Paper Stack gates.")
    parser.add_argument("target", nargs="?", default=".paper-stack", help="Paper Stack root or paper file")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    target = Path(args.target)
    paths = paper_paths(target) if target.is_dir() else [target]
    results = [validate(path) for path in paths]
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for result in results:
            status = "OK" if result["ok"] else "FAIL"
            print(f"{status} {result['paper_id']} {result['title']}")
            for issue in result["issues"]:
                print(f"  - {issue}")
    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
